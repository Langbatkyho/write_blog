// In ra JSON bộ file xuất từ hai run giả (deep và moment), để test Python
// (tests/test_artifact_export.py) kiểm tra engine đọc được. Không gọi API.
import { createFakeClient } from "../../src/core/client_fake.js";
import { exportRunFiles } from "../../src/core/export.js";
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
process.stdout.write(JSON.stringify(out));
