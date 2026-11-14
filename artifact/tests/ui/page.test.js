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

import { createFakeDb } from "../js/fake_db.js";
import { ARTIFACT_DIR } from "../js/helpers.js";

const JSZIP_URL = "https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js";

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
let buildInfo;
let jszipPath = null;

before(async () => {
  if (skip) return;
  workDir = mkdtempSync(join(tmpdir(), "artifact-ui-"));
  const out = join(workDir, "index.html");
  execFileSync(process.env.PYTHON || "python3", [join(ARTIFACT_DIR, "build_html.py"), "--out", out], { stdio: "pipe" });
  const body = readFileSync(out, "utf8");
  bundle = JSON.parse(body.match(/<script type="application\/json" id="bundle-data">([\s\S]*?)<\/script>/)[1]);
  buildInfo = JSON.parse(body.match(/<script type="application\/json" id="build-info">([\s\S]*?)<\/script>/)[1]);
  // JSZip được trang nạp từ cdnjs; test phục vụ bản tải sẵn. Không tải được thì bỏ qua test zip.
  try {
    execFileSync("curl", ["-sSfL", "-o", join(workDir, "jszip.min.js"), JSZIP_URL], { stdio: "pipe", timeout: 30000 });
    jszipPath = join(workDir, "jszip.min.js");
  } catch (_) {
    jszipPath = null;
  }
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
  // db giả lưu trong window.name: ghi đồng bộ và còn nguyên khi tải lại trong cùng tab.
  // (localStorage/sessionStorage được Chromium ghi xuống bất đồng bộ, nên tải lại ngay sau khi
  // ghi có thể đọc ra dữ liệu cũ.) Mỗi kịch bản có context riêng nên dữ liệu không lẫn nhau.
  const readAll = () => {
    try {
      return JSON.parse(window.name || "{}");
    } catch (_) {
      return {};
    }
  };
  const writeAll = (all) => { window.name = JSON.stringify(all); };
  window.__flag = (key, value) => {
    const all = readAll();
    if (value === undefined) return all[key];
    all[key] = value;
    writeAll(all);
    return value;
  };
  const read = () => new Map(readAll().db || []);
  const write = (map) => { const all = readAll(); all.db = [...map]; writeAll(all); };
  const storage = {
    get: (k) => read().get(k),
    has: (k) => read().has(k),
    set: (k, v) => { const m = read(); m.set(k, v); write(m); },
    delete: (k) => { const m = read(); m.delete(k); write(m); },
    keys: () => read().keys(),
  };
  const never = () => new Promise(() => {});
  const db = config.hangDb
    ? { doc: () => ({ collection: () => ({ orderBy: () => ({ limit: () => ({ get: never }) }), doc: () => ({ get: never }) }) }) }
    : window.__createFakeDb({ storage, failOn: config.dbFailStages ? (op, path) => op === "set" && path.includes("/stages/") : null });
  const user = { id: async () => "u_test_owner", isOwner: async () => true };
  const sample = async (prompt, options) => {
    const cfg = window.__config;
    // Learning prompt chứa YAML của workflow (có "- id: ..."), nên nhận diện nó trước.
    const id = prompt.startsWith("Bạn đang chạy learning loop")
      ? "editorial_learning"
      : prompt.startsWith("Chuyển editorial learning report")
        ? "workflow_tuning"
        : /\n- id: (\S+)/.exec(prompt)[1];
    window.__calls.push({ id, model: options.model, effort: options.effort, tier: options.modelTier, cache: options.cache });
    await new Promise((resolve) => setTimeout(resolve, 20));
    if (cfg.failOn === id) throw { code: "rate_limited", message: "Đã chạm giới hạn." };
    if (cfg.holdOn === id && !window.__flag("held")) {
      window.__flag("held", true);
      options.onText({ text: "## Artifact\n\nĐang viết dở…", delta: "" });
      await new Promise((resolve, reject) => {
        options.signal.addEventListener("abort", () => reject({ code: "cancelled", message: "Đã dừng.", text: "## Artifact\n\nĐang viết dở…" }));
      });
    }
    if (id === "editorial_learning" || id === "workflow_tuning") {
      const text = id === "editorial_learning" ? "# Báo cáo học\n\n- Người viết thêm chi tiết lá bàng." : "## breath_editor\n- Giữ chi tiết đời thường.";
      options.onText({ text, delta: text });
      return { text, truncated: false, modelTierApplied: options.modelTier, modelApplied: options.model };
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
  const downloads = {
    save: async (request) => {
      let base64 = null;
      if (request.data instanceof Blob) {
        const bytes = new Uint8Array(await request.data.arrayBuffer());
        let binary = "";
        for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
        base64 = btoa(binary);
      }
      window.__downloads.push({ filename: request.filename, data: typeof request.data === "string" ? request.data : null, base64 });
    },
  };
  const noSample = config.noSample || Boolean(window.__flag("noSample"));
  const capabilities = { sample: noSample ? null : sample, downloads, db: config.noDb ? null : db, user };
  window.claude = { use: async (name) => capabilities[name] ?? null };
}

async function openPage(config = {}, { width = 1280, colorScheme = "light" } = {}) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, colorScheme, deviceScaleFactor: 1 });
  await context.route("**/*", (route) => {
    const url = route.request().url();
    if (url.startsWith("file:")) return route.continue();
    if (url === JSZIP_URL && jszipPath) return route.fulfill({ path: jszipPath, contentType: "application/javascript" });
    return route.abort();
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.addInitScript({ content: `window.__createFakeDb = ${createFakeDb.toString()};` });
  await page.addInitScript(fakeClaude, config);
  await page.goto(pageUrl);
  await ready(page);
  return { context, page, errors };
}

async function ready(page) {
  await page.waitForFunction(() => !document.getElementById("chip-storage").textContent.includes("đang kiểm tra"));
  await page.waitForFunction(() => !document.getElementById("history-note").textContent.startsWith("Đang tải"));
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
    assert.equal(await page.textContent("#chip-storage"), "Lưu trữ: sẵn sàng");
    assert.ok((await page.textContent("#chip-build")).startsWith(`Phiên bản: ${buildInfo.build_id}`));
    if (buildInfo.commit_date) assert.match(await page.textContent("#chip-build"), / · \d{2}\/\d{2}\/\d{4}$/);
    assert.equal(await page.textContent("#history-note"), "Chưa có lần chạy nào được lưu.");
    assert.ok(await page.isHidden("#run-actions"));
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
  // Chờ chữ đang viết (phần tử cùng id hiện "Đang suy nghĩ…" trước khi có chữ).
  await page.waitForFunction(() => /Đang viết dở/.test(document.getElementById("live-moment_writer")?.textContent || ""));
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
  await ready(page);
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

const doneAll = (page, total) =>
  page.waitForFunction((n) => document.getElementById("run-status").textContent.includes(`Xong cả ${n} bước`), total);

test("lưu lịch sử: tải lại trang vẫn còn, mở lại xem đủ kết quả mà không gọi lại Claude", { skip }, async () => {
  const { context, page, errors } = await openPage({}, { width: 390 });
  await page.selectOption("#style", "va-natural");
  await fillAndRun(page);
  await doneAll(page, 6);
  await page.waitForFunction(() => document.querySelectorAll("#history li").length === 1);
  const item = page.locator("#history button").first();
  assert.match(await item.textContent(), /Chiều mưa/);
  assert.match(await item.textContent(), /Xong 6\/6/);
  assert.equal(await item.getAttribute("aria-current"), "true");
  await page.reload();
  await ready(page);
  assert.equal(await page.locator("#history li").count(), 1);
  await page.locator("#history button").first().click();
  await doneAll(page, 6);
  assert.equal(await page.locator('#stages > li[data-status="completed"]').count(), 6);
  assert.match(await page.textContent("#final-text"), /Mưa rơi trên mái tôn/);
  assert.equal((await page.evaluate(() => window.__calls)).length, 0);
  await noHorizontalScroll(page);
  await shot(page, "history-390-light");
  assert.deepEqual(errors, []);
  await context.close();
});

test("lần chạy bị gián đoạn: mở lại từ lịch sử và chạy tiếp các bước còn lại", { skip }, async () => {
  const { context, page } = await openPage({ holdOn: "moment_writer" });
  await fillAndRun(page);
  // Chờ chữ đang viết hiện ra: lúc đó Claude giả đã ghi cờ "đã treo" nên lần mở lại không treo nữa.
  await page.waitForFunction(() => /Đang viết dở/.test(document.getElementById("live-moment_writer")?.textContent || ""));
  await page.reload();
  await ready(page);
  const item = page.locator("#history button").first();
  assert.match(await item.textContent(), /Đang dở 3\/6/);
  await item.click();
  await page.waitForFunction(() => !document.getElementById("next").hidden);
  assert.equal(await page.textContent("#next"), "Chạy tiếp tới hết");
  await page.click("#next");
  await doneAll(page, 6);
  assert.deepEqual((await page.evaluate(() => window.__calls)).map((c) => c.id), ["moment_writer", "breath_editor", "gentle_witness"]);
  await page.waitForFunction(() => /Xong 6\/6/.test(document.querySelector("#history button").textContent));
  await context.close();
});

test("tải zip: đúng bố cục thư mục run của engine", { skip: skip || (jszipPath ? false : "Không tải được JSZip để test") }, async () => {
  const { context, page } = await openPage();
  await page.selectOption("#style", "va-natural");
  await fillAndRun(page);
  await doneAll(page, 6);
  assert.ok(!(await page.isHidden("#run-actions")));
  await page.click("#download-zip");
  await page.waitForFunction(() => window.__downloads.length === 1);
  const download = (await page.evaluate(() => window.__downloads))[0];
  assert.match(download.filename, /^\d{8}_\d{6}_\d{6}_[0-9a-f]{8}_moment_va-natural_chiều-mưa\.zip$/);
  const zipPath = join(workDir, "run.zip");
  writeFileSync(zipPath, Buffer.from(download.base64, "base64"));
  const names = JSON.parse(execFileSync(process.env.PYTHON || "python3", ["-c", "import json,sys,zipfile;print(json.dumps(zipfile.ZipFile(sys.argv[1]).namelist()))", zipPath], { encoding: "utf8" }));
  const folder = download.filename.replace(/\.zip$/, "");
  for (const file of ["input.md", "metadata.json", "step_outputs.json", "run_log.md", "handoff_log.md", "moment_edited.md", "edit_log.md", "witness_report.md"]) {
    assert.ok(names.includes(`${folder}/${file}`), file);
  }
  await context.close();
});

test("lỗi lưu trữ: báo rõ, lần chạy vẫn hoàn tất", { skip }, async () => {
  const { context, page } = await openPage({ dbFailStages: true });
  await fillAndRun(page);
  await doneAll(page, 6);
  assert.ok(!(await page.isHidden("#persist-note")));
  assert.match(await page.textContent("#persist-note"), /Không lưu được bước .*tải zip/);
  await context.close();
});

test("không có quyền lưu trữ: vẫn chạy được, báo không có lịch sử", { skip }, async () => {
  const { context, page, errors } = await openPage({ noDb: true });
  assert.equal(await page.textContent("#chip-storage"), "Lưu trữ: không khả dụng");
  assert.match(await page.textContent("#history-note"), /không có quyền lưu trữ/);
  await fillAndRun(page);
  await doneAll(page, 6);
  assert.equal(await page.locator("#history li").count(), 0);
  assert.ok(!(await page.isDisabled("#download-run")));
  assert.deepEqual(errors, []);
  await context.close();
});

test("lịch sử không phản hồi: sau 10 giây báo chưa tải được, trang vẫn dùng được", { skip, timeout: 30000 }, async () => {
  // openPage chờ ghi chú lịch sử rời trạng thái "Đang tải", tức là chờ hết 10 giây.
  const { context, page } = await openPage({ hangDb: true });
  assert.match(await page.textContent("#history-note"), /chưa phản hồi sau 10 giây/);
  assert.ok(await page.isEnabled("#run"));
  await context.close();
});

const EDITED = "# Chiều mưa\n\nMưa rơi trên mái tôn, chiếc lá bàng rơi nghiêng chạm vũng nước 🌧️. Mình ngồi yên.";

async function finishRun(page) {
  await page.selectOption("#style", "va-natural");
  await fillAndRun(page);
  await doneAll(page, 6);
}

test("bản cuối: khởi tạo từ bản nháp AI; chưa có hoặc chưa sửa thì không học được", { skip }, async () => {
  const { context, page } = await openPage();
  await finishRun(page);
  assert.equal(await page.inputValue("#production"), await page.textContent("#final-text"));
  assert.ok(await page.isDisabled("#learn-claude"), "chưa sửa gì thì không gọi Claude");
  assert.ok(await page.isEnabled("#learn-offline"));
  assert.match(await page.textContent("#learning-note"), /giống hệt bản nháp AI/);
  await page.fill("#production", "   ");
  assert.ok(await page.isDisabled("#learn-claude"));
  assert.ok(await page.isDisabled("#learn-offline"));
  assert.match(await page.textContent("#learning-note"), /Chưa có bản cuối/);
  await page.click("#production-reset");
  assert.equal(await page.inputValue("#production"), await page.textContent("#final-text"));
  await context.close();
});

test("lưu bản cuối, học qua Claude đúng model; tải lại trang vẫn còn bản cuối và kết quả học", { skip }, async () => {
  const { context, page, errors } = await openPage({}, { width: 390 });
  await finishRun(page);
  await page.fill("#production", EDITED);
  assert.match(await page.textContent("#production-meta"), /chưa lưu/);
  await page.click("#production-save");
  await page.waitForFunction(() => /đã lưu/.test(document.getElementById("production-meta").textContent));
  await page.click("#learn-claude");
  await page.waitForFunction(() => /Đã xong vòng học/.test(document.getElementById("learning-note").textContent));
  const calls = (await page.evaluate(() => window.__calls)).filter((c) => c.id === "editorial_learning" || c.id === "workflow_tuning");
  assert.deepEqual(calls.map((c) => c.id), ["editorial_learning", "workflow_tuning"]);
  for (const call of calls) {
    const expected = bundle.models.learning[call.id];
    assert.deepEqual([call.model, call.effort, call.tier, call.cache], [expected.model, expected.effort, expected.model_tier, false]);
  }
  assert.match(await page.textContent("#learning-report"), /Người viết thêm chi tiết lá bàng/);
  assert.match(await page.textContent("#learning-meta"), /moment · va-natural · so với moment_edited\.md/);
  await noHorizontalScroll(page);
  await shot(page, "learning-390-light");
  await page.reload();
  await ready(page);
  await page.locator("#history button").first().click();
  await page.waitForFunction(() => !document.getElementById("learning-block").hidden);
  assert.equal(await page.inputValue("#production"), EDITED);
  assert.match(await page.textContent("#production-meta"), /đã lưu/);
  assert.match(await page.textContent("#learning-report"), /Người viết thêm chi tiết lá bàng/);
  assert.deepEqual(errors, []);
  await context.close();
});

test("so sánh offline: không gọi Claude, tải kết quả học có nhãn mode và style", { skip }, async () => {
  const { context, page } = await openPage();
  await finishRun(page);
  const before = (await page.evaluate(() => window.__calls)).length;
  await page.fill("#production", EDITED);
  await page.click("#learn-offline");
  await page.waitForFunction(() => /Đã so sánh offline/.test(document.getElementById("learning-note").textContent));
  assert.equal((await page.evaluate(() => window.__calls)).length, before);
  assert.match(await page.textContent("#learning-report"), /^# Báo Cáo Chẩn Đoán Offline \(MOMENT MODE\)/);
  assert.match(await page.textContent("#learning-report"), /\+\+\+ production_blog\.md/);
  assert.match(await page.textContent("#learning-meta"), /không gọi Claude/);
  await page.click("#download-learning");
  await page.waitForFunction(() => window.__downloads.length === 1);
  const download = (await page.evaluate(() => window.__downloads))[0];
  assert.match(download.filename, /^moment_blog_patterns_va-natural_\d{8}_\d{6}_\d{6}\.md$/);
  assert.match(download.data, /^<!-- mode: moment \| style: va-natural \| run: \S+ \| learning: \S+ \| offline -->/);
  await context.close();
});

test("zip có production_blog.md và thư mục learning của engine", { skip: skip || (jszipPath ? false : "Không tải được JSZip để test") }, async () => {
  const { context, page } = await openPage();
  await finishRun(page);
  await page.fill("#production", EDITED);
  await page.click("#learn-offline");
  await page.waitForFunction(() => /Đã so sánh offline/.test(document.getElementById("learning-note").textContent));
  await page.click("#download-zip");
  await page.waitForFunction(() => window.__downloads.length === 1);
  const download = (await page.evaluate(() => window.__downloads))[0];
  const zipPath = join(workDir, "learned.zip");
  writeFileSync(zipPath, Buffer.from(download.base64, "base64"));
  const names = JSON.parse(execFileSync(process.env.PYTHON || "python3", ["-c", "import json,sys,zipfile;print(json.dumps(zipfile.ZipFile(sys.argv[1]).namelist()))", zipPath], { encoding: "utf8" }));
  const folder = download.filename.replace(/\.zip$/, "");
  assert.ok(names.includes(`${folder}/production_blog.md`));
  assert.ok(names.some((name) => /\/learning\/moment\/\d{8}_\d{6}_\d{6}\/moment_blog_patterns\.md$/.test(name)));
  await context.close();
});

test("học qua Claude bị lỗi: báo lỗi theo mã, không lưu kết quả rỗng", { skip }, async () => {
  const { context, page } = await openPage({ failOn: "editorial_learning" });
  await finishRun(page);
  await page.fill("#production", EDITED);
  await page.click("#learn-claude");
  await page.waitForFunction(() => /Vòng học lỗi/.test(document.getElementById("learning-note").textContent));
  assert.match(await page.textContent("#learning-note"), /giới hạn sử dụng Claude/);
  assert.ok(await page.isHidden("#learning-block"));
  await context.close();
});

test("mở lại run khi không có Claude: nút học qua Claude bị khóa, so sánh offline vẫn chạy", { skip }, async () => {
  const { context, page } = await openPage();
  await finishRun(page);
  // Lần mở sau không có capability sample (dữ liệu db giả trong window.name vẫn còn).
  await page.evaluate(() => window.__flag("noSample", true));
  await page.reload();
  await ready(page);
  assert.equal(await page.textContent("#chip-claude"), "Claude: không khả dụng");
  await page.locator("#history button").first().click();
  await page.waitForFunction(() => !document.getElementById("final").hidden);
  await page.fill("#production", EDITED);
  assert.ok(await page.isDisabled("#learn-claude"));
  assert.match(await page.textContent("#learning-note"), /Học qua Claude cần mở trang trong claude\.ai/);
  await page.click("#learn-offline");
  await page.waitForFunction(() => /Đã so sánh offline/.test(document.getElementById("learning-note").textContent));
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
