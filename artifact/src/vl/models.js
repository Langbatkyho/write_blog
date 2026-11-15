// Dạng dữ liệu Voice Lab schema v2, cùng thứ tự trường với model_dump(mode="json") của
// engine/voice_lab/models.py. Hàm thuần: id và thời điểm được truyền vào để test tất định.
import { pyIsoUtc, pyRound } from "../core/pycompat.js";

export const SCHEMA_VERSION = 2;

/** Lỗi Voice Lab cùng mã với AnalysisError của engine; "gemini_unavailable" đổi thành "model_unavailable". */
export class VoiceLabError extends Error {
  constructor(code, userMessage, { retryable = false, detail = "", apiCalled = false } = {}) {
    super(userMessage);
    this.name = "VoiceLabError";
    this.code = code;
    this.userMessage = userMessage;
    this.retryable = retryable;
    this.detail = detail;
    this.apiCalled = apiCalled;
  }
}

export function defaultNewId() {
  return globalThis.crypto.randomUUID();
}

export const isoNow = (now) => pyIsoUtc(now || new Date());

export function dimensionProfile(values = {}) {
  return {
    description: values.description ?? "",
    strength: values.strength ?? 0.5,
    confidence: values.confidence ?? 0.0,
    do: [...(values.do ?? [])],
    avoid: [...(values.avoid ?? [])],
    examples: [...(values.examples ?? [])],
    evidence_ids: [...(values.evidence_ids ?? [])],
    source: values.source ?? "analysis",
  };
}

export function voiceDna(dimensions, values = {}) {
  return Object.fromEntries(dimensions.map((name) => [name, dimensionProfile(values[name])]));
}

export function evidenceClaim(item, newId) {
  return {
    id: item.id ?? newId(),
    sample_id: item.sample_id ?? "",
    dimension: item.dimension,
    claim: item.claim,
    exact_quote: item.exact_quote ?? "",
    quote_start: item.quote_start ?? null,
    quote_end: item.quote_end ?? null,
    stance: item.stance ?? "support",
    status: item.status ?? "active",
    rejection_reason: item.rejection_reason ?? null,
  };
}

/** model_validator enforce_publish_state: chưa phân tích xong thì luôn là draft. */
export function enforcePublishState(profile) {
  if (profile.analysis_status !== "complete") {
    profile.is_draft = true;
    if (profile.status === "confirmed") profile.status = "draft";
  }
  return profile;
}

export function styleProfile(values, now) {
  const time = isoNow(now);
  return enforcePublishState({
    schema_version: SCHEMA_VERSION,
    revision: values.revision ?? 1,
    slug: values.slug,
    mode: values.mode,
    status: values.status ?? "draft",
    provenance: values.provenance ?? "user_generated",
    confidence: values.confidence ?? 0.0,
    dna: values.dna ?? null,
    evidence: values.evidence ?? [],
    rejected_evidence: values.rejected_evidence ?? [],
    analysis_status: values.analysis_status ?? "partial",
    analysis_warnings: values.analysis_warnings ?? [],
    interview_history: values.interview_history ?? [],
    calibration_history: values.calibration_history ?? [],
    base_style_slug: values.base_style_slug ?? "reflective",
    is_draft: values.is_draft ?? true,
    created_at: values.created_at ?? time,
    updated_at: values.updated_at ?? time,
  });
}

/** Các chiều có mô tả (VoiceDNA.non_empty_dimensions). */
export function nonEmptyDimensions(dna, dimensions) {
  return dimensions.filter((name) => dna[name].description.trim()).map((name) => dna[name]);
}

/** compute_profile_confidence: trung bình confidence của các chiều có mô tả, làm tròn 4 chữ số. */
export function computeProfileConfidence(profile, dimensions) {
  if (!profile.dna) return 0.0;
  const items = nonEmptyDimensions(profile.dna, dimensions);
  if (!items.length) return 0.0;
  let total = 0;
  for (const item of items) total += item.confidence;
  return pyRound(total / items.length, 4);
}

export const clone = (value) => structuredClone(value);
