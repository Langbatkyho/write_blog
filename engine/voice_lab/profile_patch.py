from __future__ import annotations

from typing import Callable, Mapping

from pydantic import ValidationError

from engine.gemini_client import call_gemini
from engine.voice_lab.models import (
    AnalysisError,
    DimensionProfile,
    InterviewQuestion,
    InterviewRecord,
    StyleProfile,
    VOICE_DIMENSIONS,
    compute_profile_confidence,
    utc_now,
)
from engine.voice_lab.prompts import (
    InterviewPatchPayload,
    build_interview_patch_prompt,
    interview_patch_schema,
)


GeminiCallable = Callable[..., str]


def propose_interview_patch(
    profile: StyleProfile,
    questions: list[InterviewQuestion],
    answers: Mapping[str, str],
    *,
    gemini_client: GeminiCallable = call_gemini,
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
        response = gemini_client(
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
    patch.changes = [
        item for item in patch.changes if item.dimension in allowed
    ]
    return patch


def apply_interview_patch(
    profile: StyleProfile,
    patch: InterviewPatchPayload,
    questions: list[InterviewQuestion],
    answers: Mapping[str, str],
    *,
    confirmed: bool,
) -> StyleProfile:
    if not confirmed:
        raise ValueError(
            "Interview patch phải được người dùng xác nhận trước khi áp dụng."
        )
    if not profile.dna:
        raise ValueError("Profile chưa có Voice DNA để cập nhật.")
    updated = profile.model_copy(deep=True)
    question_by_dimension = {item.dimension: item for item in questions}
    applied = 0
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
        applied += 1
    if applied:
        updated.revision += 1
        updated.updated_at = utc_now()
        updated.confidence = compute_profile_confidence(updated)
    return updated
