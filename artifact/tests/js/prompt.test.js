// ART-2-AC1: context package và prompt từng stage khớp từng byte với golden của engine.
import assert from "node:assert/strict";
import { test } from "node:test";

import { buildContextPackage } from "../../src/core/context.js";
import { createFakeClient } from "../../src/core/client_fake.js";
import { runWorkflow } from "../../src/core/orchestrator.js";
import { buildStepPrompt } from "../../src/core/prompt.js";
import { loadBundle, loadGolden, stageResponse } from "./helpers.js";

const golden = loadGolden("workflow_prompts.json");

for (const goldenCase of golden.cases) {
  test(`prompt từng stage khớp golden: ${goldenCase.mode}/${goldenCase.style}`, () => {
    const bundle = loadBundle();
    const workflow = bundle.workflows[goldenCase.mode];
    const files = bundle.styles[goldenCase.mode][goldenCase.style].files;
    const artifacts = {};
    const handoffs = {};
    assert.equal(goldenCase.stages.length, workflow.definition.steps.length);
    workflow.definition.steps.forEach((step, index) => {
      const expected = goldenCase.stages[index];
      assert.equal(step.id, expected.stage_id);
      const contextPackage = buildContextPackage(step, artifacts, handoffs);
      assert.deepEqual(contextPackage, expected.context_package);
      assert.deepEqual(Object.keys(contextPackage.handoffs), Object.keys(expected.context_package.handoffs));
      assert.deepEqual(Object.keys(contextPackage.artifacts), Object.keys(expected.context_package.artifacts));
      const prompt = buildStepPrompt(
        workflow.definition,
        step,
        files[workflow.stage_files[step.id]].yaml,
        goldenCase.author_input,
        contextPackage,
      );
      assert.equal(prompt, expected.prompt, `prompt lệch ở stage ${step.id}`);
      artifacts[step.id] = goldenCase.upstream[step.id].artifact;
      handoffs[step.id] = goldenCase.upstream[step.id].handoff;
    });
  });

  test(`orchestrator gửi đúng prompt golden cho client: ${goldenCase.mode}/${goldenCase.style}`, async () => {
    const bundle = loadBundle();
    const responses = Object.fromEntries(
      Object.entries(goldenCase.upstream).map(([id, out]) => [id, stageResponse(out.artifact, out.handoff)]),
    );
    const client = createFakeClient({ responses });
    const run = await runWorkflow({
      bundle,
      mode: goldenCase.mode,
      style: goldenCase.style,
      authorInput: goldenCase.author_input,
      client,
    });
    assert.equal(run.status, "completed");
    assert.deepEqual(
      client.calls.map((call) => call.prompt),
      goldenCase.stages.map((stage) => stage.prompt),
    );
  });
}
