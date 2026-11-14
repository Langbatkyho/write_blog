// Lấy thành phẩm của một lần chạy theo `final_output` của flow, và gộp toàn bộ
// kết quả thành một file markdown (giống run_log.md + handoff của engine).
import { countWords } from "./parser.js";

function findFile(run, filename) {
  if (!filename) return null;
  for (const id of run.stageIds) {
    const result = run.results[id];
    if (result && result.status === "completed" && result.files && Object.prototype.hasOwnProperty.call(result.files, filename)) {
      return { file: filename, stageId: id, text: result.files[filename], words: countWords(result.files[filename]) };
    }
  }
  return null;
}

/** {primary, reflection}: bản nháp AI chính và phần phản tư, hoặc null nếu chưa có. */
export function collectFinalOutputs(workflowDefinition, run) {
  const finalOutput = workflowDefinition.final_output || {};
  return {
    primary: findFile(run, finalOutput.primary_ai_draft),
    reflection: findFile(run, finalOutput.reflection),
  };
}

/** Toàn bộ input, artifact và handoff của các stage đã xong, theo thứ tự. */
export function buildRunMarkdown(run) {
  const parts = [`# Input của tác giả\n\n${run.authorInput.trim()}`];
  run.stageIds.forEach((id, index) => {
    const result = run.results[id];
    if (!result) return;
    if (result.status !== "completed") {
      parts.push(`# ${index + 1}. ${id} (${result.status})\n\n${result.error || ""}`.trim());
      return;
    }
    parts.push(`# ${index + 1}. ${id} Artifact\n\n${result.artifact}`);
    parts.push(`# ${index + 1}. ${id} Handoff\n\n${result.handoff}`);
  });
  const meta = [
    `mode: ${run.mode}`,
    `style: ${run.style}`,
    `status: ${run.status}`,
    `bundle: ${run.bundleHash.slice(0, 12)}`,
    `created_at: ${run.createdAt}`,
  ];
  return `<!-- ${meta.join(" | ")} -->\n\n${parts.join("\n\n")}\n`;
}
