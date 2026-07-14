import datetime as dt
import json
import textwrap
from pathlib import Path
from typing import Any, Callable
import yaml

from engine.utils import read_text, write_text, load_yaml, resolve_path
from engine.openai_client import call_openai, get_openai_options
from engine.parser import parse_stage_response, build_context_package, estimate_tokens, truncate_words

from engine.learning import (
    build_learning_prompt,
    build_tuning_prompt,
    build_offline_learning_report,
    build_offline_tuning_suggestions,
)

LlmClient = Callable[[str, dict[str, Any], str | None], str]

def build_dry_run_response(step_id: str, skill_path: Path, model: str) -> str:
    if step_id == "editor_agent":
        artifact = (
            "## Edited Blog\n\n"
            f"[DRY RUN] Would call OpenAI for step `{step_id}` using {skill_path} "
            f"with model `{model}`.\n\n"
            "## Edit Log\n\n"
            "- [DRY RUN] Would record minimum edits, reader friction, root causes, "
            "and expected reader effects."
        )
    else:
        artifact = f"[DRY RUN] Would call OpenAI for step `{step_id}` using {skill_path} with model `{model}`."

    return (
        "## Artifact\n\n"
        f"{artifact}\n\n"
        "## Handoff\n\n"
        f"[DRY RUN HANDOFF] Compact context for `{step_id}` that would be passed to downstream stages."
    )

def build_step_prompt(
    workflow: dict[str, Any],
    step: dict[str, Any],
    skill: dict[str, Any],
    author_input: str,
    context_package: dict[str, dict[str, str]],
) -> str:
    handoff_block = "\n\n".join(
        f"### {name}\n\n{content}"
        for name, content in context_package.get("handoffs", {}).items()
    )
    artifact_block = "\n\n".join(
        f"### {name}\n\n{content}"
        for name, content in context_package.get("artifacts", {}).items()
    )
    handoff_block = handoff_block or "No handoffs selected for this step."
    artifact_block = artifact_block or "No full artifacts selected for this step."

    return textwrap.dedent(
        f"""
        You are running one step of an automated reflective blog workflow.

        Workflow name: {workflow.get("name")}
        Workflow description: {workflow.get("description")}

        Current step:
        - id: {step.get("id")}
        - purpose: {step.get("purpose")}
        - expected output file: {step.get("output")}
        - expected handoff file: {step.get("handoff_output")}

        Skill YAML:
        ```yaml
        {yaml.safe_dump(skill, allow_unicode=True, sort_keys=False)}
        ```

        Author input:
        ```markdown
        {author_input}
        ```

        Compact handoffs selected by context_policy:
        ```markdown
        {handoff_block}
        ```

        Full artifacts selected by context_policy:
        ```markdown
        {artifact_block}
        ```

        Instructions:
        - Follow the Skill YAML strictly.
        - Produce exactly two top-level sections: `## Artifact` and `## Handoff`.
        - `## Artifact` is the full output for this step's expected output file.
        - `## Handoff` is a compact structured summary for downstream agents.
        - Keep `## Handoff` around 120-250 Vietnamese words, roughly 200-400 tokens.
        - Do not mention that you are an AI.
        - Do not include hidden reasoning or process notes.
        - Keep the writing language Vietnamese unless the author explicitly requests another language.
        """
    ).strip()

def build_run_dir(log_root: Path, input_markdown: str) -> Path:
    from engine.parser import slugify, extract_title
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = slugify(extract_title(input_markdown))
    return log_root / f"{timestamp}_{slug}"

def append_run_log(log_file: Path, title: str, body: str) -> None:
    existing = read_text(log_file) if log_file.exists() else ""
    separator = "\n\n" if existing else ""
    write_text(log_file, f"{existing}{separator}# {title}\n\n{body.strip()}\n")

def extract_markdown_section(markdown: str, heading: str) -> str | None:
    import re

    pattern = rf"(?ims)^##+\s*{re.escape(heading)}\s*$\s*(.*?)(?=^##+\s+|\Z)"
    match = re.search(pattern, markdown)
    return match.group(1).strip() if match else None

def derive_artifact_file_contents(skill: dict[str, Any], artifact: str) -> dict[str, str]:
    output = skill.get("output", {})
    primary_name = str(output.get("name") or "artifact.md")
    secondary_name = output.get("secondary_name")

    contents = {primary_name: artifact}
    if secondary_name:
        edited_blog = (
            extract_markdown_section(artifact, "Edited Blog")
            or extract_markdown_section(artifact, "edited_blog")
            or extract_markdown_section(artifact, "Edited Draft")
            or artifact
        )
        edit_log = (
            extract_markdown_section(artifact, "Edit Log")
            or extract_markdown_section(artifact, "edit_log")
            or "Edit log section was not found in the artifact."
        )
        if edited_blog == artifact:
            import warnings
            warnings.warn(
                f"Could not split artifact into primary/secondary files. "
                f"Falling back to full artifact for {primary_name}.",
                UserWarning,
                stacklevel=2,
            )
        contents[primary_name] = edited_blog
        contents[str(secondary_name)] = edit_log
    return contents

def run_workflow(config_path: Path, input_path: Path, dry_run: bool = False, llm_client: "LlmClient | None" = None) -> Path:
    if llm_client is None:
        llm_client = call_openai

    config = load_yaml(config_path)
    workflow_file = resolve_path(config.get("workflow", {}).get("file", "flow/write_blog.yaml"))
    workflow = load_yaml(workflow_file)
    author_input = read_text(input_path)

    log_root = resolve_path(config.get("workflow", {}).get("log_dir", "runs"))
    run_dir = build_run_dir(log_root, author_input)
    log_file = run_dir / "run_log.md"
    write_text(run_dir / "input.md", author_input)
    write_text(
        run_dir / "metadata.json",
        json.dumps(
            {
                "created_at": dt.datetime.now().isoformat(timespec="seconds"),
                "config_file": str(config_path),
                "workflow_file": str(workflow_file),
                "input_file": str(input_path),
                "default_model": get_openai_options(config).get("model"),
                "stage_models": {
                    str(step["id"]): get_openai_options(config, str(step["id"])).get("model")
                    for step in workflow.get("steps", [])
                },
                "endpoint": config.get("openai", {}).get("endpoint"),
                "dry_run": dry_run,
                "provider": getattr(llm_client, "__name__", "unknown").replace("call_", ""),
            },
            ensure_ascii=False,
            indent=2,
        ),
    )

    append_run_log(log_file, "Run Metadata", read_text(run_dir / "metadata.json"))
    append_run_log(log_file, "Author Input", author_input)

    artifacts: dict[str, str] = {}
    handoffs: dict[str, str] = {}
    step_outputs: dict[str, dict[str, Any]] = {}
    step_context_metrics: dict[str, dict[str, Any]] = {}
    save_step_files = bool(config.get("runtime", {}).get("save_step_files", True))
    stop_on_error = bool(config.get("workflow", {}).get("stop_on_error", True))

    for index, step in enumerate(workflow.get("steps", []), start=1):
        step_id = str(step["id"])
        skill_path = resolve_path(step["skill"])
        skill = load_yaml(skill_path)
        context_package = build_context_package(step, artifacts, handoffs)
        prompt = build_step_prompt(workflow, step, skill, author_input, context_package)
        selected_handoff_tokens = sum(
            estimate_tokens(content) for content in context_package["handoffs"].values()
        )
        selected_artifact_tokens = sum(
            estimate_tokens(content) for content in context_package["artifacts"].values()
        )

        try:
            raw_output = (
                build_dry_run_response(
                    step_id,
                    skill_path,
                    str(get_openai_options(config, step_id).get("model")),
                )
                if dry_run
                else llm_client(prompt, config, step_id)
            )
            artifact, handoff, handoff_used_fallback = parse_stage_response(raw_output)
        except Exception as exc:
            artifact = f"ERROR in step `{step_id}`:\n\n{exc}"
            handoff = truncate_words(artifact)
            handoff_used_fallback = True
            append_run_log(log_file, f"{index}. {step_id}", artifact)
            if stop_on_error:
                raise

        artifacts[step_id] = artifact
        handoffs[step_id] = handoff
        artifact_tokens = estimate_tokens(artifact)
        handoff_tokens = estimate_tokens(handoff)
        step_outputs[step_id] = {
            "artifact": artifact,
            "handoff": handoff,
            "artifact_file": str(step.get("output") or f"{step_id}.md"),
            "handoff_file": str(step.get("handoff_output") or f"{step_id}_handoff.md"),
            "secondary_artifact_file": skill.get("output", {}).get("secondary_name"),
            "handoff_used_fallback": handoff_used_fallback,
            "metrics": {
                "artifact_estimated_tokens": artifact_tokens,
                "handoff_estimated_tokens": handoff_tokens,
                "handoff_savings_estimated_tokens": max(0, artifact_tokens - handoff_tokens),
                "selected_input_handoff_estimated_tokens": selected_handoff_tokens,
                "selected_input_artifact_estimated_tokens": selected_artifact_tokens,
            },
        }
        step_context_metrics[step_id] = step_outputs[step_id]["metrics"]
        append_run_log(log_file, f"{index}. {step_id} Artifact", artifact)
        append_run_log(
            run_dir / "handoff_log.md",
            f"{index}. {step_id} Handoff",
            handoff,
        )

        if save_step_files:
            output_name = str(step.get("output") or f"{step_id}.md")
            handoff_name = str(step.get("handoff_output") or f"{step_id}_handoff.md")
            artifact_files = derive_artifact_file_contents(skill, artifact)
            if output_name not in artifact_files:
                artifact_files[output_name] = artifact
            for artifact_file, artifact_content in artifact_files.items():
                write_text(run_dir / artifact_file, artifact_content)
            write_text(run_dir / handoff_name, handoff)

    write_text(
        run_dir / "step_outputs.json",
        json.dumps(step_outputs, ensure_ascii=False, indent=2),
    )
    metadata = json.loads(read_text(run_dir / "metadata.json"))
    metadata["context_strategy"] = "artifact_plus_handoff"
    metadata["step_context_metrics"] = step_context_metrics
    metadata["total_artifact_estimated_tokens"] = sum(
        item["metrics"]["artifact_estimated_tokens"] for item in step_outputs.values()
    )
    metadata["total_handoff_estimated_tokens"] = sum(
        item["metrics"]["handoff_estimated_tokens"] for item in step_outputs.values()
    )
    write_text(run_dir / "metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
    return run_dir

def load_step_outputs_from_run(run_dir: Path, workflow: dict[str, Any]) -> dict[str, str]:
    json_path = run_dir / "step_outputs.json"
    if json_path.exists():
        data = json.loads(read_text(json_path))
        if isinstance(data, dict):
            return {
                str(key): str(value.get("artifact", "")) if isinstance(value, dict) else str(value)
                for key, value in data.items()
            }

    outputs: dict[str, str] = {}
    for step in workflow.get("steps", []):
        step_id = str(step["id"])
        output_name = str(step.get("output") or f"{step_id}.md")
        output_path = run_dir / output_name
        if output_path.exists():
            outputs[step_id] = read_text(output_path)
    return outputs

def load_workflow_skills(workflow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    skills: dict[str, dict[str, Any]] = {}
    for step in workflow.get("steps", []):
        step_id = str(step["id"])
        skills[step_id] = load_yaml(resolve_path(step["skill"]))
    skills["editorial_learning"] = load_yaml(resolve_path("skills/editorial_learning.yaml"))
    return skills

def run_learning_loop(
    config_path: Path,
    run_dir: Path,
    production_path: Path | None = None,
    dry_run: bool = False,
    offline: bool = False,
    llm_client: "LlmClient | None" = None,
) -> Path:
    if llm_client is None:
        llm_client = call_openai

    config = load_yaml(config_path)
    workflow_file = resolve_path(config.get("workflow", {}).get("file", "flow/write_blog.yaml"))
    workflow = load_yaml(workflow_file)

    if production_path is None:
        production_path = run_dir / "production_blog.md"
    if not production_path.exists():
        raise FileNotFoundError(
            f"Production blog not found: {production_path}. "
            "Create it from final_blog.md or pass --production."
        )

    final_output = workflow.get("final_output", {})
    final_file = str(
        final_output.get("human_final")
        or final_output.get("file")
        or final_output.get("primary_ai_draft")
        or "final_blog.md"
    )
    final_path = run_dir / final_file
    if not final_path.exists():
        primary_ai_draft = final_output.get("primary_ai_draft")
        if primary_ai_draft and (run_dir / str(primary_ai_draft)).exists():
            final_path = run_dir / str(primary_ai_draft)
        else:
            raise FileNotFoundError(
                f"Final blog not found: {final_path}. Create final_blog.md "
                "or configure final_output.primary_ai_draft to an existing file."
            )

    input_path = run_dir / "input.md"
    if not input_path.exists():
        raise FileNotFoundError(f"Original input not found: {input_path}")

    author_input = read_text(input_path)
    final_blog = read_text(final_path)
    comparison_label = final_path.name
    production_blog = read_text(production_path)
    step_outputs = load_step_outputs_from_run(run_dir, workflow)
    skills = load_workflow_skills(workflow)

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    learning_dir = run_dir / "learning" / timestamp
    write_text(learning_dir / "production_blog.md", production_blog)
    write_text(
        learning_dir / "metadata.json",
        json.dumps(
            {
                "created_at": dt.datetime.now().isoformat(timespec="seconds"),
                "config_file": str(config_path),
                "workflow_file": str(workflow_file),
                "source_run_dir": str(run_dir),
                "production_file": str(production_path),
                "learning_models": {
                    "editorial_learning": get_openai_options(config, "editorial_learning").get("model"),
                    "workflow_tuning": get_openai_options(config, "workflow_tuning").get("model"),
                },
                "endpoint": config.get("openai", {}).get("endpoint"),
                "dry_run": dry_run,
                "offline": offline,
                "provider": getattr(llm_client, "__name__", "unknown").replace("call_", ""),
            },
            ensure_ascii=False,
            indent=2,
        ),
    )

    if offline:
        report = build_offline_learning_report(
            final_blog,
            production_blog,
            step_outputs,
            comparison_label=comparison_label,
        )
        tuning_suggestions = build_offline_tuning_suggestions(report)
    else:
        prompt = build_learning_prompt(
            workflow=workflow,
            skills=skills,
            author_input=author_input,
            step_outputs=step_outputs,
            final_blog=final_blog,
            production_blog=production_blog,
            comparison_label=comparison_label,
        )
        report = (
            "[DRY RUN] Would call OpenAI for editorial learning using production_blog.md "
            f"with model `{get_openai_options(config, 'editorial_learning').get('model')}`."
            if dry_run
            else llm_client(prompt, config, "editorial_learning")
        )
        tuning_suggestions = (
            "[DRY RUN] Would call OpenAI to extract workflow tuning suggestions "
            f"with model `{get_openai_options(config, 'workflow_tuning').get('model')}`."
            if dry_run
            else llm_client(
                build_tuning_prompt(report),
                config,
                "workflow_tuning",
            )
        )

    write_text(learning_dir / "editorial_learning_report.md", report)
    write_text(learning_dir / "workflow_tuning_suggestions.md", tuning_suggestions)
    append_run_log(learning_dir / "learning_log.md", "Learning Metadata", read_text(learning_dir / "metadata.json"))
    append_run_log(learning_dir / "learning_log.md", "Editorial Learning Report", report)
    append_run_log(learning_dir / "learning_log.md", "Workflow Tuning Suggestions", tuning_suggestions)
    return learning_dir
