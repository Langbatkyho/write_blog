// Dựng input của tác giả theo đúng định dạng examples/*_input_template.md mà
// engine đọc, và tạo tên file từ tiêu đề (port của engine/parser.py::slugify).

/**
 * @param fields {title, rawNotes, optionalContext, targetReader, desiredLength}
 * Các mục tùy chọn bỏ trống thì không đưa vào, giống mẫu moment của engine.
 */
export function buildAuthorInput({ title = "", rawNotes = "", optionalContext = "", targetReader = "", desiredLength = "" }) {
  const clean = (value) => String(value || "").replace(/\r\n?/g, "\n").trim();
  if (!clean(rawNotes)) throw new Error("Cần nhập ghi chú thô (raw_notes).");
  const sections = [`title: ${clean(title)}`.trimEnd(), `raw_notes:\n${clean(rawNotes)}`];
  if (clean(optionalContext)) sections.push(`optional_context:\n${clean(optionalContext)}`);
  if (clean(targetReader)) sections.push(`target_reader:\n${clean(targetReader)}`);
  if (clean(desiredLength)) sections.push(`desired_length:\n${clean(desiredLength)}`);
  return sections.join("\n\n") + "\n";
}

/** Port của slugify: chữ thường, bỏ ký tự đặc biệt, khoảng trắng thành "-", tối đa 60 ký tự. */
export function slugify(text, fallback = "blog") {
  let slug = String(text || "").toLowerCase().trim();
  slug = slug.replace(/[^\p{L}\p{N}_\s-]/gu, "");
  slug = slug.replace(/[\s_]+/gu, "-");
  slug = slug.replace(/^-+|-+$/g, "");
  return [...slug].slice(0, 60).join("") || fallback;
}
