// ART-8.1: lõi Voice Lab JS so với golden do engine Python sinh ra (artifact/make_golden.py).
// Không gọi model thật: client giả trả lại đúng phản hồi mà Gemini giả đã trả cho Python.
import assert from "node:assert/strict";
import { test } from "node:test";

import { analyzeSamples, buildVoiceDna, chunkSamples, estimateTokens, planAnalysis, prepareSamples, validateEvidence } from "../../src/vl/analyzer.js";
import { applyCalibrationSelection, blindCalibrationView, calibrateAb } from "../../src/vl/calibration.js";
import { applyConflictResolutions, compileStyle, mergeOverrides } from "../../src/vl/compiler.js";
import { applyInterviewPatch, generateInterview, proposeInterviewPatch } from "../../src/vl/interview.js";
import { computeProfileConfidence, VoiceLabError } from "../../src/vl/models.js";
import { buildAnalysisPrompt, buildCalibrationPrompt, buildInterviewPatchPrompt, buildSynthesisPrompt, withResponseSchema } from "../../src/vl/prompts.js";
import { validateSchema } from "../../src/vl/schema.js";
import { loadBundle, loadGolden } from "./helpers.js";

const PROMPTS = loadGolden("voicelab_prompts.json");
const LOGIC = loadGolden("voicelab_logic.json");
const FLOW = loadGolden("voicelab_flow.json");
const TIME_KEYS = new Set(["created_at", "updated_at", "confirmed_at"]);

/** Giống _scrub của make_golden: thời điểm thay bằng "<time>". */
function scrub(value) {
  if (Array.isArray(value)) return value.map(scrub);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, TIME_KEYS.has(k) && v !== null ? "<time>" : scrub(v)]));
  }
  return value;
}

/** So khớp cả thứ tự trường (JSON.stringify), không chỉ giá trị. */
const sameJson = (actual, expected, message) => assert.equal(JSON.stringify(actual), JSON.stringify(expected), message);
const claude = (message) => message.replaceAll("Gemini", "Claude");

function makeIds() {
  let count = 0;
  return () => `id-${String(++count).padStart(4, "0")}`;
}

/** Client giả: trả lần lượt các phản hồi đã ghi của Python, ghi lại prompt nhận được. */
function replayClient(responses) {
  const calls = [];
  return {
    calls,
    async json({ prompt, modelConfig, stageId }) {
      const text = responses[calls.length];
      calls.push({ stageId, prompt, modelConfig });
      if (text === undefined) throw new Error("Không có phản hồi giả cho lần gọi này.");
      let value;
      try {
        value = JSON.parse(text);
      } catch (error) {
        throw Object.assign(new Error(error.message), { code: "invalid_json" });
      }
      return { value, modelApplied: modelConfig.model, tierApplied: modelConfig.model_tier };
    },
  };
}

test("prompt Voice Lab giống từng byte với engine; bản Claude nối JSON Schema dựng sẵn", () => {
  const bundle = loadBundle();
  const dims = bundle.voice_lab.dimensions;
  assert.equal(buildAnalysisPrompt(PROMPTS.analysis.inputs.samples, dims), PROMPTS.analysis.prompt);
  assert.equal(buildSynthesisPrompt(PROMPTS.synthesis.inputs.verified_evidence, PROMPTS.synthesis.inputs.batch_dimensions), PROMPTS.synthesis.prompt);
  assert.equal(buildInterviewPatchPrompt(PROMPTS.interview_patch.inputs.current_dimensions, PROMPTS.interview_patch.inputs.answers), PROMPTS.interview_patch.prompt);
  const c = PROMPTS.calibration.inputs;
  assert.equal(buildCalibrationPrompt(c.dimension, c.description, c.content_brief, c.fixed_constraints), PROMPTS.calibration.prompt);
  assert.match(PROMPTS.interview_patch.prompt, /"strength": 1\.0/, "golden có số thực 1.0 kiểu Python");
  const withSchema = withResponseSchema("P", bundle.voice_lab.schema_texts.analysis_payload);
  assert.ok(withSchema.startsWith("P\n\nRESPONSE SCHEMA (JSON Schema)\n{"));
  assert.match(bundle.voice_lab.schema_texts.analysis_payload, /"maximum": 1\.0/);
});

test("kiểm tra evidence: quote phải khớp nguyên văn, vị trí theo code point, lý do loại được giữ", () => {
  const bundle = loadBundle();
  const { evidence, samples_by_id } = LOGIC.evidence.inputs;
  const { active, rejected, returnedByDimension } = validateEvidence(evidence, samples_by_id, { dimensions: bundle.voice_lab.dimensions });
  sameJson(active, LOGIC.evidence.active);
  sameJson(rejected, LOGIC.evidence.rejected);
  assert.deepEqual(returnedByDimension, LOGIC.evidence.returned_by_dimension);
  assert.deepEqual(rejected.map((item) => item.rejection_reason).sort(), ["empty_quote", "quote_not_exact", "unknown_dimension", "unknown_sample_id"]);
});

test("Voice DNA và confidence tính bằng code khớp Python (trần theo số mẫu)", () => {
  const bundle = loadBundle();
  const dims = bundle.voice_lab.dimensions;
  const { evidence, samples_by_id } = LOGIC.evidence.inputs;
  const { active, rejected, returnedByDimension } = validateEvidence(evidence, samples_by_id, { dimensions: dims });
  for (const item of LOGIC.dna.cases) {
    const dna = buildVoiceDna(LOGIC.dna.inputs.raw_dna, active, rejected, returnedByDimension, item.total_samples, dims);
    sameJson(dna, item.dna, `dna total_samples=${item.total_samples}`);
    assert.equal(computeProfileConfidence({ dna }, dims), item.profile_confidence);
  }
});

test("compile_style giống hệt Python cho deep (7 agent) và moment (6 agent)", () => {
  const bundle = loadBundle();
  for (const item of LOGIC.compile) {
    const { profile, mode, changed_dimensions } = item.inputs;
    if (item.error) {
      assert.throws(() => compileStyle(profile, mode, changed_dimensions, { bundle }), { message: item.error }, item.name);
      continue;
    }
    const result = compileStyle(profile, mode, changed_dimensions, { bundle });
    sameJson(result, item.result, item.name);
  }
  const counts = Object.fromEntries(LOGIC.compile.filter((c) => c.result && c.inputs.changed_dimensions === null).map((c) => [c.name, Object.keys(c.result.artifacts).length]));
  assert.deepEqual(counts, { deep_full: 7, moment_full_base_va_natural: 6, moment_no_dna: 6 });
});

test("ước lượng token và chia mẫu theo code point khớp Python", () => {
  const bundle = loadBundle();
  const consts = bundle.voice_lab.analysis;
  for (const item of FLOW.estimate_tokens) assert.equal(estimateTokens(item.text, consts), item.tokens, JSON.stringify(item.text.slice(0, 20)));
  for (const item of FLOW.chunk) sameJson(chunkSamples(FLOW.chunk_inputs, item.budget, consts), item.batches, `budget ${item.budget}`);
});

test("phân tích một lượt: đúng prompt, đúng model vl_analysis, hồ sơ giống Python", async () => {
  const bundle = loadBundle();
  const golden = FLOW.analyze_single;
  const client = replayClient(golden.calls.map((call) => call.response));
  const result = await analyzeSamples({ bundle, ...golden.inputs, tokenBudget: golden.inputs.token_budget, client, newId: makeIds() });
  assert.equal(client.calls.length, 1);
  assert.equal(client.calls[0].stageId, "voice_lab_analyze");
  assert.equal(client.calls[0].prompt, withResponseSchema(golden.calls[0].prompt, bundle.voice_lab.schema_texts.analysis_payload));
  assert.deepEqual(client.calls[0].modelConfig, bundle.models.voice_lab.vl_analysis);
  const { telemetry, ...rest } = result;
  sameJson(scrub(rest), golden.result);
  assert.equal(result.profile.status, "draft");
  assert.equal(telemetry[0].status, "completed");
  assert.equal(telemetry[0].api_called, true);
});

test("phân tích nhiều lượt: chia lô có gối đầu, khử trùng evidence, tổng hợp bằng vl_synthesis", async () => {
  const bundle = loadBundle();
  const golden = FLOW.analyze_multi;
  const client = replayClient(golden.calls.map((call) => call.response));
  const result = await analyzeSamples({ bundle, ...golden.inputs, tokenBudget: golden.inputs.token_budget, maxPromptBytes: 10 * 1024 * 1024, client, newId: makeIds() });
  assert.deepEqual(client.calls.map((call) => call.stageId), golden.calls.map((call) => call.stage_id));
  client.calls.forEach((call, index) => {
    const schemaName = call.stageId === "voice_lab_synthesize" ? "synthesis_payload" : "analysis_payload";
    assert.equal(call.prompt, withResponseSchema(golden.calls[index].prompt, bundle.voice_lab.schema_texts[schemaName]), call.stageId);
  });
  assert.deepEqual(client.calls.at(-1).modelConfig, bundle.models.voice_lab.vl_synthesis);
  const { telemetry, ...rest } = result;
  sameJson(scrub(rest), golden.result);
  assert.equal(telemetry.length, golden.calls.length);
});

test("phân tích lỗi: sai JSON, sai schema, không có quote hợp lệ, mẫu rỗng → lỗi, không có hồ sơ", async () => {
  const bundle = loadBundle();
  for (const item of FLOW.analyze_errors) {
    const client = replayClient(item.responses);
    await assert.rejects(
      analyzeSamples({ bundle, samples: item.samples, client, newId: makeIds() }),
      (error) => error instanceof VoiceLabError && error.code === item.error.code && error.userMessage === claude(item.error.user_message),
      item.name,
    );
  }
});

test("ngân sách byte: prompt quá lớn thì chia nhỏ hơn cho tới khi vừa; quá nhiều lô thì từ chối", () => {
  const bundle = loadBundle();
  const vl = bundle.voice_lab;
  const prepared = prepareSamples(FLOW.analyze_multi.inputs.samples);
  const opts = { consts: vl.analysis, dimensions: vl.dimensions, schemaText: vl.schema_texts.analysis_payload, tokenBudget: 140000 };
  const roomy = planAnalysis(prepared, { ...opts, maxPromptBytes: 10 * 1024 * 1024 });
  assert.equal(roomy.routing, "single_pass");
  const tight = planAnalysis(prepared, { ...opts, maxPromptBytes: 40 * 1024 });
  assert.equal(tight.routing, "multi_pass");
  assert.ok(tight.prompts.every((prompt) => new TextEncoder().encode(prompt).length <= 40 * 1024));
  assert.ok(tight.tokenBudget < 140000);
  // Không chia nhỏ hơn được nữa mà prompt vẫn quá giới hạn byte.
  assert.throws(() => planAnalysis(prepared, { ...opts, maxPromptBytes: 6 * 1024 }), (error) => error.code === "input_too_large");
  // Vừa giới hạn byte nhưng vượt MAX_ANALYSIS_BATCHES.
  assert.throws(
    () => planAnalysis(prepared, { ...opts, consts: { ...vl.analysis, max_analysis_batches: 5 }, maxPromptBytes: 12 * 1024 }),
    (error) => error.code === "input_too_large" && /vượt giới hạn phân tích/.test(error.userMessage),
  );
});

test("phỏng vấn: chọn tối đa 3 chiều yếu nhất giống interview_routing", () => {
  const bundle = loadBundle();
  const golden = FLOW.interview_questions;
  sameJson(generateInterview(golden.profile, { bundle, newId: makeIds() }), golden.questions);
  assert.ok(golden.questions.length <= 3);
});

test("patch phỏng vấn: chỉ giữ chiều đã hỏi; chỉ áp dụng khi có cờ xác nhận; hồ sơ cũ không đổi", async () => {
  const bundle = loadBundle();
  const golden = FLOW.interview_patch;
  const profile = FLOW.interview_questions.profile;
  const questions = FLOW.interview_questions.questions;
  const client = replayClient(golden.calls.map((call) => call.response));
  const { patch } = await proposeInterviewPatch({ bundle, profile, questions, answers: golden.answers, client });
  assert.equal(client.calls[0].prompt, withResponseSchema(golden.calls[0].prompt, bundle.voice_lab.schema_texts.interview_patch_payload));
  assert.deepEqual(client.calls[0].modelConfig, bundle.models.voice_lab.vl_interview_patch);
  sameJson(patch, golden.patch);

  const empty = replayClient([]);
  sameJson((await proposeInterviewPatch({ bundle, profile, questions, answers: {}, client: empty })).patch, golden.empty_patch);
  assert.equal(empty.calls.length, golden.empty_calls);
  await assert.rejects(
    proposeInterviewPatch({ bundle, profile, questions, answers: golden.answers, client: replayClient(['{"changes": [{"dimension": "tone", "description": "x"}]}']) }),
    (error) => error.code === golden.invalid_patch_error.code && error.userMessage === claude(golden.invalid_patch_error.user_message),
  );

  const before = JSON.stringify(profile);
  assert.throws(() => applyInterviewPatch(profile, patch, questions, golden.answers, { bundle, confirmed: false }), { message: golden.unconfirmed_error });
  const applied = applyInterviewPatch(profile, golden.apply_patch_input, questions, golden.answers, { bundle, confirmed: true });
  assert.equal(JSON.stringify(profile), before, "hồ sơ gốc không đổi");
  sameJson(scrub(applied), golden.applied_profile);
  sameJson(generateInterview(applied, { bundle, newId: makeIds() }), golden.follow_up_questions);
});

test("calibration: nhãn A/B theo số ngẫu nhiên, bản hiển thị không có mapping, chỉ đổi đúng một chiều", async () => {
  const bundle = loadBundle();
  const golden = FLOW.calibration;
  const profile = FLOW.interview_questions.profile;
  const newId = makeIds();
  for (const item of golden.sessions) {
    const client = replayClient(item.calls.map((call) => call.response));
    const { session } = await calibrateAb({ bundle, dimension: "emoji", profile, client, random: () => item.random, newId });
    assert.equal(client.calls[0].prompt, withResponseSchema(item.calls[0].prompt, bundle.voice_lab.schema_texts.calibration_payload));
    assert.deepEqual(client.calls[0].modelConfig, bundle.models.voice_lab.vl_calibration);
    sameJson(scrub(session), item.session);
    const view = blindCalibrationView(session);
    assert.equal("shuffle_mapping" in view, false);
    assert.ok(!JSON.stringify(view).includes("amplified") && !JSON.stringify(view).includes("restrained"));
  }

  const updated = applyCalibrationSelection(profile, golden.apply.session, golden.apply.selected, { bundle });
  sameJson(scrub(updated), golden.apply.profile);
  for (const name of bundle.voice_lab.dimensions) {
    if (name !== golden.apply.session.dimension) assert.deepEqual(updated.dna[name], profile.dna[name], `chiều ${name} không đổi`);
  }
  assert.throws(() => applyCalibrationSelection(updated, golden.apply.session, "A", { bundle }), { message: golden.reapply_error });
  assert.throws(() => applyCalibrationSelection(profile, golden.apply.session, "C", { bundle }), { message: golden.bad_label_error });

  for (const item of golden.errors) {
    await assert.rejects(
      calibrateAb({ bundle, dimension: "emoji", profile, client: replayClient([item.response]), random: () => 0.1 }),
      (error) => error.code === item.error.code && error.userMessage === claude(item.error.user_message),
      item.name,
    );
  }
  for (const item of golden.value_errors) {
    await assert.rejects(calibrateAb({ bundle, dimension: item.dimension, profile, client: replayClient([]) }), { message: item.error });
  }
});

test("merge ba chiều của Canonical IR và áp lựa chọn conflict khớp Python", () => {
  const bundle = loadBundle();
  const golden = FLOW.merge;
  for (const item of golden.cases) sameJson(mergeOverrides(golden.base, item.current, item.override, { bundle }), item.result, item.name);
  const conflict = mergeOverrides(golden.base, golden.cases[3].current, golden.cases[3].override, { bundle });
  sameJson(applyConflictResolutions(conflict, { style_overlays: golden.cases[3].override.style_overlays }), golden.resolved);
  assert.throws(() => applyConflictResolutions(conflict, {}), { message: golden.missing_resolution_error });
  assert.throws(() => applyConflictResolutions(conflict, { style_overlays: [], x: 1 }), { message: golden.unknown_resolution_error });
  const invariant = mergeOverrides(golden.base, golden.base, golden.cases[4].override, { bundle });
  assert.throws(() => applyConflictResolutions(invariant, {}), { message: golden.invariant_error });
  assert.throws(() => mergeOverrides(golden.base, { ...golden.base, id: "khác" }, golden.base, { bundle }), { message: golden.mismatched_id_error });
});

test("kiểm tra schema v2: cùng kết luận với Pydantic; giá trị đã điền mặc định giống model_dump", () => {
  const bundle = loadBundle();
  for (const [name, rows] of Object.entries(FLOW.schema_cases)) {
    rows.forEach((row, index) => {
      const result = validateSchema(bundle.voice_lab.schemas[name], row.payload);
      assert.equal(result.ok, row.valid, `${name}[${index}]: ${result.errors.join("; ")}`);
      if (row.valid && name !== "style_profile") sameJson(result.value, row.value, `${name}[${index}]`);
      if (row.valid && name === "style_profile" && index === 0) sameJson(scrub(result.value), row.value);
    });
  }
  // Fail-closed: từ khóa schema chưa hỗ trợ thì báo lỗi, không bỏ qua.
  assert.throws(() => validateSchema({ type: "object", properties: {}, patternProperties: {} }, {}), /chưa hỗ trợ/);
});
