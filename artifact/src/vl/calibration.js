// Port của calibration.py: A/B mù chỉ thay đúng một chiều. Nhãn A/B gán ngẫu nhiên;
// `shuffle_mapping` không có trong dữ liệu hiển thị (blindCalibrationView).
import { pySplitWhitespace, pyStrip } from "../core/pycompat.js";
import { callStructured, DEFAULT_MAX_PROMPT_BYTES } from "./analyzer.js";
import { clone, computeProfileConfidence, defaultNewId, isoNow, VoiceLabError } from "./models.js";
import { buildCalibrationPrompt, withResponseSchema } from "./prompts.js";

function defaultRandom() {
  const bytes = new Uint32Array(1);
  globalThis.crypto.getRandomValues(bytes);
  return bytes[0] / 2 ** 32;
}

/** calibrate_ab: model viết hai bản (đậm/tiết chế) cho một chiều; kiểm tra 90–165 từ. */
export async function calibrateAb({
  bundle,
  dimension,
  profile,
  contentBrief = null,
  client,
  signal,
  random = defaultRandom,
  newId = defaultNewId,
  now = null,
  maxPromptBytes = DEFAULT_MAX_PROMPT_BYTES,
}) {
  const vl = bundle.voice_lab;
  const brief = contentBrief ?? vl.calibration.default_content_brief;
  if (!vl.dimensions.includes(dimension)) throw new Error(`Dimension không hợp lệ: ${dimension}`);
  if (!profile.dna) throw new Error("Profile chưa có Voice DNA để calibration.");
  const target = profile.dna[dimension];
  if (!target.description) throw new Error(`Dimension '${dimension}' chưa có mô tả để calibration.`);
  const fixedConstraints = Object.fromEntries(
    vl.dimensions.filter((name) => name !== dimension && profile.dna[name].description).map((name) => [name, profile.dna[name].description]),
  );
  const telemetry = [];
  let payload;
  try {
    payload = await callStructured({
      client,
      signal,
      maxPromptBytes,
      telemetry,
      prompt: withResponseSchema(buildCalibrationPrompt(dimension, target.description, brief, fixedConstraints), vl.schema_texts.calibration_payload),
      stageId: "voice_lab_calibrate",
      modelConfig: bundle.models.voice_lab.vl_calibration,
      schema: vl.schemas.calibration_payload,
      messages: { invalid: "Claude trả hai biến thể A/B không đúng cấu trúc.", unavailable: "Không thể tạo bài thử A/B từ Claude." },
    });
    const amplified = pyStrip(payload.variant_amplified);
    const restrained = pyStrip(payload.variant_restrained);
    const lengths = [pySplitWhitespace(amplified).length, pySplitWhitespace(restrained).length];
    const { min_words: min, max_words: max } = vl.calibration;
    if (!amplified || !restrained || amplified === restrained || lengths.some((length) => length < min || length > max)) {
      throw new VoiceLabError("invalid_model_output", "Hai biến thể A/B chưa đạt khoảng dung sai 90–165 từ. Vui lòng tạo lại.", { apiCalled: true });
    }
    const keep = random() < 0.5;
    return {
      session: {
        session_id: newId(),
        dimension,
        content_brief: brief,
        variant_a: keep ? amplified : restrained,
        variant_b: keep ? restrained : amplified,
        shuffle_mapping: keep ? { A: "amplified", B: "restrained" } : { A: "restrained", B: "amplified" },
        selected: null,
        created_at: isoNow(now),
      },
      telemetry,
    };
  } catch (error) {
    if (error instanceof VoiceLabError) error.telemetry = telemetry;
    throw error;
  }
}

/** Dữ liệu được phép hiển thị trước khi chọn: không có shuffle_mapping. */
export function blindCalibrationView(session) {
  return { session_id: session.session_id, dimension: session.dimension, content_brief: session.content_brief, variant_a: session.variant_a, variant_b: session.variant_b };
}

/** apply_calibration_selection: chỉnh strength ±0.15 của đúng một chiều, lưu lịch sử. */
export function applyCalibrationSelection(profile, session, selected, { bundle, now = null }) {
  if (selected !== "A" && selected !== "B") throw new Error("Lựa chọn calibration phải là A hoặc B.");
  if (session.selected !== null || profile.calibration_history.some((record) => record.session_id === session.session_id)) {
    throw new Error("Calibration session đã được áp dụng.");
  }
  if (!profile.dna) throw new Error("Profile chưa có Voice DNA để cập nhật.");
  const vl = bundle.voice_lab;
  const updated = clone(profile);
  const dimension = updated.dna[session.dimension];
  const beforeStrength = dimension.strength;
  const beforeConfidence = dimension.confidence;
  const direction = session.shuffle_mapping[selected];
  const delta = direction === "amplified" ? 0.15 : -0.15;
  dimension.strength = Math.max(0.0, Math.min(1.0, beforeStrength + delta));
  dimension.confidence = Math.max(dimension.confidence, vl.calibration.direct_user_confirmation_confidence);
  dimension.source = "calibration";
  const selectedText = selected === "A" ? session.variant_a : session.variant_b;
  if (!dimension.examples.includes(selectedText)) dimension.examples.push(selectedText);
  updated.calibration_history.push({
    session_id: session.session_id,
    dimension: session.dimension,
    selected_label: selected,
    selected_direction: direction,
    selected_text: selectedText,
    before_strength: beforeStrength,
    after_strength: dimension.strength,
    before_confidence: beforeConfidence,
    after_confidence: dimension.confidence,
    confirmation_source: "blind_ab_user_selection",
    confirmed_at: isoNow(now),
  });
  updated.revision += 1;
  updated.updated_at = isoNow(now);
  updated.confidence = computeProfileConfidence(updated, vl.dimensions);
  return updated;
}
