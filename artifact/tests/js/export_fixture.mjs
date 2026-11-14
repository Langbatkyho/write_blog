// In ra JSON bộ file xuất từ hai run giả (deep và moment), để test Python
// (tests/test_artifact_export.py) kiểm tra engine đọc được. Không gọi API.
import { createFakeClient } from "../../src/core/client_fake.js";
import { exportRunFiles } from "../../src/core/export.js";
import { runLearning } from "../../src/core/learning.js";
import { runWorkflow } from "../../src/core/orchestrator.js";
import { loadBundle } from "./helpers.js";

const bundle = loadBundle();
const INPUT = "title: Chiều mưa\n\nraw_notes:\n- Mưa rơi trên mái tôn 🌧️\n\ndesired_length:\n300-600 từ\n";
const out = {};
for (const [mode, style, failOn] of [["deep", "reflective", null], ["moment", "va-natural", null], ["moment", "reflective", "inner_weather"]]) {
  const failures = failOn ? { [failOn]: { code: "rate_limited", message: "Đã chạm giới hạn." } } : {};
  const run = await runWorkflow({ bundle, mode, style, authorInput: INPUT, client: createFakeClient({ failures }) });
  run.id = `20261114_090507_042000_ab12cd34_${mode}_${style}`;
  run.persisted = true;
  out[`${mode}/${style}${failOn ? "/failed" : ""}`] = exportRunFiles(bundle, run);
}
// Run đã có bản cuối và một vòng học offline của Artifact.
const PRODUCTION = "# Chiều mưa\n\nMưa rơi trên mái tôn. Mình sửa lại vài chữ 🌿.\n\nĐoạn mới của người viết.";
for (const [mode, style] of [["moment", "va-natural"], ["deep", "reflective"]]) {
  const run = await runWorkflow({ bundle, mode, style, authorInput: INPUT, client: createFakeClient() });
  run.id = `20261114_090507_042000_cd34ef56_${mode}_${style}`;
  run.persisted = true;
  const session = await runLearning({ bundle, run, productionBlog: PRODUCTION, offline: true, now: new Date(Date.UTC(2026, 10, 14, 9, 30)) });
  out[`${mode}/${style}/learned`] = { ...exportRunFiles(bundle, run, { production: PRODUCTION, learnings: [session] }), report: session.report, tuning: session.tuning_suggestions };
}
process.stdout.write(JSON.stringify(out));
