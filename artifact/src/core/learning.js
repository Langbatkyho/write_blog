// Learning loop trong Artifact (ART-5): port của engine/learning.py và cách
// engine/workflow_learning.py gọi model. Template văn bản lấy từ
// learning_templates.js (sinh từ mã nguồn engine), nên prompt và báo cáo offline
// khớp từng byte với Python. Không sửa skill (D3): chỉ tạo báo cáo để người viết đọc.
import {
  LEARNING_PROMPT_TEMPLATE,
  OFFLINE_REPORT_TEMPLATE,
  OFFLINE_TUNING_TEMPLATE,
  TUNING_PROMPT_TEMPLATE,
} from "./learning_templates.js";
import { collectFinalOutputs } from "./outputs.js";
import { countWords, estimateTokens } from "./parser.js";
import { pyDedent, pyFormatFixed, pySignedInt, pySplitlines, pyStr, pyStrip, PY_WS_CLASS, truncateWords } from "./pycompat.js";
import { SequenceMatcher, unifiedDiff } from "./pydifflib.js";
import { utcStamp } from "./run_record.js";

export const LEARNING_STAGES = ["editorial_learning", "workflow_tuning"];

export class LearningError extends Error {
  constructor(message, code = null) {
    super(message);
    this.name = "LearningError";
    this.code = code;
  }
}

function renderTemplate(segments, values) {
  return segments
    .map((segment) => {
      if ("text" in segment) return segment.text;
      if (!Object.prototype.hasOwnProperty.call(values, segment.expr)) throw new Error(`Thiếu giá trị cho ${segment.expr}`);
      const value = values[segment.expr];
      if (segment.spec === "") return pyStr(value);
      const fixed = /^\.(\d+)f$/.exec(segment.spec);
      if (fixed) return pyFormatFixed(value, Number(fixed[1]));
      if (segment.spec === "+d") return pySignedInt(value);
      throw new Error(`Format spec chưa hỗ trợ: ${segment.spec}`);
    })
    .join("");
}

const render = (segments, values) => pyStrip(pyDedent(renderTemplate(segments, values)));

function truncateToTokenBudget(text, maxTokens) {
  if (estimateTokens(text) <= maxTokens) return text;
  return truncateWords(text, Math.max(50, Math.trunc(maxTokens / 1.35)));
}

function budgetStepOutputs(stepOutputs, maxTokens) {
  const entries = Object.entries(stepOutputs);
  if (!entries.length) return {};
  const perStage = Math.max(50, Math.floor(maxTokens / entries.length));
  return Object.fromEntries(
    entries.map(([id, content]) => [
      id,
      estimateTokens(content) <= perStage ? content : truncateWords(content, Math.max(50, Math.trunc(perStage / 1.35))),
    ]),
  );
}

/** Port của build_learning_prompt. YAML của skill/workflow lấy từ bundle (do Python dựng sẵn). */
export function buildLearningPrompt({
  bundle,
  mode = "deep",
  style,
  authorInput,
  stepOutputs,
  finalBlog,
  productionBlog,
  comparisonLabel = "final_blog.md",
  maxContextTokens = 12000,
}) {
  const budgeted = budgetStepOutputs(stepOutputs, Math.floor(maxContextTokens / 4));
  const prompt = render(LEARNING_PROMPT_TEMPLATE, {
    mode,
    "yaml.safe_dump(learning_skill, allow_unicode=True, sort_keys=False)": bundle.learning.skill_yaml,
    workflow_yaml: bundle.learning.compact_workflow_yaml[mode],
    skills_yaml: bundle.styles[mode][style].learning_compact_skills_yaml,
    budgeted_author_input: truncateToTokenBudget(authorInput, Math.floor(maxContextTokens / 10)),
    step_outputs_block: Object.entries(budgeted).map(([name, content]) => `## ${name}\n\n${content}`).join("\n\n"),
    comparison_label: comparisonLabel,
    budgeted_final_blog: truncateToTokenBudget(finalBlog, Math.floor(maxContextTokens / 10)),
    budgeted_production_blog: truncateToTokenBudget(productionBlog, Math.floor((maxContextTokens * 15) / 100)),
  });
  const tokens = estimateTokens(prompt);
  if (tokens > maxContextTokens) {
    throw new LearningError(`Learning prompt vượt ngân sách context sau khi rút gọn: ${tokens}>${maxContextTokens} tokens.`, "budget_exceeded");
  }
  return prompt;
}

/** Port của build_tuning_prompt. */
export function buildTuningPrompt({ report, mode = "deep", stageIds = [], maxContextTokens = 6000 }) {
  const prompt = render(TUNING_PROMPT_TEMPLATE, {
    mode,
    budgeted_report: truncateToTokenBudget(report, Math.floor((maxContextTokens * 7) / 10)),
    stages_list: stageIds.join(", ") || "các stage có trong Flow",
  });
  const tokens = estimateTokens(prompt);
  if (tokens > maxContextTokens) {
    throw new LearningError(`Tuning prompt vượt ngân sách context sau khi rút gọn: ${tokens}>${maxContextTokens} tokens.`, "budget_exceeded");
  }
  return prompt;
}

/** Port của render_offline_diff. */
export function renderOfflineDiff(finalBlog, productionBlog, comparisonLabel = "final_blog.md") {
  const diff = unifiedDiff(pySplitlines(finalBlog), pySplitlines(productionBlog), {
    fromfile: comparisonLabel,
    tofile: "production_blog.md",
    lineterm: "",
  }).join("\n");
  return pyStrip(diff) ? diff : "Không phát hiện khác biệt theo từng dòng.";
}

const PARAGRAPH_BREAK = new RegExp(`\\n${PY_WS_CLASS}*\\n`);

/** Port của count_paragraphs. */
export function countParagraphs(text) {
  return pyStrip(text).split(PARAGRAPH_BREAK).filter((part) => pyStrip(part)).length;
}

/** Port của average_sentence_words. */
export function averageSentenceWords(text) {
  const sentences = String(text).split(/[.!?。！？]+/u).filter((part) => pyStrip(part));
  return sentences.length ? countWords(text) / sentences.length : 0.0;
}

/** Port của build_offline_learning_report. */
export function buildOfflineLearningReport({ finalBlog, productionBlog, stepOutputs, comparisonLabel = "final_blog.md", mode = "deep" }) {
  const finalWords = countWords(finalBlog);
  const productionWords = countWords(productionBlog);
  const wordDelta = productionWords - finalWords;
  const finalSentenceAvg = averageSentenceWords(finalBlog);
  const productionSentenceAvg = averageSentenceWords(productionBlog);
  const lengthNote =
    wordDelta < 0
      ? "Bản production ngắn hơn, cho thấy người viết có thể đã cắt phần giải thích thừa hoặc siết lại nhịp."
      : wordDelta > 0
        ? "Bản production dài hơn, cho thấy người viết có thể đã thêm ngữ cảnh, chi tiết cảm xúc hoặc phần nối ý."
        : "Bản production có cùng số từ, nên bài học chính có thể nằm ở cách diễn đạt, cấu trúc hoặc trọng tâm nhấn.";
  const rhythmNote =
    productionSentenceAvg < finalSentenceAvg
      ? "Độ dài câu trung bình giảm, cho thấy người viết có xu hướng thích nhịp ngắn hơn và khoảng dừng rõ hơn."
      : productionSentenceAvg > finalSentenceAvg
        ? "Độ dài câu trung bình tăng, cho thấy người viết có thể muốn phần suy tưởng phát triển hơn hoặc dòng văn mượt hơn."
        : "Độ dài câu trung bình gần như không đổi.";
  const stageIds = Object.keys(stepOutputs);
  return render(OFFLINE_REPORT_TEMPLATE, {
    "mode.upper()": mode.toUpperCase(),
    mode,
    similarity: new SequenceMatcher(Array.from(finalBlog), Array.from(productionBlog)).ratio(),
    comparison_label: comparisonLabel,
    final_words: finalWords,
    production_words: productionWords,
    word_delta: wordDelta,
    paragraph_delta: countParagraphs(productionBlog) - countParagraphs(finalBlog),
    final_sentence_avg: finalSentenceAvg,
    production_sentence_avg: productionSentenceAvg,
    length_note: lengthNote,
    rhythm_note: rhythmNote,
    available_steps: stageIds.join(", ") || "Không tìm thấy step output",
    stage_insights:
      stageIds
        .map(
          (id) =>
            `### ${id}\nĐối chiếu artifact của stage này với local diff; đây là câu hỏi chẩn đoán cần người dùng xác nhận, không phải kết luận đã học.`,
        )
        .join("\n\n") || "Không có stage artifact để chẩn đoán.",
    diff: renderOfflineDiff(finalBlog, productionBlog, comparisonLabel),
  });
}

/** Port của build_offline_tuning_suggestions. */
export function buildOfflineTuningSuggestions({ mode = "deep", stageIds = [] }) {
  return render(OFFLINE_TUNING_TEMPLATE, {
    "mode.upper()": mode.toUpperCase(),
    suggestions_body:
      stageIds
        .map((id) => `## ${id}\n- Trạng thái: cần người dùng review local diff trước khi sửa YAML.\n- Confidence: low`)
        .join("\n\n") || "Không có stage để tạo checklist.",
  });
}

/** Artifact đầy đủ của các stage đã xong, theo thứ tự flow (Bài học 4: không dùng handoff). */
export function learningStepOutputs(run) {
  return Object.fromEntries(run.stageIds.filter((id) => run.results[id]?.status === "completed").map((id) => [id, run.results[id].artifact]));
}

/** Kiểm tra trước khi học; trả lý do không học được, hoặc null. */
export function learningBlocker(bundle, run, productionBlog) {
  if (!run) return "Chưa có lần chạy nào.";
  const { primary } = collectFinalOutputs(bundle.workflows[run.mode].definition, run);
  if (!primary) return "Lần chạy chưa có bản nháp AI để so sánh.";
  if (!pyStrip(productionBlog || "")) return "Chưa có bản cuối. Hãy sửa bản nháp thành bài bạn sẽ đăng rồi lưu lại.";
  return null;
}

/**
 * Chạy một vòng học trên run hiện tại và bản cuối của người viết.
 * offline: chỉ thống kê và diff, không gọi Claude (như `--offline` của engine).
 * Trả một "session" để lưu và hiển thị; lỗi của từng bước nằm trong session.
 */
export async function runLearning({ bundle, run, productionBlog, client = null, offline = false, signal, onText, now = new Date() }) {
  const blocker = learningBlocker(bundle, run, productionBlog);
  if (blocker) throw new LearningError(blocker, "not_ready");
  const { primary } = collectFinalOutputs(bundle.workflows[run.mode].definition, run);
  const stepOutputs = learningStepOutputs(run);
  const session = {
    id: utcStamp(now),
    kind: offline ? "offline" : "claude",
    mode: run.mode,
    style: run.style,
    run_id: run.id || null,
    created_at: now.toISOString(),
    comparison_label: primary.file,
    production_blog: productionBlog,
    report: null,
    tuning_suggestions: null,
    telemetry: {},
    api_attempted: false,
    api_called: false,
    status: "running",
    error: null,
    error_code: null,
  };
  if (offline) {
    session.report = buildOfflineLearningReport({ finalBlog: primary.text, productionBlog, stepOutputs, comparisonLabel: primary.file, mode: run.mode });
    session.tuning_suggestions = buildOfflineTuningSuggestions({ mode: run.mode, stageIds: run.stageIds });
    session.status = "completed";
    return session;
  }
  if (!client) throw new LearningError("Không gọi được Claude trong lần mở này.", "no_client");

  const callStage = async (stageId, prompt) => {
    const modelConfig = { ...bundle.models.learning[stageId] };
    const { provider, apiCapable } = client.describe(stageId, modelConfig);
    session.api_attempted = session.api_attempted || Boolean(apiCapable);
    const started = Date.now();
    const entry = { provider, model: modelConfig.model, effort: modelConfig.effort, status: "running" };
    session.telemetry[stageId] = entry;
    try {
      const response = await client.call({
        prompt,
        stageId,
        modelConfig,
        signal,
        onText: onText ? ({ text }) => onText({ stageId, text }) : undefined,
      });
      Object.assign(entry, {
        status: "completed",
        model_applied: response.modelApplied || null,
        tier_applied: response.tierApplied || null,
        truncated: Boolean(response.truncated),
        api_called: Boolean(apiCapable),
        duration_ms: Date.now() - started,
      });
      session.api_called = session.api_called || entry.api_called;
      return response.text;
    } catch (error) {
      Object.assign(entry, {
        status: "failed",
        api_called: Boolean(error && error.apiCalled),
        duration_ms: Date.now() - started,
        error: (error && error.message) || String(error),
        error_code: (error && error.code) || null,
      });
      session.api_called = session.api_called || entry.api_called;
      throw error;
    }
  };

  try {
    const prompt = buildLearningPrompt({
      bundle,
      mode: run.mode,
      style: run.style,
      authorInput: run.authorInput,
      stepOutputs,
      finalBlog: primary.text,
      productionBlog,
      comparisonLabel: primary.file,
    });
    session.report = await callStage("editorial_learning", prompt);
    session.tuning_suggestions = await callStage("workflow_tuning", buildTuningPrompt({ report: session.report, mode: run.mode, stageIds: run.stageIds }));
    session.status = "completed";
  } catch (error) {
    session.status = (error && error.code) === "cancelled" ? "cancelled" : "failed";
    session.error = (error && error.message) || String(error);
    session.error_code = (error && error.code) || null;
  }
  return session;
}
