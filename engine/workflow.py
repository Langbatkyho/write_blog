"""Compatibility facade for workflow execution, persistence and learning."""

from engine.workflow_artifacts import (
    append_run_log,
    derive_artifact_file_contents,
    extract_markdown_section,
)
from engine.workflow_context import build_dry_run_response, build_step_prompt
from engine.workflow_execution import (
    preview_workflow,
    preview_workflow_text,
    run_workflow,
)
from engine.workflow_learning import (
    load_step_outputs_from_run,
    run_learning_loop,
)
from engine.workflow_persistence import build_run_dir
from engine.workflow_resolution import (
    load_workflow_skills,
    resolve_step_skill_path,
    resolve_workflow_file,
)


__all__ = [
    "append_run_log",
    "build_dry_run_response",
    "build_run_dir",
    "build_step_prompt",
    "derive_artifact_file_contents",
    "extract_markdown_section",
    "load_step_outputs_from_run",
    "load_workflow_skills",
    "preview_workflow",
    "preview_workflow_text",
    "resolve_step_skill_path",
    "resolve_workflow_file",
    "run_learning_loop",
    "run_workflow",
]
