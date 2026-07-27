from __future__ import annotations

import random
from typing import Dict, List, Mapping, Optional

from pydantic import ValidationError

from engine.gemini_client import call_gemini
from engine.voice_lab.models import (
    AnalysisError,
    CalibrationRecord,
    CalibrationSession,
    DimensionProfile,
    InterviewQuestion,
    InterviewRecord,
    StyleProfile,
    VOICE_DIMENSIONS,
    compute_profile_confidence,
    utc_now,
)
from engine.voice_lab.prompts import (
    CalibrationPayload,
    InterviewPatchPayload,
    build_calibration_prompt,
    build_interview_patch_prompt,
    calibration_schema,
    interview_patch_schema,
)


DIMENSION_VI = {
    "tone": "Giọng điệu",
    "vocabulary": "Từ vựng",
    "sentence_structure": "Cấu trúc câu",
    "rhythm": "Nhịp điệu",
    "formatting": "Định dạng",
    "humor": "Sự hài hước",
    "sensory_density": "Mật độ giác quan",
    "emoji": "Biểu tượng cảm xúc",
    "metaphor_density": "Mật độ ẩn dụ",
    "emotional_depth": "Chiều sâu cảm xúc",
    "pacing": "Nhịp độ",
    "perspective": "Góc nhìn / Ngôi kể",
}

DEFAULT_CONTENT_BRIEF = (
    "Một người tắt thông báo điện thoại, ngồi yên bên cửa sổ vài phút và nhận ra "
    "sự tĩnh lặng giúp họ nghe rõ điều mình đang cần."
)
CALIBRATION_MIN_WORDS = 90
CALIBRATION_MAX_WORDS = 165


def _dimension_priority(profile: StyleProfile, dimension: str) -> tuple:
    value = getattr(profile.dna, dimension) if profile.dna else DimensionProfile()
    contradictions = sum(
        item.dimension == dimension and item.stance == "contradict"
        for item in profile.evidence
    )
    confirmed = any(
        record.dimension == dimension for record in profile.interview_history
    )
    return (
        confirmed,
        bool(value.description.strip()),
        value.confidence,
        -contradictions,
        VOICE_DIMENSIONS.index(dimension),
    )


def generate_interview(
    profile: StyleProfile,
    *,
    max_questions: int = 3,
) -> List[InterviewQuestion]:
    """Ask only the weakest unresolved dimensions, never more than three."""
    if not profile.dna:
        return []
    confirmed_dimensions = {
        record.dimension for record in profile.interview_history
    }
    contradicted_dimensions = {
        item.dimension
        for item in profile.evidence
        if item.stance == "contradict" and item.status == "active"
    }
    candidates = [
        dimension
        for dimension in VOICE_DIMENSIONS
        if dimension not in confirmed_dimensions
        or dimension in contradicted_dimensions
    ]
    selected = sorted(
        candidates,
        key=lambda dimension: _dimension_priority(profile, dimension),
    )[: max(0, min(max_questions, 3))]
    questions: List[InterviewQuestion] = []
    for dimension in selected:
        current = getattr(profile.dna, dimension)
        label = DIMENSION_VI[dimension]
        observed = current.description or "chưa có đủ bằng chứng"
        questions.append(
            InterviewQuestion(
                dimension=dimension,
                question=(
                    f"Mẫu hiện đang cho thấy {label.lower()} như thế nào, và bạn "
                    "muốn giữ hay thay đổi đặc điểm đó khi viết?"
                ),
                context=(
                    f"Quan sát hiện tại: “{observed}”. "
                    f"Độ chắc chắn: {current.confidence:.2f}."
                ),
            )
        )
    return questions


def propose_interview_patch(
    profile: StyleProfile,
    questions: List[InterviewQuestion],
    answers: Mapping[str, str],
) -> InterviewPatchPayload:
    usable = [
        {
            "question_id": question.id,
            "dimension": question.dimension,
            "question": question.question,
            "answer": answers.get(question.id, "").strip(),
        }
        for question in questions
        if answers.get(question.id, "").strip()
    ]
    if not usable:
        return InterviewPatchPayload()
    current = [
        {
            "dimension": item["dimension"],
            "profile": getattr(profile.dna, item["dimension"]).model_dump(),
        }
        for item in usable
        if profile.dna
    ]
    try:
        response = call_gemini(
            build_interview_patch_prompt(current, usable),
            stage_id="voice_lab_interview_patch",
            temperature=0.1,
            max_output_tokens=4096,
            config={
                "response_mime_type": "application/json",
                "response_schema": interview_patch_schema(),
            },
        )
        patch = InterviewPatchPayload.model_validate_json(response)
    except ValidationError as exc:
        raise AnalysisError(
            "invalid_model_output",
            "Gemini trả patch phỏng vấn không đúng cấu trúc.",
            detail=str(exc),
        ) from exc
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(
            "gemini_unavailable",
            "Không thể tạo đề xuất từ câu trả lời phỏng vấn.",
            retryable=True,
            detail=str(exc),
        ) from exc
    allowed = {item["dimension"] for item in usable}
    patch.changes = [item for item in patch.changes if item.dimension in allowed]
    return patch


def apply_interview_patch(
    profile: StyleProfile,
    patch: InterviewPatchPayload,
    questions: List[InterviewQuestion],
    answers: Mapping[str, str],
    *,
    confirmed: bool,
) -> StyleProfile:
    if not confirmed:
        raise ValueError("Interview patch phải được người dùng xác nhận trước khi áp dụng.")
    if not profile.dna:
        raise ValueError("Profile chưa có Voice DNA để cập nhật.")
    updated = profile.model_copy(deep=True)
    question_by_dimension = {item.dimension: item for item in questions}
    for change in patch.changes:
        if change.dimension not in VOICE_DIMENSIONS:
            continue
        question = question_by_dimension.get(change.dimension)
        if question is None:
            continue
        before = getattr(updated.dna, change.dimension).model_copy(deep=True)
        after = DimensionProfile(
            description=change.description,
            strength=change.strength,
            confidence=max(before.confidence, 0.95),
            do=change.do,
            avoid=change.avoid,
            examples=before.examples,
            evidence_ids=before.evidence_ids,
            source="interview",
        )
        setattr(updated.dna, change.dimension, after)
        updated.interview_history.append(
            InterviewRecord(
                question_id=question.id,
                dimension=change.dimension,
                answer=answers.get(question.id, ""),
                before=before,
                after=after,
            )
        )
    if patch.changes:
        updated.revision += 1
        updated.updated_at = utc_now()
        updated.confidence = compute_profile_confidence(updated)
    return updated


def calibrate_ab(
    dimension: str,
    profile: StyleProfile,
    *,
    content_brief: str = DEFAULT_CONTENT_BRIEF,
    rng: Optional[random.Random] = None,
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
        response = call_gemini(
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
            length < CALIBRATION_MIN_WORDS or length > CALIBRATION_MAX_WORDS
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
    if session.selected is not None:
        raise ValueError("Calibration session đã được áp dụng.")
    if not profile.dna:
        raise ValueError("Profile chưa có Voice DNA để cập nhật.")
    updated = profile.model_copy(deep=True)
    dimension = getattr(updated.dna, session.dimension)
    before_strength = dimension.strength
    direction = session.shuffle_mapping[selected]
    delta = 0.15 if direction == "amplified" else -0.15
    dimension.strength = max(0.0, min(1.0, before_strength + delta))
    dimension.confidence = max(dimension.confidence, 0.95)
    dimension.source = "calibration"
    selected_text = session.variant_a if selected == "A" else session.variant_b
    if selected_text not in dimension.examples:
        dimension.examples.append(selected_text)
    session.selected = selected
    updated.calibration_history.append(
        CalibrationRecord(
            session_id=session.session_id,
            dimension=session.dimension,
            selected_label=selected,
            selected_direction=direction,
            selected_text=selected_text,
            before_strength=before_strength,
            after_strength=dimension.strength,
        )
    )
    updated.revision += 1
    updated.updated_at = utc_now()
    updated.confidence = compute_profile_confidence(updated)
    return updated
