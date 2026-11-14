// Tiện ích dùng chung cho test JS. Bundle được build mới bằng Python vào thư mục
// tạm của hệ điều hành (không ghi vào repo, không ghi runs/).
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
export const ARTIFACT_DIR = resolve(here, "..", "..");
export const GOLDEN_DIR = join(ARTIFACT_DIR, "tests", "golden");

let cachedBundle = null;

/** Bundle hiện tại của repo (build một lần cho mỗi tiến trình test). */
export function loadBundle() {
  if (cachedBundle) return structuredClone(cachedBundle);
  const dir = mkdtempSync(join(tmpdir(), "artifact-bundle-"));
  try {
    const out = join(dir, "bundle.json");
    execFileSync(process.env.PYTHON || "python3", [join(ARTIFACT_DIR, "build_bundle.py"), "--out", out], { stdio: "pipe" });
    cachedBundle = JSON.parse(readFileSync(out, "utf8"));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
  return structuredClone(cachedBundle);
}

export function loadGolden(name) {
  return JSON.parse(readFileSync(join(GOLDEN_DIR, name), "utf8"));
}

/** Phản hồi chuẩn hai section cho client giả. */
export function stageResponse(artifact, handoff) {
  return `## Artifact\n\n${artifact}\n\n## Handoff\n\n${handoff}`;
}
