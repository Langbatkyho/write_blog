// Điều phối một lần chạy workflow trong Artifact. Tương ứng vòng lặp của
// engine/workflow_execution.py::run_workflow, nhưng không ghi file: lưu trữ
// thuộc repository (ART-4). Client gọi model được inject từ ngoài (Bài học 6).
//
// Có thể chạy liền một mạch (runWorkflow) hoặc từng bước (createRun + runNextStage),
// và chạy lại một stage lỗi (retryStage).
import { buildContextPackage } from "./context.js";
import { deriveArtifactFileContents } from "./artifacts.js";
import { modelConfigForStage, resolveStyle } from "./contracts.js";
import { estimateTokens, normalizeNewlines, parseStageResponseStrict } from "./parser.js";
import { buildStepPrompt } from "./prompt.js";

export const RUN_STATUS = Object.freeze({ RUNNING: "running", COMPLETED: "completed", FAILED: "failed", CANCELLED: "cancelled" });

const now = () => Date.now();

/** Tạo trạng thái một lần chạy. Ném lỗi nếu mode/style không có trong bundle. */
export function createRun({ bundle, mode, style, authorInput, runSource = "artifact", stopOnError = true }) {
  const workflow = bundle.workflows[mode];
  if (!workflow) throw new Error(`Mode không hợp lệ: ${mode}`);
  const resolvedStyle = resolveStyle(bundle, mode, style);
  if (!resolvedStyle) {
    throw new Error(`Style '${style}' không có trong mode '${mode}'. Có: ${Object.keys(bundle.styles[mode]).join(", ")}`);
  }
  if (typeof authorInput !== "string" || !authorInput.trim()) throw new Error("Thiếu input của tác giả.");
  return {
    bundleHash: bundle.content_hash,
    mode,
    style: resolvedStyle,
    authorInput,
    runSource,
    stopOnError,
    stageIds: [...workflow.stage_ids],
    results: {},
    artifacts: {},
    handoffs: {},
    status: RUN_STATUS.RUNNING,
    apiAttempted: false,
    apiCalled: false,
    createdAt: new Date().toISOString(),
    completedAt: null,
  };
}

/** Chỉ số stage kế tiếp chưa chạy, hoặc -1 nếu đã hết hoặc run đã dừng. */
export function nextStageIndex(run) {
  if (run.status !== RUN_STATUS.RUNNING) return -1;
  return run.stageIds.findIndex((id) => !run.results[id]);
}

function telemetry(result) {
  return {
    status: result.status,
    provider: result.provider,
    model: result.model,
    model_applied: result.model_applied,
    tier_applied: result.tier_applied,
    effort: result.effort,
    truncated: result.truncated,
    api_attempted: result.api_attempted,
    api_called: result.api_called,
    duration_ms: result.duration_ms,
    error: result.error,
    error_code: result.error_code,
  };
}

/** Bảng telemetry theo stage, cùng dạng `stage_telemetry` trong metadata của engine. */
export function stageTelemetry(run) {
  return Object.fromEntries(Object.entries(run.results).map(([id, result]) => [id, telemetry(result)]));
}

function settle(run) {
  const results = run.stageIds.map((id) => run.results[id]).filter(Boolean);
  const failed = results.filter((result) => result.status === "failed");
  const cancelled = failed.some((result) => result.error_code === "cancelled");
  const allSettled = results.length === run.stageIds.length;
  if (failed.length && (run.stopOnError || cancelled)) {
    run.status = cancelled ? RUN_STATUS.CANCELLED : RUN_STATUS.FAILED;
  } else if (allSettled) {
    run.status = failed.length ? RUN_STATUS.FAILED : RUN_STATUS.COMPLETED;
  } else {
    run.status = RUN_STATUS.RUNNING;
  }
  run.completedAt = run.status === RUN_STATUS.RUNNING ? null : new Date().toISOString();
}

function baseResult(step, skill) {
  return {
    stage_id: step.id,
    artifact_file: step.output,
    handoff_file: step.handoff_output,
    secondary_artifact_file: skill.output?.secondary_name || skill.output?.secondary_artifact || null,
  };
}

/**
 * Chạy stage thứ `index`. Chỉ được chạy stage kế tiếp (nextStageIndex).
 * @param options.client  client đã inject (thật hoặc giả)
 * @param options.signal  AbortSignal để dừng
 * @param options.onText  ({stageId, text}) khi phản hồi đang được viết
 */
export async function runStage(run, index, { bundle, client, signal, onText } = {}) {
  if (index !== nextStageIndex(run)) {
    throw new Error(`Chỉ chạy được stage kế tiếp (${nextStageIndex(run)}), không phải ${index}.`);
  }
  const workflow = bundle.workflows[run.mode];
  const step = workflow.definition.steps[index];
  const skillFile = bundle.styles[run.mode][run.style].files[workflow.stage_files[step.id]];
  const skill = skillFile.data;
  const policy = step.context_policy || {};
  const required = new Set([...(policy.handoffs || []), ...(policy.artifacts || [])]);
  const failedDependencies = [...required]
    .filter((dep) => run.results[dep] && run.results[dep].status !== "completed")
    .sort();

  if (failedDependencies.length) {
    run.results[step.id] = {
      ...baseResult(step, skill),
      status: "skipped",
      error: "Dependency không hoàn tất: " + failedDependencies.join(", "),
    };
    settle(run);
    return run.results[step.id];
  }

  const modelConfig = modelConfigForStage(bundle, step.id);
  const contextPackage = buildContextPackage(step, run.artifacts, run.handoffs);
  const prompt = buildStepPrompt(workflow.definition, step, skillFile.yaml, run.authorInput, contextPackage);
  const { provider, apiCapable } = client.describe(step.id, modelConfig);
  const sum = (entries) => Object.values(entries).reduce((total, value) => total + estimateTokens(value), 0);
  const common = {
    ...baseResult(step, skill),
    provider,
    model: modelConfig.model,
    effort: modelConfig.effort,
    api_attempted: Boolean(apiCapable),
  };
  run.apiAttempted = run.apiAttempted || common.api_attempted;

  const started = now();
  // Engine ghi api_called=false khi parse lỗi dù lời gọi đã diễn ra; ở đây ghi đúng
  // việc lời gọi đã trả về hay chưa (AGENTS §5: api_called phải trung thực).
  let called = false;
  try {
    const response = await client.call({
      prompt,
      stageId: step.id,
      modelConfig,
      signal,
      onText: onText ? ({ text }) => onText({ stageId: step.id, text }) : undefined,
    });
    called = Boolean(apiCapable);
    const { artifact, handoff } = parseStageResponseStrict(normalizeNewlines(response.text));
    const { files, warned } = deriveArtifactFileContents(skill, artifact);
    if (!Object.prototype.hasOwnProperty.call(files, step.output)) {
      throw new Error(`Skill '${step.id}' không tạo Flow output '${step.output}'.`);
    }
    const warnings = [];
    if (response.truncated) warnings.push("Phản hồi chạm giới hạn độ dài; nên đọc lại trước khi dùng.");
    if (warned) warnings.push(`Không tách được bài và edit log; ${step.output} chứa toàn bộ artifact.`);
    if (!response.modelApplied) warnings.push(`Model ${modelConfig.model} không trả lời; đã chạy bằng hạng ${response.tierApplied}.`);
    const artifactTokens = estimateTokens(artifact);
    const handoffTokens = estimateTokens(handoff);
    const result = {
      ...common,
      status: "completed",
      artifact,
      handoff,
      files,
      model_applied: response.modelApplied || null,
      tier_applied: response.tierApplied || null,
      truncated: Boolean(response.truncated),
      warnings,
      api_called: called,
      duration_ms: now() - started,
      error: null,
      error_code: null,
      metrics: {
        artifact_estimated_tokens: artifactTokens,
        handoff_estimated_tokens: handoffTokens,
        handoff_savings_estimated_tokens: Math.max(0, artifactTokens - handoffTokens),
        selected_input_handoff_estimated_tokens: sum(contextPackage.handoffs),
        selected_input_artifact_estimated_tokens: sum(contextPackage.artifacts),
      },
    };
    run.results[step.id] = result;
    run.artifacts[step.id] = artifact;
    run.handoffs[step.id] = handoff;
  } catch (error) {
    run.results[step.id] = {
      ...common,
      status: "failed",
      api_called: called || Boolean(error && error.apiCalled),
      duration_ms: now() - started,
      error: (error && error.message) || String(error),
      error_code: (error && error.code) || null,
      partial_text: (error && typeof error.text === "string" && error.text) || null,
    };
  }
  run.apiCalled = run.apiCalled || run.results[step.id].api_called;
  settle(run);
  return run.results[step.id];
}

/** Chạy stage kế tiếp; trả null nếu không còn stage nào để chạy. */
export async function runNextStage(run, options) {
  const index = nextStageIndex(run);
  return index === -1 ? null : runStage(run, index, options);
}

/** Bỏ kết quả từ stage `index` trở đi để chạy lại. */
export function resetFromStage(run, index) {
  for (const id of run.stageIds.slice(index)) {
    delete run.results[id];
    delete run.artifacts[id];
    delete run.handoffs[id];
  }
  run.status = RUN_STATUS.RUNNING;
  run.completedAt = null;
  return run;
}

/** Chạy lại một stage đã lỗi hoặc bị bỏ qua; các stage sau nó bị xóa kết quả. */
export async function retryStage(run, index, options) {
  const id = run.stageIds[index];
  const result = run.results[id];
  if (!result || result.status === "completed") throw new Error(`Stage ${id} không ở trạng thái lỗi hoặc bị bỏ qua.`);
  resetFromStage(run, index);
  return runStage(run, index, options);
}

/** Chạy liền một mạch cho tới khi xong, lỗi (nếu stopOnError) hoặc bị dừng. */
export async function runWorkflow({ bundle, mode, style, authorInput, client, stopOnError = true, signal, onText, onStageStart, onStageEnd, runSource }) {
  const run = createRun({ bundle, mode, style, authorInput, stopOnError, runSource });
  for (let index = nextStageIndex(run); index !== -1; index = nextStageIndex(run)) {
    if (onStageStart) onStageStart({ index, stageId: run.stageIds[index] });
    const result = await runStage(run, index, { bundle, client, signal, onText });
    if (onStageEnd) onStageEnd({ index, stageId: run.stageIds[index], result });
  }
  return run;
}
