// Chuyển một lần chạy (trạng thái của orchestrator) sang document lưu trữ và
// ngược lại. Hàm thuần: không gọi db, không chạm DOM.
import { deriveArtifactFileContents } from "./artifacts.js";
import { slugify } from "./input.js";
import { RUN_STATUS } from "./orchestrator.js";

export const RECORD_SCHEMA = 1;

const pad = (value, width = 2) => String(value).padStart(width, "0");

/**
 * Run ID chống va chạm, cùng dạng engine (timestamp đến micro giây + 8 ký tự
 * hex ngẫu nhiên + mode + style), chỉ gồm ký tự hợp lệ cho đường dẫn db.
 */
export function newRunId({ mode, style, now = new Date(), randomHex }) {
  const suffix = (randomHex || defaultRandomHex)(8);
  return `${utcStamp(now)}_${suffix}_${mode}_${style}`;
}

/** Dấu thời gian kiểu `%Y%m%d_%H%M%S_%f` (UTC) mà engine dùng cho tên run và thư mục learning. */
export function utcStamp(now = new Date()) {
  return (
    `${now.getUTCFullYear()}${pad(now.getUTCMonth() + 1)}${pad(now.getUTCDate())}_` +
    `${pad(now.getUTCHours())}${pad(now.getUTCMinutes())}${pad(now.getUTCSeconds())}_` +
    `${pad(now.getUTCMilliseconds() * 1000, 6)}`
  );
}

function defaultRandomHex(length) {
  const bytes = new Uint8Array(Math.ceil(length / 2));
  globalThis.crypto.getRandomValues(bytes);
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, length);
}

/**
 * Port của engine/parser.py::extract_title, giữ nguyên cả hành vi của regex:
 * `title:` để trống khiến `\s*` vượt xuống dòng và lấy dòng kế tiếp (vì vậy run
 * của engine hay có đuôi "raw-notes").
 */
export function extractTitle(inputMarkdown) {
  const match = /^title:\s*(.+)$/im.exec(inputMarkdown);
  if (match && match[1].trim()) return match[1].trim();
  const heading = /^#\s+(.+)$/m.exec(inputMarkdown);
  return heading ? heading[1].trim() : "blog";
}

/** Tên thư mục giống build_run_dir của engine: <run id>_<slug tiêu đề>. */
export function runFolderName(run) {
  return `${run.id}_${slugify(extractTitle(run.authorInput))}`;
}

/** Document của một lần chạy: đủ để hiện lịch sử mà không phải đọc từng stage. */
export function serializeRunDoc(run, extras = {}) {
  return {
    schema: RECORD_SCHEMA,
    id: run.id,
    mode: run.mode,
    style: run.style,
    title: extras.title ?? run.title ?? "",
    author_input: run.authorInput,
    bundle_hash: run.bundleHash,
    build_id: extras.buildId ?? run.buildId ?? null,
    run_source: run.runSource,
    status: run.status,
    stage_ids: [...run.stageIds],
    stage_status: Object.fromEntries(run.stageIds.filter((id) => run.results[id]).map((id) => [id, run.results[id].status])),
    api_attempted: Boolean(run.apiAttempted),
    api_called: Boolean(run.apiCalled),
    primary_words: extras.primaryWords ?? null,
    created_at: run.createdAt,
    updated_at: (extras.now || new Date()).toISOString(),
    completed_at: run.completedAt,
  };
}

/**
 * Document của một stage. Không lưu `files`: chúng được tách lại từ artifact khi
 * khôi phục, để document nhỏ (giới hạn 256 KiB) và không lưu trùng nội dung.
 */
export function serializeStageDoc(result) {
  const { files, ...rest } = result;
  return { schema: RECORD_SCHEMA, ...rest };
}

/**
 * Dựng lại trạng thái run từ document đã lưu, theo bundle hiện tại.
 * @returns {{run, resumable: boolean, problems: string[]}}
 */
export function restoreRun(bundle, runDoc, stageDocs) {
  const problems = [];
  const workflow = bundle.workflows[runDoc.mode];
  const style = workflow && bundle.styles[runDoc.mode][runDoc.style];
  if (!workflow) problems.push(`Bản hiện tại không còn mode ${runDoc.mode}.`);
  if (workflow && !style) problems.push(`Bản hiện tại không còn style ${runDoc.style}.`);
  if (workflow && JSON.stringify(workflow.stage_ids) !== JSON.stringify(runDoc.stage_ids)) {
    problems.push("Các bước của workflow đã thay đổi so với lúc chạy.");
  }
  const byId = Object.fromEntries(stageDocs.map((doc) => [doc.stage_id, doc]));
  const run = {
    id: runDoc.id,
    title: runDoc.title || "",
    buildId: runDoc.build_id || null,
    bundleHash: runDoc.bundle_hash,
    mode: runDoc.mode,
    style: runDoc.style,
    authorInput: runDoc.author_input,
    runSource: runDoc.run_source || "artifact",
    stopOnError: true,
    stageIds: [...runDoc.stage_ids],
    results: {},
    artifacts: {},
    handoffs: {},
    status: runDoc.status,
    apiAttempted: Boolean(runDoc.api_attempted),
    apiCalled: Boolean(runDoc.api_called),
    createdAt: runDoc.created_at,
    completedAt: runDoc.completed_at || null,
    persisted: true,
  };
  // Chỉ nhận các stage liên tiếp từ đầu; một bản ghi lẻ phía sau (do ghi dở) bị bỏ qua.
  for (const id of run.stageIds) {
    const doc = byId[id];
    if (!doc) break;
    const { schema, ...result } = doc;
    if (result.status === "completed") {
      const skill = style?.files[workflow.stage_files[id]]?.data;
      result.files = skill ? deriveArtifactFileContents(skill, result.artifact).files : { [result.artifact_file]: result.artifact };
      run.artifacts[id] = result.artifact;
      run.handoffs[id] = result.handoff;
    }
    run.results[id] = result;
  }
  // Một run "đang chạy" khi mở lại nghĩa là lần trước bị gián đoạn: có thể chạy tiếp.
  const known = [RUN_STATUS.RUNNING, RUN_STATUS.COMPLETED, RUN_STATUS.FAILED, RUN_STATUS.CANCELLED];
  if (!known.includes(run.status)) problems.push(`Trạng thái lạ: ${run.status}.`);
  return { run, resumable: problems.length === 0, problems };
}
