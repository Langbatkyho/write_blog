// ART-4: Run ID, lưu/khôi phục run qua db (giả) và xuất bộ file theo bố cục runs/ của engine.
import assert from "node:assert/strict";
import { test } from "node:test";

import { createFakeClient } from "../../src/core/client_fake.js";
import { exportRunFiles, runMetadata } from "../../src/core/export.js";
import { createRun, nextStageIndex, resetFromStage, retryStage, runNextStage, runWorkflow } from "../../src/core/orchestrator.js";
import { createRunRepository, MAX_DOC_BYTES } from "../../src/core/repository.js";
import { extractTitle, newRunId, restoreRun, runFolderName, serializeRunDoc, serializeStageDoc } from "../../src/core/run_record.js";
import { createFakeDb } from "./fake_db.js";
import { loadBundle } from "./helpers.js";

const INPUT = "title: Chiều mưa\n\nraw_notes:\n- Mưa rơi 🌧️\n";
const UID = "u_test";

async function persistedRun(bundle, repo, options = {}) {
  const run = createRun({ bundle, mode: "moment", style: "va-natural", authorInput: INPUT });
  await repo.createRun(run, { title: "Chiều mưa" });
  const client = options.client || createFakeClient();
  for (let index = nextStageIndex(run); index !== -1; index = nextStageIndex(run)) {
    const result = await runNextStage(run, { bundle, client });
    await repo.saveStage(run, result.stage_id, { title: "Chiều mưa" });
  }
  return run;
}

test("Run ID: đúng dạng engine, chỉ ký tự hợp lệ cho db, không trùng", () => {
  const id = newRunId({ mode: "moment", style: "va-natural", now: new Date(Date.UTC(2026, 10, 14, 9, 5, 7, 42)), randomHex: () => "ab12cd34" });
  assert.equal(id, "20261114_090507_042000_ab12cd34_moment_va-natural");
  assert.match(id, /^[A-Za-z0-9_\-.~:@+]+$/);
  const ids = new Set(Array.from({ length: 200 }, () => newRunId({ mode: "deep", style: "reflective" })));
  assert.equal(ids.size, 200);
});

test("extractTitle giữ hành vi của engine, kể cả khi title trống", () => {
  assert.equal(extractTitle("title: Chiều mưa\n\nraw_notes:\nx"), "Chiều mưa");
  assert.equal(extractTitle("title:\n\nraw_notes:\nx"), "raw_notes:");
  assert.equal(extractTitle("# Tiêu đề H1\nx"), "Tiêu đề H1");
  assert.equal(extractTitle("không có gì"), "blog");
});

test("lưu run và từng stage, rồi khôi phục giống hệt để hiển thị", async () => {
  const bundle = loadBundle();
  const db = createFakeDb();
  const repo = createRunRepository({ db, userId: UID });
  const run = await persistedRun(bundle, repo);
  assert.equal(run.status, "completed");
  assert.ok(run.persisted);
  const runPath = `data/users/${UID}/blog/runs/${run.id}`;
  assert.ok(db.store.has(runPath));
  for (const id of run.stageIds) assert.ok(db.store.has(`${runPath}/stages/${id}`), id);
  assert.equal(db.store.get(`${runPath}/stages/breath_editor`).files, undefined, "không lưu files trùng lặp");

  const listed = await repo.listRuns();
  assert.equal(listed.length, 1);
  assert.equal(listed[0].title, "Chiều mưa");
  assert.equal(listed[0].status, "completed");
  assert.deepEqual(Object.values(listed[0].stage_status), Array(6).fill("completed"));

  const { runDoc, stageDocs } = await repo.loadRun(run.id);
  const { run: restored, resumable, problems } = restoreRun(bundle, runDoc, stageDocs);
  assert.ok(resumable, problems.join(" "));
  assert.equal(restored.status, "completed");
  assert.deepEqual(restored.results.breath_editor.files, run.results.breath_editor.files);
  assert.deepEqual(restored.handoffs, run.handoffs);
  assert.equal(await repo.loadRun("khong-co"), null);
});

test("lịch sử xếp mới nhất trước", async () => {
  const bundle = loadBundle();
  const times = [new Date(Date.UTC(2026, 0, 1)), new Date(Date.UTC(2026, 5, 1))];
  let tick = 0;
  const repo = createRunRepository({ db: createFakeDb(), userId: UID, clock: () => times[Math.min(tick, 1)] });
  const older = createRun({ bundle, mode: "deep", style: "reflective", authorInput: INPUT });
  older.createdAt = times[0].toISOString();
  await repo.createRun(older);
  tick = 1;
  const newer = createRun({ bundle, mode: "moment", style: "reflective", authorInput: INPUT });
  newer.createdAt = times[1].toISOString();
  await repo.createRun(newer);
  assert.deepEqual((await repo.listRuns()).map((r) => r.id), [newer.id, older.id]);
});

test("không ghi đè run đã có: Run ID trùng thì sinh ID khác, quá 5 lần thì báo lỗi", async () => {
  const bundle = loadBundle();
  const db = createFakeDb();
  const fixed = createRunRepository({ db, userId: UID, randomHex: () => "00000000", clock: () => new Date(Date.UTC(2026, 0, 1)) });
  const first = createRun({ bundle, mode: "moment", style: "reflective", authorInput: INPUT });
  await fixed.createRun(first);
  const before = JSON.stringify(db.store.get(`data/users/${UID}/blog/runs/${first.id}`));
  await assert.rejects(fixed.createRun(createRun({ bundle, mode: "moment", style: "reflective", authorInput: INPUT })), /5 lần/);
  assert.equal(JSON.stringify(db.store.get(`data/users/${UID}/blog/runs/${first.id}`)), before);

  const sequence = ["00000000", "00000000", "11111111"];
  const retrying = createRunRepository({ db, userId: UID, randomHex: () => sequence.shift(), clock: () => new Date(Date.UTC(2026, 0, 1)) });
  const second = createRun({ bundle, mode: "moment", style: "reflective", authorInput: INPUT });
  await retrying.createRun(second);
  assert.match(second.id, /_11111111_/);
});

test("run bị gián đoạn giữa chừng: mở lại và chạy tiếp tới hết", async () => {
  const bundle = loadBundle();
  const db = createFakeDb();
  const repo = createRunRepository({ db, userId: UID });
  const run = createRun({ bundle, mode: "moment", style: "va-natural", authorInput: INPUT });
  await repo.createRun(run);
  const client = createFakeClient();
  for (let i = 0; i < 3; i += 1) {
    const result = await runNextStage(run, { bundle, client });
    await repo.saveStage(run, result.stage_id);
  }
  // Trang bị đóng ở đây. Mở lại từ db:
  const { runDoc, stageDocs } = await repo.loadRun(run.id);
  const { run: restored, resumable } = restoreRun(bundle, runDoc, stageDocs);
  assert.ok(resumable);
  assert.equal(restored.status, "running");
  assert.equal(nextStageIndex(restored), 3);
  while (nextStageIndex(restored) !== -1) {
    const result = await runNextStage(restored, { bundle, client });
    await repo.saveStage(restored, result.stage_id);
  }
  assert.equal(restored.status, "completed");
  // Prompt của bước 4 sau khi mở lại giống hệt prompt khi chạy liền một mạch.
  const straight = createFakeClient();
  await runWorkflow({ bundle, mode: "moment", style: "va-natural", authorInput: INPUT, client: straight });
  assert.equal(client.calls[3].prompt, straight.calls[3].prompt);
});

test("chạy lại bước lỗi: xóa document của các bước từ đó trở đi rồi lưu lại", async () => {
  const bundle = loadBundle();
  const db = createFakeDb();
  const repo = createRunRepository({ db, userId: UID });
  const failures = { moment_writer: { code: "upstream_error", message: "x" } };
  const run = await persistedRun(bundle, repo, { client: createFakeClient({ failures }) });
  assert.equal(run.status, "failed");
  const stagePath = (id) => `data/users/${UID}/blog/runs/${run.id}/stages/${id}`;
  assert.ok(db.store.has(stagePath("moment_writer")));
  delete failures.moment_writer;
  await repo.deleteStagesFrom(run, 3);
  assert.ok(!db.store.has(stagePath("moment_writer")));
  const client = createFakeClient();
  const retried = await retryStage(run, 3, { bundle, client });
  await repo.saveStage(run, retried.stage_id);
  assert.ok(db.store.has(stagePath("moment_writer")));
  assert.equal(db.store.get(`data/users/${UID}/blog/runs/${run.id}`).stage_status.moment_writer, "completed");
});

test("khôi phục bằng bundle mà workflow đã đổi thì chỉ xem, không chạy tiếp", async () => {
  const bundle = loadBundle();
  const run = await runWorkflow({ bundle, mode: "moment", style: "reflective", authorInput: INPUT, client: createFakeClient() });
  run.id = "r1";
  const runDoc = serializeRunDoc(run);
  const stageDocs = run.stageIds.map((id) => serializeStageDoc(run.results[id]));
  const changed = loadBundle();
  changed.workflows.moment.stage_ids = [...changed.workflows.moment.stage_ids].reverse();
  assert.equal(restoreRun(changed, runDoc, stageDocs).resumable, false);
  delete changed.styles.moment.reflective;
  assert.match(restoreRun(changed, runDoc, stageDocs).problems.join(" "), /không còn style/);
});

test("lỗi lưu trữ được báo ra, hàng đợi ghi vẫn chạy tiếp", async () => {
  const bundle = loadBundle();
  let broken = true;
  const db = createFakeDb({ failOn: (op, path) => broken && op === "set" && path.includes("/stages/") });
  const repo = createRunRepository({ db, userId: UID });
  const run = createRun({ bundle, mode: "moment", style: "reflective", authorInput: INPUT });
  await repo.createRun(run);
  const client = createFakeClient();
  const first = await runNextStage(run, { bundle, client });
  await assert.rejects(repo.saveStage(run, first.stage_id), (e) => e.code === "unavailable");
  broken = false;
  const second = await runNextStage(run, { bundle, client });
  await repo.saveStage(run, second.stage_id);
  assert.ok(db.store.has(`data/users/${UID}/blog/runs/${run.id}/stages/${second.stage_id}`));
});

test("document quá 256 KiB bị chặn trước khi gửi", async () => {
  const bundle = loadBundle();
  const repo = createRunRepository({ db: createFakeDb(), userId: UID });
  const huge = "chữ ".repeat(MAX_DOC_BYTES / 4);
  const run = createRun({ bundle, mode: "moment", style: "reflective", authorInput: INPUT });
  await repo.createRun(run);
  const result = await runNextStage(run, { bundle, client: createFakeClient({ responses: { sensory_capture: `## Artifact\n\n${huge}\n\n## Handoff\n\nH` } }) });
  await assert.rejects(repo.saveStage(run, result.stage_id), (e) => e.code === "too_large");
});

test("không có userId hoặc db thì không tạo được repository", () => {
  assert.throws(() => createRunRepository({ db: createFakeDb(), userId: null }), /vùng lưu trữ riêng/);
  assert.throws(() => createRunRepository({ db: null, userId: UID }), /vùng lưu trữ riêng/);
});

test("xuất bộ file theo bố cục runs/ của engine", async () => {
  const bundle = loadBundle();
  const run = await runWorkflow({ bundle, mode: "deep", style: "reflective", authorInput: INPUT, client: createFakeClient() });
  assert.throws(() => exportRunFiles(bundle, run), /chưa có ID/);
  run.id = "20261114_090507_042000_ab12cd34_deep_reflective";
  const { folderName, files } = exportRunFiles(bundle, run);
  assert.equal(folderName, `${run.id}_chiều-mưa`);
  assert.equal(runFolderName(run), folderName);
  for (const name of ["input.md", "metadata.json", "step_outputs.json", "run_log.md", "handoff_log.md", "story_map.md", "edited_blog.md", "edit_log.md", "future_handoff.md"]) {
    assert.ok(name in files, name);
  }
  const metadata = JSON.parse(files["metadata.json"]);
  const engineKeys = ["created_at", "config_file", "workflow_file", "input_file", "dry_run", "run_source", "persisted", "api_attempted", "api_called", "status", "client_map", "style", "mode", "stage_telemetry", "completed_at", "context_strategy", "step_context_metrics", "total_artifact_estimated_tokens", "total_handoff_estimated_tokens"];
  for (const key of engineKeys) assert.ok(key in metadata, key);
  assert.equal(metadata.workflow_file, "flow/write_blog.yaml");
  assert.deepEqual(metadata, runMetadata(bundle, run));
  const steps = JSON.parse(files["step_outputs.json"]);
  assert.deepEqual(Object.keys(steps.editor_agent), ["status", "artifact", "handoff", "artifact_file", "handoff_file", "secondary_artifact_file", "warnings", "metrics", "error", "provider", "model", "api_attempted", "api_called", "duration_ms"]);
  assert.ok(files["run_log.md"].startsWith("# Run Metadata\n\n{"));
  assert.ok(files["run_log.md"].includes("\n\n\n# Author Input\n\n"));
  assert.ok(files["handoff_log.md"].startsWith("# 1. story_architect Handoff\n\n"));
});

test("xuất run lỗi: ghi ERROR vào run_log, chỉ có file của các bước đã xong", async () => {
  const bundle = loadBundle();
  const run = await runWorkflow({ bundle, mode: "moment", style: "reflective", authorInput: INPUT, client: createFakeClient({ failures: { inner_weather: { code: "rate_limited", message: "chậm lại" } } }) });
  run.id = "r_loi";
  const { files } = exportRunFiles(bundle, run);
  assert.ok(files["run_log.md"].includes("# 2. inner_weather ERROR\n\nchậm lại"));
  assert.ok("sensory_notes.md" in files);
  assert.ok(!("inner_weather.md" in files));
  assert.equal(JSON.parse(files["step_outputs.json"]).inner_weather.status, "failed");
  resetFromStage(run, 0);
});
