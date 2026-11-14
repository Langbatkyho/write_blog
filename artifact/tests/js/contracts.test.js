// Kiểm tra bundle khi tải (fail-closed) và tính độc lập của core (NFR: không chạm DOM/window.claude).
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { BundleContractError, listStyles, modelConfigForStage, resolveStyle, validateBundle } from "../../src/core/contracts.js";
import { ARTIFACT_DIR, loadBundle } from "./helpers.js";

test("bundle thật hợp lệ", () => {
  const bundle = loadBundle();
  assert.equal(validateBundle(bundle), bundle);
});

const breakers = {
  "bundle_format lạ": (b) => { b.bundle_format = 2; },
  "thiếu content_hash": (b) => { delete b.content_hash; },
  "thiếu workflow moment": (b) => { delete b.workflows.moment; },
  "stage_ids lệch steps": (b) => { b.workflows.deep.stage_ids.reverse(); },
  "thiếu model của stage": (b) => { delete b.models.stages.gentle_witness; },
  "model thiếu effort": (b) => { delete b.models.stages.writing_agent.effort; },
  "style thiếu skill": (b) => { delete b.styles.deep.provocative.files["coach_agent.yaml"]; },
  "skill thiếu yaml": (b) => { delete b.styles.moment.reflective.files["breath_editor.yaml"].yaml; },
  "mode không có style": (b) => { b.styles.deep = {}; },
};

for (const [name, breakBundle] of Object.entries(breakers)) {
  test(`bundle sai bị từ chối: ${name}`, () => {
    const bundle = loadBundle();
    breakBundle(bundle);
    assert.throws(() => validateBundle(bundle), BundleContractError);
  });
}

test("tra cứu style và model", () => {
  const bundle = loadBundle();
  assert.equal(resolveStyle(bundle, "deep", "reflective"), "reflective");
  assert.equal(resolveStyle(bundle, "deep", "va-natural"), null);
  assert.deepEqual(listStyles(bundle, "moment").map((s) => s.slug).sort(), ["minh-hom-hinh", "reflective", "va-natural"]);
  assert.ok(listStyles(bundle, "deep").every((s) => s.system));
  assert.deepEqual(modelConfigForStage(bundle, "writing_agent"), { model: "claude-opus-5-5", effort: "high", model_tier: "complex" });
  assert.throws(() => modelConfigForStage(bundle, "khong_co"), BundleContractError);
});

test("core không dùng DOM, window, capability của Artifact hay module ngoài core", () => {
  const coreDir = join(ARTIFACT_DIR, "src", "core");
  for (const file of readdirSync(coreDir).filter((name) => name.endsWith(".js"))) {
    const source = readFileSync(join(coreDir, file), "utf8").replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
    assert.doesNotMatch(source, /\b(window|document|localStorage|claude\.use|fetch)\b/, file);
    for (const [, target] of source.matchAll(/from\s+"([^"]+)"/g)) {
      assert.match(target, /^\.\/[a-z_]+\.js$/, `${file} import ngoài core: ${target}`);
    }
  }
});
