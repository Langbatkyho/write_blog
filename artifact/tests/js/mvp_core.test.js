// ART-3: input của tác giả, thành phẩm và client gọi `sample` (với hàm sample giả).
import assert from "node:assert/strict";
import { test } from "node:test";

import { createSampleClient, MAX_PROMPT_BYTES } from "../../src/core/client_sample.js";
import { createFakeClient } from "../../src/core/client_fake.js";
import { buildAuthorInput, slugify } from "../../src/core/input.js";
import { runWorkflow } from "../../src/core/orchestrator.js";
import { buildRunMarkdown, collectFinalOutputs } from "../../src/core/outputs.js";
import { loadBundle } from "./helpers.js";

test("input theo đúng mẫu examples/*_input_template.md, bỏ mục trống", () => {
  const text = buildAuthorInput({
    title: "Chiều mưa",
    rawNotes: "- Mưa rơi\r\n- Mùi cà phê 🌧️",
    targetReader: "- Người đang vội",
    desiredLength: "300-600 từ",
  });
  assert.equal(text, "title: Chiều mưa\n\nraw_notes:\n- Mưa rơi\n- Mùi cà phê 🌧️\n\ntarget_reader:\n- Người đang vội\n\ndesired_length:\n300-600 từ\n");
  assert.equal(buildAuthorInput({ rawNotes: "x" }), "title:\n\nraw_notes:\nx\n");
  assert.throws(() => buildAuthorInput({ rawNotes: "   " }), /raw_notes/);
});

test("slugify giống engine cho tên file", () => {
  assert.equal(slugify("Khi ta đi, đất đã hóa tâm hồn!"), "khi-ta-đi-đất-đã-hóa-tâm-hồn");
  assert.equal(slugify("  __  "), "blog");
  assert.equal([...slugify("a".repeat(80))].length, 60);
});

test("thành phẩm lấy theo final_output của flow", async () => {
  const bundle = loadBundle();
  for (const [mode, style, primaryFile, reflectionFile] of [
    ["deep", "reflective", "edited_blog.md", "future_reflection.md"],
    ["moment", "va-natural", "moment_edited.md", "witness_report.md"],
  ]) {
    const run = await runWorkflow({ bundle, mode, style, authorInput: "raw_notes:\nx", client: createFakeClient() });
    const { primary, reflection } = collectFinalOutputs(bundle.workflows[mode].definition, run);
    assert.equal(primary.file, primaryFile);
    assert.ok(primary.text.startsWith("[FAKE] Bài đã biên tập"));
    assert.ok(primary.words > 0);
    assert.equal(reflection.file, reflectionFile);
    const markdown = buildRunMarkdown(run);
    assert.ok(markdown.includes(`# 1. ${run.stageIds[0]} Artifact`));
    assert.ok(markdown.includes(`status: completed`));
  }
});

test("chưa có bản biên tập thì không có thành phẩm", async () => {
  const bundle = loadBundle();
  const client = createFakeClient({ failures: { moment_writer: { code: "upstream_error", message: "x" } } });
  const run = await runWorkflow({ bundle, mode: "moment", style: "reflective", authorInput: "raw_notes:\nx", client });
  assert.equal(collectFinalOutputs(bundle.workflows.moment.definition, run).primary, null);
  assert.ok(buildRunMarkdown(run).includes("moment_writer (failed)"));
});

function fakeSample(behaviour) {
  const calls = [];
  const sample = async (prompt, options) => {
    calls.push({ prompt, options });
    return behaviour(prompt, options);
  };
  return { sample, calls };
}

test("client sample gửi đúng model, hạng, effort, cache: false và chuyển tiếp chữ đang viết", async () => {
  const { sample, calls } = fakeSample((prompt, options) => {
    options.onText({ text: "## Artifact", delta: "## Artifact" });
    return { text: "## Artifact\n\nA\n\n## Handoff\n\nH", truncated: false, modelTierApplied: "complex", modelApplied: "claude-opus-5-5" };
  });
  const client = createSampleClient(sample);
  const seen = [];
  const controller = new AbortController();
  const result = await client.call({
    prompt: "xin chào",
    stageId: "writing_agent",
    modelConfig: { model: "claude-opus-5-5", effort: "high", model_tier: "complex" },
    signal: controller.signal,
    onText: ({ text }) => seen.push(text),
  });
  assert.deepEqual(result, { text: "## Artifact\n\nA\n\n## Handoff\n\nH", modelApplied: "claude-opus-5-5", tierApplied: "complex", truncated: false });
  const { options } = calls[0];
  assert.equal(options.model, "claude-opus-5-5");
  assert.equal(options.modelTier, "complex");
  assert.equal(options.effort, "high");
  assert.equal(options.cache, false);
  assert.equal(options.signal, controller.signal);
  assert.deepEqual(seen, ["## Artifact"]);
  assert.deepEqual(client.describe(), { provider: "claude-sample", apiCapable: true });
});

test("client sample: bị hạ hạng, lỗi trước và sau khi tới Claude, prompt quá lớn", async () => {
  const config = { model: "claude-sonnet-5-5", effort: "low", model_tier: "default" };
  const downgraded = createSampleClient(async () => ({ text: "t", truncated: true, modelTierApplied: "default" }));
  assert.deepEqual(await downgraded.call({ prompt: "p", modelConfig: config }), { text: "t", modelApplied: null, tierApplied: "default", truncated: true });

  const rateLimited = createSampleClient(async () => { throw { code: "rate_limited", message: "chậm lại" }; });
  await assert.rejects(rateLimited.call({ prompt: "p", modelConfig: config }), (e) => e.code === "rate_limited" && e.apiCalled === false);

  const partial = createSampleClient(async () => { throw { code: "cancelled", message: "dừng", text: "## Artifact\n\nmột phần" }; });
  await assert.rejects(partial.call({ prompt: "p", modelConfig: config }), (e) => e.code === "cancelled" && e.apiCalled === true && e.text.includes("một phần"));

  const refused = createSampleClient(async () => { throw { code: "refused", message: "không" }; });
  await assert.rejects(refused.call({ prompt: "p", modelConfig: config }), (e) => e.apiCalled === true);

  let called = false;
  const tooLarge = createSampleClient(async () => { called = true; });
  await assert.rejects(tooLarge.call({ prompt: "ă".repeat(MAX_PROMPT_BYTES / 2 + 1), modelConfig: config }), (e) => e.code === "prompt_too_large");
  assert.equal(called, false);
  assert.throws(() => createSampleClient(null), /hàm sample/);
});

test("orchestrator + client sample: phần đã viết được giữ lại khi bị dừng", async () => {
  const bundle = loadBundle();
  const client = createSampleClient(async () => { throw { code: "cancelled", message: "dừng", text: "## Artifact\n\nđang viết dở" }; });
  const run = await runWorkflow({ bundle, mode: "moment", style: "reflective", authorInput: "raw_notes:\nx", client });
  const result = run.results.sensory_capture;
  assert.equal(run.status, "cancelled");
  assert.equal(result.api_called, true);
  assert.equal(result.partial_text, "## Artifact\n\nđang viết dở");
});
