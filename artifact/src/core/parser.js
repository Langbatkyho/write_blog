// Port của engine/parser.py (phần dùng ở runtime): parse chặt Artifact/Handoff,
// đếm từ và ước lượng token.
import { PY_LINE_END, PY_LINE_START, pyStrip } from "./pycompat.js";

export class StageResponseError extends Error {
  constructor(message) {
    super(message);
    this.name = "StageResponseError";
  }
}

// Tương đương `(?im)^##[ \t]+(Artifact|Handoff)[ \t]*$` của Python.
const CONTRACT_SECTION_RE = new RegExp(`${PY_LINE_START}##[ \\t]+(Artifact|Handoff)[ \\t]*${PY_LINE_END}`, "gi");

/**
 * Port của `_parse_strict_stage_response`: đúng hai section theo thứ tự
 * `## Artifact`, `## Handoff`; cho phép lời dẫn phía trước; không được rỗng.
 * Hàm thuần, không chuẩn hóa xuống dòng (giống Python: chuỗi CRLF bị từ chối).
 */
export function parseStageResponseStrict(responseText) {
  const text = String(responseText);
  const sections = [...text.matchAll(CONTRACT_SECTION_RE)];
  const names = sections.map((match) => match[1].toLowerCase());
  if (names.length !== 2 || names[0] !== "artifact" || names[1] !== "handoff") {
    throw new StageResponseError(
      "Stage response strict phải có đúng hai section contract theo thứ tự: ## Artifact, ## Handoff.",
    );
  }
  const artifact = pyStrip(text.slice(sections[0].index + sections[0][0].length, sections[1].index));
  const handoff = pyStrip(text.slice(sections[1].index + sections[1][0].length));
  if (!artifact || !handoff) {
    throw new StageResponseError("Stage response có Artifact/Handoff rỗng.");
  }
  return { artifact, handoff };
}

/**
 * Engine đọc phản hồi từ file bằng `read_text`, vốn đã chuẩn hóa xuống dòng.
 * Phản hồi trong Artifact đến thẳng dạng chuỗi, nên chuẩn hóa trước khi parse
 * để tương đương đường file. Không bỏ BOM: đường file của engine cũng giữ BOM.
 */
export function normalizeNewlines(text) {
  return String(text).replace(/\r\n?/g, "\n");
}

// `\w+` của Python trên str: chữ cái (L*), chữ số/ký tự số (N*) và "_".
// Không gồm dấu kết hợp (M*), nên ký tự biến thể emoji U+FE0F không được đếm.
const WORD_RE = /[\p{L}\p{N}_]+/gu;

/** Port của `count_words`. */
export function countWords(text) {
  return (String(text).match(WORD_RE) || []).length;
}

/** Port của `estimate_tokens`. */
export function estimateTokens(text) {
  if (!pyStrip(text)) return 0;
  return Math.max(1, Math.trunc(countWords(text) * 1.35));
}
