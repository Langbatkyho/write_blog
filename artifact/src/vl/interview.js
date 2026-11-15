// Port của interview_routing.py và profile_patch.py: chọn tối đa 3 chiều yếu nhất để hỏi,
// nhờ model đề xuất patch, và chỉ áp dụng patch khi người dùng xác nhận.
import { pyFormatFixed, pyStrip } from "../core/pycompat.js";
import { callStructured, DEFAULT_MAX_PROMPT_BYTES } from "./analyzer.js";
import { clone, computeProfileConfidence, defaultNewId, dimensionProfile, isoNow, VoiceLabError } from "./models.js";
import { buildInterviewPatchPrompt, withResponseSchema } from "./prompts.js";

function compareTuples(a, b) {
  for (let i = 0; i < a.length; i += 1) {
    const x = typeof a[i] === "boolean" ? Number(a[i]) : a[i];
    const y = typeof b[i] === "boolean" ? Number(b[i]) : b[i];
    if (x < y) return -1;
    if (x > y) return 1;
  }
  return 0;
}

function priority(profile, dimension, dimensions) {
  const value = profile.dna ? profile.dna[dimension] : dimensionProfile();
  const contradictions = profile.evidence.filter((item) => item.dimension === dimension && item.stance === "contradict").length;
  const confirmed = profile.interview_history.some((record) => record.dimension === dimension);
  return [confirmed, Boolean(pyStrip(value.description)), value.confidence, -contradictions, dimensions.indexOf(dimension)];
}

/** generate_interview: chiều chưa xác nhận (hoặc có mâu thuẫn), yếu nhất trước, tối đa 3. */
export function generateInterview(profile, { bundle, maxQuestions = 3, newId = defaultNewId }) {
  if (!profile.dna) return [];
  const { dimensions, dimension_labels: labels } = bundle.voice_lab;
  const confirmed = new Set(profile.interview_history.map((record) => record.dimension));
  const contradicted = new Set(profile.evidence.filter((item) => item.stance === "contradict" && item.status === "active").map((item) => item.dimension));
  const candidates = dimensions.filter((dimension) => !confirmed.has(dimension) || contradicted.has(dimension));
  // Sắp xếp ổn định như sorted() của Python.
  const selected = candidates
    .map((dimension) => ({ dimension, key: priority(profile, dimension, dimensions) }))
    .sort((a, b) => compareTuples(a.key, b.key))
    .slice(0, Math.max(0, Math.min(maxQuestions, 3)))
    .map((item) => item.dimension);
  return selected.map((dimension) => {
    const current = profile.dna[dimension];
    const observed = current.description || "chưa có đủ bằng chứng";
    return {
      id: newId(),
      dimension,
      question: `Mẫu hiện đang cho thấy ${labels[dimension].toLowerCase()} như thế nào, và bạn muốn giữ hay thay đổi đặc điểm đó khi viết?`,
      context: `Quan sát hiện tại: “${observed}”. Độ chắc chắn: ${pyFormatFixed(current.confidence, 2)}.`,
    };
  });
}

/** Câu trả lời dùng được (không rỗng sau strip), theo thứ tự câu hỏi. */
export function usableAnswers(questions, answers) {
  return questions
    .filter((question) => pyStrip(answers[question.id] ?? ""))
    .map((question) => ({ question_id: question.id, dimension: question.dimension, question: question.question, answer: pyStrip(answers[question.id] ?? "") }));
}

/** propose_interview_patch: model đề xuất; chỉ giữ thay đổi cho chiều đã được hỏi và có trả lời. */
export async function proposeInterviewPatch({ bundle, profile, questions, answers, client, signal, maxPromptBytes = DEFAULT_MAX_PROMPT_BYTES }) {
  const usable = usableAnswers(questions, answers);
  const telemetry = [];
  if (!usable.length) return { patch: { changes: [] }, telemetry };
  const current = profile.dna ? usable.map((item) => ({ dimension: item.dimension, profile: profile.dna[item.dimension] })) : [];
  const vl = bundle.voice_lab;
  let patch;
  try {
    patch = await callStructured({
      client,
      signal,
      maxPromptBytes,
      telemetry,
      prompt: withResponseSchema(buildInterviewPatchPrompt(current, usable), vl.schema_texts.interview_patch_payload),
      stageId: "voice_lab_interview_patch",
      modelConfig: bundle.models.voice_lab.vl_interview_patch,
      schema: vl.schemas.interview_patch_payload,
      messages: { invalid: "Claude trả patch phỏng vấn không đúng cấu trúc.", unavailable: "Không thể tạo đề xuất từ câu trả lời phỏng vấn." },
    });
  } catch (error) {
    if (error instanceof VoiceLabError) error.telemetry = telemetry;
    throw error;
  }
  const allowed = new Set(usable.map((item) => item.dimension));
  patch.changes = patch.changes.filter((item) => allowed.has(item.dimension));
  return { patch, telemetry };
}

/** apply_interview_patch: bắt buộc `confirmed`; trả hồ sơ mới, hồ sơ cũ không đổi. */
export function applyInterviewPatch(profile, patch, questions, answers, { bundle, confirmed, now = null }) {
  if (!confirmed) throw new Error("Interview patch phải được người dùng xác nhận trước khi áp dụng.");
  if (!profile.dna) throw new Error("Profile chưa có Voice DNA để cập nhật.");
  const { dimensions } = bundle.voice_lab;
  const updated = clone(profile);
  const questionByDimension = new Map(questions.map((item) => [item.dimension, item]));
  let applied = 0;
  for (const change of patch.changes) {
    if (!dimensions.includes(change.dimension)) continue;
    const question = questionByDimension.get(change.dimension);
    if (!question) continue;
    const before = clone(updated.dna[change.dimension]);
    const after = dimensionProfile({
      description: change.description,
      strength: change.strength,
      confidence: Math.max(before.confidence, 0.95),
      do: change.do,
      avoid: change.avoid,
      examples: before.examples,
      evidence_ids: before.evidence_ids,
      source: "interview",
    });
    updated.dna[change.dimension] = after;
    updated.interview_history.push({
      question_id: question.id,
      dimension: change.dimension,
      answer: answers[question.id] ?? "",
      before,
      after: clone(after),
      confirmed_at: isoNow(now),
    });
    applied += 1;
  }
  if (applied) {
    updated.revision += 1;
    updated.updated_at = isoNow(now);
    updated.confidence = computeProfileConfidence(updated, dimensions);
  }
  return updated;
}
