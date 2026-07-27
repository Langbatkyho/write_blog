from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List

from engine.gemini_client import call_gemini
from engine.voice_lab.models import (
    AnalysisError,
    AnalysisResult,
    EvidenceClaim,
    StyleProfile,
    VOICE_DIMENSIONS,
    compute_profile_confidence,
)
from engine.voice_lab.parser import (
    build_voice_dna,
    parse_analysis_response,
    parse_synthesis_response,
    validate_evidence,
)
from engine.voice_lab.prompts import (
    analysis_schema,
    build_analysis_prompt,
    build_synthesis_prompt,
    synthesis_schema,
)


DEFAULT_CONTEXT_TOKENS = 200_000
INPUT_BUDGET_RATIO = 0.70
CHUNK_OVERLAP_CHARS = 400
MAX_ANALYSIS_BATCHES = 24


def estimate_tokens(text: str) -> int:
    """Conservative tokenizer-free estimate suitable for routing."""
    return max(1, (len(text) + 3) // 4)


def _context_budget() -> int:
    raw = os.getenv("VOICE_LAB_GEMINI_CONTEXT_TOKENS", str(DEFAULT_CONTEXT_TOKENS))
    try:
        value = int(raw)
    except ValueError:
        value = DEFAULT_CONTEXT_TOKENS
    return max(value, 8_192)


def _output_budget(sample_count: int) -> int:
    return min(16_384, 4_096 + 512 * min(max(sample_count, 1), 12))


def _call_structured(
    prompt: str,
    *,
    stage_id: str,
    schema: Dict[str, Any],
    temperature: float = 0.1,
    max_output_tokens: int = 8192,
) -> str:
    required_tokens = estimate_tokens(prompt) + max_output_tokens
    context_budget = _context_budget()
    if required_tokens > context_budget:
        raise AnalysisError(
            "input_too_large",
            "Prompt Voice Lab vượt ngân sách context an toàn. "
            "Vui lòng giảm số lượng hoặc độ dài mẫu.",
            detail=(
                f"required_tokens={required_tokens}, "
                f"context_budget={context_budget}"
            ),
        )
    try:
        return call_gemini(
            prompt,
            stage_id=stage_id,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            config={
                "response_mime_type": "application/json",
                "response_schema": schema,
            },
        )
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(
            "gemini_unavailable",
            "Không thể kết nối Gemini sau các lần thử lại. Vui lòng thử lại sau.",
            retryable=True,
            detail=str(exc),
        ) from exc


def _prepare_samples(samples: Iterable[str]) -> List[Dict[str, str]]:
    prepared = [
        {"sample_id": f"sample_{index + 1}", "content": sample.replace("\r\n", "\n")}
        for index, sample in enumerate(samples)
        if sample and sample.strip()
    ]
    if not prepared:
        raise AnalysisError(
            "insufficient_valid_evidence",
            "Cần ít nhất một mẫu bài viết không rỗng.",
        )
    return prepared


def _chunk_samples(
    samples: List[Dict[str, str]],
    token_budget: int,
) -> List[List[Dict[str, str]]]:
    char_budget = max(2_000, token_budget * 4)
    units: List[Dict[str, str]] = []
    for sample in samples:
        content = sample["content"]
        if len(content) <= char_budget:
            units.append(sample)
            continue
        start = 0
        while start < len(content):
            end = min(len(content), start + char_budget)
            units.append(
                {
                    "sample_id": sample["sample_id"],
                    "content": content[start:end],
                }
            )
            if end == len(content):
                break
            start = max(start + 1, end - CHUNK_OVERLAP_CHARS)

    batches: List[List[Dict[str, str]]] = []
    current: List[Dict[str, str]] = []
    current_tokens = 0
    for unit in units:
        size = estimate_tokens(unit["content"])
        if current and current_tokens + size > token_budget:
            batches.append(current)
            current = []
            current_tokens = 0
        current.append(unit)
        current_tokens += size
    if current:
        batches.append(current)
    return batches


def _profile_from_payload(
    *,
    slug: str,
    mode: str,
    raw_dna: Dict[str, Any],
    active: List[EvidenceClaim],
    rejected: List[EvidenceClaim],
    returned_by_dimension: Dict[str, int],
    warnings: List[str],
    sample_count: int,
) -> StyleProfile:
    if not active:
        raise AnalysisError(
            "insufficient_valid_evidence",
            "Gemini không trả bằng chứng nguyên văn hợp lệ. Profile chưa được tạo.",
        )
    dna = build_voice_dna(
        raw_dna,
        active,
        rejected,
        returned_by_dimension,
        sample_count,
    )
    missing = [
        dimension
        for dimension in VOICE_DIMENSIONS
        if not getattr(dna, dimension).description
    ]
    if missing:
        warnings.append(
            "Chưa đủ evidence cho các chiều: " + ", ".join(missing)
        )
    profile = StyleProfile(
        slug=slug,
        mode=mode,
        status="draft",
        dna=dna,
        evidence=active,
        rejected_evidence=rejected,
        analysis_status="complete",
        analysis_warnings=warnings,
        is_draft=True,
    )
    profile.confidence = compute_profile_confidence(profile)
    return profile


def _dedupe_evidence(items: List[EvidenceClaim]) -> List[EvidenceClaim]:
    seen = set()
    unique = []
    for item in items:
        key = (
            item.sample_id,
            item.dimension,
            item.exact_quote,
            item.stance,
        )
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def analyze_samples(
    samples: List[str],
    *,
    slug: str = "temp",
    mode: str = "deep",
) -> AnalysisResult:
    prepared = _prepare_samples(samples)
    samples_by_id = {item["sample_id"]: item["content"] for item in prepared}
    input_budget = int(_context_budget() * INPUT_BUDGET_RATIO)
    total_tokens = sum(estimate_tokens(item["content"]) for item in prepared)

    if total_tokens <= input_budget:
        response = _call_structured(
            build_analysis_prompt(prepared),
            stage_id="voice_lab_analyze",
            schema=analysis_schema(),
            max_output_tokens=_output_budget(len(prepared)),
        )
        payload = parse_analysis_response(response)
        active, rejected, counts = validate_evidence(
            payload.evidence, samples_by_id
        )
        warnings = list(payload.warnings)
        if rejected:
            warnings.append(f"Đã loại {len(rejected)} evidence không hợp lệ.")
        profile = _profile_from_payload(
            slug=slug,
            mode=mode,
            raw_dna=payload.dna,
            active=active,
            rejected=rejected,
            returned_by_dimension=counts,
            warnings=warnings,
            sample_count=len(prepared),
        )
        return AnalysisResult(
            profile=profile,
            rejected_evidence=rejected,
            warnings=warnings,
            routing_mode="single_pass",
            usage={"estimated_input_tokens": total_tokens, "api_calls": 1},
        )

    batches = _chunk_samples(prepared, input_budget)
    if len(batches) > MAX_ANALYSIS_BATCHES:
        raise AnalysisError(
            "input_too_large",
            "Tổng dung lượng mẫu vượt giới hạn phân tích an toàn. "
            "Vui lòng rút gọn hoặc chia thành nhiều profile.",
        )
    all_active: List[EvidenceClaim] = []
    all_rejected: List[EvidenceClaim] = []
    all_counts: Dict[str, int] = {}
    batch_dimensions: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for index, batch in enumerate(batches):
        response = _call_structured(
            build_analysis_prompt(batch),
            stage_id=f"voice_lab_analyze_batch_{index + 1}",
            schema=analysis_schema(),
            max_output_tokens=_output_budget(len(batch)),
        )
        payload = parse_analysis_response(response)
        active, rejected, counts = validate_evidence(
            payload.evidence, samples_by_id
        )
        all_active.extend(active)
        all_rejected.extend(rejected)
        warnings.extend(payload.warnings)
        batch_dimensions.append(
            {
                name: value.model_dump()
                for name, value in payload.dna.items()
                if name in VOICE_DIMENSIONS
            }
        )
        for dimension, count in counts.items():
            all_counts[dimension] = all_counts.get(dimension, 0) + count

    all_active = _dedupe_evidence(all_active)
    if not all_active:
        raise AnalysisError(
            "insufficient_valid_evidence",
            "Gemini không trả bằng chứng nguyên văn hợp lệ. Profile chưa được tạo.",
        )
    synthesis_response = _call_structured(
        build_synthesis_prompt(
            [item.model_dump() for item in all_active],
            batch_dimensions,
        ),
        stage_id="voice_lab_synthesize",
        schema=synthesis_schema(),
    )
    synthesis = parse_synthesis_response(synthesis_response)
    warnings.extend(synthesis.warnings)
    if all_rejected:
        warnings.append(f"Đã loại {len(all_rejected)} evidence không hợp lệ.")
    profile = _profile_from_payload(
        slug=slug,
        mode=mode,
        raw_dna=synthesis.dna,
        active=all_active,
        rejected=all_rejected,
        returned_by_dimension=all_counts,
        warnings=warnings,
        sample_count=len(prepared),
    )
    return AnalysisResult(
        profile=profile,
        rejected_evidence=all_rejected,
        warnings=warnings,
        routing_mode="multi_pass",
        usage={
            "estimated_input_tokens": total_tokens,
            "api_calls": len(batches) + 1,
        },
    )
