"""Compatibility facade for Guided Interview and Blind A/B calibration."""

from __future__ import annotations

import random
from typing import Mapping

from engine.gemini_client import call_gemini
from engine.voice_lab.calibration import (
    CALIBRATION_MAX_WORDS,
    CALIBRATION_MIN_WORDS,
    DEFAULT_CONTENT_BRIEF,
    apply_calibration_selection,
    calibrate_ab as _calibrate_ab,
)
from engine.voice_lab.interview_routing import DIMENSION_VI, generate_interview
from engine.voice_lab.models import (
    CalibrationSession,
    InterviewQuestion,
    StyleProfile,
)
from engine.voice_lab.profile_patch import (
    apply_interview_patch,
    propose_interview_patch as _propose_interview_patch,
)
from engine.voice_lab.prompts import InterviewPatchPayload


def propose_interview_patch(
    profile: StyleProfile,
    questions: list[InterviewQuestion],
    answers: Mapping[str, str],
) -> InterviewPatchPayload:
    return _propose_interview_patch(
        profile,
        questions,
        answers,
        gemini_client=call_gemini,
    )


def calibrate_ab(
    dimension: str,
    profile: StyleProfile,
    *,
    content_brief: str = DEFAULT_CONTENT_BRIEF,
    rng: random.Random | None = None,
) -> CalibrationSession:
    return _calibrate_ab(
        dimension,
        profile,
        content_brief=content_brief,
        rng=rng,
        gemini_client=call_gemini,
    )


__all__ = [
    "CALIBRATION_MAX_WORDS",
    "CALIBRATION_MIN_WORDS",
    "DEFAULT_CONTENT_BRIEF",
    "DIMENSION_VI",
    "apply_calibration_selection",
    "apply_interview_patch",
    "calibrate_ab",
    "generate_interview",
    "propose_interview_patch",
]
