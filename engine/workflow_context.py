from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import yaml


def build_dry_run_response(
    step_id: str, skill_path: Path, model: str
) -> str:
    if step_id in {"editor_agent", "breath_editor"}:
        artifact = (
            "## Edited Blog\n\n"
            f"[DRY RUN] Would call provider for step `{step_id}` using "
            f"{skill_path} with model `{model}`.\n\n"
            "## Edit Log\n\n"
            "- [DRY RUN] Would record minimum edits, reader friction, root "
            "causes, and expected reader effects."
        )
    else:
        artifact = (
            f"[DRY RUN] Would call provider for step `{step_id}` using "
            f"{skill_path} with model `{model}`."
        )
    return (
        "## Artifact\n\n"
        f"{artifact}\n\n"
        "## Handoff\n\n"
        f"[DRY RUN HANDOFF] Compact context for `{step_id}` that would be "
        "passed to downstream stages."
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
    ) or "No handoffs selected for this step."
    artifact_block = "\n\n".join(
        f"### {name}\n\n{content}"
        for name, content in context_package.get("artifacts", {}).items()
    ) or "No full artifacts selected for this step."

    prompt_parts = [
        "You are running one step of an automated reflective blog workflow.",
        f"Workflow name: {workflow.get('name')}",
        f"Workflow description: {workflow.get('description')}",
    ]
    if step.get("needs_author_input", True):
        prompt_parts.append(f"Author input:\n```markdown\n{author_input}\n```")
    prompt_parts.append(
        textwrap.dedent(
            """
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
    )
    prompt_parts.extend(
        [
            "---",
            "Current step context:",
            f"- id: {step.get('id')}",
            f"- purpose: {step.get('purpose')}",
            f"- expected output file: {step.get('output')}",
            f"- expected handoff file: {step.get('handoff_output')}",
            "Compact handoffs selected by context_policy:\n"
            f"```markdown\n{handoff_block}\n```",
            "Full artifacts selected by context_policy:\n"
            f"```markdown\n{artifact_block}\n```",
            "Skill YAML:\n```yaml\n"
            f"{yaml.safe_dump(skill, allow_unicode=True, sort_keys=False)}\n```",
        ]
    )
    return "\n\n".join(prompt_parts)
