// Giao diện (ART-3, ART-4). Chỉ lo hiển thị và tương tác; mọi logic workflow và
// lưu trữ nằm trong ../core. Nội dung do model sinh luôn được gán qua textContent.
import { listStyles, validateBundle } from "../core/contracts.js";
import { createSampleClient } from "../core/client_sample.js";
import { exportRunFiles } from "../core/export.js";
import { buildAuthorInput, slugify } from "../core/input.js";
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
  const requested = state.bundle.models.stages[stageId];
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
  $("download-zip").disabled = busy || !state.downloads || !window.JSZip;
  $("persist-note").hidden = !state.persistNote;
  $("persist-note").textContent = state.persistNote;
  for (const button of $("history").querySelectorAll("button")) button.disabled = busy;
}

function renderAll() {
  renderStages();
  renderFinal();
  updateControls();
}

// --- Chạy -------------------------------------------------------------------

async function go({ retryIndex = null, continuous = $("pace-all").checked } = {}) {
  if (state.busy || !state.run || !state.client) return;
  state.busy = true;
  state.controller = new AbortController();
  const options = {
    bundle: state.bundle,
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

function saveExtras() {
  const { primary } = collectFinalOutputs(state.bundle.workflows[state.run.mode].definition, state.run);
  return { title: state.run.title, buildId: state.buildInfo.build_id || null, primaryWords: primary ? primary.words : null };
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

function renderHistory() {
  const items = state.history.map((record) => {
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
    note.textContent = runs.length ? "" : "Chưa có lần chạy nào được lưu.";
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
    const { folderName, files } = exportRunFiles(state.bundle, state.run);
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

// --- Khởi động --------------------------------------------------------------

async function connectClaude() {
  if (!window.claude || typeof window.claude.use !== "function") {
    setChip("chip-claude", "Claude: không khả dụng", "bad");
    setChip("chip-storage", "Lưu trữ: không khả dụng", "bad");
    state.storageMessage = "Lịch sử chỉ có khi mở trang trong claude.ai.";
    showBanner("Trang này cần được mở trong claude.ai để gọi Claude.");
    loadHistory();
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

  for (const button of document.querySelectorAll("[data-mode]")) {
    button.addEventListener("click", () => {
      if (state.busy) return;
      // Không xóa lần chạy đang xem: kết quả chỉ mất khi chủ động chạy mới (có bước xác nhận).
      setMode(button.dataset.mode);
      saveDraft();
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
  $("download-zip").addEventListener("click", downloadZip);
  $("copy-draft").addEventListener("click", copyDraft);
  $("download-draft").addEventListener("click", () => {
    const { primary } = collectFinalOutputs(state.bundle.workflows[state.run.mode].definition, state.run);
    if (primary) saveFile(`${baseName()}.md`, primary.text.trim() + "\n");
  });
  $("download-run").addEventListener("click", () => saveFile(`${baseName()}-toan-bo.md`, buildRunMarkdown(state.run), showRunNote));
  renderAll();
  connectClaude();
}

boot();
