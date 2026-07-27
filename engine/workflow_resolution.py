from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.utils import load_yaml, resolve_path


STANDARD_FLOWS = {
    "write_blog.yaml",
    "write_deep_blog.yaml",
    "write_moment_blog.yaml",
}


def resolve_workflow_file(config: dict[str, Any], mode: str) -> Path:
    config_file = config.get("workflow", {}).get("file")
    is_standard = (
        config_file and Path(config_file).name in STANDARD_FLOWS
    )
    if config_file and not is_standard:
        return resolve_path(config_file)
    if mode == "moment":
        return resolve_path("flow/write_moment_blog.yaml")
    if mode == "deep":
        return resolve_path("flow/write_blog.yaml")
    raise ValueError(f"Mode không hợp lệ: {mode}")


def resolve_step_skill_path(
    step: dict[str, Any], style: str, mode: str
) -> Path:
    filename = Path(step["skill"]).name
    from engine.style_manager import resolve_style_by_slug_or_alias

    resolved = resolve_style_by_slug_or_alias(mode, style)
    if resolved:
        style = resolved
    primary = resolve_path(f"skills/{mode}/{style}/{filename}")
    if primary.exists():
        return primary
    if mode == "deep":
        legacy = resolve_path(f"skills/{style}/{filename}")
        if legacy.exists():
            return legacy
    raise FileNotFoundError(
        f"Skill '{filename}' not found for style '{style}' in mode '{mode}'. "
        f"Expected at: skills/{mode}/{style}/{filename}"
    )


def load_workflow_skills(
    workflow: dict[str, Any], style: str, mode: str = "deep"
) -> dict[str, dict[str, Any]]:
    skills: dict[str, dict[str, Any]] = {}
    for step in workflow.get("steps", []):
        step_id = str(step["id"])
        skills[step_id] = load_yaml(
            resolve_step_skill_path(step, style, mode)
        )
    skills["editorial_learning"] = load_yaml(
        resolve_path("skills/editorial_learning.yaml")
    )
    return skills
