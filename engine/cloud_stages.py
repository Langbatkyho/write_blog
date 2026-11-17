"""Checkpointed, model-free stage handoff for Codex Cloud."""

from __future__ import annotations

import hashlib
import json
import datetime as dt
import subprocess
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


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_commit() -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def _runtime_sha() -> str:
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for name in ("cloud_stages.py", "article_length.py", "parser.py", "workflow_artifacts.py",
                 "workflow_context.py", "workflow_contracts.py", "workflow_persistence.py"):
        digest.update(name.encode("utf-8") + b"\0" + (root / name).read_bytes())
    return digest.hexdigest()


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
        "protocol_version": 2, "source_commit": _source_commit(), "runtime_sha256": _runtime_sha(),
        "input_sha256": _sha(author_input.encode("utf-8")),
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
    if metadata.get("protocol_version", 1) not in (1, 2):
        raise ValueError("Unsupported Cloud checkpoint protocol")
    if metadata.get("protocol_version") == 2 and _sha((run_dir / "input.md").read_bytes()) != metadata.get("input_sha256"):
        raise ValueError("Input checksum mismatch")
    flow, definition, style, skills, hashes = _contract(config_path, metadata["mode"], metadata["style"])
    if hashes != metadata["contract_hashes"]:
        raise ValueError("Flow/style changed since run creation")
    results = json.loads((run_dir / "step_outputs.json").read_text(encoding="utf-8"))
    return metadata, flow, definition, skills, results


def _expected_files(run_dir: Path, flow: dict, definition, skills: dict, results: dict, style: str, approval: dict | None = None) -> dict[str, str]:
    order = list(definition.stage_ids)
    if list(results) != order[:len(results)]:
        raise ValueError("Checkpoint stages are not an ordered prefix of the flow")
    author_input = (run_dir / "input.md").read_text(encoding="utf-8")
    log = [f"# Run {run_dir.name}", f"Mode: {flow['mode']}", f"Style: {style}",
           "## Author Input", author_input.strip()]
    expected = {}
    for step in flow["steps"][:len(results)]:
        stage_id = step["id"]
        result = results[stage_id]
        if result.get("status") != "completed" or not all(isinstance(result.get(k), str) and result[k] for k in ("artifact", "handoff", "token", "response_sha256")):
            raise ValueError(f"Invalid checkpoint for stage {stage_id}")
        if "artifact_sha256" in result and _sha(result["artifact"].encode("utf-8")) != result["artifact_sha256"]:
            raise ValueError(f"Artifact checkpoint checksum mismatch: {stage_id}")
        if "handoff_sha256" in result and _sha(result["handoff"].encode("utf-8")) != result["handoff_sha256"]:
            raise ValueError(f"Handoff checkpoint checksum mismatch: {stage_id}")
        files = derive_artifact_file_contents(skills[stage_id], result["artifact"])
        for name, content in files.items():
            if name in expected and expected[name] != content:
                raise ValueError(f"Conflicting checkpoint artifact: {name}")
            expected[name] = content
        expected[step["handoff_output"]] = result["handoff"]
        log.extend([f"## {stage_id} Artifact", result["artifact"],
                    f"## {stage_id} Handoff", result["handoff"]])
    if approval:
        log.extend(["## Author Approval", f"Approved at: {approval['approved_at']}\nFinal SHA-256: {approval['final_sha256']}"])
    expected["run_log.md"] = "\n\n".join(log).strip() + "\n"
    return expected


def verify_run(run_dir: Path, config_path: Path) -> dict:
    metadata, flow, definition, skills, results = _state(run_dir, config_path)
    if metadata.get("protocol_version") == 2 and any(
        "artifact_sha256" not in result or "handoff_sha256" not in result
        for result in results.values()
    ):
        raise ValueError("Version 2 checkpoint lacks stage checksums")
    approval = metadata.get("author_approval")
    if approval:
        final_path = run_dir / definition.final_output["human_final"]
        if not final_path.is_file() or _sha(final_path.read_bytes()) != approval.get("final_sha256"):
            raise ValueError("Approved final article checksum mismatch or missing file")
    expected = _expected_files(run_dir, flow, definition, skills, results, metadata["style"], approval)
    missing, conflicts, stale = [], [], []
    for name, content in expected.items():
        path = run_dir / name
        if not path.exists():
            missing.append(name)
        elif path.read_text(encoding="utf-8") != content:
            if name == "run_log.md" and any(
                path.read_text(encoding="utf-8") == _expected_files(run_dir, flow, definition, skills, dict(list(results.items())[:count]), metadata["style"])["run_log.md"]
                for count in range(len(results))
            ) or (name == "run_log.md" and approval and path.read_text(encoding="utf-8") == _expected_files(run_dir, flow, definition, skills, results, metadata["style"])["run_log.md"]):
                stale.append(name)
            else:
                conflicts.append(name)
    complete = len(results) == len(definition.steps)
    correct_status = "completed" if complete else "running"
    return {"status": "ok" if not missing and not stale and not conflicts and metadata["status"] == correct_status else "needs_recovery",
            "missing": missing, "stale": stale, "conflicts": conflicts, "metadata_expected": correct_status,
            "metadata_actual": metadata["status"], "completed_stages": len(results), "total_stages": len(definition.steps)}


def recover_run(run_dir: Path, config_path: Path) -> dict:
    report = verify_run(run_dir, config_path)
    if report["conflicts"]:
        raise ValueError(f"Recovery conflicts with existing files: {report['conflicts']}")
    if report["metadata_actual"] == "completed" and report["metadata_expected"] != "completed":
        raise ValueError("Completed metadata conflicts with incomplete checkpoint")
    metadata, flow, definition, skills, results = _state(run_dir, config_path)
    expected = _expected_files(run_dir, flow, definition, skills, results, metadata["style"], metadata.get("author_approval"))
    for name in report["missing"] + report["stale"]:
        atomic_write_text(run_dir / name, expected[name])
    if metadata["status"] != report["metadata_expected"]:
        metadata["status"] = report["metadata_expected"]
        RunRepository(run_dir.parent).write_metadata(run_dir, metadata)
    return verify_run(run_dir, config_path)


def prepare_stage(run_dir: Path, config_path: Path) -> dict:
    metadata, flow, definition, skills, results = _state(run_dir, config_path)
    if verify_run(run_dir, config_path)["status"] != "ok":
        raise ValueError("Run needs recovery; call verify then recover")
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
    if verify_run(run_dir, config_path)["status"] != "ok":
        raise ValueError("Run needs recovery; call verify then recover")
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
        "artifact_sha256": _sha(artifact.encode("utf-8")),
        "handoff_sha256": _sha(handoff.encode("utf-8")),
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
    if verify_run(run_dir, config_path)["status"] != "ok":
        raise ValueError("Run needs recovery; call verify then recover")
    if metadata["status"] != "completed" or len(results) != len(definition.steps):
        raise ValueError("Complete every stage before author approval")
    final_path = run_dir / definition.final_output["human_final"]
    approved = approved_file.read_text(encoding="utf-8").strip()
    if not approved:
        raise ValueError("Approved article is empty")
    final_text = approved + "\n"
    final_hash = _sha(final_text.encode("utf-8"))
    approved_hash = _sha(approved_file.read_bytes())
    receipt = metadata.get("author_approval")
    if receipt:
        if receipt.get("approved_file_sha256") == approved_hash and receipt.get("final_sha256") == final_hash:
            return final_path
        raise ValueError("Different article was already approved")
    if final_path.exists() and _sha(final_path.read_bytes()) != final_hash:
        raise FileExistsError(final_path)
    # The approved file is explicit author input; never silently copy the AI draft.
    if not final_path.exists():
        atomic_write_text(final_path, final_text)
    metadata["author_approval"] = {"approved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                                   "approved_file_sha256": approved_hash, "final_sha256": final_hash,
                                   "source": "approved_file", "normalization": "strip_and_final_newline_v1"}
    RunRepository(run_dir.parent).write_metadata(run_dir, metadata)
    expected = _expected_files(run_dir, flow, definition, skills, results, metadata["style"], metadata["author_approval"])
    atomic_write_text(run_dir / "run_log.md", expected["run_log.md"])
    return final_path
