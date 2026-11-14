// ART-3-AC1: kiểm tra trang bằng Chromium với `window.claude` giả. Không gọi
// Claude thật; kết quả runtime thật phải được nghiệm thu riêng trên claude.ai (AC4).
// Bỏ qua nếu máy không có Playwright.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, before, test } from "node:test";
import { pathToFileURL } from "node:url";

import { ARTIFACT_DIR } from "../js/helpers.js";

let chromium = null;
try {
  ({ chromium } = createRequire(import.meta.url)("playwright"));
} catch (_) {
  chromium = null;
}
const skip = chromium ? false : "Playwright không có trên máy này";
const SHOTS = process.env.ARTIFACT_UI_SHOTS || null;

let browser;
let workDir;
let pageUrl;
let bundle;

before(async () => {
  if (skip) return;
  workDir = mkdtempSync(join(tmpdir(), "artifact-ui-"));
  const out = join(workDir, "index.html");
  execFileSync(process.env.PYTHON || "python3", [join(ARTIFACT_DIR, "build_html.py"), "--out", out], { stdio: "pipe" });
  const body = readFileSync(out, "utf8");
  bundle = JSON.parse(body.match(/<script type="application\/json" id="bundle-data">([\s\S]*?)<\/script>/)[1]);
  // Giống khung mà Artifact bọc quanh trang khi publish.
  const wrapped = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>${body}</body></html>`;
  writeFileSync(join(workDir, "page.html"), wrapped);
  pageUrl = pathToFileURL(join(workDir, "page.html")).href;
  browser = await chromium.launch();
});

after(async () => {
  if (browser) await browser.close();
  if (workDir) rmSync(workDir, { recursive: true, force: true });
});

function fakeClaude(config) {
  window.__config = config;
  window.__calls = [];
  window.__downloads = [];
  if (config.noClaude) return;
  const sample = async (prompt, options) => {
    const cfg = window.__config;
    const id = /\n- id: (\S+)/.exec(prompt)[1];
    window.__calls.push({ id, model: options.model, effort: options.effort, tier: options.modelTier, cache: options.cache });
    await new Promise((resolve) => setTimeout(resolve, 20));
    if (cfg.failOn === id) throw { code: "rate_limited", message: "Đã chạm giới hạn." };
    if (cfg.holdOn === id) {
      options.onText({ text: "## Artifact\n\nĐang viết dở…", delta: "" });
      await new Promise((resolve, reject) => {
        options.signal.addEventListener("abort", () => reject({ code: "cancelled", message: "Đã dừng.", text: "## Artifact\n\nĐang viết dở…" }));
      });
    }
    const editor = id === "breath_editor" || id === "editor_agent";
    const artifact = editor
      ? "## Edited Blog\n\n# Chiều mưa\n\nMưa rơi trên mái tôn, ly cà phê tan đá 🌧️. Mình ngồi yên, không vội.\n\n## Edit Log\n\n- Cắt một câu lặp."
      : id === "sensory_capture"
        ? 'Tiếng mưa <img src=x onerror="window.__xss=1"> và mùi cà phê.'
        : `Kết quả của ${id}.`;
    const text = `## Artifact\n\n${artifact}\n\n## Handoff\n\nHandoff của ${id}.`;
    options.onText({ text, delta: text });
    return {
      text,
      truncated: cfg.truncateOn === id,
      modelTierApplied: options.modelTier,
      modelApplied: cfg.downgradeOn === id ? undefined : options.model,
    };
  };
  const downloads = { save: async (request) => { window.__downloads.push({ filename: request.filename, data: request.data }); } };
  window.claude = { use: async (name) => (name === "sample" ? (config.noSample ? null : sample) : name === "downloads" ? downloads : null) };
}

async function openPage(config = {}, { width = 1280, colorScheme = "light" } = {}) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, colorScheme, deviceScaleFactor: 1 });
  await context.route("**/*", (route) => (route.request().url().startsWith("file:") ? route.continue() : route.abort()));
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.addInitScript(fakeClaude, config);
  await page.goto(pageUrl);
  await page.waitForFunction(() => !document.getElementById("chip-claude").textContent.includes("đang kiểm tra"));
  return { context, page, errors };
}

async function noHorizontalScroll(page) {
  const { scroll, client } = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  assert.ok(scroll <= client, `cuộn ngang: ${scroll} > ${client}`);
}

async function shot(page, name) {
  if (SHOTS) await page.screenshot({ path: join(SHOTS, `${name}.png`), fullPage: true });
}

async function fillAndRun(page, { title = "Chiều mưa", notes = "- Mưa rào bất chợt\n- Mùi cà phê phin 🌧️" } = {}) {
  await page.fill("#title", title);
  await page.fill("#raw-notes", notes);
  await page.click("#run");
}

const status = (page) => page.textContent("#run-status");

for (const [width, colorScheme] of [[390, "light"], [390, "dark"], [1280, "light"], [1280, "dark"]]) {
  test(`trang trống hiển thị đúng ở ${width}px, theme ${colorScheme}`, { skip }, async () => {
    const { context, page, errors } = await openPage({}, { width, colorScheme });
    assert.equal(await page.textContent("#chip-claude"), "Claude: sẵn sàng");
    assert.equal(await page.locator("#stages > li").count(), 6);
    assert.equal(await page.locator('#stages > li[data-status="pending"]').count(), 6);
    assert.equal(await page.inputValue("#desired-length"), "300-600 từ");
    assert.ok(await page.isEnabled("#run"));
    assert.ok(await page.isHidden("#final"), "chưa có bài thì không hiện khung Bản nháp");
    assert.ok(await page.isHidden("#next"));
    await noHorizontalScroll(page);
    const background = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    assert.equal(background, colorScheme === "dark" ? "rgb(19, 24, 21)" : "rgb(243, 245, 242)");
    await shot(page, `idle-${width}-${colorScheme}`);
    assert.deepEqual(errors, []);
    await context.close();
  });
}

test("chạy liền đủ 6 bước moment/va-natural, đúng model, rồi tải bài", { skip }, async () => {
  const { context, page, errors } = await openPage({}, { width: 1280, colorScheme: "dark" });
  await page.selectOption("#style", "va-natural");
  await fillAndRun(page);
  await page.waitForFunction(() => document.getElementById("run-status").textContent.includes("Xong cả 6 bước"));
  const calls = await page.evaluate(() => window.__calls);
  assert.deepEqual(calls.map((call) => call.id), bundle.workflows.moment.stage_ids);
  for (const call of calls) {
    const expected = bundle.models.stages[call.id];
    assert.deepEqual([call.model, call.effort, call.tier, call.cache], [expected.model, expected.effort, expected.model_tier, false]);
  }
  assert.equal(await page.locator('#stages > li[data-status="completed"]').count(), 6);
  assert.ok(!(await page.isHidden("#final")));
  assert.match(await page.textContent("#final-text"), /Mưa rơi trên mái tôn/);
  assert.match(await page.textContent("#final-meta"), /moment_edited\.md/);
  assert.ok(!(await page.isHidden("#reflection")));
  await page.click("#download-draft");
  await page.waitForFunction(() => window.__downloads.length === 1);
  const download = (await page.evaluate(() => window.__downloads))[0];
  assert.equal(download.filename, "chiều-mưa.md");
  assert.match(download.data, /^# Chiều mưa/);
  await page.click("#download-run");
  await page.waitForFunction(() => window.__downloads.length === 2);
  assert.match((await page.evaluate(() => window.__downloads))[1].data, /# 6\. gentle_witness Handoff/);
  await noHorizontalScroll(page);
  await shot(page, "done-1280-dark");
  assert.deepEqual(errors, []);
  await context.close();
});

test("nội dung từ model hiển thị dạng chữ, không chạy được mã", { skip }, async () => {
  const { context, page } = await openPage();
  await fillAndRun(page);
  await page.waitForFunction(() => document.getElementById("run-status").textContent.includes("Xong"));
  await page.click('[data-stage="sensory_capture"] summary');
  assert.match(await page.textContent('[data-stage="sensory_capture"] pre'), /<img src=x/);
  assert.equal(await page.locator("#stages img").count(), 0);
  assert.equal(await page.evaluate(() => window.__xss), undefined);
  await context.close();
});

test("lỗi ở một bước: dừng, báo lỗi theo mã, chạy lại bước đó rồi đi tiếp", { skip }, async () => {
  const { context, page, errors } = await openPage({ failOn: "inner_weather" }, { width: 390, colorScheme: "dark" });
  await fillAndRun(page);
  await page.waitForFunction(() => document.getElementById("run-status").textContent.includes("Dừng ở bước inner_weather"));
  const card = page.locator('[data-stage="inner_weather"]');
  assert.equal(await card.getAttribute("data-status"), "failed");
  assert.match(await card.textContent(), /giới hạn sử dụng Claude/);
  assert.equal(await page.locator('#stages > li[data-status="pending"]').count(), 4);
  assert.ok(await page.isHidden("#final"), "chưa có bản biên tập thì không hiện khung Bản nháp");
  await noHorizontalScroll(page);
  await shot(page, "error-390-dark");
  await page.evaluate(() => { window.__config.failOn = null; });
  await card.getByRole("button", { name: "Chạy lại bước này" }).click();
  await page.waitForFunction(() => document.getElementById("run-status").textContent.includes("Xong cả 6 bước"));
  assert.deepEqual(errors, []);
  await context.close();
});

test("bấm Dừng khi đang viết: giữ phần đã viết, trạng thái đã dừng", { skip }, async () => {
  const { context, page } = await openPage({ holdOn: "moment_writer" });
  await fillAndRun(page);
  await page.waitForSelector("#live-moment_writer");
  assert.match(await page.textContent("#live-moment_writer"), /Đang viết dở/);
  assert.ok(await page.isDisabled("#raw-notes"));
  await page.click("#stop");
  await page.waitForFunction(() => document.getElementById("run-status").textContent.includes("Đã dừng ở bước moment_writer"));
  const card = page.locator('[data-stage="moment_writer"]');
  assert.match(await card.textContent(), /Đã dừng theo yêu cầu/);
  assert.match(await card.textContent(), /Phần đã viết được/);
  assert.ok(await page.isEnabled("#raw-notes"));
  await context.close();
});

test("chạy từng bước: dừng sau mỗi bước, bấm tiếp để chạy bước sau", { skip }, async () => {
  const { context, page } = await openPage();
  await page.check("#pace-step");
  await fillAndRun(page);
  await page.waitForFunction(() => document.getElementById("run-status").textContent.includes("Đã xong 1/6"));
  assert.ok(!(await page.isHidden("#next")));
  assert.match(await page.textContent("#next"), /Thời tiết bên trong/);
  await page.click("#next");
  await page.waitForFunction(() => document.getElementById("run-status").textContent.includes("Đã xong 2/6"));
  assert.equal((await page.evaluate(() => window.__calls)).length, 2);
  await context.close();
});

test("bị hạ hạng và bị cắt: hiện cảnh báo trên bước", { skip }, async () => {
  const { context, page } = await openPage({ downgradeOn: "sensory_capture", truncateOn: "gentle_witness" });
  await fillAndRun(page);
  await page.waitForFunction(() => document.getElementById("run-status").textContent.includes("Xong"));
  assert.match(await page.textContent('[data-stage="sensory_capture"] .meta'), /bị hạ xuống hạng default/);
  assert.match(await page.textContent('[data-stage="inner_weather"] .meta'), /đúng model/);
  assert.match(await page.textContent('[data-stage="gentle_witness"]'), /giới hạn độ dài/);
  await context.close();
});

test("đổi sang Deep: 7 bước, độ dài mặc định 1200-1800 từ, kết quả cũ không bị xóa", { skip }, async () => {
  const { context, page } = await openPage();
  await fillAndRun(page);
  await page.waitForFunction(() => document.getElementById("run-status").textContent.includes("Xong"));
  await page.click("#mode-deep");
  assert.equal(await page.inputValue("#desired-length"), "1200-1800 từ");
  assert.equal(await page.locator("#stages > li").count(), 6, "vẫn hiển thị lần chạy moment");
  await page.click("#run");
  assert.equal(await page.textContent("#run"), "Bấm lần nữa để chạy mới");
  await page.click("#run");
  await page.waitForFunction(() => document.getElementById("run-status").textContent.includes("Xong cả 7 bước"));
  assert.match(await page.textContent("#final-meta"), /edited_blog\.md/);
  await context.close();
});

test("bản nháp form được giữ khi tải lại trang", { skip }, async () => {
  const { context, page } = await openPage();
  await page.click("#mode-deep");
  await page.fill("#raw-notes", "Ghi chú dang dở 🌿");
  await page.waitForTimeout(600);
  await page.reload();
  await page.waitForFunction(() => !document.getElementById("chip-claude").textContent.includes("đang kiểm tra"));
  assert.equal(await page.inputValue("#raw-notes"), "Ghi chú dang dở 🌿");
  assert.equal(await page.getAttribute("#mode-deep", "aria-pressed"), "true");
  assert.equal(await page.locator("#stages > li").count(), 7);
  await context.close();
});

test("thiếu input: báo ngay, không gọi Claude", { skip }, async () => {
  const { context, page } = await openPage();
  await page.click("#run");
  assert.match(await page.textContent("#form-note"), /ghi chú thô/);
  assert.equal((await page.evaluate(() => window.__calls)).length, 0);
  await context.close();
});

for (const [name, config, message] of [
  ["sample trả null", { noSample: true }, /Không gọi được Claude/],
  ["không có window.claude", { noClaude: true }, /cần được mở trong claude\.ai/],
]) {
  test(`không có Claude (${name}): trang vẫn hiển thị, nút chạy bị khóa`, { skip }, async () => {
    const { context, page, errors } = await openPage(config, { width: 390 });
    assert.match(await page.textContent("#banner"), message);
    assert.ok(await page.isDisabled("#run"));
    assert.equal(await page.locator("#stages > li").count(), 6);
    await noHorizontalScroll(page);
    assert.deepEqual(errors, []);
    await context.close();
  });
}
