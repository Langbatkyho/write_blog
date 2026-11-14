// ART-5: learning loop. Prompt, báo cáo offline và định dạng số khớp từng byte với engine.
import assert from "node:assert/strict";
import { test } from "node:test";

import { createFakeClient } from "../../src/core/client_fake.js";
import {
  averageSentenceWords,
  buildLearningPrompt,
  buildOfflineLearningReport,
  buildOfflineTuningSuggestions,
  buildTuningPrompt,
  countParagraphs,
  LearningError,
  learningBlocker,
  learningStepOutputs,
  renderOfflineDiff,
  runLearning,
} from "../../src/core/learning.js";
import { runWorkflow } from "../../src/core/orchestrator.js";
import { pyFormatFixed, pySignedInt } from "../../src/core/pycompat.js";
import { loadBundle, loadGolden } from "./helpers.js";

const golden = loadGolden("learning_prompts.json");

for (const item of golden.learning) {
  test(`learning prompt khớp golden: ${item.name}`, () => {
    const bundle = loadBundle();
    const args = {
      bundle,
      mode: item.inputs.mode,
      style: item.inputs.style,
      authorInput: item.inputs.author_input,
      stepOutputs: item.inputs.step_outputs,
      finalBlog: item.inputs.final_blog,
      productionBlog: item.inputs.production_blog,
      comparisonLabel: item.inputs.comparison_label,
      maxContextTokens: item.inputs.max_context_tokens,
    };
    if (item.error) {
      assert.throws(() => buildLearningPrompt(args), (error) => error instanceof LearningError && error.message === item.error);
    } else {
      assert.equal(buildLearningPrompt(args), item.prompt);
    }
  });
}

for (const item of golden.tuning) {
  test(`tuning prompt khớp golden: ${item.name}`, () => {
    const { report, mode, stage_ids: stageIds, max_context_tokens: maxContextTokens } = item.inputs;
    assert.equal(buildTuningPrompt({ report, mode, stageIds, maxContextTokens }), item.prompt);
  });
}

for (const item of golden.offline) {
  test(`báo cáo offline khớp golden: ${item.name}`, () => {
    const { mode, comparison_label: comparisonLabel, final_blog: finalBlog, production_blog: productionBlog, step_outputs: stepOutputs, stage_ids: stageIds } = item.inputs;
    assert.equal(renderOfflineDiff(finalBlog, productionBlog, comparisonLabel), item.diff);
    assert.deepEqual([countParagraphs(finalBlog), countParagraphs(productionBlog)], item.metrics.paragraphs);
    assert.deepEqual([averageSentenceWords(finalBlog), averageSentenceWords(productionBlog)], item.metrics.sentence_avg);
    assert.equal(buildOfflineLearningReport({ finalBlog, productionBlog, stepOutputs, comparisonLabel, mode }), item.report);
    assert.equal(buildOfflineTuningSuggestions({ mode, stageIds }), item.tuning);
  });
}

test("định dạng số giống f-string của Python (làm tròn half-even, -0)", () => {
  for (const item of golden.format_fixed) {
    assert.equal(pyFormatFixed(item.value, 3), item["3f"], String(item.value));
    assert.equal(pyFormatFixed(item.value, 2), item["2f"], String(item.value));
  }
  for (const item of golden.signed_int) assert.equal(pySignedInt(item.value), item["+d"]);
});

const INPUT = "title: Chiều mưa\n\nraw_notes:\n- Mưa rơi 🌧️\n";
const PRODUCTION = "# Chiều mưa\n\nMưa rơi trên mái tôn. Mình ngồi yên, đọc lại và sửa vài chữ 🌿.";

async function completedRun(bundle, mode = "moment", style = "va-natural") {
  const run = await runWorkflow({ bundle, mode, style, authorInput: INPUT, client: createFakeClient() });
  run.id = "run_test";
  return run;
}

test("học offline: không gọi Claude, báo cáo gắn mode và dùng bản nháp AI làm mốc so sánh", async () => {
  const bundle = loadBundle();
  const run = await completedRun(bundle);
  const session = await runLearning({ bundle, run, productionBlog: PRODUCTION, offline: true, now: new Date(Date.UTC(2026, 10, 14, 1, 2, 3, 4)) });
  assert.equal(session.status, "completed");
  assert.equal(session.kind, "offline");
  assert.equal(session.id, "20261114_010203_004000");
  assert.equal(session.comparison_label, "moment_edited.md");
  assert.equal(session.api_called, false);
  assert.match(session.report, /^# Báo Cáo Chẩn Đoán Offline \(MOMENT MODE\)/);
  assert.match(session.report, /--- moment_edited\.md\n\+\+\+ production_blog\.md/);
  assert.match(session.tuning_suggestions, /## breath_editor/);
});

test("học qua Claude: hai bước đúng model learning, prompt dùng artifact đầy đủ, tuning dùng báo cáo", async () => {
  const bundle = loadBundle();
  const run = await completedRun(bundle, "deep", "reflective");
  const client = createFakeClient({
    apiCapable: true,
    responses: { editorial_learning: "# Báo cáo\n\nNgười viết bỏ emoji cuối bài.", workflow_tuning: "## editor_agent\n- Giữ emoji." },
  });
  const seen = [];
  const session = await runLearning({ bundle, run, productionBlog: PRODUCTION, client, onText: ({ stageId }) => seen.push(stageId) });
  assert.equal(session.status, "completed");
  assert.deepEqual(client.calls.map((c) => c.stageId), ["editorial_learning", "workflow_tuning"]);
  for (const call of client.calls) assert.deepEqual(call.modelConfig, bundle.models.learning[call.stageId]);
  const expectedPrompt = buildLearningPrompt({
    bundle, mode: "deep", style: "reflective", authorInput: INPUT, stepOutputs: learningStepOutputs(run),
    finalBlog: run.results.editor_agent.files["edited_blog.md"], productionBlog: PRODUCTION, comparisonLabel: "edited_blog.md",
  });
  assert.equal(client.calls[0].prompt, expectedPrompt);
  assert.ok(expectedPrompt.includes(run.results.story_architect.artifact));
  assert.ok(!expectedPrompt.includes(run.results.story_architect.handoff), "learning không được dùng handoff thay cho artifact");
  assert.equal(client.calls[1].prompt, buildTuningPrompt({ report: session.report, mode: "deep", stageIds: run.stageIds }));
  assert.equal(session.report, "# Báo cáo\n\nNgười viết bỏ emoji cuối bài.");
  assert.equal(session.telemetry.editorial_learning.model_applied, bundle.models.learning.editorial_learning.model);
  assert.equal(session.api_called, true);
  assert.deepEqual([...new Set(seen)], ["editorial_learning", "workflow_tuning"]);
});

test("học qua Claude: lỗi ở bước báo cáo thì không gọi bước tuning; bị dừng thì trạng thái cancelled", async () => {
  const bundle = loadBundle();
  const run = await completedRun(bundle);
  const failing = createFakeClient({ failures: { editorial_learning: { code: "rate_limited", message: "chậm lại" } } });
  const failed = await runLearning({ bundle, run, productionBlog: PRODUCTION, client: failing });
  assert.equal(failed.status, "failed");
  assert.equal(failed.error_code, "rate_limited");
  assert.equal(failing.calls.length, 1);
  assert.equal(failed.telemetry.editorial_learning.status, "failed");

  const controller = new AbortController();
  controller.abort();
  const cancelled = await runLearning({ bundle, run, productionBlog: PRODUCTION, client: createFakeClient(), signal: controller.signal });
  assert.equal(cancelled.status, "cancelled");
});

test("chưa sẵn sàng để học: thiếu bản cuối, chưa có bản nháp AI, hoặc không có Claude", async () => {
  const bundle = loadBundle();
  const run = await completedRun(bundle);
  assert.match(learningBlocker(bundle, run, "   "), /Chưa có bản cuối/);
  assert.equal(learningBlocker(bundle, run, PRODUCTION), null);
  await assert.rejects(runLearning({ bundle, run, productionBlog: "", offline: true }), (e) => e.code === "not_ready");
  await assert.rejects(runLearning({ bundle, run, productionBlog: PRODUCTION }), (e) => e.code === "no_client");
  const failed = await runWorkflow({ bundle, mode: "moment", style: "reflective", authorInput: INPUT, client: createFakeClient({ failures: { moment_writer: { code: "x", message: "x" } } }) });
  assert.match(learningBlocker(bundle, failed, PRODUCTION), /chưa có bản nháp AI/);
});
