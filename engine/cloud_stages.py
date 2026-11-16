"""Checkpointed, model-free stage handoff for Codex Cloud."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from engine.parser import build_context_package, parse_stage_response
from engine.article_length import check_article_length, requested_word_range, word_range_label
from engine.utils import load_yaml
from engine.workflow_artifacts import derive_artifact_file_contents, extract_markdown_section, extract_markdown_section_before
from engine.workflow_context import build_step_prompt
from engine.workflow_contracts import WorkflowDefinition, validate_step_skill_contract, validate_workflow_artifact_set
from engine.workflow_persistence import RunRepository, atomic_write_text
from engine.workflow_resolution import resolve_step_skill_path, resolve_workflow_file
from engine.style_manager import validate_style_contract


def _contract(config_path: Path, mode: str, style: str):
    flow_path = resolve_workflow_file(load_yaml(config_path), mode)
    flow = load_yaml(flow_path)
    definition = WorkflowDefinition.from_dict(flow, expected_mode=mode)
    style = validate_style_contract(mode, style, flow_path)
    skills = {}
    hashes = {"flow": hashlib.sha256(flow_path.read_bytes()).hexdigest()}
    for step in flow["steps"]:
        path = resolve_step_skill_path(step, style, mode)
        skills[step["id"]] = load_yaml(path)
        hashes[step["id"]] = hashlib.sha256(path.read_bytes()).hexdigest()
    for step in definition.steps:
        validate_step_skill_contract(step, skills[step.id])
    validate_workflow_artifact_set(definition, skills)
    return flow, definition, style, skills, hashes


def create_run(config_path: Path, input_path: Path, output_root: Path, *, mode: str = "moment", style: str = "reflective") -> Path:
    flow, definition, style, skills, hashes = _contract(config_path, mode, style)
    author_input = input_path.read_text(encoding="utf-8")
    requested_word_range(author_input, flow)
    repository = RunRepository(output_root)
    run_dir = repository.create(author_input, style, mode)
    repository.write_internal(run_dir, "input.md", author_input)
    repository.write_metadata(run_dir, {
        "status": "running", "run_source": "user", "persisted": True,
        "api_attempted": False, "api_called": False,
        "mode": mode, "style": style, "contract_hashes": hashes,
        "stage_order": list(definition.stage_ids),
    })
    repository.checkpoint(run_dir, {})
    atomic_write_text(run_dir / "run_log.md", f"# Run {run_dir.name}\n\nMode: {mode}\n\nStyle: {style}\n\n## Author Input\n\n{author_input.strip()}\n")
    return run_dir


def _state(run_dir: Path, config_path: Path):
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("status") not in {"running", "completed"}:
        raise ValueError("Run status is not resumable")
    flow, definition, style, skills, hashes = _contract(config_path, metadata["mode"], metadata["style"])
    if hashes != metadata["contract_hashes"]:
        raise ValueError("Flow/style changed since run creation")
    results = json.loads((run_dir / "step_outputs.json").read_text(encoding="utf-8"))
    return metadata, flow, definition, skills, results


def prepare_stage(run_dir: Path, config_path: Path) -> dict:
    metadata, flow, definition, skills, results = _state(run_dir, config_path)
    for step in flow["steps"]:
        stage_id = step["id"]
        if stage_id in results:
            continue
        policy = step.get("context_policy") or {}
        needed = set(policy.get("handoffs", [])) | set(policy.get("artifacts", []))
        if not needed.issubset(results):
            raise ValueError("Stage dependencies are incomplete")
        context = build_context_package(
            step,
            {key: results[key]["artifact"] for key in needed},
            {key: results[key]["handoff"] for key in needed},
        )
        author_input = (run_dir / "input.md").read_text(encoding="utf-8")
        prompt = build_step_prompt(flow, step, skills[stage_id], author_input, context)
        if step.get("needs_author_input", True):
            minimum, maximum = requested_word_range(author_input, flow)
            prompt += (
                "\n\nFinal edited article length contract: "
                f"{word_range_label(minimum, maximum)} words, counted with "
                "engine.parser.count_words(). This applies to the edited article, "
                "not to this stage's handoff or report."
            )
        token = hashlib.sha256((stage_id + prompt).encode("utf-8")).hexdigest()
        return {"stage_id": stage_id, "token": token, "prompt": prompt}
    return {"status": "completed"}


def submit_stage(run_dir: Path, config_path: Path, stage_id: str, token: str, response: str) -> dict:
    metadata, flow, definition, skills, results = _state(run_dir, config_path)
    if stage_id in results:
        existing = results[stage_id]
        if existing["token"] == token and existing["response_sha256"] == hashlib.sha256(response.encode("utf-8")).hexdigest():
            return {"status": "already_completed", "stage_id": stage_id}
        raise ValueError("Stage already completed with different content")
    task = prepare_stage(run_dir, config_path)
    if task.get("stage_id") != stage_id or task.get("token") != token:
        raise ValueError("Stale or out-of-order stage submission")
    artifact, handoff, _ = parse_stage_response(response, strict=True)
    output_contract = skills[stage_id].get("output") or {}
    if output_contract.get("secondary_name") or output_contract.get("secondary_artifact"):
        edited_blog = extract_markdown_section_before(artifact, "Edited Blog", ["Edit Log", "edit_log"])
        if not edited_blog or not extract_markdown_section(artifact, "Edit Log"):
            raise ValueError("Editor artifact requires nonempty Edited Blog and Edit Log sections")
    files = derive_artifact_file_contents(skills[stage_id], artifact)
    output = next(step for step in flow["steps"] if step["id"] == stage_id)
    if output["output"] == definition.final_output["primary_ai_draft"]:
        check_article_length(
            files[output["output"]],
            (run_dir / "input.md").read_text(encoding="utf-8"),
            flow,
        )
    repository = RunRepository(run_dir.parent)
    for name, content in files.items():
        repository.write_artifact(run_dir, name, content)
    repository.write_artifact(run_dir, output["handoff_output"], handoff)
    results[stage_id] = {
        "status": "completed", "token": token,
        "response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
        "artifact": artifact, "handoff": handoff,
    }
    repository.write_internal(run_dir, "step_outputs.json", json.dumps(results, ensure_ascii=False, indent=2))
    log = [f"# Run {run_dir.name}", f"Mode: {metadata['mode']}", f"Style: {metadata['style']}",
           "## Author Input", (run_dir / "input.md").read_text(encoding="utf-8").strip()]
    for name in definition.stage_ids:
        if name in results:
            log.extend([f"## {name} Artifact", results[name]["artifact"],
                        f"## {name} Handoff", results[name]["handoff"]])
    atomic_write_text(run_dir / "run_log.md", "\n\n".join(log).strip() + "\n")
    if len(results) == len(definition.steps):
        metadata["status"] = "completed"
        repository.write_metadata(run_dir, metadata)
    return {"status": metadata["status"], "stage_id": stage_id}


def finalize_blog(run_dir: Path, config_path: Path, approved_file: Path) -> Path:
    """Save the author's selected/edited version after a completed run."""
    metadata, flow, definition, skills, results = _state(run_dir, config_path)
    if metadata["status"] != "completed" or len(results) != len(definition.steps):
        raise ValueError("Complete every stage before author approval")
    final_path = run_dir / definition.final_output["human_final"]
    if final_path.exists():
        raise FileExistsError(final_path)
    approved = approved_file.read_text(encoding="utf-8").strip()
    if not approved:
        raise ValueError("Approved article is empty")
    # The approved file is explicit author input; never silently copy the AI draft.
    atomic_write_text(final_path, approved + "\n")
    return final_path
