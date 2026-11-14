// ART-2-AC3: orchestrator với client giả.
import assert from "node:assert/strict";
import { test } from "node:test";

import { createFakeClient } from "../../src/core/client_fake.js";
import {
  createRun,
  nextStageIndex,
  retryStage,
  runNextStage,
  runStage,
  runWorkflow,
  stageTelemetry,
} from "../../src/core/orchestrator.js";
import { loadBundle } from "./helpers.js";

const INPUT = "title: Thử\n\nraw_notes:\nMột buổi sáng có biển mây 🌥️.";
const DEEP = ["story_architect", "reflection_engine", "writing_agent", "reader_experience", "editor_agent", "coach_agent", "future_self"];

test("chạy đủ 7 stage deep và 6 stage moment, không gọi API", async () => {
  const bundle = loadBundle();
  for (const [mode, style, count] of [["deep", "reflective", 7], ["moment", "va-natural", 6]]) {
    const client = createFakeClient();
    const run = await runWorkflow({ bundle, mode, style, authorInput: INPUT, client });
    assert.equal(run.status, "completed");
    assert.equal(client.calls.length, count);
    assert.equal(run.apiAttempted, false);
    assert.equal(run.apiCalled, false);
    for (const result of Object.values(run.results)) {
      assert.equal(result.status, "completed");
      assert.equal(result.api_called, false);
      assert.equal(result.model_applied, bundle.models.stages[result.stage_id].model);
      assert.ok(result.metrics.artifact_estimated_tokens > 0);
      assert.ok(result.files[result.artifact_file]);
    }
  }
});

test("client nhận đúng model/effort của từng stage trong bundle", async () => {
  const bundle = loadBundle();
  const client = createFakeClient();
  await runWorkflow({ bundle, mode: "deep", style: "reflective", authorInput: INPUT, client });
  for (const call of client.calls) {
    assert.deepEqual(call.modelConfig, bundle.models.stages[call.stageId]);
  }
});

test("stage biên tập được tách thành bài và edit log", async () => {
  const bundle = loadBundle();
  const run = await runWorkflow({ bundle, mode: "deep", style: "reflective", authorInput: INPUT, client: createFakeClient() });
  const editor = run.results.editor_agent;
  assert.deepEqual(Object.keys(editor.files), ["edited_blog.md", "edit_log.md"]);
  assert.ok(editor.files["edited_blog.md"].startsWith("[FAKE] Bài đã biên tập"));
  assert.ok(editor.files["edit_log.md"].startsWith("- [FAKE]"));
});

test("dừng ở stage lỗi khi stopOnError (mặc định)", async () => {
  const bundle = loadBundle();
  const client = createFakeClient({ failures: { writing_agent: { code: "rate_limited", message: "Đã chạm giới hạn." } } });
  const run = await runWorkflow({ bundle, mode: "deep", style: "reflective", authorInput: INPUT, client });
  assert.equal(run.status, "failed");
  assert.deepEqual(client.calls.map((call) => call.stageId), DEEP.slice(0, 3));
  assert.equal(run.results.writing_agent.status, "failed");
  assert.equal(run.results.writing_agent.error_code, "rate_limited");
  assert.equal(run.results.reader_experience, undefined);
  assert.equal(nextStageIndex(run), -1);
  assert.ok(run.completedAt);
});

test("không stopOnError: chỉ bỏ qua stage phụ thuộc vào stage lỗi", async () => {
  const bundle = loadBundle();
  const client = createFakeClient({ failures: { reader_experience: { code: "upstream_error", message: "Lỗi máy chủ." } } });
  const run = await runWorkflow({ bundle, mode: "deep", style: "reflective", authorInput: INPUT, client, stopOnError: false });
  assert.equal(run.status, "failed");
  assert.equal(run.results.reader_experience.status, "failed");
  assert.equal(run.results.editor_agent.status, "skipped");
  assert.equal(run.results.editor_agent.error, "Dependency không hoàn tất: reader_experience");
  // coach_agent và future_self phụ thuộc editor_agent (đã bị bỏ qua) nên cũng bị bỏ qua.
  assert.equal(run.results.coach_agent.status, "skipped");
  assert.equal(run.results.future_self.error, "Dependency không hoàn tất: coach_agent, editor_agent");
  assert.ok(!client.calls.some((call) => ["editor_agent", "coach_agent", "future_self"].includes(call.stageId)));
});

test("phản hồi sai contract làm stage lỗi; client có API ghi api_called đúng sự thật", async () => {
  const bundle = loadBundle();
  const client = createFakeClient({ apiCapable: true, responses: { story_architect: "Chỉ có chữ, không có section." } });
  const run = await runWorkflow({ bundle, mode: "deep", style: "reflective", authorInput: INPUT, client });
  const result = run.results.story_architect;
  assert.equal(result.status, "failed");
  assert.match(result.error, /đúng hai section/);
  assert.equal(result.api_attempted, true);
  assert.equal(result.api_called, true);
  assert.equal(run.apiCalled, true);
});

test("bị cắt và bị hạ hạng: stage vẫn xong nhưng có cảnh báo và telemetry", async () => {
  const bundle = loadBundle();
  const client = createFakeClient({ truncated: ["sensory_capture"], downgrade: ["inner_weather"] });
  const run = await runWorkflow({ bundle, mode: "moment", style: "va-natural", authorInput: INPUT, client });
  assert.equal(run.status, "completed");
  assert.equal(run.results.sensory_capture.truncated, true);
  assert.match(run.results.sensory_capture.warnings.join(" "), /giới hạn độ dài/);
  assert.equal(run.results.inner_weather.model_applied, null);
  assert.match(run.results.inner_weather.warnings.join(" "), /không trả lời/);
  const telemetry = stageTelemetry(run);
  assert.deepEqual(Object.keys(telemetry), run.stageIds);
  for (const key of ["status", "provider", "model", "model_applied", "tier_applied", "effort", "truncated", "api_attempted", "api_called", "duration_ms", "error", "error_code"]) {
    assert.ok(key in telemetry.sensory_capture, key);
  }
});

test("dừng bằng AbortSignal cho trạng thái cancelled", async () => {
  const bundle = loadBundle();
  const controller = new AbortController();
  controller.abort();
  const run = await runWorkflow({ bundle, mode: "moment", style: "reflective", authorInput: INPUT, client: createFakeClient(), signal: controller.signal, stopOnError: false });
  assert.equal(run.status, "cancelled");
  assert.equal(run.results.sensory_capture.error_code, "cancelled");
  assert.equal(Object.keys(run.results).length, 1);
});

test("chạy từng bước, chỉ được chạy stage kế tiếp, và chạy lại stage lỗi", async () => {
  const bundle = loadBundle();
  const failures = { inner_weather: { code: "upstream_error", message: "Lỗi máy chủ." } };
  const client = createFakeClient({ failures });
  const run = createRun({ bundle, mode: "moment", style: "va-natural", authorInput: INPUT });
  await assert.rejects(runStage(run, 2, { bundle, client }), /stage kế tiếp/);
  await runNextStage(run, { bundle, client });
  await runNextStage(run, { bundle, client });
  assert.equal(run.status, "failed");
  assert.equal(await runNextStage(run, { bundle, client }), null);

  delete failures.inner_weather;
  const retried = await retryStage(run, 1, { bundle, client });
  assert.equal(retried.status, "completed");
  assert.equal(run.status, "running");
  while (await runNextStage(run, { bundle, client }));
  assert.equal(run.status, "completed");
  await assert.rejects(retryStage(run, 0, { bundle, client }), /không ở trạng thái lỗi/);
});

test("style theo alias, style lạ và input rỗng", () => {
  const bundle = loadBundle();
  bundle.styles.moment["va-natural"].meta.previous_slugs = ["van-anh"];
  assert.equal(createRun({ bundle, mode: "moment", style: "van-anh", authorInput: INPUT }).style, "va-natural");
  assert.throws(() => createRun({ bundle, mode: "moment", style: "khong-co", authorInput: INPUT }), /không có trong mode/);
  assert.throws(() => createRun({ bundle, mode: "deep", style: "reflective", authorInput: "  " }), /Thiếu input/);
  assert.throws(() => createRun({ bundle, mode: "dai", style: "reflective", authorInput: INPUT }), /Mode không hợp lệ/);
});

test("moment: breath_editor dùng tên file làm tiêu đề vẫn tách được bài và edit log (lỗi khi nghiệm thu ART-3)", async () => {
  const bundle = loadBundle();
  const breath = "## Artifact\n\n### moment_edited.md\n\nBài khoảnh khắc 🌿\n\n### edit_log.md\n\n- Cắt một câu.\n\n## Handoff\n\nĐã cắt một câu.";
  const run = await runWorkflow({
    bundle, mode: "moment", style: "va-natural", authorInput: INPUT, client: createFakeClient({ responses: { breath_editor: breath } }),
  });
  const result = run.results.breath_editor;
  assert.equal(result.files["moment_edited.md"], "Bài khoảnh khắc 🌿");
  assert.equal(result.files["edit_log.md"], "- Cắt một câu.");
  assert.deepEqual(result.warnings, []);
});
