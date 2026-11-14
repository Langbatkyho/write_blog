// Xuất một lần chạy thành bộ file theo bố cục thư mục run của engine
// (input.md, metadata.json, step_outputs.json, run_log.md, handoff_log.md và
// các file artifact/handoff), để engine Python đọc lại được, kể cả learning loop.
// Chỉ dựng nội dung; việc nén zip do tầng UI làm.
import { runFolderName } from "./run_record.js";
import { stageTelemetry } from "./orchestrator.js";

// Cùng dạng append_run_log của engine: "# tiêu đề\n\nnội dung\n", nối bằng "\n\n".
function logText(blocks) {
  return blocks.map(([title, body]) => `# ${title}\n\n${String(body).trim()}\n`).join("\n\n");
}

/** Cùng các trường của StageResult.to_dict() trong engine. */
function stepOutput(result) {
  return {
    status: result.status,
    artifact: result.artifact || "",
    handoff: result.handoff || "",
    artifact_file: result.artifact_file || "",
    handoff_file: result.handoff_file || "",
    secondary_artifact_file: result.secondary_artifact_file || null,
    warnings: result.warnings || [],
    metrics: result.metrics || {},
    error: result.error || null,
    provider: result.provider || null,
    model: result.model || null,
    api_attempted: Boolean(result.api_attempted),
    api_called: Boolean(result.api_called),
    duration_ms: result.duration_ms || 0,
  };
}

/** Metadata cùng khóa với metadata.json của engine, thêm vài trường của Artifact. */
export function runMetadata(bundle, run) {
  const results = run.stageIds.map((id) => run.results[id]).filter(Boolean);
  const metrics = Object.fromEntries(results.map((r) => [r.stage_id, r.metrics || {}]));
  const sum = (key) => results.reduce((total, r) => total + ((r.metrics || {})[key] || 0), 0);
  return {
    created_at: run.createdAt,
    config_file: "artifact",
    workflow_file: bundle.workflows[run.mode]?.file || null,
    input_file: null,
    dry_run: false,
    run_source: run.runSource,
    persisted: Boolean(run.persisted),
    api_attempted: Boolean(run.apiAttempted),
    api_called: Boolean(run.apiCalled),
    status: run.status,
    client_map: null,
    style: run.style,
    mode: run.mode,
    stage_telemetry: stageTelemetry(run),
    completed_at: run.completedAt,
    context_strategy: "artifact_plus_handoff",
    step_context_metrics: metrics,
    total_artifact_estimated_tokens: sum("artifact_estimated_tokens"),
    total_handoff_estimated_tokens: sum("handoff_estimated_tokens"),
    run_id: run.id || null,
    bundle_hash: run.bundleHash,
    build_id: run.buildId || null,
  };
}

/** @returns {{folderName: string, files: Object<string,string>}} */
export function exportRunFiles(bundle, run) {
  if (!run.id) throw new Error("Run chưa có ID; hãy lưu run trước khi xuất.");
  const metadata = runMetadata(bundle, run);
  const files = {
    "input.md": run.authorInput,
    "metadata.json": JSON.stringify(metadata, null, 2),
  };
  const runLog = [["Run Metadata", JSON.stringify(metadata, null, 2)], ["Author Input", run.authorInput]];
  const handoffLog = [];
  const stepOutputs = {};
  run.stageIds.forEach((id, index) => {
    const result = run.results[id];
    if (!result) return;
    stepOutputs[id] = stepOutput(result);
    if (result.status === "completed") {
      runLog.push([`${index + 1}. ${id} Artifact`, result.artifact]);
      handoffLog.push([`${index + 1}. ${id} Handoff`, result.handoff]);
      for (const [file, content] of Object.entries(result.files || { [result.artifact_file]: result.artifact })) files[file] = content;
      files[result.handoff_file] = result.handoff;
    } else if (result.status === "failed") {
      runLog.push([`${index + 1}. ${id} ERROR`, result.error || ""]);
    }
  });
  files["step_outputs.json"] = JSON.stringify(stepOutputs, null, 2);
  files["run_log.md"] = logText(runLog);
  if (handoffLog.length) files["handoff_log.md"] = logText(handoffLog);
  return { folderName: runFolderName(run), files };
}

