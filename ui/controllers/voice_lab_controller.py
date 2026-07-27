from __future__ import annotations

from typing import Mapping

from engine.voice_lab.analyzer import analyze_samples
from engine.voice_lab.compiler import compile_style
from engine.voice_lab.interview import (
    apply_calibration_selection,
    apply_interview_patch,
    calibrate_ab,
    generate_interview,
    propose_interview_patch,
)
from engine.voice_lab.models import (
    AnalysisResult,
    CalibrationSession,
    InterviewQuestion,
    StyleProfile,
)
from engine.voice_lab.prompts import InterviewPatchPayload
from engine.voice_lab.publisher import publish_style


def analyze_voice_samples(samples: list[str], mode: str) -> AnalysisResult:
    usable = [sample for sample in samples if sample.strip()]
    if not usable:
        raise ValueError("Vui lòng nhập ít nhất 1 mẫu bài viết.")
    return analyze_samples(usable, mode=mode)


def prepare_interview(profile: StyleProfile) -> list[InterviewQuestion]:
    return generate_interview(profile)


def propose_patch(
    profile: StyleProfile,
    questions: list[InterviewQuestion],
    answers: Mapping[str, str],
) -> InterviewPatchPayload:
    return propose_interview_patch(profile, questions, answers)


def confirm_patch(
    profile: StyleProfile,
    patch: InterviewPatchPayload,
    questions: list[InterviewQuestion],
    answers: Mapping[str, str],
) -> StyleProfile:
    return apply_interview_patch(
        profile, patch, questions, answers, confirmed=True
    )


def prepare_calibration(
    profile: StyleProfile, dimension: str
) -> CalibrationSession:
    return calibrate_ab(dimension, profile)


def apply_calibration_and_compile(
    profile: StyleProfile,
    session: CalibrationSession,
    selected: str,
    mode: str,
):
    if profile.mode != mode:
        raise ValueError(
            f"Profile mode '{profile.mode}' không khớp UI mode '{mode}'."
        )
    updated = apply_calibration_selection(profile, session, selected)
    updated.status = "confirmed"
    updated.is_draft = False
    return updated, compile_style(updated, mode=mode)


def publish_profile(
    profile: StyleProfile,
    compiled,
    *,
    name: str,
    slug: str,
    mode: str,
):
    if profile.mode != mode:
        raise ValueError(
            f"Profile mode '{profile.mode}' không khớp UI mode '{mode}'."
        )
    updated = profile.model_copy(deep=True)
    updated.slug = slug
    return updated, publish_style(
        updated,
        compiled,
        name=name,
        slug=slug,
        mode=mode,
    )
