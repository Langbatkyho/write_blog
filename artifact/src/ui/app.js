// Giao diện (ART-3, ART-4). Chỉ lo hiển thị và tương tác; mọi logic workflow và
// lưu trữ nằm trong ../core. Nội dung do model sinh luôn được gán qua textContent.
import { blindDrafts, createAbSession, decideAb, revealAb } from "../core/ab.js";
import { listStyles, validateBundle } from "../core/contracts.js";
import { createSampleClient } from "../core/client_sample.js";
import { exportRunFiles } from "../core/export.js";
import { buildAuthorInput, slugify } from "../core/input.js";
import { learningBlocker, runLearning } from "../core/learning.js";
import {
  cleanOverrides,
  effectiveModels,
  matchingPreset,
  modelProfile,
  overridesFrom,
  PRESETS,
  presetModels,
  withModels,
} from "../core/model_settings.js";
import { createRun, nextStageIndex, retryStage, runStage, RUN_STATUS } from "../core/orchestrator.js";
import { buildRunMarkdown, collectFinalOutputs } from "../core/outputs.js";
import { countWords } from "../core/parser.js";
import { createRunRepository } from "../core/repository.js";
import { newRunId, restoreRun } from "../core/run_record.js";

const AGENTS = {
  story_architect: ["Câu chuyện", "Điều gì thật sự đã xảy ra?"],
  reflection_engine: ["Nhận thức", "Điều gì thay đổi bên trong người viết?"],
  writing_agent: ["Giọng người viết", "Nếu có đủ thời gian, tác giả sẽ kể chuyện này thế nào?"],
  reader_experience: ["Trải nghiệm đọc", "Độc giả lần đầu đã cảm thấy gì?"],
  editor_agent: ["Kết nối", "Cần thay đổi tối thiểu điều gì để giảm ma sát?"],
  coach_agent: ["Sự phát triển", "Người viết còn chưa nhìn thấy điều gì?"],
  future_self: ["Con người đang trở thành", "5 năm nữa, tác giả còn muốn đứng tên bài này không?"],
  sensory_capture: ["Giác quan", "Khoảnh khắc này hiện ra qua giác quan thế nào?"],
  inner_weather: ["Thời tiết bên trong", "Bên trong người viết lúc này ra sao?"],
  cosmic_signal_reader: ["Trực giác", "Khoảnh khắc này đang thì thầm điều gì?"],
  moment_writer: ["Năng lượng hiện tại", "Nếu chỉ giữ lại khoảnh khắc này, bài cần nói gì?"],
  breath_editor: ["Độ trong", "Cần bỏ hoặc làm nhẹ điều gì?"],
  gentle_witness: ["Sự thật", "Bài còn là một khoảnh khắc sống hay đã thành bài học?"],
};
const MODEL_NAMES = { "claude-opus-5-5": "Opus 5.5", "claude-sonnet-5-5": "Sonnet 5.5", "claude-haiku-5-5": "Haiku 5.5" };
const STATUS_TEXT = { pending: "Chờ", running: "Đang chạy", completed: "Xong", failed: "Lỗi", skipped: "Bỏ qua" };
const ERROR_TEXT = {
  not_granted: "Bạn chưa cho phép trang này dùng Claude. Tải lại trang để được hỏi lại.",
  rate_limited: "Đã chạm giới hạn sử dụng Claude. Đợi một lúc rồi bấm chạy lại bước này.",
  cancelled: "Đã dừng theo yêu cầu.",
  sampling_disabled: "Tài khoản này đang không dùng được Claude trong Artifact.",
  prompt_too_large: "Prompt vượt giới hạn 256 KiB. Hãy rút gọn ghi chú.",
  refused: "Claude từ chối yêu cầu này.",
  empty_completion: "Claude trả về câu trả lời rỗng. Chạy lại bước này.",
  upstream_error: "Lỗi phía Claude. Chạy lại bước này.",
  session_expired: "Phiên đăng nhập đã hết hạn. Tải lại trang.",
  queue_overflow: "Có quá nhiều yêu cầu đang chờ. Đợi một lúc rồi chạy lại.",
};
const DB_ERROR_TEXT = {
  quota_exceeded: "Kho lưu trữ của trang đã đầy. Tải zip các lần chạy cần giữ.",
  unavailable: "Máy chủ lưu trữ tạm thời không phản hồi.",
  resource_exhausted: "Đang ghi quá nhanh; đợi một lúc.",
  revoked: "Trang không còn quyền lưu trữ trong lần mở này.",
  not_granted: "Trang không được cấp quyền lưu trữ.",
  timeout: "Máy chủ lưu trữ chưa phản hồi sau 10 giây.",
};
const HISTORY_STATUS = { completed: ["Xong", "ok"], failed: ["Lỗi", "bad"], cancelled: ["Đã dừng", "warn"], running: ["Đang dở", "warn"] };
const DRAFT_KEY = "mindful-blog-workflow:draft:v1";
const SETTINGS_KEY = "mindful-blog-workflow:model-settings:v1";
const STORE_TIMEOUT_MS = 10000;

const $ = (id) => document.getElementById(id);
const state = {
  bundle: null,
  client: null,
  downloads: null,
  mode: "moment",
  run: null,
  busy: false,
  controller: null,
  liveStage: null,
  live: {},
  open: new Set(),
  armedRestart: false,
  lengthEdited: false,
  repo: null,
  storageMessage: "Đang kết nối lưu trữ…",
  history: [],
  historyToken: 0,
  armedOpen: null,
  persistNote: "",
  buildInfo: {},
  productionForRun: null,
  productionLoaded: null,
  productionSaved: null,
  learnings: [],
  learningSelected: null,
  learningLive: null,
  learningMessage: "",
  settings: null,
  settingsDraft: null,
  settingsMessage: "",
  ab: null,
  abSessions: [],
  abMessage: "",
  abRenderedKey: null,
};

function withTimeout(promise, ms) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject({ code: "timeout", message: "timeout" }), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

function dbErrorText(error) {
  return (error && DB_ERROR_TEXT[error.code]) || (error && error.message) || String(error);
}

function h(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child !== null && child !== undefined && child !== false) node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

const seconds = (ms) => `${(ms / 1000).toFixed(1).replace(".", ",")} s`;
const modelName = (id) => MODEL_NAMES[id] || id;

function setChip(id, text, tone) {
  const chip = $(id);
  chip.textContent = text;
  chip.className = "chip" + (tone ? " " + tone : "");
}

function showBanner(text) {
  const banner = $("banner");
  banner.textContent = text;
  banner.hidden = !text;
}

// --- Form và bản nháp lưu trong trình duyệt ---------------------------------

function fields() {
  return {
    mode: state.mode,
    style: $("style").value,
    title: $("title").value,
    rawNotes: $("raw-notes").value,
    optionalContext: $("optional-context").value,
    targetReader: $("target-reader").value,
    desiredLength: $("desired-length").value,
    pace: $("pace-step").checked ? "step" : "all",
    lengthEdited: state.lengthEdited,
  };
}

let saveTimer = null;
function saveDraft() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(fields()));
    } catch (_) {
      // Không lưu được bản nháp (chế độ riêng tư, bị chặn): trang vẫn chạy bình thường.
    }
  }, 400);
}

function loadDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

function defaultLength(mode) {
  const value = state.bundle.workflows[mode].definition.input?.desired_length?.default || "";
  return String(value).replace(/\bwords\b/, "từ");
}

function setMode(mode, preferredStyle) {
  state.mode = mode;
  for (const button of document.querySelectorAll("[data-mode]")) {
    button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
  }
  const select = $("style");
  const current = preferredStyle || select.value;
  const styles = listStyles(state.bundle, mode).sort((a, b) => a.name.localeCompare(b.name, "vi"));
  select.replaceChildren(...styles.map((style) => h("option", { value: style.slug, text: style.name })));
  select.value = styles.some((style) => style.slug === current) ? current : styles.some((s) => s.slug === "reflective") ? "reflective" : styles[0].slug;
  if (!state.lengthEdited) $("desired-length").value = defaultLength(mode);
  if (!state.run) renderStages();
}

// --- Hiển thị ---------------------------------------------------------------

function errorText(result) {
  if (result.error_code && ERROR_TEXT[result.error_code]) return ERROR_TEXT[result.error_code];
  if (/section/.test(result.error || "")) return `Phản hồi không đúng định dạng Artifact/Handoff: ${result.error}`;
  return result.error || "Lỗi không xác định.";
}

function detailsBlock(key, summary, body) {
  const node = h("details", { "data-key": key, open: state.open.has(key) }, h("summary", { text: summary }), body);
  node.addEventListener("toggle", () => (node.open ? state.open.add(key) : state.open.delete(key)));
  return node;
}

function stageCard(stageId, index, total) {
  const run = state.run;
  const result = run?.results[stageId];
  const status = result ? result.status : state.liveStage === stageId ? "running" : "pending";
  const [label, question] = AGENTS[stageId] || [stageId, ""];
  const requested = result?.model ? { model: result.model, effort: result.effort } : (run?.models || activeModels()).stages[stageId];
  const meta = [h("span", { text: `${modelName(requested.model)} · ${requested.effort}` })];
  if (result && result.status === "completed") {
    meta.push(
      result.model_applied
        ? h("span", { text: "đúng model" })
        : h("span", { class: "warn", text: `bị hạ xuống hạng ${result.tier_applied}` }),
      h("span", { text: seconds(result.duration_ms) }),
      h("span", { text: `${countWords(result.artifact)} từ` }),
    );
  } else if (result && result.duration_ms !== undefined) {
    meta.push(h("span", { text: seconds(result.duration_ms) }));
  }

  const body = [];
  if (status === "running") {
    const live = state.live[stageId];
    body.push(
      live
        ? h("pre", { class: "text live", id: `live-${stageId}`, text: live })
        : h("p", { class: "thinking", id: `live-${stageId}`, text: "Đang suy nghĩ…" }),
    );
  } else if (status === "completed") {
    if (result.warnings.length) body.push(h("ul", { class: "notes" }, result.warnings.map((text) => h("li", { text }))));
    const files = Object.entries(result.files);
    if (files.length > 1) {
      for (const [file, text] of files) body.push(detailsBlock(`${stageId}:${file}`, `${file} · ${countWords(text)} từ`, h("pre", { class: "text", text })));
    } else {
      body.push(detailsBlock(`${stageId}:artifact`, `Artifact · ${result.artifact_file}`, h("pre", { class: "text", text: result.artifact })));
    }
    body.push(detailsBlock(`${stageId}:handoff`, "Handoff cho bước sau", h("pre", { class: "text", text: result.handoff })));
  } else if (status === "failed" || status === "skipped") {
    body.push(h("p", { class: "error", text: status === "skipped" ? result.error : errorText(result) }));
    if (result.partial_text) body.push(detailsBlock(`${stageId}:partial`, "Phần đã viết được", h("pre", { class: "text", text: result.partial_text })));
    if (!state.busy && !run.readOnly) {
      body.push(h("div", { class: "row" }, h("button", { type: "button", class: "small", text: "Chạy lại bước này", onclick: () => go({ retryIndex: index }) })));
    }
  }

  return h(
    "li",
    { class: "stage", "data-status": status, "data-stage": stageId },
    h(
      "div",
      { class: "stage-head" },
      h("span", { class: "stage-num", text: String(index + 1).padStart(2, "0") + "/" + String(total).padStart(2, "0") }),
      h("div", { class: "stage-title" }, h("h3", { text: label }), h("span", { class: "stage-id", text: stageId }), h("span", { class: "q", text: question })),
      h("span", { class: "status", "data-status": status, text: STATUS_TEXT[status] }),
    ),
    h("div", { class: "meta" }, meta),
    body,
  );
}

function renderStages() {
  const ids = state.run ? state.run.stageIds : state.bundle.workflows[state.mode].stage_ids;
  $("stages").replaceChildren(...ids.map((id, index) => stageCard(id, index, ids.length)));
}

function updateLive(stageId) {
  const node = $(`live-${stageId}`);
  if (!node) return;
  if (node.tagName !== "PRE") {
    renderStages();
    return;
  }
  node.textContent = state.live[stageId];
  node.scrollTop = node.scrollHeight;
}

function runStatusText() {
  const run = state.run;
  if (!run) return "Chưa chạy. Mỗi bước bên dưới sẽ gọi một model Claude riêng.";
  const prefix = `${run.mode} · ${run.style}`;
  if (run.readOnly) return `${prefix} — Chỉ xem, không chạy tiếp được: ${run.problems.join(" ")}`;
  return `${prefix} — ${runProgressText(run)}`;
}

function runProgressText(run) {
  const total = run.stageIds.length;
  const done = run.stageIds.filter((id) => run.results[id]?.status === "completed").length;
  const firstCall = !run.stageIds.some((id) => run.results[id]);
  if (state.busy) {
    const step = Math.min(done + 1, total);
    return `Đang chạy bước ${step}/${total}…` + (firstCall ? " Lần đầu, claude.ai sẽ hỏi bạn cho phép trang dùng Claude." : "");
  }
  const stopped = run.stageIds.find((id) => run.results[id] && run.results[id].status !== "completed");
  if (run.status === RUN_STATUS.COMPLETED) {
    const total_ms = Object.values(run.results).reduce((sum, r) => sum + (r.duration_ms || 0), 0);
    return `Xong cả ${total} bước trong ${seconds(total_ms)}. Bản nháp ở trên; bản cuối vẫn do bạn hoàn thiện.`;
  }
  if (run.status === RUN_STATUS.CANCELLED) return `Đã dừng ở bước ${stopped}. Bấm "Chạy lại bước này" để tiếp tục.`;
  if (run.status === RUN_STATUS.FAILED) return `Dừng ở bước ${stopped}. Xem lỗi bên dưới rồi bấm "Chạy lại bước này".`;
  return `Đã xong ${done}/${total} bước. Đọc kết quả rồi bấm "Chạy bước tiếp".`;
}

function renderFinal() {
  const section = $("final");
  if (!state.run) {
    section.hidden = true;
    return;
  }
  const { primary, reflection } = collectFinalOutputs(state.bundle.workflows[state.run.mode].definition, state.run);
  section.hidden = !primary;
  if (!primary) return;
  $("final-title").textContent = state.run.status === RUN_STATUS.COMPLETED ? "Bản nháp" : "Bản nháp (workflow chưa xong)";
  $("final-meta").replaceChildren(
    h("span", { text: primary.file }),
    h("span", { text: `${primary.words} từ` }),
    h("span", { text: `mục tiêu: ${fields().desiredLength || "không đặt"}` }),
  );
  $("final-text").textContent = primary.text;
  $("reflection").hidden = !reflection;
  if (reflection) {
    $("reflection-title").textContent = `Phản tư · ${reflection.file}`;
    $("reflection-text").textContent = reflection.text;
  }
  $("download-draft").disabled = !state.downloads;
  if (!state.downloads) $("final-note").textContent = "Tải file chỉ có khi mở trang trong claude.ai; vẫn có thể sao chép bài.";
  if (state.productionForRun !== state.run.id) {
    // Lần đầu thấy bản nháp của run này: bắt đầu từ bản cuối đã lưu, nếu không thì từ bản nháp AI.
    state.productionForRun = state.run.id;
    state.productionSaved = state.productionLoaded;
    $("production").value = state.productionLoaded ?? primary.text;
  }
  renderProduction();
  renderLearning();
}

function updateControls() {
  const busy = state.busy;
  for (const node of $("form").querySelectorAll("input, textarea, select, .segmented button")) node.disabled = busy;
  $("run").disabled = busy || !state.client;
  $("run").textContent = state.armedRestart ? "Bấm lần nữa để chạy mới" : state.run ? "Chạy lại từ đầu" : "Chạy workflow";
  $("stop").disabled = !busy;
  const next = state.run && !state.run.readOnly ? nextStageIndex(state.run) : -1;
  const nextButton = $("next");
  nextButton.hidden = busy || next === -1;
  if (next !== -1) {
    nextButton.textContent = $("pace-all").checked
      ? "Chạy tiếp tới hết"
      : `Chạy bước tiếp: ${(AGENTS[state.run.stageIds[next]] || [state.run.stageIds[next]])[0]}`;
  }
  $("run-status").textContent = runStatusText();
  $("run-actions").hidden = !state.run;
  $("download-run").disabled = busy || !state.downloads;
  $("download-runlog").disabled = busy || !state.downloads;
  if (state.run && !$("final").hidden) renderProduction();
  $("download-zip").disabled = busy || !state.downloads || !window.JSZip;
  $("persist-note").hidden = !state.persistNote;
  $("persist-note").textContent = state.persistNote;
  for (const button of $("history").querySelectorAll("button")) button.disabled = busy;
}

function renderAll() {
  renderStages();
  renderFinal();
  updateControls();
  renderAb();
}

// --- Chạy -------------------------------------------------------------------

async function go({ retryIndex = null, continuous = $("pace-all").checked } = {}) {
  if (state.busy || !state.run || !state.client) return;
  state.busy = true;
  state.controller = new AbortController();
  const options = {
    bundle: runBundle(state.run),
    client: state.client,
    signal: state.controller.signal,
    onText: ({ stageId, text }) => {
      state.live[stageId] = text;
      updateLive(stageId);
    },
  };
  try {
    let index = retryIndex ?? nextStageIndex(state.run);
    while (index !== -1) {
      const stageId = state.run.stageIds[index];
      state.liveStage = stageId;
      state.live[stageId] = "";
      renderAll();
      if (retryIndex !== null && index === retryIndex) {
        await persistReset(index);
        await retryStage(state.run, index, options);
      } else {
        await runStage(state.run, index, options);
      }
      state.liveStage = null;
      await persistStage(stageId);
      renderAll();
      if (!continuous) break;
      index = nextStageIndex(state.run);
    }
  } catch (error) {
    showBanner(`Không chạy được: ${error.message || error}`);
  } finally {
    state.busy = false;
    state.liveStage = null;
    state.controller = null;
    renderAll();
    loadHistory();
  }
}

// --- Lưu trữ và lịch sử -----------------------------------------------------

function saveExtras(run = state.run) {
  const { primary } = collectFinalOutputs(state.bundle.workflows[run.mode].definition, run);
  return { title: run.title, buildId: state.buildInfo.build_id || null, primaryWords: primary ? primary.words : null };
}

async function persistStage(stageId) {
  if (!state.repo || !state.run.persisted) return;
  try {
    await state.repo.saveStage(state.run, stageId, saveExtras());
  } catch (error) {
    state.persistNote = `Không lưu được bước ${stageId}: ${dbErrorText(error)} Kết quả vẫn ở trên trang; hãy tải zip để giữ lại.`;
  }
}

async function persistReset(index) {
  if (!state.repo || !state.run.persisted) return;
  try {
    await state.repo.deleteStagesFrom(state.run, index);
  } catch (error) {
    state.persistNote = `Không xóa được kết quả cũ trước khi chạy lại: ${dbErrorText(error)}`;
  }
}

function formatWhen(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function historyTags(record) {
  const tags = [];
  const preset = record.model_profile?.preset;
  if (preset && preset !== "balanced") tags.push(presetLabel(preset));
  if (record.ab_session) tags.push(`A/B · bài ${record.ab_session.letter || "?"}${record.ab_session.chosen ? " ✓" : ""}`);
  return tags;
}

function renderHistory() {
  // Bài A/B chưa chốt bị ẩn: mở ra sẽ thấy model của từng bước, lộ cấu hình.
  const visible = state.history.filter((record) => !record.ab_session || record.ab_session.decided);
  const items = visible.map((record) => {
    const [label, tone] = HISTORY_STATUS[record.status] || [record.status, ""];
    const done = Object.values(record.stage_status || {}).filter((value) => value === "completed").length;
    const total = (record.stage_ids || []).length;
    const current = state.run && state.run.id === record.id;
    return h(
      "li",
      {},
      h(
        "button",
        { type: "button", "data-run": record.id, "aria-current": current ? "true" : null, disabled: state.busy, onclick: () => openRun(record.id) },
        h("span", { class: "h-title", text: record.title || extractTitleForList(record) }),
        h(
          "span",
          { class: "h-meta" },
          h("span", { text: formatWhen(record.created_at) }),
          h("span", { text: `${record.mode} · ${record.style}` }),
          h("span", { class: tone, text: `${label} ${done}/${total}` }),
          record.primary_words ? h("span", { text: `${record.primary_words} từ` }) : null,
          historyTags(record).map((text) => h("span", { text })),
        ),
      ),
    );
  });
  $("history").replaceChildren(...items);
}

function extractTitleForList(record) {
  const firstNote = String(record.author_input || "").split("raw_notes:")[1] || "";
  const line = firstNote.split("\n").map((text) => text.replace(/^[-\s]+/, "").trim()).find(Boolean);
  return line ? (line.length > 60 ? line.slice(0, 60) + "…" : line) : "(không tiêu đề)";
}

async function loadHistory() {
  const note = $("history-note");
  if (!state.repo) {
    state.history = [];
    renderHistory();
    note.textContent = state.storageMessage;
    return;
  }
  const token = ++state.historyToken;
  if (!state.history.length) note.textContent = "Đang tải…";
  try {
    const runs = await withTimeout(state.repo.listRuns(50), STORE_TIMEOUT_MS);
    if (token !== state.historyToken) return;
    state.history = runs;
    note.textContent = runs.some((record) => !record.ab_session || record.ab_session.decided) ? "" : "Chưa có lần chạy nào được lưu.";
  } catch (error) {
    if (token !== state.historyToken) return;
    note.textContent = `Chưa tải được lịch sử: ${dbErrorText(error)} Bấm "Tải lại" để thử lại.`;
  }
  renderHistory();
}

async function openRun(id) {
  if (state.busy || !state.repo) return;
  const note = $("history-note");
  const current = state.run;
  if (current && !current.persisted && Object.keys(current.results).length && state.armedOpen !== id) {
    state.armedOpen = id;
    note.textContent = "Lần chạy đang xem chưa được lưu. Tải zip nếu cần giữ, rồi bấm lần nữa để mở.";
    return;
  }
  state.armedOpen = null;
  note.textContent = "Đang mở…";
  try {
    const data = await withTimeout(state.repo.loadRun(id), STORE_TIMEOUT_MS);
    if (!data) {
      note.textContent = "Không tìm thấy lần chạy này nữa.";
      return;
    }
    const { run, resumable, problems } = restoreRun(state.bundle, data.runDoc, data.stageDocs);
    run.readOnly = !resumable;
    run.problems = problems;
    resetLearningState();
    try {
      state.productionLoaded = await withTimeout(state.repo.loadProduction(id), STORE_TIMEOUT_MS);
      state.learnings = await withTimeout(state.repo.listLearning(id), STORE_TIMEOUT_MS);
      state.learningSelected = state.learnings[0]?.id || null;
    } catch (error) {
      state.learningMessage = `Chưa tải được bản cuối hoặc kết quả học: ${dbErrorText(error)}`;
    }
    state.run = run;
    state.live = {};
    state.open.clear();
    state.armedRestart = false;
    state.persistNote = "";
    note.textContent = "";
    renderAll();
    renderHistory();
  } catch (error) {
    note.textContent = `Không mở được lần chạy: ${dbErrorText(error)}`;
  }
}

async function downloadZip() {
  if (!state.run || !window.JSZip) return;
  try {
    const { folderName, files } = exportRunFiles(state.bundle, state.run, {
      production: productionForExport(),
      learnings: state.learnings.filter((session) => session.report),
    });
    const zip = new window.JSZip();
    const folder = zip.folder(folderName);
    for (const [name, content] of Object.entries(files)) folder.file(name, content);
    const blob = await zip.generateAsync({ type: "blob" });
    await saveFile(`${folderName}.zip`, blob, showRunNote);
  } catch (error) {
    showRunNote(`Không tạo được file zip: ${(error && error.message) || error}`);
  }
}

function startRun(event) {
  event.preventDefault();
  if (state.busy || !state.client) return;
  const note = $("form-note");
  if (state.run && !state.armedRestart) {
    state.armedRestart = true;
    note.textContent = "Kết quả hiện tại sẽ mất khi chạy mới (lưu lịch sử có ở bản sau). Bấm lần nữa để xác nhận.";
    updateControls();
    return;
  }
  state.armedRestart = false;
  note.textContent = "";
  let authorInput;
  try {
    authorInput = buildAuthorInput(fields());
  } catch (error) {
    note.textContent = error.message;
    $("raw-notes").focus();
    updateControls();
    return;
  }
  state.run = createRun({ bundle: state.bundle, mode: state.mode, style: $("style").value, authorInput });
  state.run.title = $("title").value.trim();
  state.run.buildId = state.buildInfo.build_id || null;
  state.run.models = activeModels();
  state.run.modelProfile = modelProfile(state.bundle, state.settings);
  resetLearningState();
  state.live = {};
  state.open.clear();
  state.persistNote = "";
  showBanner("");
  startPersisted();
}

async function startPersisted() {
  if (state.repo) {
    try {
      await state.repo.createRun(state.run, saveExtras());
    } catch (error) {
      state.persistNote = `Không lưu được lần chạy này: ${dbErrorText(error)} Kết quả vẫn hiện trên trang; hãy tải zip để giữ lại.`;
    }
  } else {
    state.persistNote = "";
  }
  // Run không lưu được vẫn cần ID để xuất zip.
  if (!state.run.id) state.run.id = newRunId({ mode: state.run.mode, style: state.run.style });
  go();
}

const showFinalNote = (text) => ($("final-note").textContent = text);
const showRunNote = (text) => {
  state.persistNote = text;
  updateControls();
};

async function saveFile(filename, data, showNote = showFinalNote) {
  if (!state.downloads) return;
  try {
    await state.downloads.save({ filename, data });
    showNote(`Đã lưu ${filename}.`);
  } catch (error) {
    showNote(error && error.code === "declined" ? "Bạn đã hủy tải về." : `Không tải được file: ${(error && error.message) || error}`);
  }
}

// --- ART-7: tải final_blog.md và run_log.md (thay cho gửi Gmail) -----------------

/** final_blog.md: đúng bài đang có trong khung "Bản cuối của bạn" (kể cả khi chưa lưu). */
function downloadFinalBlog() {
  const text = $("production").value;
  if (!text.trim()) return;
  saveFile("final_blog.md", text.endsWith("\n") ? text : text + "\n", (note) => {
    state.learningMessage = note;
    renderProduction();
  });
}

/** run_log.md: cùng nội dung và định dạng với run_log.md trong zip (append_run_log của engine). */
function downloadRunLog() {
  if (!state.run) return;
  try {
    const { files } = exportRunFiles(state.bundle, state.run);
    saveFile("run_log.md", files["run_log.md"], showRunNote);
  } catch (error) {
    showRunNote(`Không tạo được run_log.md: ${(error && error.message) || error}`);
  }
}

function baseName() {
  return slugify($("title").value || (state.run && state.run.mode) || "blog");
}

async function copyDraft() {
  const text = $("final-text").textContent;
  try {
    await navigator.clipboard.writeText(text);
    $("final-note").textContent = "Đã sao chép bản nháp.";
  } catch (_) {
    const range = document.createRange();
    range.selectNodeContents($("final-text"));
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    $("final-note").textContent = "Không sao chép tự động được; bài đã được chọn sẵn, nhấn Ctrl+C hoặc ⌘C.";
  }
}

// --- Bản cuối và learning loop ---------------------------------------------

function resetLearningState() {
  state.productionForRun = null;
  state.productionLoaded = null;
  state.productionSaved = null;
  state.learnings = [];
  state.learningSelected = null;
  state.learningLive = null;
  state.learningMessage = "";
}

function primaryDraft() {
  return state.run ? collectFinalOutputs(state.bundle.workflows[state.run.mode].definition, state.run).primary : null;
}

/** Bản cuối đưa vào zip: bản đã lưu, hoặc bản đang sửa nếu khác bản nháp AI. */
function productionForExport() {
  if (state.productionSaved) return state.productionSaved;
  const text = $("production").value;
  const primary = primaryDraft();
  return text.trim() && primary && text !== primary.text ? text : null;
}

function renderProduction() {
  const text = $("production").value;
  const primary = primaryDraft();
  const canStore = Boolean(state.repo && state.run && state.run.persisted);
  const saved = text === state.productionSaved;
  $("production-meta").textContent = `${countWords(text)} từ · ${!canStore ? "không lưu được trong lần mở này" : saved ? "đã lưu" : "chưa lưu"}`;
  $("production-save").disabled = state.busy || !canStore || saved || !text.trim();
  $("production-reset").disabled = state.busy || !primary || text === primary.text;
  const blocker = learningBlocker(state.bundle, state.run, text);
  const unchanged = Boolean(primary) && text === primary.text;
  $("learn-claude").disabled = state.busy || !state.client || Boolean(blocker) || unchanged;
  $("learn-offline").disabled = state.busy || Boolean(blocker);
  $("download-final").disabled = state.busy || !state.downloads || !text.trim();
  const hint = blocker || (unchanged ? "Bản cuối đang giống hệt bản nháp AI, chưa có gì để học. Sửa bài rồi bấm học." : !state.client ? "Học qua Claude cần mở trang trong claude.ai; vẫn so sánh offline được." : "");
  $("learning-note").textContent = state.learningMessage || hint;
}

/** Lưu bản cuối; trả lỗi dạng chữ, hoặc null nếu lưu được. */
async function persistProduction(text) {
  if (!state.repo || !state.run || !state.run.persisted) return "Lần mở này không lưu được bản cuối.";
  try {
    await state.repo.saveProduction(state.run, text);
    state.productionSaved = text;
    return null;
  } catch (error) {
    return `Không lưu được bản cuối: ${dbErrorText(error)}`;
  }
}

async function saveProduction() {
  const problem = await persistProduction($("production").value);
  state.learningMessage = problem || "Đã lưu bản cuối.";
  renderProduction();
}

const LEARNING_LABEL = { editorial_learning: "Báo cáo chẩn đoán", workflow_tuning: "Gợi ý tinh chỉnh workflow" };

function sessionLabel(session) {
  const kind = session.kind === "offline" ? "Offline" : "Claude";
  const status = { completed: "xong", failed: "lỗi", cancelled: "đã dừng" }[session.status] || session.status;
  return `${formatWhen(session.created_at)} · ${kind} · ${status}`;
}

function renderLearning() {
  const block = $("learning-block");
  const live = state.learningLive;
  const session = state.learnings.find((item) => item.id === state.learningSelected) || state.learnings[0];
  block.hidden = !live && !session;
  if (block.hidden) return;
  const select = $("learning-select");
  select.replaceChildren(...state.learnings.map((item) => h("option", { value: item.id, text: sessionLabel(item) })));
  select.hidden = Boolean(live) || state.learnings.length < 2;
  if (session) select.value = session.id;
  $("download-learning").disabled = Boolean(live) || !state.downloads || !session?.report;
  if (live) {
    $("learning-meta").textContent = live.stageId ? `Đang chạy: ${LEARNING_LABEL[live.stageId]}…` : "Đang chuẩn bị…";
    $("learning-report").textContent = live.stageId === "editorial_learning" ? live.text || "Đang suy nghĩ…" : live.report || "Đang suy nghĩ…";
    $("learning-tuning").textContent = live.stageId === "workflow_tuning" ? live.text || "Đang suy nghĩ…" : "";
    return;
  }
  const models = Object.entries(session.telemetry || {})
    .map(([stage, entry]) => `${stage}: ${modelName(entry.model)} · ${entry.effort}${entry.status === "completed" && !entry.model_applied ? " (bị hạ hạng)" : ""}`)
    .join(" · ");
  $("learning-meta").textContent = `${session.mode} · ${session.style} · so với ${session.comparison_label} · ${models || "không gọi Claude"}`;
  $("learning-report").textContent = session.report || session.error || "";
  $("learning-tuning").textContent = session.tuning_suggestions || "";
}

async function learn(offline) {
  if (state.busy || !state.run) return;
  const text = $("production").value;
  const blocker = learningBlocker(state.bundle, state.run, text);
  if (blocker) {
    state.learningMessage = blocker;
    renderProduction();
    return;
  }
  state.busy = true;
  state.controller = new AbortController();
  state.learningMessage = "";
  state.learningLive = { stageId: null, text: "", report: "" };
  renderAll();
  try {
    const saveProblem = state.repo && state.run.persisted && text !== state.productionSaved ? await persistProduction(text) : null;
    const session = await runLearning({
      bundle: withModels(state.bundle, activeModels()),
      run: state.run,
      productionBlog: text,
      client: state.client,
      offline,
      signal: state.controller.signal,
      onText: ({ stageId, text: partial }) => {
        if (stageId === "workflow_tuning" && state.learningLive.stageId === "editorial_learning") state.learningLive.report = state.learningLive.text;
        state.learningLive.stageId = stageId;
        state.learningLive.text = partial;
        renderLearning();
      },
    });
    const notes = [];
    if (saveProblem) notes.push(saveProblem);
    if (session.report) {
      state.learnings.unshift(session);
      state.learningSelected = session.id;
      if (state.repo && state.run.persisted) {
        try {
          await state.repo.saveLearning(state.run, session);
        } catch (error) {
          notes.push(`Không lưu được kết quả học: ${dbErrorText(error)} Hãy tải về để giữ lại.`);
        }
      }
    }
    {
      const outcome =
        session.status === "completed"
          ? offline
            ? "Đã so sánh offline. Đây chỉ là thống kê và câu hỏi chẩn đoán, chưa phải kết luận."
            : "Đã xong vòng học. Đọc gợi ý, rồi tự quyết định sửa skill trong repo."
          : session.status === "cancelled"
            ? "Đã dừng vòng học."
            : `Vòng học lỗi: ${ERROR_TEXT[session.error_code] || session.error}`;
      state.learningMessage = [outcome, ...notes].join(" ");
    }
  } catch (error) {
    state.learningMessage = error.message || String(error);
  } finally {
    state.busy = false;
    state.controller = null;
    state.learningLive = null;
    renderAll();
  }
}

function downloadLearning() {
  const session = state.learnings.find((item) => item.id === state.learningSelected) || state.learnings[0];
  if (!session || !session.report) return;
  const header = `<!-- mode: ${session.mode} | style: ${session.style} | run: ${session.run_id || ""} | learning: ${session.id} | ${session.kind} -->`;
  const body = [
    header,
    `# Kết quả học (${session.mode} · ${session.style})`,
    `## Báo cáo chẩn đoán\n\n${session.report.trim()}`,
    `## Gợi ý tinh chỉnh workflow\n\n${(session.tuning_suggestions || "").trim()}`,
  ].join("\n\n");
  saveFile(`${session.mode}_blog_patterns_${session.style}_${session.id}.md`, body + "\n", (note) => {
    state.learningMessage = note;
    renderProduction();
  });
}

// --- Cấu hình model theo từng bước (ART-6.1) ---------------------------------

const VOICE_LAB_NAMES = {
  vl_analysis: "Phân tích giọng",
  vl_synthesis: "Tổng hợp style",
  vl_interview_patch: "Vá theo phỏng vấn",
  vl_calibration: "Hiệu chỉnh",
};

const presetLabel = (id) => (PRESETS.find((preset) => preset.id === id) || { label: "Tùy chỉnh" }).label;

/** Bảng model đang áp dụng cho lần chạy mới: bảng trong repo + cấu hình đã lưu. */
function activeModels() {
  return effectiveModels(state.bundle, state.settings);
}

/** Bundle cho một run: run giữ bảng model lúc tạo, để chạy lại/chạy tiếp vẫn đúng cấu hình đó. */
function runBundle(run) {
  return withModels(state.bundle, run?.models || activeModels());
}

function settingsSections() {
  const stageRows = (mode) => state.bundle.workflows[mode].stage_ids.map((id) => ({ group: "stages", id, label: (AGENTS[id] || [id])[0] }));
  return [
    { title: "Deep · bài dài", rows: stageRows("deep") },
    { title: "Moment · bài ngắn", rows: stageRows("moment") },
    { title: "Vòng học", rows: Object.keys(state.bundle.models.learning).map((id) => ({ group: "learning", id, label: LEARNING_LABEL[id] || id })) },
    {
      title: "Voice Lab (dùng từ ART-8)",
      rows: Object.keys(state.bundle.models.voice_lab || {}).map((id) => ({ group: "voice_lab", id, label: VOICE_LAB_NAMES[id] || id })),
    },
  ];
}

function buildSettingsTable() {
  const catalog = state.bundle.model_catalog;
  $("preset").replaceChildren(
    ...PRESETS.map((preset) => h("option", { value: preset.id, text: preset.label })),
    h("option", { value: "custom", text: "Tùy chỉnh", disabled: true }),
  );
  const sections = settingsSections().map((section) =>
    h(
      "fieldset",
      { class: "settings-group" },
      h("legend", { text: section.title }),
      section.rows.map((row) => {
        const key = `${row.group}-${row.id}`;
        return h(
          "div",
          { class: "settings-row", "data-setting": key },
          h("span", { class: "s-label" }, h("span", { id: `s-label-${key}`, text: row.label }), h("span", { class: "s-default", id: `s-default-${key}` })),
          h(
            "select",
            { id: `model-${key}`, "aria-labelledby": `s-label-${key}`, "aria-label": "Model", onchange: (event) => editSetting(row, { model: event.target.value }) },
            Object.keys(catalog.models).map((id) => h("option", { value: id, text: modelName(id) })),
          ),
          h(
            "select",
            { id: `effort-${key}`, "aria-label": `Effort của ${row.label}`, onchange: (event) => editSetting(row, { effort: event.target.value }) },
            catalog.efforts.map((effort) => h("option", { value: effort, text: effort })),
          ),
        );
      }),
    ),
  );
  $("settings-table").replaceChildren(...sections);
}

function editSetting(row, change) {
  const current = state.settingsDraft[row.group][row.id];
  const next = { ...current, ...change };
  next.model_tier = state.bundle.model_catalog.models[next.model];
  state.settingsDraft[row.group][row.id] = next;
  state.settingsMessage = "";
  renderSettings();
}

function draftDirty() {
  return JSON.stringify(state.settingsDraft) !== JSON.stringify(activeModels());
}

function renderSettings() {
  if (!state.settingsDraft) state.settingsDraft = activeModels();
  const draftPreset = matchingPreset(state.bundle, { overrides: overridesFrom(state.bundle, state.settingsDraft) });
  $("preset").value = draftPreset;
  $("preset-hint").textContent = draftPreset === "custom" ? "Bạn đã chỉnh riêng từng bước." : PRESETS.find((p) => p.id === draftPreset).description;
  for (const section of settingsSections()) {
    for (const row of section.rows) {
      const key = `${row.group}-${row.id}`;
      const value = state.settingsDraft[row.group][row.id];
      const base = state.bundle.models[row.group][row.id];
      $(`model-${key}`).value = value.model;
      $(`effort-${key}`).value = value.effort;
      const changed = value.model !== base.model || value.effort !== base.effort;
      $(`s-default-${key}`).textContent = changed ? `mặc định: ${modelName(base.model)} · ${base.effort}` : "";
      document.querySelector(`[data-setting="${key}"]`).classList.toggle("changed", changed);
    }
  }
  const savedPreset = matchingPreset(state.bundle, state.settings);
  $("settings-summary").textContent = presetLabel(savedPreset);
  const dirty = draftDirty();
  $("settings-save").disabled = !dirty;
  $("settings-reset").disabled = savedPreset === "balanced" && !dirty;
  $("settings-note").textContent = state.settingsMessage || (dirty ? "Có thay đổi chưa lưu. Lần chạy mới vẫn dùng cấu hình đã lưu cho tới khi bạn bấm Lưu." : "");
}

function readLocalSettings() {
  try {
    return JSON.parse(localStorage.getItem(SETTINGS_KEY) || "null");
  } catch (_) {
    return null;
  }
}

async function loadSettings() {
  let saved = null;
  const messages = [];
  try {
    saved = state.repo ? await withTimeout(state.repo.loadSettings(), STORE_TIMEOUT_MS) : readLocalSettings();
  } catch (error) {
    messages.push(`Chưa tải được cấu hình đã lưu: ${dbErrorText(error)} Đang dùng mặc định.`);
  }
  if (saved) {
    const { overrides, dropped } = cleanOverrides(state.bundle, saved.overrides);
    if (dropped.length) messages.push(`Bỏ qua phần cấu hình không còn hợp lệ: ${dropped.join(", ")}.`);
    state.settings = { schema: 1, preset: saved.preset || null, overrides };
  } else {
    state.settings = null;
  }
  state.settingsDraft = activeModels();
  state.settingsMessage = messages.join(" ");
  renderSettings();
  renderAbSetup();
  renderAll();
}

async function saveSettings(models) {
  const overrides = overridesFrom(state.bundle, models);
  const settings = { schema: 1, preset: matchingPreset(state.bundle, { overrides }), overrides };
  state.settings = settings;
  state.settingsDraft = activeModels();
  try {
    if (state.repo) {
      await withTimeout(state.repo.saveSettings(settings), STORE_TIMEOUT_MS);
    } else {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    }
    state.settingsMessage = state.repo
      ? "Đã lưu vào tài khoản của bạn. Lần chạy mới sẽ dùng cấu hình này."
      : "Đã lưu trong trình duyệt này (trang không có quyền lưu trữ). Lần chạy mới sẽ dùng cấu hình này.";
  } catch (error) {
    state.settingsMessage = `Chưa lưu được: ${dbErrorText(error)} Cấu hình vẫn áp dụng cho tới khi tải lại trang.`;
  }
  renderSettings();
  renderAll();
}

// --- So sánh A/B mù (ART-6.1) ------------------------------------------------

function abChoices() {
  const saved = matchingPreset(state.bundle, state.settings);
  return [
    { value: "saved", label: `Cấu hình đang lưu (${presetLabel(saved)})` },
    ...PRESETS.map((preset) => ({ value: `preset:${preset.id}`, label: preset.label })),
  ];
}

function abConfig(value) {
  if (value === "saved") {
    const preset = matchingPreset(state.bundle, state.settings);
    return { label: preset === "custom" ? "Cấu hình riêng của bạn" : presetLabel(preset), preset, models: activeModels() };
  }
  const id = value.slice("preset:".length);
  return { label: presetLabel(id), preset: id, models: presetModels(state.bundle, id) };
}

function renderAbSetup() {
  for (const [id, fallback] of [["ab-config-1", "saved"], ["ab-config-2", null]]) {
    const select = $(id);
    const previous = select.value;
    select.replaceChildren(...abChoices().map((choice) => h("option", { value: choice.value, text: choice.label })));
    if (previous && [...select.options].some((option) => option.value === previous)) select.value = previous;
    else if (fallback) select.value = fallback;
    else select.value = matchingPreset(state.bundle, state.settings) === "opus-medium" ? "preset:balanced" : "preset:opus-medium";
  }
  renderAbCost();
}

function renderAbCost() {
  const steps = state.bundle.workflows[state.mode].stage_ids.length;
  $("ab-cost").textContent = `Một lượt A/B gọi Claude ${steps * 2} lần (${steps} bước × 2 cấu hình), gấp đôi một lần chạy thường.`;
}

const letterOf = (session, index) => (session.letters.A === index ? "A" : "B");

function abDrafts(ab) {
  return ab.runs.map((run) => {
    const primary = run && collectFinalOutputs(state.bundle.workflows[run.mode].definition, run).primary;
    return primary ? { text: primary.text, words: primary.words } : null;
  });
}

function renderAb() {
  const ab = state.ab;
  $("ab-view").hidden = !ab;
  $("ab-note").textContent = state.abMessage;
  $("ab-start").disabled = state.busy || !state.client;
  for (const button of $("ab-list").querySelectorAll("button")) button.disabled = state.busy;
  if (!ab) {
    state.abRenderedKey = null;
    return;
  }
  const { session } = ab;
  const total = session.mode ? state.bundle.workflows[session.mode].stage_ids.length : 0;
  let text;
  if (state.busy && ab.progress) {
    const [label] = AGENTS[ab.progress.stageId] || [ab.progress.stageId];
    text = `Đang viết bài ${ab.progress.letter} · bước ${ab.progress.index + 1}/${total}: ${label}${ab.progress.chars ? ` (${ab.progress.chars} ký tự)` : ""}.`;
  } else if (ab.error) {
    text = ab.error;
  } else if (session.status === "ready") {
    text = "Đọc hai bài rồi chọn bài bạn thích hơn. Cấu hình của từng bài được giấu cho tới khi bạn chốt.";
  } else if (session.status === "decided") {
    text = session.choice === "tie" ? "Bạn thấy hai bài ngang nhau." : `Bạn chọn bài ${session.choice}.`;
  } else {
    text = "Đang chuẩn bị…";
  }
  $("ab-status").textContent = [text, ab.saveProblem].filter(Boolean).join(" ");
  $("ab-stop").hidden = !state.busy;
  $("ab-close").disabled = state.busy;
  $("ab-resume").hidden = state.busy || !ab.error;
  $("ab-choose").hidden = session.status !== "ready";
  $("ab-decide").disabled = state.busy;

  const key = `${session.id}:${session.status}`;
  if (state.abRenderedKey !== key) {
    state.abRenderedKey = key;
    const drafts = abDrafts(ab);
    const showDrafts = (session.status === "ready" || session.status === "decided") && drafts.every(Boolean);
    $("ab-drafts").replaceChildren(
      ...(showDrafts
        ? blindDrafts(session, drafts).map((draft) =>
            h(
              "article",
              { class: "ab-draft", "data-letter": draft.letter },
              h("div", { class: "row", style: "justify-content:space-between" }, h("h3", { text: `Bài ${draft.letter}` }), h("span", { class: "meta", text: `${draft.words} từ` })),
              h("pre", { class: "text", text: draft.text }),
            ),
          )
        : []),
    );
    if (session.status === "ready") {
      for (const input of document.querySelectorAll('input[name="ab-choice"]')) input.checked = false;
      $("ab-reason").value = "";
    }
    $("ab-reveal").hidden = session.status !== "decided";
    $("ab-reveal").replaceChildren(
      ...(session.status === "decided"
        ? [
            h("h3", { text: "Bài nào của cấu hình nào" }),
            h(
              "ul",
              { class: "ab-reveal-list" },
              revealAb(session).map((row) =>
                h(
                  "li",
                  { "data-letter": row.letter, class: row.chosen ? "chosen" : null },
                  h("strong", { text: `Bài ${row.letter}` }),
                  h("span", { text: row.label }),
                  row.chosen ? h("span", { class: "ok", text: "bạn chọn" }) : null,
                  row.run_id && state.repo
                    ? h("button", { type: "button", class: "small", text: "Mở trong khung chính", onclick: () => openRun(row.run_id) })
                    : null,
                ),
              ),
            ),
            session.note ? h("p", { class: "hint", text: `Ghi chú: ${session.note}` }) : null,
          ]
        : []),
    );
  }
}

function renderAbList() {
  const items = state.abSessions.map((session) => {
    const when = formatWhen(session.created_at);
    let outcome;
    if (session.status === "decided") {
      outcome = session.choice === "tie" ? "Ngang nhau" : `Chọn: ${session.configs[session.chosen_config].label}`;
    } else {
      outcome = "Chưa chọn · mở để làm tiếp";
    }
    return h(
      "li",
      {},
      h(
        "button",
        { type: "button", "data-ab": session.id, disabled: state.busy, onclick: () => openAbSession(session.id) },
        h("span", { class: "h-title", text: outcome }),
        h("span", { class: "h-meta" }, h("span", { text: when }), h("span", { text: `${session.mode} · ${session.style}` })),
      ),
    );
  });
  $("ab-list").replaceChildren(...items);
  $("ab-list-note").textContent = state.repo
    ? state.abSessions.length
      ? ""
      : "Chưa có phiên A/B nào."
    : "Phiên A/B chỉ được lưu khi trang có quyền lưu trữ.";
}

async function loadAbSessions() {
  if (!state.repo) {
    state.abSessions = [];
    renderAbList();
    return;
  }
  try {
    state.abSessions = await withTimeout(state.repo.listAbSessions(10), STORE_TIMEOUT_MS);
  } catch (error) {
    state.abMessage = `Chưa tải được các phiên A/B: ${dbErrorText(error)}`;
  }
  renderAbList();
  renderAb();
}

async function saveAbState(runs = []) {
  const ab = state.ab;
  if (!state.repo) return;
  try {
    for (const run of runs) await state.repo.saveRun(run, saveExtras(run));
    await state.repo.saveAbSession(ab.session);
  } catch (error) {
    ab.saveProblem = `Không lưu được phiên A/B: ${dbErrorText(error)}`;
  }
}

async function startAb() {
  if (state.busy || !state.client) return;
  state.abMessage = "";
  let authorInput;
  let session;
  try {
    authorInput = buildAuthorInput(fields());
    session = createAbSession({
      mode: state.mode,
      style: $("style").value,
      authorInput,
      configs: [abConfig($("ab-config-1").value), abConfig($("ab-config-2").value)],
    });
  } catch (error) {
    state.abMessage = error.message || String(error);
    renderAb();
    return;
  }
  const runs = session.configs.map((config, index) => {
    const run = createRun({ bundle: state.bundle, mode: session.mode, style: session.style, authorInput });
    run.title = $("title").value.trim();
    run.buildId = state.buildInfo.build_id || null;
    run.models = config.models;
    run.modelProfile = modelProfile(state.bundle, { overrides: overridesFrom(state.bundle, config.models) });
    run.abSession = { id: session.id, slot: index, letter: letterOf(session, index), decided: false };
    return run;
  });
  state.ab = { session, runs, error: "", saveProblem: "", progress: null };
  if (state.repo) {
    try {
      for (const run of runs) await state.repo.createRun(run, saveExtras(run));
    } catch (error) {
      state.ab.saveProblem = `Không lưu được phiên A/B: ${dbErrorText(error)} Hai bài vẫn hiện trên trang.`;
    }
  }
  for (const run of runs) if (!run.id) run.id = newRunId({ mode: run.mode, style: run.style });
  session.run_ids = runs.map((run) => run.id);
  if (state.repo && !state.ab.saveProblem) await saveAbState();
  await advanceAb({ resume: false });
}

/** Chạy hai bài theo thứ tự A rồi B. Khi làm tiếp (`resume`), chạy lại bước lỗi một lần. */
async function advanceAb({ resume }) {
  const ab = state.ab;
  if (!ab || state.busy) return;
  state.busy = true;
  state.controller = new AbortController();
  ab.error = "";
  renderAll();
  try {
    for (const letter of ["A", "B"]) {
      const run = ab.runs[ab.session.letters[letter]];
      const options = {
        bundle: runBundle(run),
        client: state.client,
        signal: state.controller.signal,
        // Chỉ báo số ký tự đã viết; nội dung đang viết không hiện để hai bài chỉ lộ ra cùng lúc.
        onText: ({ text: partial }) => {
          if (!ab.progress) return;
          ab.progress.chars = partial.length;
          renderAb();
        },
      };
      let retryAllowed = resume;
      for (;;) {
        let index = nextStageIndex(run);
        let retry = false;
        if (index === -1) {
          if (run.status === RUN_STATUS.COMPLETED) break;
          index = run.stageIds.findIndex((id) => run.results[id] && run.results[id].status !== "completed");
          if (!retryAllowed || index === -1) break;
          retryAllowed = false;
          retry = true;
        }
        const stageId = run.stageIds[index];
        ab.progress = { letter, index, stageId };
        renderAb();
        if (retry) {
          if (state.repo && run.persisted) await state.repo.deleteStagesFrom(run, index).catch(() => {});
          await retryStage(run, index, options);
        } else {
          await runStage(run, index, options);
        }
        if (state.repo && run.persisted) {
          await state.repo.saveStage(run, stageId, saveExtras(run)).catch((error) => {
            ab.saveProblem = `Không lưu được bước ${stageId}: ${dbErrorText(error)}`;
          });
        }
      }
      if (run.status !== RUN_STATUS.COMPLETED) {
        const failed = run.stageIds.map((id) => run.results[id]).find((result) => result && result.status !== "completed");
        const cancelled = failed && failed.error_code === "cancelled";
        const reason = cancelled ? "đã dừng." : `lỗi: ${failed ? errorText(failed).replace(/\.?$/, ".") : "chưa xong."}`;
        ab.error = `Bài ${letter} ${reason} Bấm "Chạy tiếp" để làm nốt.`;
        break;
      }
    }
    if (!ab.error) {
      ab.session.status = "ready";
      await saveAbState();
    }
  } catch (error) {
    ab.error = `Không chạy được A/B: ${error.message || error}`;
  } finally {
    state.busy = false;
    state.controller = null;
    ab.progress = null;
    renderAll();
    loadAbSessions();
  }
}

async function decideAbChoice() {
  const ab = state.ab;
  if (!ab || state.busy) return;
  const picked = document.querySelector('input[name="ab-choice"]:checked');
  if (!picked) {
    $("ab-choose-note").textContent = "Hãy chọn bài A, bài B hoặc ngang nhau.";
    return;
  }
  $("ab-choose-note").textContent = "";
  decideAb(ab.session, picked.value, $("ab-reason").value);
  ab.runs.forEach((run, index) => {
    run.abSession = { ...run.abSession, letter: letterOf(ab.session, index), decided: true, chosen: ab.session.chosen_config === index };
  });
  await saveAbState(state.repo ? ab.runs.filter((run) => run.persisted) : []);
  renderAll();
  loadHistory();
  loadAbSessions();
}

async function openAbSession(id) {
  if (state.busy || !state.repo) return;
  const session = state.abSessions.find((item) => item.id === id);
  if (!session) return;
  state.abMessage = "Đang mở phiên A/B…";
  renderAb();
  try {
    if (!session.run_ids.every(Boolean)) throw new Error("Phiên này chưa kịp lưu hai bài.");
    const runs = [];
    for (const runId of session.run_ids) {
      const data = await withTimeout(state.repo.loadRun(runId), STORE_TIMEOUT_MS);
      if (!data) throw new Error("Không còn tìm thấy một trong hai bài.");
      const { run, resumable, problems } = restoreRun(state.bundle, data.runDoc, data.stageDocs);
      if (!resumable && session.status !== "decided") throw new Error(problems.join(" "));
      runs.push(run);
    }
    const copy = structuredClone(session);
    const complete = runs.every((run) => run.status === RUN_STATUS.COMPLETED);
    if (copy.status === "running" && complete) copy.status = "ready";
    state.ab = { session: copy, runs, error: "", saveProblem: "", progress: null };
    if (copy.status === "running") state.ab.error = 'Phiên này chưa xong. Bấm "Chạy tiếp" để làm nốt.';
    state.abMessage = "";
  } catch (error) {
    state.abMessage = `Không mở được phiên A/B: ${error.message || dbErrorText(error)}`;
  }
  renderAll();
}

// --- Khởi động --------------------------------------------------------------

async function connectClaude() {
  if (!window.claude || typeof window.claude.use !== "function") {
    setChip("chip-claude", "Claude: không khả dụng", "bad");
    setChip("chip-storage", "Lưu trữ: không khả dụng", "bad");
    state.storageMessage = "Lịch sử chỉ có khi mở trang trong claude.ai.";
    showBanner("Trang này cần được mở trong claude.ai để gọi Claude.");
    loadHistory();
    loadSettings();
    loadAbSessions();
    return;
  }
  const [sample, downloads, db, user] = await Promise.all(["sample", "downloads", "db", "user"].map((name) => window.claude.use(name)));
  state.client = sample ? createSampleClient(sample) : null;
  state.downloads = downloads;
  setChip("chip-claude", sample ? "Claude: sẵn sàng" : "Claude: không khả dụng", sample ? "ok" : "bad");
  if (!sample) showBanner("Không gọi được Claude từ trang này. Hãy mở trang trong claude.ai bằng tài khoản Claude của bạn.");
  const userId = db && user ? await user.id() : null;
  if (db && userId) {
    state.repo = createRunRepository({ db, userId });
    setChip("chip-storage", "Lưu trữ: sẵn sàng", "ok");
  } else {
    setChip("chip-storage", "Lưu trữ: không khả dụng", "bad");
    state.storageMessage = db
      ? "Không xác định được tài khoản nên không lưu được lịch sử. Lần chạy vẫn tải zip được."
      : "Trang không có quyền lưu trữ trong lần mở này. Lần chạy vẫn tải zip được.";
  }
  renderAll();
  loadHistory();
  loadSettings();
  loadAbSessions();
}

function boot() {
  try {
    state.bundle = validateBundle(JSON.parse($("bundle-data").textContent));
  } catch (error) {
    showBanner(`Bản build của trang bị lỗi, không thể chạy: ${error.message}`);
    $("run").disabled = true;
    return;
  }
  try {
    state.buildInfo = JSON.parse($("build-info").textContent) || {};
  } catch (_) {
    state.buildInfo = {};
  }
  const builtOn = state.buildInfo.commit_date ? ` · ${new Date(state.buildInfo.commit_date).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" })}` : "";
  setChip("chip-build", `Phiên bản: ${state.buildInfo.build_id || state.bundle.content_hash.slice(0, 12)}${builtOn}`);
  const draft = loadDraft();
  if (draft) {
    $("title").value = draft.title || "";
    $("raw-notes").value = draft.rawNotes || "";
    $("optional-context").value = draft.optionalContext || "";
    $("target-reader").value = draft.targetReader || "";
    if (draft.optionalContext || draft.targetReader) $("more").open = true;
    state.lengthEdited = Boolean(draft.lengthEdited);
    if (state.lengthEdited) $("desired-length").value = draft.desiredLength || "";
    if (draft.pace === "step") $("pace-step").checked = true;
  }
  setMode(draft && state.bundle.workflows[draft.mode] ? draft.mode : "moment", draft && draft.style);
  buildSettingsTable();
  renderSettings();
  renderAbSetup();

  for (const button of document.querySelectorAll("[data-mode]")) {
    button.addEventListener("click", () => {
      if (state.busy) return;
      // Không xóa lần chạy đang xem: kết quả chỉ mất khi chủ động chạy mới (có bước xác nhận).
      setMode(button.dataset.mode);
      saveDraft();
      renderAbCost();
      renderAll();
    });
  }
  $("desired-length").addEventListener("input", () => (state.lengthEdited = true));
  $("form").addEventListener("input", saveDraft);
  $("form").addEventListener("change", saveDraft);
  $("form").addEventListener("submit", startRun);
  $("stop").addEventListener("click", () => state.controller && state.controller.abort());
  $("next").addEventListener("click", () => go({ continuous: $("pace-all").checked }));
  $("history-reload").addEventListener("click", loadHistory);
  $("production").addEventListener("input", () => {
    state.learningMessage = "";
    renderProduction();
  });
  $("production-save").addEventListener("click", saveProduction);
  $("production-reset").addEventListener("click", () => {
    const primary = primaryDraft();
    if (primary) $("production").value = primary.text;
    state.learningMessage = "";
    renderProduction();
  });
  $("learn-claude").addEventListener("click", () => learn(false));
  $("learn-offline").addEventListener("click", () => learn(true));
  $("learning-select").addEventListener("change", (event) => {
    state.learningSelected = event.target.value;
    renderLearning();
  });
  $("download-learning").addEventListener("click", downloadLearning);
  $("download-zip").addEventListener("click", downloadZip);
  $("download-final").addEventListener("click", downloadFinalBlog);
  $("download-runlog").addEventListener("click", downloadRunLog);
  $("copy-draft").addEventListener("click", copyDraft);
  $("download-draft").addEventListener("click", () => {
    const { primary } = collectFinalOutputs(state.bundle.workflows[state.run.mode].definition, state.run);
    if (primary) saveFile(`${baseName()}.md`, primary.text.trim() + "\n");
  });
  $("download-run").addEventListener("click", () => saveFile(`${baseName()}-toan-bo.md`, buildRunMarkdown(state.run), showRunNote));
  $("preset").addEventListener("change", (event) => {
    state.settingsDraft = presetModels(state.bundle, event.target.value);
    state.settingsMessage = "";
    renderSettings();
  });
  $("settings-save").addEventListener("click", () => saveSettings(state.settingsDraft).then(renderAbSetup));
  $("settings-reset").addEventListener("click", () => saveSettings(structuredClone(state.bundle.models)).then(renderAbSetup));
  $("ab-start").addEventListener("click", startAb);
  $("ab-stop").addEventListener("click", () => state.controller && state.controller.abort());
  $("ab-resume").addEventListener("click", () => advanceAb({ resume: true }));
  $("ab-decide").addEventListener("click", decideAbChoice);
  $("ab-close").addEventListener("click", () => {
    if (state.busy) return;
    state.ab = null;
    renderAb();
  });
  renderAll();
  connectClaude();
}

boot();
