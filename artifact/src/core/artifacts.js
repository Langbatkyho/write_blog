// Port của engine/workflow_artifacts.py: tách artifact của stage biên tập thành
// file chính (bài đã sửa) và file phụ (edit log).
import { escapeRegExp, PY_LINE_END, PY_LINE_START, PY_WS_CLASS, pyStrip } from "./pycompat.js";

const WS = PY_WS_CLASS;

const LEGACY_PRIMARY_HEADINGS = ["Edited Blog", "edited_blog", "Edited Draft"];
const LEGACY_LOG_HEADINGS = ["Edit Log", "edit_log"];
const MISSING_EDIT_LOG = "Edit log section was not found in the artifact.";

/** Port của `heading_pattern`: gạch dưới và khoảng trắng được coi là như nhau. */
export function headingPattern(heading) {
  return String(heading).trim().split(/[ _]+/).filter(Boolean).map(escapeRegExp).join("[ _]+");
}

/** Port của `extract_markdown_section` (`(?ims)^##+\s*H\s*$\s*(.*?)(?=^##+\s+|\Z)`). */
export function extractMarkdownSection(markdown, heading) {
  const re = new RegExp(
    `${PY_LINE_START}##+${WS}*${headingPattern(heading)}${WS}*${PY_LINE_END}${WS}*([\\s\\S]*?)(?=${PY_LINE_START}##+${WS}+|$)`,
    "i",
  );
  const match = re.exec(markdown);
  return match ? pyStrip(match[1]) : null;
}

/** Port của `extract_markdown_section_before`. */
export function extractMarkdownSectionBefore(markdown, heading, stopHeadings) {
  const start = new RegExp(`${PY_LINE_START}##+${WS}*${headingPattern(heading)}${WS}*${PY_LINE_END}`, "i").exec(markdown);
  if (!start) return null;
  const startEnd = start.index + start[0].length;
  const stopAlternatives = stopHeadings.map(headingPattern).join("|");
  const stop = new RegExp(`${PY_LINE_START}##+${WS}*(?:${stopAlternatives})${WS}*${PY_LINE_END}`, "i").exec(markdown.slice(startEnd));
  const sectionEnd = stop ? startEnd + stop.index : markdown.length;
  return pyStrip(markdown.slice(startEnd, sectionEnd));
}

/**
 * Port của `derive_artifact_file_contents`.
 * @returns {{files: Object<string,string>, warned: boolean}} `warned` thay cho
 *   UserWarning của Python khi không tách được bài khỏi edit log.
 */
export function deriveArtifactFileContents(skill, artifact) {
  const output = (skill && skill.output) || {};
  let primaryName = output.name;
  if (typeof primaryName !== "string") primaryName = output.artifact;
  if (typeof primaryName !== "string") throw new Error("Skill output thiếu name/artifact.");
  let secondaryName = output.secondary_name || output.secondary_artifact;
  if (typeof secondaryName !== "string") secondaryName = null;

  const files = { [primaryName]: artifact };
  let warned = false;
  if (secondaryName) {
    // Tiêu đề hợp lệ: tên cũ của Deep, tên phần trong output.sections, rồi tên file.
    const sectionNames = Array.isArray(output.sections) ? output.sections.filter((item) => typeof item === "string") : [];
    const primaryHeadings = [...LEGACY_PRIMARY_HEADINGS, ...sectionNames.slice(0, 1), primaryName];
    const logHeadings = [...LEGACY_LOG_HEADINGS, ...sectionNames.slice(1, 2), secondaryName];
    let editedBlog = null;
    for (const heading of primaryHeadings) {
      editedBlog = extractMarkdownSectionBefore(artifact, heading, logHeadings);
      if (editedBlog) break;
    }
    editedBlog = editedBlog || artifact;
    let editLog = null;
    for (const heading of logHeadings) {
      editLog = extractMarkdownSection(artifact, heading);
      if (editLog) break;
    }
    editLog = editLog || MISSING_EDIT_LOG;
    warned = editedBlog === artifact;
    files[primaryName] = editedBlog;
    files[secondaryName] = editLog;
  }
  return { files, warned };
}
