// ART-6.1: cấu hình model riêng của người dùng, preset, và phiên A/B mù.
import assert from "node:assert/strict";
import { test } from "node:test";

import { blindDrafts, createAbSession, decideAb, revealAb } from "../../src/core/ab.js";
import { createFakeClient } from "../../src/core/client_fake.js";
import {
  changedStages,
  cleanOverrides,
  effectiveModels,
  matchingPreset,
  modelProfile,
  overridesFrom,
  PRESETS,
  presetModels,
  settingsForPreset,
  withModels,
} from "../../src/core/model_settings.js";
import { runWorkflow } from "../../src/core/orchestrator.js";
import { createRunRepository } from "../../src/core/repository.js";
import { restoreRun } from "../../src/core/run_record.js";
import { createFakeDb } from "./fake_db.js";
import { loadBundle } from "./helpers.js";

const OPUS = "claude-opus-5-5";
const SONNET = "claude-sonnet-5-5";
const INPUT = "title: Chiều mưa\n\nraw_notes:\n- Mưa rơi\n";

test("không có cài đặt: bảng hiệu lực đúng bảng trong repo (Cân bằng)", () => {
  const bundle = loadBundle();
  assert.deepEqual(effectiveModels(bundle, null), bundle.models);
  assert.deepEqual(changedStages(bundle, null), []);
  assert.equal(matchingPreset(bundle, null), "balanced");
  assert.deepEqual(settingsForPreset(bundle, "balanced").overrides, {});
});

test("preset phủ cả stages, learning và voice_lab với model trong danh mục", () => {
  const bundle = loadBundle();
  for (const preset of PRESETS) {
    const models = presetModels(bundle, preset.id);
    for (const group of ["stages", "learning", "voice_lab"]) {
      assert.deepEqual(Object.keys(models[group]), Object.keys(bundle.models[group]), `${preset.id}.${group}`);
      for (const value of Object.values(models[group])) {
        assert.equal(value.model_tier, bundle.model_catalog.models[value.model]);
        assert.ok(bundle.model_catalog.efforts.includes(value.effort));
      }
    }
    assert.equal(matchingPreset(bundle, settingsForPreset(bundle, preset.id)), preset.id);
  }
  const max = presetModels(bundle, "max");
  assert.ok(Object.values(max.stages).every((v) => v.model === OPUS && v.effort === "high"));
  const fast = presetModels(bundle, "fast");
  assert.deepEqual(fast.stages.writing_agent, { model: OPUS, effort: "medium", model_tier: "complex" });
  assert.deepEqual(fast.stages.sensory_capture, { model: SONNET, effort: "medium", model_tier: "default" });
  const baseline = presetModels(bundle, "opus-medium");
  assert.ok(Object.values(baseline.voice_lab).every((v) => v.model === OPUS && v.effort === "medium"));
  assert.throws(() => presetModels(bundle, "nope"), /Preset không tồn tại/);
});

test("ghi đè: chỉ lưu phần khác mặc định; giá trị lạ bị bỏ và báo lại", () => {
  const bundle = loadBundle();
  const models = structuredClone(bundle.models);
  models.stages.gentle_witness = { model: OPUS, effort: "high", model_tier: "complex" };
  const overrides = overridesFrom(bundle, models);
  assert.deepEqual(overrides, { stages: { gentle_witness: { model: OPUS, effort: "high" } } });
  assert.equal(matchingPreset(bundle, { overrides }), "custom");
  assert.deepEqual(changedStages(bundle, { overrides }), ["stages.gentle_witness"]);

  const dirty = {
    stages: { gentle_witness: { model: OPUS, effort: "high" }, unknown_stage: { model: OPUS, effort: "high" }, sensory_capture: { model: "gpt-x", effort: "high" } },
    learning: { editorial_learning: { model: OPUS, effort: "max" } },
    other: { x: { model: OPUS, effort: "high" } },
  };
  const { overrides: clean, dropped } = cleanOverrides(bundle, dirty);
  assert.deepEqual(clean, overrides);
  assert.deepEqual(dropped.sort(), ["learning.editorial_learning", "other.x", "stages.sensory_capture", "stages.unknown_stage"]);
  const effective = effectiveModels(bundle, { overrides: dirty });
  assert.deepEqual(effective.stages.gentle_witness, { model: OPUS, effort: "high", model_tier: "complex" });
  assert.deepEqual(effective.stages.sensory_capture, bundle.models.stages.sensory_capture);
  assert.deepEqual(modelProfile(bundle, { overrides }), { preset: "custom", changed: ["stages.gentle_witness"] });
});

test("bundle với bảng model riêng: orchestrator gọi đúng model/effort; bundle gốc không đổi", async () => {
  const bundle = loadBundle();
  const original = structuredClone(bundle.models);
  const active = withModels(bundle, effectiveModels(bundle, settingsForPreset(bundle, "opus-medium")));
  const client = createFakeClient();
  const run = await runWorkflow({ bundle: active, mode: "moment", style: "va-natural", authorInput: INPUT, client });
  assert.equal(run.status, "completed");
  assert.ok(client.calls.length === 6);
  for (const call of client.calls) assert.deepEqual(call.modelConfig, { model: OPUS, effort: "medium", model_tier: "complex" });
  assert.deepEqual(bundle.models, original);
});

test("cài đặt và phiên A/B lưu trong vùng riêng của người dùng", async () => {
  const bundle = loadBundle();
  const db = createFakeDb();
  const repo = createRunRepository({ db, userId: "u1", clock: () => new Date(Date.UTC(2026, 10, 15)) });
  assert.equal(await repo.loadSettings(), null);
  await repo.saveSettings(settingsForPreset(bundle, "fast"));
  const saved = await repo.loadSettings();
  assert.equal(saved.preset, "fast");
  assert.equal(saved.updated_at, "2026-11-15T00:00:00.000Z");
  assert.ok(db.store.has("data/users/u1/settings"));

  const session = createAbSession({
    mode: "moment", style: "va-natural", authorInput: INPUT, random: () => 0.1, now: new Date(Date.UTC(2026, 10, 15, 1)),
    configs: [
      { label: "Cân bằng", preset: "balanced", models: presetModels(bundle, "balanced") },
      { label: "Opus medium", preset: "opus-medium", models: presetModels(bundle, "opus-medium") },
    ],
  });
  await repo.saveAbSession(session);
  assert.ok(db.store.has(`data/users/u1/blog/ab/${session.id}`));
  assert.deepEqual((await repo.listAbSessions()).map((s) => s.id), [session.id]);
});

test("model_profile và ab_session được lưu cùng run và khôi phục lại", async () => {
  const bundle = loadBundle();
  const run = await runWorkflow({ bundle, mode: "moment", style: "va-natural", authorInput: INPUT, client: createFakeClient() });
  run.modelProfile = { preset: "fast", changed: ["stages.sensory_capture"] };
  run.abSession = { id: "ab1", slot: 0 };
  const db = createFakeDb();
  const repo = createRunRepository({ db, userId: "u1" });
  await repo.createRun(run);
  const { runDoc, stageDocs } = await repo.loadRun(run.id);
  assert.deepEqual(runDoc.model_profile, run.modelProfile);
  const restored = restoreRun(bundle, runDoc, stageDocs).run;
  assert.deepEqual(restored.modelProfile, run.modelProfile);
  assert.deepEqual(restored.abSession, run.abSession);
});

test("A/B: nhãn gán ngẫu nhiên, bài mù không lộ cấu hình, tiết lộ sau khi chọn", () => {
  const bundle = loadBundle();
  const configs = [
    { label: "Cân bằng", preset: "balanced", models: presetModels(bundle, "balanced") },
    { label: "Opus medium", preset: "opus-medium", models: presetModels(bundle, "opus-medium") },
  ];
  assert.throws(() => createAbSession({ mode: "moment", style: "va-natural", authorInput: INPUT, configs: [configs[0], configs[0]] }), /giống hệt/);
  const kept = createAbSession({ mode: "moment", style: "va-natural", authorInput: INPUT, configs, random: () => 0.9 });
  const swapped = createAbSession({ mode: "moment", style: "va-natural", authorInput: INPUT, configs, random: () => 0.1 });
  assert.deepEqual(kept.letters, { A: 0, B: 1 });
  assert.deepEqual(swapped.letters, { A: 1, B: 0 });

  const drafts = [{ text: "bài của cấu hình 0", words: 4 }, { text: "bài của cấu hình 1", words: 4 }];
  const blind = blindDrafts(swapped, drafts);
  assert.deepEqual(blind.map((d) => d.letter), ["A", "B"]);
  assert.equal(blind[0].text, "bài của cấu hình 1");
  assert.deepEqual(Object.keys(blind[0]).sort(), ["letter", "text", "words"]);

  assert.throws(() => revealAb(swapped), /Chưa chọn/);
  assert.throws(() => decideAb(swapped, "A"), /đủ hai bài/);
  swapped.status = "ready";
  swapped.run_ids = ["r0", "r1"];
  assert.throws(() => decideAb(swapped, "C"), /không hợp lệ/);
  const reveal = decideAb(swapped, "A", "  giọng tự nhiên hơn  ", new Date(Date.UTC(2026, 10, 15)));
  assert.equal(swapped.chosen_config, 1);
  assert.equal(swapped.note, "giọng tự nhiên hơn");
  assert.deepEqual(reveal[0], { letter: "A", index: 1, label: "Opus medium", preset: "opus-medium", run_id: "r1", chosen: true });
  assert.equal(reveal[1].chosen, false);

  const tie = createAbSession({ mode: "moment", style: "va-natural", authorInput: INPUT, configs, random: () => 0.9 });
  tie.status = "ready";
  assert.ok(decideAb(tie, "tie").every((row) => !row.chosen));
  assert.equal(tie.chosen_config, null);
});
