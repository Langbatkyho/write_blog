// ART-2-AC4: tách Edited Blog / Edit Log giống engine.
import assert from "node:assert/strict";
import { test } from "node:test";

import { deriveArtifactFileContents } from "../../src/core/artifacts.js";
import { loadBundle, loadGolden } from "./helpers.js";

const golden = loadGolden("parser_cases.json");

test("tách file khớp golden cho mọi skill × artifact", () => {
  const bundle = loadBundle();
  for (const item of golden.artifact_split) {
    const [mode, style, stage] = item.skill.split("/");
    const skill = bundle.styles[mode][style].files[`${stage}.yaml`].data;
    const { files, warned } = deriveArtifactFileContents(skill, item.artifact);
    const label = `${item.skill} / ${item.artifact_case}`;
    assert.deepEqual(files, item.files, label);
    assert.deepEqual(Object.keys(files), Object.keys(item.files), label);
    assert.equal(warned, item.warned, label);
  }
});

const editorSkill = { output: { name: "edited_blog.md", secondary_name: "edit_log.md" } };

// Các case tương đương tests/test_handoff_parser.py
test("py: secondary_artifact_file_contents_are_split", () => {
  const { files } = deriveArtifactFileContents(
    editorSkill,
    "## Edited Blog\n\nEdited article body.\n\n## Edit Log\n\n- Merged two paragraphs.\n",
  );
  assert.equal(files["edited_blog.md"], "Edited article body.");
  assert.equal(files["edit_log.md"], "- Merged two paragraphs.");
});

test("py: secondary_artifact_keeps_internal_blog_headings", () => {
  const { files } = deriveArtifactFileContents(
    editorSkill,
    "## Edited Blog\n\n# Kết nối\n\n## Nơi mình thuộc về\n\nEdited article section.\n\n## Vẫn đi tiếp\n\nAnother edited article section.\n\n## Edit Log\n\n- Merged two paragraphs.\n",
  );
  assert.ok(files["edited_blog.md"].includes("## Nơi mình thuộc về"));
  assert.ok(files["edited_blog.md"].includes("## Vẫn đi tiếp"));
  assert.ok(!files["edited_blog.md"].includes("## Edit Log"));
  assert.equal(files["edit_log.md"], "- Merged two paragraphs.");
});

test("py: secondary_fallback_when_heading_missing", () => {
  const artifact = "Just plain text without expected headings.";
  const { files, warned } = deriveArtifactFileContents(editorSkill, artifact);
  assert.equal(files["edited_blog.md"], artifact);
  assert.ok(files["edit_log.md"].includes("not found"));
  assert.equal(warned, true);
});

test("skill thiếu output.name/artifact thì báo lỗi", () => {
  assert.throws(() => deriveArtifactFileContents({ output: {} }, "x"), /thiếu name\/artifact/);
});
