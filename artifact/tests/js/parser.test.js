// ART-2-AC1 (đếm từ) và ART-2-AC2 (parser chặt): khớp golden và các case của tests/test_handoff_parser.py.
import assert from "node:assert/strict";
import { test } from "node:test";

import { buildContextPackage } from "../../src/core/context.js";
import {
  countWords,
  estimateTokens,
  normalizeNewlines,
  parseStageResponseStrict,
  StageResponseError,
} from "../../src/core/parser.js";
import { pyStrip } from "../../src/core/pycompat.js";
import { loadGolden } from "./helpers.js";

const golden = loadGolden("parser_cases.json");

for (const item of golden.strict_parse) {
  test(`parse chặt khớp golden: ${item.name}`, () => {
    if (item.ok) {
      assert.deepEqual(parseStageResponseStrict(item.input), { artifact: item.artifact, handoff: item.handoff });
    } else {
      assert.throws(() => parseStageResponseStrict(item.input), (error) => {
        assert.ok(error instanceof StageResponseError);
        assert.equal(error.message, item.error);
        return true;
      });
    }
  });
}

test("countWords và estimateTokens khớp Python trên mọi case golden", () => {
  for (const item of golden.words) {
    assert.equal(countWords(item.text), item.count_words, JSON.stringify(item.text));
    assert.equal(estimateTokens(item.text), item.estimate_tokens, JSON.stringify(item.text));
  }
});

test("countWords không đếm ký tự biến thể emoji U+FE0F (lỗi đã gặp ở ART-0)", () => {
  assert.equal(countWords("🌥️🌥️🌥️ biển mây"), 2);
});

test("pyStrip giữ BOM và bỏ khoảng trắng kiểu Python", () => {
  assert.equal(pyStrip("\ufeffA "), "\ufeffA");
  assert.equal(pyStrip("\x1c\x85 A \u3000"), "A");
});

test("chuẩn hóa CRLF giúp phản hồi kiểu Windows parse được như đường file của engine", () => {
  const crlf = golden.strict_parse.find((item) => item.name === "crlf");
  assert.equal(crlf.ok, false);
  assert.deepEqual(parseStageResponseStrict(normalizeNewlines(crlf.input)), { artifact: "A", handoff: "H" });
});

// Các case tương đương tests/test_handoff_parser.py
test("py: parse_artifact_and_handoff_sections", () => {
  const { artifact, handoff } = parseStageResponseStrict("## Artifact\n\nFull artifact body.\n\n## Handoff\n\nCompact handoff body.\n");
  assert.equal(artifact, "Full artifact body.");
  assert.equal(handoff, "Compact handoff body.");
});

test("py: strict_parser_accepts_exact_contract", () => {
  const response =
    "## Artifact\n\nNội dung đầy đủ.\n\n### Chi tiết hợp lệ\n\nMột mục con.\n\n## Tiêu đề H2 thuộc Artifact\n\nNội dung bài viết.\n\n## Handoff\n\nTóm tắt bàn giao.\n";
  const { artifact, handoff } = parseStageResponseStrict(response);
  assert.ok(artifact.includes("### Chi tiết hợp lệ"));
  assert.ok(artifact.includes("## Tiêu đề H2 thuộc Artifact"));
  assert.equal(handoff, "Tóm tắt bàn giao.");
});

test("py: strict_parser_rejects_extra_duplicate_or_reordered_sections", () => {
  for (const response of [
    "## Artifact\nA\n## Artifact\nB\n## Handoff\nH\n",
    "## Handoff\nH\n## Artifact\nA\n",
    "## Artifact\nA\n## Handoff\nH\n## Handoff\nH2\n",
  ]) {
    assert.throws(() => parseStageResponseStrict(response), StageResponseError);
  }
});

test("py: context_package_uses_policy", () => {
  const step = { context_policy: { handoffs: ["reflection_engine", "reader_experience"], artifacts: ["writing_agent"] } };
  const contextPackage = buildContextPackage(
    step,
    { writing_agent: "draft" },
    { reflection_engine: "reflection", reader_experience: "reader", story_architect: "story" },
  );
  assert.deepEqual(contextPackage, {
    handoffs: { reflection_engine: "reflection", reader_experience: "reader" },
    artifacts: { writing_agent: "draft" },
  });
});
