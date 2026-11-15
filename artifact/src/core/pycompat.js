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

// --- Bổ sung cho Voice Lab (ART-8.1) ----------------------------------------

/** round(x, n) của Python: làm tròn half-even trên giá trị nhị phân chính xác. */
export function pyRound(x, digits) {
  return Number(pyFormatFixed(x, digits));
}

/** str.split() không tham số của Python: tách theo khoảng trắng Unicode, bỏ phần rỗng. */
export function pySplitWhitespace(text) {
  return String(text).match(PY_NON_SPACE_RE) || [];
}

/** Số code point (len() của Python), không phải số đơn vị UTF-16. */
export function pyLen(text) {
  let count = 0;
  for (const _ of String(text)) count += 1;
  return count;
}

/** str.find() của Python: chỉ số tính theo code point, -1 nếu không có. */
export function pyFind(haystack, needle) {
  const index = String(haystack).indexOf(needle);
  return index < 0 ? -1 : pyLen(String(haystack).slice(0, index));
}

/** So sánh chuỗi theo code point như sorted() của Python (JS mặc định so theo UTF-16). */
export function pyCompare(a, b) {
  const x = [...String(a)];
  const y = [...String(b)];
  for (let i = 0; i < Math.min(x.length, y.length); i += 1) {
    const d = x[i].codePointAt(0) - y[i].codePointAt(0);
    if (d) return d < 0 ? -1 : 1;
  }
  return x.length === y.length ? 0 : x.length < y.length ? -1 : 1;
}

/**
 * str.casefold() của Python, gần đúng: lower() cộng các trường hợp gập đặc biệt hay gặp
 * (ß, ẞ, ς, ſ, ligature). Chỉ dùng để phát hiện rule trùng giữa do và avoid.
 */
export function pyCasefold(text) {
  const SPECIAL = { "ß": "ss", "ẞ": "ss", "ς": "σ", "ſ": "s", "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st" };
  return String(text)
    .toLowerCase()
    .replace(/[ßẞςſﬀ-ﬆ]/g, (ch) => SPECIAL[ch] ?? ch);
}

/** repr() của float trong Python: "1.0", "0.5", "1e-05", "1e+16". */
export function pyFloatRepr(x) {
  if (Number.isNaN(x)) return "NaN";
  if (x === Infinity) return "Infinity";
  if (x === -Infinity) return "-Infinity";
  if (x === 0) return Object.is(x, -0) ? "-0.0" : "0.0";
  const [mantissa, expText] = x.toExponential().split("e");
  const exponent = Number(expText);
  if (exponent < -4 || exponent >= 16) {
    return `${mantissa}e${exponent < 0 ? "-" : "+"}${String(Math.abs(exponent)).padStart(2, "0")}`;
  }
  const negative = mantissa.startsWith("-");
  const digits = mantissa.replace("-", "").replace(".", "");
  let text;
  if (exponent >= digits.length - 1) text = digits + "0".repeat(exponent - digits.length + 1) + ".0";
  else if (exponent >= 0) text = digits.slice(0, exponent + 1) + "." + digits.slice(exponent + 1);
  else text = "0." + "0".repeat(-exponent - 1) + digits;
  return (negative ? "-" : "") + text;
}

/**
 * json.dumps(value, ensure_ascii=False) của Python (separators ", " và ": ").
 * JS không phân biệt 1 và 1.0, nên số dưới các key trong `floatKeys` luôn in kiểu float
 * của Python (giống trường float của Pydantic); số không nguyên luôn là float.
 */
export function pyJsonDumps(value, floatKeys = new Set()) {
  const render = (item, isFloat) => {
    if (item === null || item === undefined) return "null";
    if (typeof item === "boolean") return item ? "true" : "false";
    if (typeof item === "number") return isFloat || !Number.isInteger(item) ? pyFloatRepr(item) : String(item);
    if (typeof item === "string") return JSON.stringify(item);
    if (Array.isArray(item)) return "[" + item.map((entry) => render(entry, isFloat)).join(", ") + "]";
    return "{" + Object.entries(item).map(([key, entry]) => `${JSON.stringify(key)}: ${render(entry, floatKeys.has(key))}`).join(", ") + "}";
  };
  return render(value, false);
}

/** Thời điểm UTC theo định dạng JSON của Pydantic: "2026-11-14T09:05:07Z" hoặc ".042000Z". */
export function pyIsoUtc(date) {
  const iso = date.toISOString();
  const ms = date.getUTCMilliseconds();
  return iso.slice(0, 19) + (ms ? `.${String(ms * 1000).padStart(6, "0")}` : "") + "Z";
}
