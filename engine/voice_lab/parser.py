from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Tuple

from pydantic import ValidationError

from engine.voice_lab.models import (
    AnalysisError,
    DimensionProfile,
    EvidenceClaim,
    VOICE_DIMENSIONS,
    VoiceDNA,
)
from engine.voice_lab.prompts import ModelAnalysisPayload, ModelSynthesisPayload


def parse_analysis_response(response: str) -> ModelAnalysisPayload:
    try:
        return ModelAnalysisPayload.model_validate_json(response)
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        raise AnalysisError(
            "invalid_model_output",
            "Gemini trả kết quả không đúng cấu trúc. Vui lòng thử lại.",
            detail=str(exc),
        ) from exc


def parse_synthesis_response(response: str) -> ModelSynthesisPayload:
    try:
        return ModelSynthesisPayload.model_validate_json(response)
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        raise AnalysisError(
            "invalid_model_output",
            "Gemini trả kết quả tổng hợp không đúng cấu trúc. Vui lòng thử lại.",
            detail=str(exc),
        ) from exc


def validate_evidence(
    evidence: Iterable[Any],
    samples_by_id: Dict[str, str],
) -> Tuple[List[EvidenceClaim], List[EvidenceClaim], Dict[str, int]]:
    active: List[EvidenceClaim] = []
    rejected: List[EvidenceClaim] = []
    returned_by_dimension: Dict[str, int] = {}
    for raw in evidence:
        item = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
        dimension = str(item.get("dimension", ""))
        returned_by_dimension[dimension] = returned_by_dimension.get(dimension, 0) + 1
        claim = EvidenceClaim.model_validate(item)
        sample = samples_by_id.get(claim.sample_id)
        reason = None
        if dimension not in VOICE_DIMENSIONS:
            reason = "unknown_dimension"
        elif sample is None:
            reason = "unknown_sample_id"
        elif not claim.exact_quote:
            reason = "empty_quote"
        else:
            normalized_sample = sample.replace("\r\n", "\n")
            normalized_quote = claim.exact_quote.replace("\r\n", "\n")
            start = normalized_sample.find(normalized_quote)
            if start < 0:
                reason = "quote_not_exact"
            else:
                claim.quote_start = start
                claim.quote_end = start + len(normalized_quote)
        if reason:
            claim.status = "rejected"
            claim.rejection_reason = reason
            rejected.append(claim)
        else:
            active.append(claim)
    return active, rejected, returned_by_dimension


def build_voice_dna(
    raw_dna: Dict[str, Any],
    active: List[EvidenceClaim],
    rejected: List[EvidenceClaim],
    returned_by_dimension: Dict[str, int],
    total_samples: int,
) -> VoiceDNA:
    values: Dict[str, DimensionProfile] = {}
    cap = 0.55 if total_samples == 1 else 0.75 if total_samples == 2 else 0.90
    for dimension in VOICE_DIMENSIONS:
        evidence = [item for item in active if item.dimension == dimension]
        if not evidence:
            values[dimension] = DimensionProfile()
            continue
        supporting_samples = {
            item.sample_id for item in evidence if item.stance == "support"
        }
        support_count = sum(item.stance == "support" for item in evidence)
        contradict_count = sum(item.stance == "contradict" for item in evidence)
        coverage = len(supporting_samples) / max(total_samples, 1)
        consistency = support_count / max(support_count + contradict_count, 1)
        returned = returned_by_dimension.get(dimension, len(evidence))
        quote_validity = len(evidence) / max(returned, 1)
        confidence = min(
            cap,
            0.45 * coverage + 0.35 * consistency + 0.20 * quote_validity,
        )
        raw = raw_dna.get(dimension)
        raw_data = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw or {})
        values[dimension] = DimensionProfile(
            description=str(raw_data.get("description", "")).strip(),
            strength=float(raw_data.get("strength", 0.5)),
            confidence=round(confidence, 4),
            do=[str(item) for item in raw_data.get("do", []) if str(item).strip()],
            avoid=[
                str(item) for item in raw_data.get("avoid", []) if str(item).strip()
            ],
            evidence_ids=[item.id for item in evidence],
            source="analysis",
        )
    return VoiceDNA.model_validate(values)
