"""Contract cho khối `claude:` trong engine/config.example.yaml.

Consumer duy nhất: artifact/build_bundle.py. Khối này quy định model Claude và
effort cho từng stage khi workflow chạy trong Claude Artifact (capability `sample`).
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

# Model ID đã kiểm chứng gọi theo tên trong Artifact (spike ART-0, 2026-11-14),
# ánh xạ sang `modelTier` cùng hạng để khi bị hạ vẫn ở hạng tương đương.
# Thêm model mới vào đây chỉ sau khi đã kiểm chứng; `sample` không báo lỗi khi
# model sai tên mà âm thầm chạy bằng `modelTier`.
VERIFIED_MODELS: Dict[str, str] = {
    "claude-haiku-5-5": "quick",
    "claude-sonnet-5-5": "default",
    "claude-opus-5-5": "complex",
}
LEARNING_STAGES = ("editorial_learning", "workflow_tuning")
VOICE_LAB_STAGES = ("vl_analysis", "vl_synthesis", "vl_interview_patch", "vl_calibration")


class ClaudeConfigError(ValueError):
    pass


class StageModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    effort: Literal["low", "medium", "high"]

    @field_validator("model")
    @classmethod
    def model_must_be_verified(cls, value: str) -> str:
        if value not in VERIFIED_MODELS:
            raise ValueError(
                f"model '{value}' chưa được kiểm chứng; chỉ chấp nhận: "
                + ", ".join(sorted(VERIFIED_MODELS))
            )
        return value


class ClaudeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stages: Dict[str, StageModel]
    learning: Dict[str, StageModel]
    voice_lab: Dict[str, StageModel]


def _check_keys(group: str, actual: Iterable[str], expected: Iterable[str]) -> None:
    actual_set, expected_set = set(actual), set(expected)
    missing = sorted(expected_set - actual_set)
    unknown = sorted(actual_set - expected_set)
    problems = []
    if missing:
        problems.append("thiếu " + ", ".join(missing))
    if unknown:
        problems.append("thừa " + ", ".join(unknown))
    if problems:
        raise ClaudeConfigError(f"claude.{group}: " + "; ".join(problems) + ".")


def validate_claude_config(
    raw: Any, *, workflow_stage_ids: Iterable[str]
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """Kiểm tra khối `claude:` (fail-closed) và trả bảng model kèm `model_tier`."""
    if not isinstance(raw, dict):
        raise ClaudeConfigError("Config thiếu khối `claude:`.")
    try:
        parsed = ClaudeConfig.model_validate(raw)
    except ValidationError as exc:
        raise ClaudeConfigError(f"Khối `claude:` không hợp lệ: {exc}") from exc
    _check_keys("stages", parsed.stages, workflow_stage_ids)
    _check_keys("learning", parsed.learning, LEARNING_STAGES)
    _check_keys("voice_lab", parsed.voice_lab, VOICE_LAB_STAGES)

    def table(entries: Dict[str, StageModel], order: Iterable[str]) -> Dict[str, Dict[str, str]]:
        return {
            stage: {
                "model": entries[stage].model,
                "effort": entries[stage].effort,
                "model_tier": VERIFIED_MODELS[entries[stage].model],
            }
            for stage in order
        }

    return {
        "stages": table(parsed.stages, sorted(parsed.stages)),
        "learning": table(parsed.learning, LEARNING_STAGES),
        "voice_lab": table(parsed.voice_lab, VOICE_LAB_STAGES),
    }
