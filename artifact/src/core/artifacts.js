// Port của engine/workflow_artifacts.py: tách artifact của stage biên tập thành
// file chính (bài đã sửa) và file phụ (edit log).
import { escapeRegExp, PY_LINE_END, PY_LINE_START, PY_WS_CLASS, pyStrip } from "./pycompat.js";

const WS = PY_WS_CLASS;

/** Port của `extract_markdown_section` (`(?ims)^##+\s*H\s*$\s*(.*?)(?=^##+\s+|\Z)`). */
export function extractMarkdownSection(markdown, heading) {
  const re = new RegExp(
    `${PY_LINE_START}##+${WS}*${escapeRegExp(heading)}${WS}*${PY_LINE_END}${WS}*([\\s\\S]*?)(?=${PY_LINE_START}##+${WS}+|$)`,
    "i",
  );
  const match = re.exec(markdown);
  return match ? pyStrip(match[1]) : null;
}

/** Port của `extract_markdown_section_before`. */
export function extractMarkdownSectionBefore(markdown, heading, stopHeadings) {
  const start = new RegExp(`${PY_LINE_START}##+${WS}*${escapeRegExp(heading)}${WS}*${PY_LINE_END}`, "i").exec(markdown);
  if (!start) return null;
  const startEnd = start.index + start[0].length;
  const stopAlternatives = stopHeadings.map(escapeRegExp).join("|");
  const stop = new RegExp(`${PY_LINE_START}##+${WS}*(?:${stopAlternatives})${WS}*${PY_LINE_END}`, "i").exec(markdown.slice(startEnd));
  const sectionEnd = stop ? startEnd + stop.index : markdown.length;
  return pyStrip(markdown.slice(startEnd, sectionEnd));
}

const STOP_HEADINGS = ["Edit Log", "edit_log"];
const MISSING_EDIT_LOG = "Edit log section was not found in the artifact.";

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
    const editedBlog =
      extractMarkdownSectionBefore(artifact, "Edited Blog", STOP_HEADINGS) ||
      extractMarkdownSectionBefore(artifact, "edited_blog", STOP_HEADINGS) ||
      extractMarkdownSectionBefore(artifact, "Edited Draft", STOP_HEADINGS) ||
      artifact;
    const editLog =
      extractMarkdownSection(artifact, "Edit Log") || extractMarkdownSection(artifact, "edit_log") || MISSING_EDIT_LOG;
    warned = editedBlog === artifact;
    files[primaryName] = editedBlog;
    files[secondaryName] = editLog;
  }
  return { files, warned };
}
