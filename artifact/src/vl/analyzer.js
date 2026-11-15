// Port của engine/voice_lab/analyzer.py và parser.py: chia mẫu văn theo ngân sách, gọi model
// trả JSON, kiểm tra schema (fail-closed) và quote khớp nguyên văn, gộp và khử trùng evidence,
// tính confidence bằng code. Client gọi model được inject; không chạm DOM, không lưu trữ.
//
// Khác bản Python có chủ đích:
// - Ngoài ngân sách token như Python, mỗi prompt còn phải vừa giới hạn byte của `sample`.
//   Prompt quá lớn thì giảm một nửa ngân sách và chia lại (tất định); vừa ngân sách thì
//   chia giống hệt Python.
// - Không có kiểm tra "token prompt + token output > context" của Gemini; thay bằng kiểm tra byte.
// - Mã "gemini_unavailable" đổi thành "model_unavailable"; thông báo nói "Claude".
import { pyFind, pyLen, pyRound, pyStrip } from "../core/pycompat.js";
import { computeProfileConfidence, defaultNewId, dimensionProfile, evidenceClaim, styleProfile, VoiceLabError } from "./models.js";
import { buildAnalysisPrompt, buildSynthesisPrompt, withResponseSchema } from "./prompts.js";
import { parseWithSchema, SchemaError } from "./schema.js";

export const DEFAULT_MAX_PROMPT_BYTES = 256 * 1024;
const MIN_TOKEN_BUDGET = 1000;
const utf8Bytes = (text) => new TextEncoder().encode(text).length;

/** estimate_tokens: ước lượng thận trọng theo code point, ký tự ngoài ASCII tính đắt hơn. */
export function estimateTokens(text, consts) {
  if (!text) return 0;
  let ascii = 0;
  let total = 0;
  for (const ch of text) {
    total += 1;
    if (ch.codePointAt(0) < 128) ascii += 1;
  }
  return Math.max(1, Math.ceil(ascii / consts.ascii_chars_per_token) + Math.ceil((total - ascii) / consts.non_ascii_chars_per_token));
}

function tokenCounter(content, consts) {
  const points = [...content];
  const asciiPrefix = new Int32Array(points.length + 1);
  points.forEach((ch, i) => (asciiPrefix[i + 1] = asciiPrefix[i] + (ch.codePointAt(0) < 128 ? 1 : 0)));
  const estimate = (start, end) => {
    if (end <= start) return 0;
    const ascii = asciiPrefix[end] - asciiPrefix[start];
    return Math.max(1, Math.ceil(ascii / consts.ascii_chars_per_token) + Math.ceil((end - start - ascii) / consts.non_ascii_chars_per_token));
  };
  return { points, estimate };
}

/** _max_chunk_end: vị trí cắt lớn nhất (theo code point) còn vừa ngân sách. */
function maxChunkEnd(counter, start, budget) {
  let low = start + 1;
  let high = counter.points.length;
  let best = low;
  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    if (counter.estimate(start, middle) <= budget) {
      best = middle;
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return best;
}

/** _prepare_samples: bỏ mẫu rỗng nhưng giữ số thứ tự gốc trong sample_id. */
export function prepareSamples(samples) {
  const prepared = [];
  samples.forEach((sample, index) => {
    if (sample && pyStrip(sample)) prepared.push({ sample_id: `sample_${index + 1}`, content: sample.replaceAll("\r\n", "\n") });
  });
  if (!prepared.length) throw new VoiceLabError("insufficient_valid_evidence", "Cần ít nhất một mẫu bài viết không rỗng.");
  return prepared;
}

/** _chunk_samples: cắt mẫu dài có gối đầu, rồi gom thành các lô vừa ngân sách. */
export function chunkSamples(samples, budget, consts) {
  const units = [];
  for (const sample of samples) {
    const content = sample.content;
    if (estimateTokens(content, consts) <= budget) {
      units.push(sample);
      continue;
    }
    const counter = tokenCounter(content, consts);
    let start = 0;
    while (start < counter.points.length) {
      const end = maxChunkEnd(counter, start, budget);
      units.push({ sample_id: sample.sample_id, content: counter.points.slice(start, end).join("") });
      if (end === counter.points.length) break;
      start = Math.max(start + 1, end - consts.chunk_overlap_chars);
    }
  }
  const batches = [];
  let current = [];
  let currentTokens = 0;
  for (const unit of units) {
    const size = estimateTokens(unit.content, consts);
    if (current.length && currentTokens + size > budget) {
      batches.push(current);
      current = [];
      currentTokens = 0;
    }
    current.push(unit);
    currentTokens += size;
  }
  if (current.length) batches.push(current);
  return batches;
}

/** validate_evidence: quote phải khớp nguyên văn; quote_start/end tính theo code point. */
export function validateEvidence(evidence, samplesById, { dimensions, newId = defaultNewId }) {
  const active = [];
  const rejected = [];
  const returnedByDimension = {};
  for (const item of evidence) {
    const dimension = String(item.dimension ?? "");
    returnedByDimension[dimension] = (returnedByDimension[dimension] || 0) + 1;
    const claim = evidenceClaim(item, newId);
    const sample = Object.prototype.hasOwnProperty.call(samplesById, claim.sample_id) ? samplesById[claim.sample_id] : undefined;
    let reason = null;
    if (!dimensions.includes(dimension)) reason = "unknown_dimension";
    else if (sample === undefined) reason = "unknown_sample_id";
    else if (!claim.exact_quote) reason = "empty_quote";
    else {
      const normalizedSample = sample.replaceAll("\r\n", "\n");
      const normalizedQuote = claim.exact_quote.replaceAll("\r\n", "\n");
      const start = pyFind(normalizedSample, normalizedQuote);
      if (start < 0) reason = "quote_not_exact";
      else {
        claim.quote_start = start;
        claim.quote_end = start + pyLen(normalizedQuote);
      }
    }
    if (reason) {
      claim.status = "rejected";
      claim.rejection_reason = reason;
      rejected.push(claim);
    } else {
      active.push(claim);
    }
  }
  return { active, rejected, returnedByDimension };
}

/** build_voice_dna: confidence = độ phủ, độ nhất quán, tỉ lệ quote hợp lệ; trần theo số mẫu. */
export function buildVoiceDna(rawDna, active, rejected, returnedByDimension, totalSamples, dimensions) {
  const values = {};
  const cap = totalSamples === 1 ? 0.55 : totalSamples === 2 ? 0.75 : 0.9;
  for (const dimension of dimensions) {
    const evidence = active.filter((item) => item.dimension === dimension);
    if (!evidence.length) {
      values[dimension] = dimensionProfile();
      continue;
    }
    const supportingSamples = new Set(evidence.filter((item) => item.stance === "support").map((item) => item.sample_id));
    const supportCount = evidence.filter((item) => item.stance === "support").length;
    const contradictCount = evidence.filter((item) => item.stance === "contradict").length;
    const coverage = supportingSamples.size / Math.max(totalSamples, 1);
    const consistency = supportCount / Math.max(supportCount + contradictCount, 1);
    const returned = Object.prototype.hasOwnProperty.call(returnedByDimension, dimension) ? returnedByDimension[dimension] : evidence.length;
    const quoteValidity = evidence.length / Math.max(returned, 1);
    const confidence = Math.min(cap, 0.45 * coverage + 0.35 * consistency + 0.2 * quoteValidity);
    const raw = rawDna[dimension] || {};
    values[dimension] = dimensionProfile({
      description: pyStrip(String(raw.description ?? "")),
      strength: Number(raw.strength ?? 0.5),
      confidence: pyRound(confidence, 4),
      do: (raw.do || []).map(String).filter((item) => pyStrip(item)),
      avoid: (raw.avoid || []).map(String).filter((item) => pyStrip(item)),
      evidence_ids: evidence.map((item) => item.id),
      source: "analysis",
    });
  }
  return values;
}

/** _dedupe_evidence: bỏ evidence trùng (sample, chiều, quote, stance), giữ cái đầu. */
export function dedupeEvidence(items) {
  const seen = new Set();
  return items.filter((item) => {
    const key = JSON.stringify([item.sample_id, item.dimension, item.exact_quote, item.stance]);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function profileFromPayload({ slug, mode, rawDna, active, rejected, returnedByDimension, warnings, sampleCount, dimensions, now }) {
  if (!active.length) throw new VoiceLabError("insufficient_valid_evidence", "Claude không trả bằng chứng nguyên văn hợp lệ. Profile chưa được tạo.", { apiCalled: true });
  const dna = buildVoiceDna(rawDna, active, rejected, returnedByDimension, sampleCount, dimensions);
  const missing = dimensions.filter((name) => !dna[name].description);
  if (missing.length) warnings.push("Chưa đủ evidence cho các chiều: " + missing.join(", "));
  const profile = styleProfile(
    { slug, mode, status: "draft", dna, evidence: active, rejected_evidence: rejected, analysis_status: "complete", analysis_warnings: warnings, is_draft: true },
    now,
  );
  profile.confidence = computeProfileConfidence(profile, dimensions);
  return profile;
}

/**
 * Gọi model một lần và kiểm tra JSON theo schema.
 * client.json({prompt, modelConfig, stageId, signal}) -> {value, modelApplied?, tierApplied?, truncated?}
 */
export async function callStructured({ client, prompt, stageId, modelConfig, schema, signal, maxPromptBytes, telemetry, messages }) {
  const bytes = utf8Bytes(prompt);
  if (bytes > maxPromptBytes) {
    throw new VoiceLabError("input_too_large", "Prompt Voice Lab vượt ngân sách an toàn. Vui lòng giảm số lượng hoặc độ dài mẫu.", {
      detail: `prompt_bytes=${bytes}, max_prompt_bytes=${maxPromptBytes}`,
    });
  }
  const started = Date.now();
  const record = { stage_id: stageId, model: modelConfig.model, effort: modelConfig.effort, prompt_bytes: bytes, status: "failed", api_called: false };
  telemetry.push(record);
  let response;
  try {
    response = await client.json({ prompt, modelConfig, stageId, signal });
  } catch (error) {
    record.duration_ms = Date.now() - started;
    record.error_code = (error && error.code) || null;
    if (error && error.code === "invalid_json") {
      record.api_called = true;
      throw new VoiceLabError("invalid_model_output", messages.invalid, { detail: error.message || "", apiCalled: true });
    }
    if (error && error.code === "cancelled") throw new VoiceLabError("cancelled", "Đã dừng theo yêu cầu.", { apiCalled: Boolean(error.apiCalled) });
    record.api_called = Boolean(error && error.apiCalled);
    throw new VoiceLabError("model_unavailable", messages.unavailable, { retryable: true, detail: (error && error.message) || String(error), apiCalled: record.api_called });
  }
  record.duration_ms = Date.now() - started;
  record.api_called = true;
  record.model_applied = response.modelApplied ?? null;
  record.tier_applied = response.tierApplied ?? null;
  record.truncated = Boolean(response.truncated);
  try {
    const value = parseWithSchema(schema, response.value);
    record.status = "completed";
    return value;
  } catch (error) {
    record.error_code = "invalid_model_output";
    if (error instanceof SchemaError) throw new VoiceLabError("invalid_model_output", messages.invalid, { detail: error.message, apiCalled: true });
    throw error;
  }
}

const ANALYSIS_MESSAGES = {
  invalid: "Claude trả kết quả không đúng cấu trúc. Vui lòng thử lại.",
  unavailable: "Không gọi được Claude. Vui lòng thử lại sau.",
};
const SYNTHESIS_MESSAGES = {
  invalid: "Claude trả kết quả tổng hợp không đúng cấu trúc. Vui lòng thử lại.",
  unavailable: "Không gọi được Claude. Vui lòng thử lại sau.",
};

/**
 * Chọn cách chạy: một lượt nếu tổng mẫu vừa ngân sách token và prompt vừa giới hạn byte;
 * không thì chia lô, giảm một nửa ngân sách cho tới khi mọi prompt vừa giới hạn byte.
 */
export function planAnalysis(prepared, { consts, dimensions, schemaText, tokenBudget, maxPromptBytes }) {
  const promptFor = (samples) => withResponseSchema(buildAnalysisPrompt(samples, dimensions), schemaText);
  const total = prepared.reduce((sum, item) => sum + estimateTokens(item.content, consts), 0);
  if (total <= tokenBudget) {
    const prompt = promptFor(prepared);
    if (utf8Bytes(prompt) <= maxPromptBytes) return { routing: "single_pass", totalTokens: total, batches: [prepared], prompts: [prompt], tokenBudget };
  }
  for (let budget = tokenBudget; budget >= MIN_TOKEN_BUDGET; budget = Math.floor(budget / 2)) {
    const batches = chunkSamples(prepared, budget, consts);
    const prompts = batches.map(promptFor);
    if (prompts.every((prompt) => utf8Bytes(prompt) <= maxPromptBytes)) {
      if (batches.length > consts.max_analysis_batches) {
        throw new VoiceLabError("input_too_large", "Tổng dung lượng mẫu vượt giới hạn phân tích an toàn. Vui lòng rút gọn hoặc chia thành nhiều profile.");
      }
      return { routing: "multi_pass", totalTokens: total, batches, prompts, tokenBudget: budget };
    }
  }
  throw new VoiceLabError("input_too_large", "Mẫu văn quá lớn so với giới hạn của một lần gọi Claude. Vui lòng rút gọn mẫu.");
}

/**
 * analyze_samples. Trả AnalysisResult cùng dạng Python, kèm `telemetry` (mỗi lần gọi model).
 * @param bundle  bundle (dùng voice_lab.* và models.voice_lab)
 * @param client  client có hàm json(...)
 */
export async function analyzeSamples({
  bundle,
  samples,
  slug = "temp",
  mode = "deep",
  client,
  signal,
  tokenBudget = null,
  maxPromptBytes = DEFAULT_MAX_PROMPT_BYTES,
  newId = defaultNewId,
  now = null,
}) {
  const vl = bundle.voice_lab;
  const consts = vl.analysis;
  const dimensions = vl.dimensions;
  const budget = tokenBudget ?? Math.floor(consts.default_context_tokens * consts.input_budget_ratio);
  const telemetry = [];
  const prepared = prepareSamples(samples);
  const samplesById = Object.fromEntries(prepared.map((item) => [item.sample_id, item.content]));
  const plan = planAnalysis(prepared, { consts, dimensions, schemaText: vl.schema_texts.analysis_payload, tokenBudget: budget, maxPromptBytes });
  const analysisModel = bundle.models.voice_lab.vl_analysis;
  const common = { client, signal, maxPromptBytes, telemetry };

  try {
    if (plan.routing === "single_pass") {
      const payload = await callStructured({ ...common, prompt: plan.prompts[0], stageId: "voice_lab_analyze", modelConfig: analysisModel, schema: vl.schemas.analysis_payload, messages: ANALYSIS_MESSAGES });
      const { active, rejected, returnedByDimension } = validateEvidence(payload.evidence, samplesById, { dimensions, newId });
      const warnings = [...payload.warnings];
      if (rejected.length) warnings.push(`Đã loại ${rejected.length} evidence không hợp lệ.`);
      const profile = profileFromPayload({ slug, mode, rawDna: payload.dna, active, rejected, returnedByDimension, warnings, sampleCount: prepared.length, dimensions, now });
      return {
        profile,
        rejected_evidence: rejected,
        warnings,
        routing_mode: "single_pass",
        usage: { estimated_input_tokens: plan.totalTokens, api_calls: 1 },
        telemetry,
      };
    }

    let allActive = [];
    const allRejected = [];
    const allCounts = {};
    const batchDimensions = [];
    const warnings = [];
    for (let index = 0; index < plan.batches.length; index += 1) {
      const payload = await callStructured({
        ...common,
        prompt: plan.prompts[index],
        stageId: `voice_lab_analyze_batch_${index + 1}`,
        modelConfig: analysisModel,
        schema: vl.schemas.analysis_payload,
        messages: ANALYSIS_MESSAGES,
      });
      const { active, rejected, returnedByDimension } = validateEvidence(payload.evidence, samplesById, { dimensions, newId });
      allActive.push(...active);
      allRejected.push(...rejected);
      warnings.push(...payload.warnings);
      batchDimensions.push(Object.fromEntries(Object.entries(payload.dna).filter(([name]) => dimensions.includes(name))));
      for (const [dimension, count] of Object.entries(returnedByDimension)) allCounts[dimension] = (allCounts[dimension] || 0) + count;
    }
    allActive = dedupeEvidence(allActive);
    if (!allActive.length) throw new VoiceLabError("insufficient_valid_evidence", "Claude không trả bằng chứng nguyên văn hợp lệ. Profile chưa được tạo.", { apiCalled: true });
    const synthesis = await callStructured({
      ...common,
      prompt: withResponseSchema(buildSynthesisPrompt(allActive, batchDimensions), vl.schema_texts.synthesis_payload),
      stageId: "voice_lab_synthesize",
      modelConfig: bundle.models.voice_lab.vl_synthesis,
      schema: vl.schemas.synthesis_payload,
      messages: SYNTHESIS_MESSAGES,
    });
    warnings.push(...synthesis.warnings);
    if (allRejected.length) warnings.push(`Đã loại ${allRejected.length} evidence không hợp lệ.`);
    const profile = profileFromPayload({ slug, mode, rawDna: synthesis.dna, active: allActive, rejected: allRejected, returnedByDimension: allCounts, warnings, sampleCount: prepared.length, dimensions, now });
    return {
      profile,
      rejected_evidence: allRejected,
      warnings,
      routing_mode: "multi_pass",
      usage: { estimated_input_tokens: plan.totalTokens, api_calls: plan.batches.length + 1 },
      telemetry,
    };
  } catch (error) {
    if (error instanceof VoiceLabError) error.telemetry = telemetry;
    throw error;
  }
}
