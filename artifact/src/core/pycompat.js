// Tái tạo vài ngữ nghĩa của Python mà engine dựa vào, để kết quả JS khớp từng byte
// với golden do Python sinh (artifact/tests/golden/).

// Tập ký tự mà Python coi là khoảng trắng (str.isspace / `\s` của re trên str).
// Khác `\s` và trim() của JS: Python có \x1c-\x1f, \x85; không có U+FEFF (BOM).
export const PY_WS_CLASS = "[\\t\\n\\x0b\\x0c\\r\\x1c-\\x20\\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]";

// `^` và `$` của Python ở chế độ MULTILINE chỉ nhận "\n" làm ranh giới dòng,
// còn cờ `m` của JS nhận cả U+000D, U+2028, U+2029. Dùng hai mảnh này
// (regex không bật cờ `m`) để giữ đúng ngữ nghĩa Python.
export const PY_LINE_START = "(?:^|(?<=\\n))";
export const PY_LINE_END = "(?=\\n|$)";

const PY_STRIP_RE = new RegExp(`^${PY_WS_CLASS}+|${PY_WS_CLASS}+$`, "g");

/** str.strip() của Python. */
export function pyStrip(text) {
  return String(text).replace(PY_STRIP_RE, "");
}

/** str(value) của Python cho các giá trị gặp trong flow/skill. */
export function pyStr(value) {
  if (value === null || value === undefined) return "None";
  if (value === true) return "True";
  if (value === false) return "False";
  return String(value);
}

/** Độ "truthy" kiểu Python cho giá trị JSON. */
export function pyTruthy(value) {
  if (value === null || value === undefined || value === false || value === 0 || value === "") return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value).length > 0;
  return true;
}

/** re.escape đủ dùng cho tiêu đề cố định. */
export function escapeRegExp(text) {
  return String(text).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** textwrap.dedent của Python 3.13: dòng chỉ có khoảng trắng thành rỗng, rồi bỏ lề chung. */
export function pyDedent(text) {
  const lines = String(text).split("\n").map((line) => (/^[ \t]+$/.test(line) ? "" : line));
  let margin = null;
  for (const line of lines) {
    const match = /^([ \t]*)[^ \t\n]/.exec(line);
    if (!match) continue;
    const indent = match[1];
    if (margin === null || margin.startsWith(indent)) margin = indent;
    else if (!indent.startsWith(margin)) {
      let i = 0;
      while (i < margin.length && i < indent.length && margin[i] === indent[i]) i += 1;
      margin = margin.slice(0, i);
    }
  }
  if (!margin) return lines.join("\n");
  return lines.map((line) => (line.startsWith(margin) ? line.slice(margin.length) : line)).join("\n");
}

// Ranh giới dòng của str.splitlines() trong Python.
const PY_LINE_BREAK = /\r\n|[\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029]/;

/** str.splitlines() của Python (không giữ ký tự xuống dòng). */
export function pySplitlines(text) {
  const parts = String(text).split(PY_LINE_BREAK);
  if (parts.length && parts[parts.length - 1] === "") parts.pop();
  return parts;
}

/**
 * format(x, ".Nf") của Python: làm tròn half-even trên giá trị nhị phân chính xác,
 * khác toFixed của JS ở các trường hợp hòa (ví dụ 0.0625 -> "0.062").
 */
export function pyFormatFixed(x, digits) {
  const negative = x < 0 || Object.is(x, -0);
  const exact = Math.abs(x).toFixed(100); // đủ để biểu diễn chính xác số double trong khoảng dùng ở đây
  const [intPart, fraction] = exact.split(".");
  const kept = intPart + fraction.slice(0, digits);
  const rest = fraction.slice(digits);
  let roundUp = false;
  if (rest[0] > "5") roundUp = true;
  else if (rest[0] === "5") roundUp = /[1-9]/.test(rest.slice(1)) || Number(kept[kept.length - 1]) % 2 === 1;
  const rounded = roundUp ? (BigInt(kept) + 1n).toString().padStart(kept.length, "0") : kept;
  const whole = rounded.slice(0, rounded.length - digits) || "0";
  return (negative ? "-" : "") + whole + (digits ? "." + rounded.slice(rounded.length - digits) : "");
}

/** format(n, "+d") của Python. */
export function pySignedInt(n) {
  return (n < 0 ? "-" : "+") + String(Math.abs(n));
}

const PY_NON_SPACE_RE = new RegExp(`[^${PY_WS_CLASS.slice(1, -1)}]+`, "g");

/** Port của engine/parser.py::truncate_words. */
export function truncateWords(text, maxWords = 220) {
  const words = String(text).match(PY_NON_SPACE_RE) || [];
  if (words.length <= maxWords) return pyStrip(text);
  return pyStrip(words.slice(0, maxWords).join(" ")) + "\n\n[Fallback handoff truncated locally.]";
}
