// Giao diện MVP (ART-3). Chỉ lo hiển thị và tương tác; mọi logic workflow nằm
// trong ../core. Nội dung do model sinh luôn được gán qua textContent.
import { listStyles, validateBundle } from "../core/contracts.js";
import { createSampleClient } from "../core/client_sample.js";
import { buildAuthorInput, slugify } from "../core/input.js";
import { createRun, nextStageIndex, retryStage, runStage, RUN_STATUS } from "../core/orchestrator.js";
import { buildRunMarkdown, collectFinalOutputs } from "../core/outputs.js";
import { countWords } from "../core/parser.js";

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
const DRAFT_KEY = "mindful-blog-workflow:draft:v1";

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
};

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
    if (!state.busy) {
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
  return `${run.mode} · ${run.style} — ${runProgressText(run)}`;
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
  const canSave = Boolean(state.downloads);
  $("download-draft").disabled = !canSave;
  $("download-run").disabled = !canSave;
  if (!canSave) $("final-note").textContent = "Tải file chỉ có khi mở trang trong claude.ai; vẫn có thể sao chép bài.";
}

function updateControls() {
  const busy = state.busy;
  for (const node of $("form").querySelectorAll("input, textarea, select, .segmented button")) node.disabled = busy;
  $("run").disabled = busy || !state.client;
  $("run").textContent = state.armedRestart ? "Bấm lần nữa để chạy mới" : state.run ? "Chạy lại từ đầu" : "Chạy workflow";
  $("stop").disabled = !busy;
  const next = state.run ? nextStageIndex(state.run) : -1;
  const nextButton = $("next");
  nextButton.hidden = busy || next === -1;
  if (next !== -1) nextButton.textContent = `Chạy bước tiếp: ${(AGENTS[state.run.stageIds[next]] || [state.run.stageIds[next]])[0]}`;
  $("run-status").textContent = runStatusText();
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
      if (retryIndex !== null && index === retryIndex) await retryStage(state.run, index, options);
      else await runStage(state.run, index, options);
      state.liveStage = null;
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
  state.live = {};
  state.open.clear();
  showBanner("");
  go();
}

async function saveFile(filename, data) {
  const note = $("final-note");
  if (!state.downloads) return;
  try {
    await state.downloads.save({ filename, data });
    note.textContent = `Đã lưu ${filename}.`;
  } catch (error) {
    note.textContent = error && error.code === "declined" ? "Bạn đã hủy tải về." : `Không tải được file: ${(error && error.message) || error}`;
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
    showBanner("Trang này cần được mở trong claude.ai để gọi Claude.");
    return;
  }
  const [sample, downloads] = await Promise.all([window.claude.use("sample"), window.claude.use("downloads")]);
  state.client = sample ? createSampleClient(sample) : null;
  state.downloads = downloads;
  setChip("chip-claude", sample ? "Claude: sẵn sàng" : "Claude: không khả dụng", sample ? "ok" : "bad");
  if (!sample) showBanner("Không gọi được Claude từ trang này. Hãy mở trang trong claude.ai bằng tài khoản Claude của bạn.");
  renderAll();
}

function boot() {
  try {
    state.bundle = validateBundle(JSON.parse($("bundle-data").textContent));
  } catch (error) {
    showBanner(`Bản build của trang bị lỗi, không thể chạy: ${error.message}`);
    $("run").disabled = true;
    return;
  }
  setChip("chip-bundle", `Bản build: ${state.bundle.content_hash.slice(0, 12)}`);
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
  $("next").addEventListener("click", () => go({ continuous: false }));
  $("copy-draft").addEventListener("click", copyDraft);
  $("download-draft").addEventListener("click", () => {
    const { primary } = collectFinalOutputs(state.bundle.workflows[state.run.mode].definition, state.run);
    if (primary) saveFile(`${baseName()}.md`, primary.text.trim() + "\n");
  });
  $("download-run").addEventListener("click", () => saveFile(`${baseName()}-toan-bo.md`, buildRunMarkdown(state.run)));
  renderAll();
  connectClaude();
}

boot();
