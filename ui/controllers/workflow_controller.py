from __future__ import annotations

from pathlib import Path

from engine.workflow import preview_workflow, preview_workflow_text
from engine.workflow_contracts import WorkflowRunResult


def preview_workbench(
    *,
    config_path: Path,
    style: str,
    mode: str,
    input_path: Path | None = None,
    input_markdown: str | None = None,
) -> WorkflowRunResult:
    if (input_path is None) == (input_markdown is None):
        raise ValueError("Phải truyền đúng một nguồn input cho workbench.")
    if input_markdown is not None:
        return preview_workflow_text(
            config_path,
            input_markdown,
            style=style,
            mode=mode,
            run_source="ui",
        )
    assert input_path is not None
    return preview_workflow(
        config_path,
        input_path,
        style=style,
        mode=mode,
        run_source="ui",
    )


def preview_metadata(preview: WorkflowRunResult) -> dict:
    return {
        "mode": preview.mode,
        "style": preview.style,
        "status": preview.status,
        "run_source": preview.run_source,
        "persisted": preview.persisted,
        "api_attempted": preview.api_attempted,
        "api_called": preview.api_called,
        "stages": {
            stage_id: {
                "status": result.status,
                "provider": result.provider,
                "model": result.model,
                "api_attempted": result.api_attempted,
                "api_called": result.api_called,
                "duration_ms": result.duration_ms,
            }
            for stage_id, result in preview.stages.items()
        },
    }
