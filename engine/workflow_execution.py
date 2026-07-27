from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path
from typing import Any, Callable

from engine.openai_client import call_openai, get_openai_options
from engine.parser import build_context_package, estimate_tokens, parse_stage_response
from engine.style_manager import validate_style_contract
from engine.utils import load_yaml, read_text, resolve_path
from engine.workflow_artifacts import append_run_log, derive_artifact_file_contents
from engine.workflow_context import build_dry_run_response, build_step_prompt
from engine.workflow_contracts import (
    StageResult,
    WorkflowDefinition,
    WorkflowRunResult,
    validate_step_skill_contract,
    validate_workflow_artifact_set,
)
from engine.workflow_persistence import RunRepository
from engine.workflow_resolution import (
    resolve_step_skill_path,
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


def _client_descriptor(
    llm_client: LlmClient,
    config: dict[str, Any],
    stage_id: str,
) -> tuple[str, str | None, bool]:
    if hasattr(llm_client, "describe_stage"):
        descriptor = llm_client.describe_stage(stage_id, config)
        return (
            str(descriptor.get("provider", "unknown")),
            descriptor.get("model"),
            bool(descriptor.get("api_capable", True)),
        )
    provider = getattr(llm_client, "provider_name", None) or getattr(
        llm_client, "__name__", "unknown"
    ).replace("call_", "")
    model = (
        str(get_openai_options(config, stage_id).get("model"))
        if provider in {"openai", "routing_client"}
        else None
    )
    return (
        str(provider),
        model,
        bool(getattr(llm_client, "api_capable", True)),
    )


def _load_contract(
    config: dict[str, Any],
    mode: str,
    style: str,
    llm_client: LlmClient,
) -> tuple[
    Path,
    dict[str, Any],
    WorkflowDefinition,
    str,
    dict[str, tuple[Path, dict[str, Any]]],
]:
    workflow_file = resolve_workflow_file(config, mode)
    workflow = load_yaml(workflow_file)
    definition = WorkflowDefinition.from_dict(workflow, expected_mode=mode)
    client_map = getattr(llm_client, "client_map", None)
    if isinstance(client_map, dict):
        from engine.client_router import validate_client_map

        validate_client_map(client_map, set(definition.stage_ids))
    resolved_style = validate_style_contract(mode, style, workflow_file)
    skills: dict[str, tuple[Path, dict[str, Any]]] = {}
    for step, step_definition in zip(workflow["steps"], definition.steps):
        skill_path = resolve_step_skill_path(step, resolved_style, mode)
        skill = load_yaml(skill_path)
        validate_step_skill_contract(step_definition, skill)
        skills[step_definition.id] = (skill_path, skill)
    validate_workflow_artifact_set(
        definition,
        {stage_id: value[1] for stage_id, value in skills.items()},
    )
    return workflow_file, workflow, definition, resolved_style, skills


def run_workflow(
    config_path: Path,
    input_path: Path | None,
    dry_run: bool = False,
    llm_client: LlmClient | None = None,
    style: str = "reflective",
    mode: str = "deep",
    *,
    persist: bool | None = None,
    output_root: Path | None = None,
    run_source: str | None = None,
    input_markdown: str | None = None,
) -> Path | WorkflowRunResult:
    llm_client = llm_client or call_openai
    config = load_yaml(config_path)
    workflow_file, workflow, definition, style, skills = _load_contract(
        config, mode, style, llm_client
    )
    if input_markdown is not None and input_path is not None:
        raise ValueError("Chỉ truyền input_path hoặc input_markdown, không truyền cả hai.")
    if input_markdown is None:
        if input_path is None:
            raise ValueError("Thiếu input_path/input_markdown.")
        author_input = read_text(input_path)
    else:
        author_input = input_markdown

    should_persist = (not dry_run) if persist is None else persist
    effective_source = run_source or ("dry_run" if dry_run else "user")
    if effective_source not in VALID_RUN_SOURCES:
        raise ValueError(f"run_source không hợp lệ: {effective_source}")
    if dry_run and should_persist and output_root is None:
        raise ValueError(
            "Dry-run chỉ được persist khi truyền output_root tạm tường minh."
        )

    repository: RunRepository | None = None
    run_dir: Path | None = None
    log_file: Path | None = None
    if should_persist:
        log_root = (
            output_root.resolve()
            if output_root is not None
            else resolve_path(config.get("workflow", {}).get("log_dir", "runs"))
        )
        repository = RunRepository(log_root)
        run_dir = repository.create(author_input, style, mode)
        log_file = run_dir / "run_log.md"
        repository.write_internal(run_dir, "input.md", author_input)

    stage_results: dict[str, StageResult] = {}
    artifacts: dict[str, str] = {}
    handoffs: dict[str, str] = {}
    save_step_files = bool(config.get("runtime", {}).get("save_step_files", True))
    stop_on_error = bool(config.get("workflow", {}).get("stop_on_error", True))
    metadata: dict[str, Any] = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "config_file": str(config_path),
        "workflow_file": str(workflow_file),
        "input_file": str(input_path) if input_path is not None else None,
        "dry_run": dry_run,
        "run_source": effective_source,
        "persisted": should_persist,
        "api_attempted": False,
        "api_called": False,
        "status": "running" if should_persist else "preview",
        "client_map": getattr(llm_client, "client_map", None),
        "style": style,
        "mode": mode,
        "stage_telemetry": {},
    }
    if repository and run_dir and log_file:
        repository.write_metadata(run_dir, metadata)
        append_run_log(
            log_file,
            "Run Metadata",
            json.dumps(metadata, ensure_ascii=False, indent=2),
        )
        append_run_log(log_file, "Author Input", author_input)

    terminal_error: Exception | None = None
    for index, (step, step_definition) in enumerate(
        zip(workflow["steps"], definition.steps), start=1
    ):
        step_id = step_definition.id
        skill_path, skill = skills[step_id]
        required_context = set(step_definition.context_handoffs) | set(
            step_definition.context_artifacts
        )
        failed_dependencies = [
            dependency
            for dependency in required_context
            if dependency in stage_results
            and stage_results[dependency].status != "completed"
        ]
        if failed_dependencies:
            stage_results[step_id] = StageResult(
                stage_id=step_id,
                status="skipped",
                artifact_file=step_definition.output,
                handoff_file=step_definition.handoff_output,
                error="Dependency không hoàn tất: "
                + ", ".join(sorted(failed_dependencies)),
            )
            if repository and run_dir:
                repository.checkpoint(run_dir, stage_results)
            continue

        context_package = build_context_package(step, artifacts, handoffs)
        prompt = build_step_prompt(
            workflow, step, skill, author_input, context_package
        )
        input_handoff_tokens = sum(
            estimate_tokens(value)
            for value in context_package["handoffs"].values()
        )
        input_artifact_tokens = sum(
            estimate_tokens(value)
            for value in context_package["artifacts"].values()
        )
        provider, model, api_capable = _client_descriptor(
            llm_client, config, step_id
        )
        api_attempted = bool(
            not dry_run and api_capable
        )
        stage_api_called = False
        started = time.perf_counter()
        try:
            raw_output = (
                build_dry_run_response(
                    step_id, skill_path, str(model or "provider-default")
                )
                if dry_run
                else llm_client(prompt, config, step_id)
            )
            stage_api_called = api_attempted
            artifact, handoff, _ = parse_stage_response(raw_output, strict=True)
            result = StageResult(
                stage_id=step_id,
                status="completed",
                artifact=artifact,
                handoff=handoff,
                artifact_file=step_definition.output,
                handoff_file=step_definition.handoff_output,
                secondary_artifact_file=(
                    skill.get("output", {}).get("secondary_name")
                    or skill.get("output", {}).get("secondary_artifact")
                ),
                provider=provider,
                model=str(model) if model else None,
                api_attempted=api_attempted,
                api_called=stage_api_called,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:
            result = StageResult(
                stage_id=step_id,
                status="failed",
                artifact_file=step_definition.output,
                handoff_file=step_definition.handoff_output,
                error=str(exc),
                provider=provider,
                model=str(model) if model else None,
                api_attempted=api_attempted,
                api_called=bool(getattr(exc, "api_called", False)),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            stage_results[step_id] = result
            metadata["api_attempted"] = (
                metadata["api_attempted"] or api_attempted
            )
            metadata["api_called"] = (
                metadata["api_called"] or result.api_called
            )
            metadata["stage_telemetry"][step_id] = _telemetry(result)
            if repository and run_dir and log_file:
                repository.checkpoint(run_dir, stage_results)
                append_run_log(log_file, f"{index}. {step_id} ERROR", str(exc))
            if stop_on_error:
                terminal_error = exc
                break
            continue

        artifact_tokens = estimate_tokens(result.artifact)
        handoff_tokens = estimate_tokens(result.handoff)
        result.metrics = {
            "artifact_estimated_tokens": artifact_tokens,
            "handoff_estimated_tokens": handoff_tokens,
            "handoff_savings_estimated_tokens": max(
                0, artifact_tokens - handoff_tokens
            ),
            "selected_input_handoff_estimated_tokens": input_handoff_tokens,
            "selected_input_artifact_estimated_tokens": input_artifact_tokens,
        }
        stage_results[step_id] = result
        artifacts[step_id] = result.artifact
        handoffs[step_id] = result.handoff
        metadata["api_attempted"] = (
            metadata["api_attempted"] or api_attempted
        )
        metadata["api_called"] = metadata["api_called"] or result.api_called
        metadata["stage_telemetry"][step_id] = _telemetry(result)

        try:
            if repository and run_dir and log_file:
                append_run_log(
                    log_file, f"{index}. {step_id} Artifact", result.artifact
                )
                append_run_log(
                    run_dir / "handoff_log.md",
                    f"{index}. {step_id} Handoff",
                    result.handoff,
                )
                if save_step_files:
                    artifact_files = derive_artifact_file_contents(
                        skill, result.artifact
                    )
                    if step_definition.output not in artifact_files:
                        raise ValueError(
                            f"Skill '{step_id}' không tạo Flow output "
                            f"'{step_definition.output}'."
                        )
                    for filename, content in artifact_files.items():
                        repository.write_artifact(run_dir, filename, content)
                    repository.write_artifact(
                        run_dir, step_definition.handoff_output, result.handoff
                    )
                repository.checkpoint(run_dir, stage_results)
        except Exception as exc:
            artifacts.pop(step_id, None)
            handoffs.pop(step_id, None)
            result = StageResult(
                stage_id=step_id,
                status="failed",
                artifact_file=step_definition.output,
                handoff_file=step_definition.handoff_output,
                error=f"Persistence failure: {exc}",
                provider=provider,
                model=str(model) if model else None,
                api_attempted=api_attempted,
                api_called=stage_api_called,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            stage_results[step_id] = result
            metadata["api_attempted"] = (
                metadata["api_attempted"] or api_attempted
            )
            metadata["api_called"] = (
                metadata["api_called"] or result.api_called
            )
            metadata["stage_telemetry"][step_id] = _telemetry(result)
            if repository and run_dir:
                try:
                    repository.checkpoint(run_dir, stage_results)
                except Exception:
                    pass
            if stop_on_error:
                terminal_error = exc
                break

    has_failed = terminal_error is not None or any(
        result.status == "failed" for result in stage_results.values()
    )
    final_status = (
        "failed"
        if has_failed
        else ("completed" if should_persist else "preview")
    )
    metadata.update(
        {
            "status": final_status,
            "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "context_strategy": "artifact_plus_handoff",
            "step_context_metrics": {
                stage_id: result.metrics
                for stage_id, result in stage_results.items()
            },
            "total_artifact_estimated_tokens": sum(
                result.metrics.get("artifact_estimated_tokens", 0)
                for result in stage_results.values()
            ),
            "total_handoff_estimated_tokens": sum(
                result.metrics.get("handoff_estimated_tokens", 0)
                for result in stage_results.values()
            ),
        }
    )
    if repository and run_dir:
        repository.write_metadata(run_dir, metadata)
    if terminal_error:
        raise terminal_error
    result = WorkflowRunResult(
        status=final_status,
        mode=mode,
        style=style,
        persisted=should_persist,
        api_attempted=bool(metadata["api_attempted"]),
        api_called=bool(metadata["api_called"]),
        run_source=effective_source,
        stages=stage_results,
        run_dir=run_dir,
    )
    return run_dir if run_dir is not None else result


def _telemetry(result: StageResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "provider": result.provider,
        "model": result.model,
        "api_attempted": result.api_attempted,
        "api_called": result.api_called,
        "duration_ms": result.duration_ms,
        "error": result.error,
    }


def preview_workflow(
    config_path: Path,
    input_path: Path,
    *,
    style: str = "reflective",
    mode: str = "deep",
    run_source: str = "dry_run",
) -> WorkflowRunResult:
    result = run_workflow(
        config_path,
        input_path,
        dry_run=True,
        style=style,
        mode=mode,
        persist=False,
        run_source=run_source,
    )
    if not isinstance(result, WorkflowRunResult):
        raise RuntimeError("Preview không được persist.")
    return result


def preview_workflow_text(
    config_path: Path,
    input_markdown: str,
    *,
    style: str = "reflective",
    mode: str = "deep",
    run_source: str = "dry_run",
) -> WorkflowRunResult:
    result = run_workflow(
        config_path,
        None,
        input_markdown=input_markdown,
        dry_run=True,
        style=style,
        mode=mode,
        persist=False,
        run_source=run_source,
    )
    if not isinstance(result, WorkflowRunResult):
        raise RuntimeError("Preview không được persist.")
    return result
