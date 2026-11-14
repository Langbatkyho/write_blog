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
