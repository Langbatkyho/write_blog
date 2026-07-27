from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Callable

from engine.learning import (
    build_learning_prompt,
    build_offline_learning_report,
    build_offline_tuning_suggestions,
    build_tuning_prompt,
)
from engine.openai_client import call_openai, get_openai_options
from engine.style_manager import validate_style_contract
from engine.utils import load_yaml, read_text
from engine.workflow_artifacts import append_run_log
from engine.workflow_contracts import LearningRunResult, WorkflowDefinition
from engine.workflow_persistence import (
    atomic_write_json,
    atomic_write_text,
    resolve_relative_path,
)
from engine.workflow_resolution import (
    load_workflow_skills,
    resolve_workflow_file,
)


LlmClient = Callable[[str, dict[str, Any], str | None], str]
VALID_RUN_SOURCES = {
    "user",
    "test",
    "dry_run",
    "ui",
    "cli",
    "agent_validation",
}


def _stage_api_capable(
    llm_client: LlmClient,
    config: dict[str, Any],
    stage_id: str,
) -> bool:
    if hasattr(llm_client, "describe_stage"):
        descriptor = llm_client.describe_stage(stage_id, config)
        return bool(descriptor.get("api_capable", True))
    return bool(getattr(llm_client, "api_capable", True))


def load_step_outputs_from_run(
    run_dir: Path, workflow: dict[str, Any]
) -> dict[str, str]:
    definition = WorkflowDefinition.from_dict(workflow)
    valid_stage_ids = set(definition.stage_ids)
    json_path = run_dir / "step_outputs.json"
    if json_path.exists():
        data = json.loads(read_text(json_path))
        if isinstance(data, dict):
            return {
                str(key): (
                    str(value.get("artifact", ""))
                    if isinstance(value, dict)
                    else str(value)
                )
                for key, value in data.items()
                if str(key) in valid_stage_ids
                and (
                    not isinstance(value, dict)
                    or value.get("status", "completed") == "completed"
                )
            }
    outputs: dict[str, str] = {}
    for step in definition.steps:
        step_id = step.id
        output_path = resolve_relative_path(
            run_dir,
            step.output,
            field_name=f"{step_id}.output",
        )
        if output_path.exists():
            outputs[step_id] = read_text(output_path)
    return outputs


def run_learning_loop(
    config_path: Path,
    run_dir: Path,
    production_path: Path | None = None,
    dry_run: bool = False,
    offline: bool = False,
    llm_client: LlmClient | None = None,
    style: str | None = None,
    mode: str | None = None,
    *,
    persist: bool | None = None,
    output_root: Path | None = None,
    run_source: str | None = None,
) -> Path | LearningRunResult:
    llm_client = llm_client or call_openai
    should_persist = (not dry_run) if persist is None else persist
    source = run_source or ("dry_run" if dry_run else "user")
    if source not in VALID_RUN_SOURCES:
        raise ValueError(f"run_source không hợp lệ: {source}")
    if dry_run and should_persist and output_root is None:
        raise ValueError(
            "Learning dry-run chỉ được persist khi truyền output_root tạm."
        )
    config = load_yaml(config_path)
    metadata_path = run_dir / "metadata.json"
    if metadata_path.exists():
        source_metadata = json.loads(read_text(metadata_path))
        style = style or source_metadata.get("style", "reflective")
        mode = mode or source_metadata.get("mode", "deep")
    else:
        style = style or "reflective"
        mode = mode or "deep"

    workflow_file = resolve_workflow_file(config, mode)
    workflow = load_yaml(workflow_file)
    definition = WorkflowDefinition.from_dict(workflow, expected_mode=mode)
    style = validate_style_contract(mode, style, workflow_file)
    production_path = production_path or resolve_relative_path(
        run_dir,
        "production_blog.md",
        field_name="production output",
    )
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
    final_path = resolve_relative_path(
        run_dir,
        final_file,
        field_name="final output",
    )
    if not final_path.exists():
        primary = final_output.get("primary_ai_draft")
        primary_path = (
            resolve_relative_path(
                run_dir,
                str(primary),
                field_name="primary AI draft",
            )
            if primary
            else None
        )
        if primary_path and primary_path.exists():
            final_path = primary_path
        else:
            raise FileNotFoundError(f"Final blog not found: {final_path}")
    input_path = run_dir / "input.md"
    if not input_path.exists():
        raise FileNotFoundError(f"Original input not found: {input_path}")

    author_input = read_text(input_path)
    final_blog = read_text(final_path)
    production_blog = read_text(production_path)
    step_outputs = load_step_outputs_from_run(run_dir, workflow)
    skills = load_workflow_skills(workflow, style, mode)
    stage_ids = definition.stage_ids
    api_attempted = False
    api_called = False
    if offline:
        report = build_offline_learning_report(
            final_blog,
            production_blog,
            step_outputs,
            comparison_label=final_path.name,
            mode=mode,
        )
        tuning_suggestions = build_offline_tuning_suggestions(
            report, mode=mode, stage_ids=stage_ids
        )
    else:
        prompt = build_learning_prompt(
            workflow=workflow,
            skills=skills,
            author_input=author_input,
            step_outputs=step_outputs,
            final_blog=final_blog,
            production_blog=production_blog,
            comparison_label=final_path.name,
            mode=mode,
        )
        if dry_run:
            report = (
                "[DRY RUN] Would call provider for editorial diagnostic with "
                f"model `{get_openai_options(config, 'editorial_learning').get('model')}`."
            )
            tuning_suggestions = (
                "[DRY RUN] Would call provider for workflow tuning suggestions "
                f"with model `{get_openai_options(config, 'workflow_tuning').get('model')}`."
            )
        else:
            report_api_capable = _stage_api_capable(
                llm_client, config, "editorial_learning"
            )
            api_attempted = api_attempted or report_api_capable
            report = llm_client(prompt, config, "editorial_learning")
            api_called = api_called or report_api_capable
            tuning_api_capable = _stage_api_capable(
                llm_client, config, "workflow_tuning"
            )
            api_attempted = api_attempted or tuning_api_capable
            tuning_suggestions = llm_client(
                build_tuning_prompt(report, mode=mode, stage_ids=stage_ids),
                config,
                "workflow_tuning",
            )
            api_called = api_called or tuning_api_capable

    metadata = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "config_file": str(config_path),
        "workflow_file": str(workflow_file),
        "source_run_dir": str(run_dir),
        "production_file": str(production_path),
        "dry_run": dry_run,
        "offline": offline,
        "run_source": source,
        "persisted": should_persist,
        "api_attempted": api_attempted,
        "api_called": api_called,
        "status": "completed" if should_persist else "preview",
        "provider": getattr(llm_client, "provider_name", None)
        or getattr(llm_client, "__name__", "unknown").replace("call_", ""),
        "client_map": getattr(llm_client, "client_map", None),
        "style": style,
        "mode": mode,
    }
    if not should_persist:
        return LearningRunResult(
            report=report,
            tuning_suggestions=tuning_suggestions,
            mode=mode,
            style=style,
            persisted=False,
            api_attempted=api_attempted,
            api_called=api_called,
            run_source=source,
        )

    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    learning_root = (
        output_root.resolve()
        if output_root is not None
        else run_dir / "learning" / mode
    )
    learning_dir = learning_root / timestamp
    learning_dir.mkdir(parents=True, exist_ok=False)
    report_name = f"{mode}_blog_patterns.md"
    atomic_write_text(learning_dir / "production_blog.md", production_blog)
    atomic_write_text(learning_dir / report_name, report)
    atomic_write_text(
        learning_dir / "workflow_tuning_suggestions.md", tuning_suggestions
    )
    atomic_write_json(learning_dir / "metadata.json", metadata)
    append_run_log(
        learning_dir / "learning_log.md",
        "Learning Metadata",
        json.dumps(metadata, ensure_ascii=False, indent=2),
    )
    append_run_log(
        learning_dir / "learning_log.md",
        f"{mode.title()} Diagnostic Report",
        report,
    )
    append_run_log(
        learning_dir / "learning_log.md",
        "Workflow Tuning Suggestions",
        tuning_suggestions,
    )
    return learning_dir
