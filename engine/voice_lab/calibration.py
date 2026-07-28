from __future__ import annotations

import random
from typing import Callable

from pydantic import ValidationError

from engine.gemini_client import call_gemini
from engine.voice_lab.models import (
    AnalysisError,
    CalibrationRecord,
    CalibrationSession,
    StyleProfile,
    VOICE_DIMENSIONS,
    compute_profile_confidence,
    utc_now,
)
from engine.voice_lab.prompts import (
    CalibrationPayload,
    build_calibration_prompt,
    calibration_schema,
)


GeminiCallable = Callable[..., str]
DEFAULT_CONTENT_BRIEF = (
    "Một người tắt thông báo điện thoại, ngồi yên bên cửa sổ vài phút và nhận ra "
    "sự tĩnh lặng giúp họ nghe rõ điều mình đang cần."
)
CALIBRATION_MIN_WORDS = 90
CALIBRATION_MAX_WORDS = 165
DIRECT_USER_CONFIRMATION_CONFIDENCE = 0.95


def calibrate_ab(
    dimension: str,
    profile: StyleProfile,
    *,
    content_brief: str = DEFAULT_CONTENT_BRIEF,
    rng: random.Random | None = None,
    gemini_client: GeminiCallable = call_gemini,
) -> CalibrationSession:
    if dimension not in VOICE_DIMENSIONS:
        raise ValueError(f"Dimension không hợp lệ: {dimension}")
    if not profile.dna:
        raise ValueError("Profile chưa có Voice DNA để calibration.")
    target = getattr(profile.dna, dimension)
    if not target.description:
        raise ValueError(f"Dimension '{dimension}' chưa có mô tả để calibration.")
    fixed_constraints = {
        name: getattr(profile.dna, name).description
        for name in VOICE_DIMENSIONS
        if name != dimension and getattr(profile.dna, name).description
    }
    try:
        response = gemini_client(
            build_calibration_prompt(
                dimension,
                target.description,
                content_brief,
                fixed_constraints,
            ),
            stage_id="voice_lab_calibrate",
            temperature=0.6,
            max_output_tokens=4096,
            config={
                "response_mime_type": "application/json",
                "response_schema": calibration_schema(),
            },
        )
        payload = CalibrationPayload.model_validate_json(response)
    except ValidationError as exc:
        raise AnalysisError(
            "invalid_model_output",
            "Gemini trả hai biến thể A/B không đúng cấu trúc.",
            detail=str(exc),
        ) from exc
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(
            "gemini_unavailable",
            "Không thể tạo bài thử A/B từ Gemini.",
            retryable=True,
            detail=str(exc),
        ) from exc

    amplified = payload.variant_amplified.strip()
    restrained = payload.variant_restrained.strip()
    lengths = [len(amplified.split()), len(restrained.split())]
    if (
        not amplified
        or not restrained
        or amplified == restrained
        or any(
            length < CALIBRATION_MIN_WORDS
            or length > CALIBRATION_MAX_WORDS
            for length in lengths
        )
    ):
        raise AnalysisError(
            "invalid_model_output",
            "Hai biến thể A/B chưa đạt khoảng dung sai 90–165 từ. "
            "Vui lòng tạo lại.",
        )
    randomizer = rng or random.SystemRandom()
    if randomizer.random() < 0.5:
        variants = (amplified, restrained)
        mapping = {"A": "amplified", "B": "restrained"}
    else:
        variants = (restrained, amplified)
        mapping = {"A": "restrained", "B": "amplified"}
    return CalibrationSession(
        dimension=dimension,
        content_brief=content_brief,
        variant_a=variants[0],
        variant_b=variants[1],
        shuffle_mapping=mapping,
    )


def apply_calibration_selection(
    profile: StyleProfile,
    session: CalibrationSession,
    selected: str,
) -> StyleProfile:
    if selected not in {"A", "B"}:
        raise ValueError("Lựa chọn calibration phải là A hoặc B.")
    if session.selected is not None or any(
        record.session_id == session.session_id
        for record in profile.calibration_history
    ):
        raise ValueError("Calibration session đã được áp dụng.")
    if not profile.dna:
        raise ValueError("Profile chưa có Voice DNA để cập nhật.")
    updated = profile.model_copy(deep=True)
    dimension = getattr(updated.dna, session.dimension)
    before_strength = dimension.strength
    before_confidence = dimension.confidence
    direction = session.shuffle_mapping[selected]
    delta = 0.15 if direction == "amplified" else -0.15
    dimension.strength = max(0.0, min(1.0, before_strength + delta))
    # A blind A/B choice is direct user confirmation, so the plan permits
    # confidence up to 0.95. The record below preserves the exact provenance.
    dimension.confidence = max(
        dimension.confidence,
        DIRECT_USER_CONFIRMATION_CONFIDENCE,
    )
    dimension.source = "calibration"
    selected_text = session.variant_a if selected == "A" else session.variant_b
    if selected_text not in dimension.examples:
        dimension.examples.append(selected_text)
    applied_session = session.model_copy(deep=True)
    applied_session.selected = selected
    updated.calibration_history.append(
        CalibrationRecord(
            session_id=applied_session.session_id,
            dimension=applied_session.dimension,
            selected_label=selected,
            selected_direction=direction,
            selected_text=selected_text,
            before_strength=before_strength,
            after_strength=dimension.strength,
            before_confidence=before_confidence,
            after_confidence=dimension.confidence,
        )
    )
    updated.revision += 1
    updated.updated_at = utc_now()
    updated.confidence = compute_profile_confidence(updated)
    return updated
