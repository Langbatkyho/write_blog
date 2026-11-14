// Port của engine/workflow_context.py::build_step_prompt. Kết quả phải khớp từng
// byte với golden workflow_prompts.json.
import { pyStr, pyTruthy } from "./pycompat.js";

// Khối hướng dẫn sau `textwrap.dedent(...).strip()` của engine.
export const STEP_INSTRUCTIONS = [
  "Instructions:",
  "- Follow the Skill YAML strictly.",
  "- Produce exactly two top-level sections: `## Artifact` and `## Handoff`.",
  "- `## Artifact` is the full output for this step's expected output file.",
  "- `## Handoff` is a compact structured summary for downstream agents.",
  "- Keep `## Handoff` around 120-250 Vietnamese words, roughly 200-400 tokens.",
  "- Do not mention that you are an AI.",
  "- Do not include hidden reasoning or process notes.",
  "- Keep the writing language Vietnamese unless the author explicitly requests another language.",
].join("\n");

function block(entries, emptyText) {
  const parts = Object.entries(entries || {}).map(([name, content]) => `### ${name}\n\n${content}`);
  return parts.join("\n\n") || emptyText;
}

/**
 * @param workflow   định nghĩa flow (bundle.workflows[mode].definition)
 * @param step       một phần tử của workflow.steps
 * @param skillYaml  chuỗi YAML dựng sẵn của skill (bundle.styles[mode][style].files[file].yaml)
 * @param authorInput nội dung input của tác giả
 * @param contextPackage kết quả buildContextPackage
 */
export function buildStepPrompt(workflow, step, skillYaml, authorInput, contextPackage) {
  const handoffBlock = block(contextPackage.handoffs, "No handoffs selected for this step.");
  const artifactBlock = block(contextPackage.artifacts, "No full artifacts selected for this step.");
  const parts = [
    "You are running one step of an automated reflective blog workflow.",
    `Workflow name: ${pyStr(workflow.name)}`,
    `Workflow description: ${pyStr(workflow.description)}`,
  ];
  const needsAuthorInput = Object.prototype.hasOwnProperty.call(step, "needs_author_input") ? step.needs_author_input : true;
  if (pyTruthy(needsAuthorInput)) {
    parts.push(`Author input:\n\`\`\`markdown\n${authorInput}\n\`\`\``);
  }
  parts.push(STEP_INSTRUCTIONS);
  parts.push(
    "---",
    "Current step context:",
    `- id: ${pyStr(step.id)}`,
    `- purpose: ${pyStr(step.purpose)}`,
    `- expected output file: ${pyStr(step.output)}`,
    `- expected handoff file: ${pyStr(step.handoff_output)}`,
    `Compact handoffs selected by context_policy:\n\`\`\`markdown\n${handoffBlock}\n\`\`\``,
    `Full artifacts selected by context_policy:\n\`\`\`markdown\n${artifactBlock}\n\`\`\``,
    `Skill YAML:\n\`\`\`yaml\n${skillYaml}\n\`\`\``,
  );
  return parts.join("\n\n");
}
