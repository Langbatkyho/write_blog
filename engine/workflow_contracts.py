from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


RunSource = Literal["user", "test", "dry_run", "ui", "cli", "agent_validation"]
RunStatus = Literal["preview", "running", "completed", "failed"]
StageStatus = Literal["completed", "failed", "skipped"]
RUN_INTERNAL_PATHS = frozenset(
    {
        "input.md",
        "metadata.json",
        "step_outputs.json",
        "run_log.md",
        "handoff_log.md",
    }
)


def validate_relative_output_path(value: str, *, field_name: str) -> str:
    candidate = Path(value)
    if (
        not value.strip()
        or candidate.is_absolute()
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or candidate.drive
    ):
        raise ValueError(f"{field_name} phải là đường dẫn tương đối an toàn: {value!r}")
    return value


def validate_run_artifact_path(value: str, *, field_name: str) -> str:
    validated = validate_relative_output_path(value, field_name=field_name)
    normalized = Path(validated).as_posix().casefold()
    if normalized in RUN_INTERNAL_PATHS:
        raise ValueError(
            f"{field_name} trùng file nội bộ của run: {validated!r}"
        )
    return validated


@dataclass(frozen=True)
class StepDefinition:
    id: str
    skill: str
    purpose: str
    output: str
    handoff_output: str
    context_handoffs: tuple[str, ...] = ()
    context_artifacts: tuple[str, ...] = ()
    needs_author_input: bool = True

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "StepDefinition":
        step_id = str(raw.get("id", "")).strip()
        if not step_id:
            raise ValueError("Workflow step thiếu id.")
        skill = validate_relative_output_path(
            str(raw.get("skill", "")), field_name=f"{step_id}.skill"
        )
        output = validate_run_artifact_path(
            str(raw.get("output", "")), field_name=f"{step_id}.output"
        )
        handoff_output = validate_run_artifact_path(
            str(raw.get("handoff_output", "")),
            field_name=f"{step_id}.handoff_output",
        )
        policy = raw.get("context_policy") or {}
        if not isinstance(policy, dict):
            raise ValueError(f"{step_id}.context_policy phải là object.")
        handoffs = policy.get("handoffs", [])
        artifacts = policy.get("artifacts", [])
        if not isinstance(handoffs, list) or not isinstance(artifacts, list):
            raise ValueError(
                f"{step_id}.context_policy.handoffs/artifacts phải là danh sách."
            )
        return cls(
            id=step_id,
            skill=skill,
            purpose=str(raw.get("purpose", "")),
            output=output,
            handoff_output=handoff_output,
            context_handoffs=tuple(str(item) for item in handoffs),
            context_artifacts=tuple(str(item) for item in artifacts),
            needs_author_input=bool(raw.get("needs_author_input", True)),
        )

    def to_runtime_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "skill": self.skill,
            "purpose": self.purpose,
            "output": self.output,
            "handoff_output": self.handoff_output,
            "needs_author_input": self.needs_author_input,
            "context_policy": {
                "handoffs": list(self.context_handoffs),
                "artifacts": list(self.context_artifacts),
            },
        }


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    mode: str
    description: str
    steps: tuple[StepDefinition, ...]
    final_output: dict[str, Any]
    raw: dict[str, Any] = field(repr=False)

    @classmethod
    def from_dict(
        cls, raw: dict[str, Any], *, expected_mode: str | None = None
    ) -> "WorkflowDefinition":
        mode = str(raw.get("mode", "")).strip()
        if mode not in {"deep", "moment"}:
            raise ValueError(f"Workflow mode không hợp lệ: {mode!r}")
        if expected_mode and mode != expected_mode:
            raise ValueError(
                f"Workflow mode '{mode}' không khớp mode yêu cầu '{expected_mode}'."
            )
        raw_steps = raw.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ValueError("Workflow phải có danh sách steps không rỗng.")
        steps = tuple(StepDefinition.from_dict(item) for item in raw_steps)
        ids = [step.id for step in steps]
        if len(ids) != len(set(ids)):
            raise ValueError("Workflow có stage id trùng.")
        output_paths = [
            path for step in steps for path in (step.output, step.handoff_output)
        ]
        if len(output_paths) != len(set(output_paths)):
            raise ValueError("Workflow có output/handoff filename trùng.")
        known: set[str] = set()
        all_ids = set(ids)
        for step in steps:
            references = set(step.context_handoffs) | set(step.context_artifacts)
            unknown = references - all_ids
            forward = references - known
            if unknown:
                raise ValueError(
                    f"Stage '{step.id}' tham chiếu stage không tồn tại: "
                    f"{sorted(unknown)}"
                )
            if forward:
                raise ValueError(
                    f"Stage '{step.id}' tham chiếu stage chưa chạy: {sorted(forward)}"
                )
            known.add(step.id)
        final_output = raw.get("final_output") or {}
        if not isinstance(final_output, dict):
            raise ValueError("final_output phải là object.")
        for key, value in final_output.items():
            if key != "format" and isinstance(value, str):
                validate_relative_output_path(
                    value, field_name=f"final_output.{key}"
                )
        return cls(
            name=str(raw.get("name", "")).strip(),
            mode=mode,
            description=str(raw.get("description", "")),
            steps=steps,
            final_output=dict(final_output),
            raw=raw,
        )

    @property
    def stage_ids(self) -> tuple[str, ...]:
        return tuple(step.id for step in self.steps)


def validate_step_skill_contract(
    step: StepDefinition, skill: dict[str, Any]
) -> None:
    output = skill.get("output") or {}
    if not isinstance(output, dict):
        raise ValueError(f"Skill của stage '{step.id}' thiếu output object.")
    declared = output.get("name")
    if not isinstance(declared, str):
        declared = output.get("artifact")
    if not isinstance(declared, str) or not declared.strip():
        raise ValueError(
            f"Skill của stage '{step.id}' thiếu output.name/output.artifact."
        )
    validate_run_artifact_path(
        declared, field_name=f"{step.id}.skill.output"
    )
    if declared != step.output:
        raise ValueError(
            f"Flow–Skill mismatch tại '{step.id}': "
            f"Flow={step.output!r}, Skill={declared!r}."
        )
    secondary = output.get("secondary_name") or output.get("secondary_artifact")
    if secondary is not None:
        validate_run_artifact_path(
            str(secondary), field_name=f"{step.id}.skill.secondary_output"
        )


def validate_workflow_artifact_set(
    definition: WorkflowDefinition,
    skills: dict[str, dict[str, Any]],
) -> None:
    claimed: dict[str, str] = {}

    def claim(path: str, owner: str) -> None:
        key = Path(path).as_posix().casefold()
        previous = claimed.get(key)
        if previous is not None:
            raise ValueError(
                f"Artifact path trùng giữa '{previous}' và '{owner}': {path!r}"
            )
        claimed[key] = owner

    for step in definition.steps:
        claim(step.output, f"{step.id}.output")
        claim(step.handoff_output, f"{step.id}.handoff_output")
        skill_output = skills[step.id].get("output") or {}
        if not isinstance(skill_output, dict):
            continue
        secondary = skill_output.get("secondary_name") or skill_output.get(
            "secondary_artifact"
        )
        if secondary is not None:
            validated = validate_run_artifact_path(
                str(secondary),
                field_name=f"{step.id}.skill.secondary_output",
            )
            claim(validated, f"{step.id}.skill.secondary_output")


@dataclass
class StageResult:
    stage_id: str
    status: StageStatus
    artifact: str = ""
    handoff: str = ""
    artifact_file: str = ""
    handoff_file: str = ""
    secondary_artifact_file: str | None = None
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    provider: str | None = None
    model: str | None = None
    api_attempted: bool = False
    api_called: bool = False
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "artifact": self.artifact,
            "handoff": self.handoff,
            "artifact_file": self.artifact_file,
            "handoff_file": self.handoff_file,
            "secondary_artifact_file": self.secondary_artifact_file,
            "warnings": self.warnings,
            "metrics": self.metrics,
            "error": self.error,
            "provider": self.provider,
            "model": self.model,
            "api_attempted": self.api_attempted,
            "api_called": self.api_called,
            "duration_ms": self.duration_ms,
        }


@dataclass
class WorkflowRunResult:
    status: RunStatus
    mode: str
    style: str
    persisted: bool
    api_attempted: bool
    api_called: bool
    run_source: RunSource
    stages: dict[str, StageResult]
    run_dir: Path | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def artifacts(self) -> dict[str, str]:
        return {
            stage_id: result.artifact
            for stage_id, result in self.stages.items()
            if result.status == "completed"
        }

    @property
    def handoffs(self) -> dict[str, str]:
        return {
            stage_id: result.handoff
            for stage_id, result in self.stages.items()
            if result.status == "completed"
        }


@dataclass
class LearningRunResult:
    report: str
    tuning_suggestions: str
    mode: str
    style: str
    persisted: bool
    api_attempted: bool
    api_called: bool
    run_source: RunSource
    learning_dir: Path | None = None
