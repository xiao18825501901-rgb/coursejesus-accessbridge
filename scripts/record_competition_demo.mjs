import fs from "node:fs";
import path from "node:path";

import { chromium } from "@playwright/test";

const repositoryRoot = process.cwd();
const evidenceDirectory = path.join(repositoryRoot, "evidence");
const screenshotDirectory = path.join(evidenceDirectory, "screenshots");
const baseUrl = "http://127.0.0.1:15273/ui-extension/";
const chromeExecutable = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

fs.mkdirSync(evidenceDirectory, { recursive: true });
fs.mkdirSync(screenshotDirectory, { recursive: true });

const browser = await chromium.launch({
  executablePath: chromeExecutable,
  headless: true,
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  recordVideo: {
    dir: path.join(evidenceDirectory, "video-build"),
    size: { width: 1440, height: 900 },
  },
});
const page = await context.newPage();
const cues = [];
const recordingStartedAt = Date.now();

function timestamp(milliseconds) {
  const value = Math.max(0, Math.round(milliseconds));
  const hours = Math.floor(value / 3_600_000);
  const minutes = Math.floor((value % 3_600_000) / 60_000);
  const seconds = Math.floor((value % 60_000) / 1_000);
  const millis = value % 1_000;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")},${String(millis).padStart(3, "0")}`;
}

async function installCaption() {
  await page.evaluate(() => {
    const existing = document.getElementById("demo-recording-caption");
    if (existing) return;
    const caption = document.createElement("div");
    caption.id = "demo-recording-caption";
    caption.setAttribute("aria-live", "off");
    Object.assign(caption.style, {
      position: "fixed",
      left: "50%",
      bottom: "26px",
      transform: "translateX(-50%)",
      zIndex: "2147483647",
      width: "min(1040px, calc(100vw - 48px))",
      boxSizing: "border-box",
      padding: "14px 22px",
      border: "2px solid rgba(255,255,255,.9)",
      borderRadius: "12px",
      background: "rgba(10, 24, 32, .94)",
      color: "#fff",
      font: "600 22px/1.35 Arial, sans-serif",
      textAlign: "center",
      boxShadow: "0 8px 30px rgba(0,0,0,.35)",
    });
    document.body.appendChild(caption);
  });
}

async function caption(text, holdSeconds) {
  await installCaption();
  const startedAt = Date.now() - recordingStartedAt;
  await page.evaluate((value) => {
    const node = document.getElementById("demo-recording-caption");
    if (node) node.textContent = value;
  }, text);
  await page.waitForTimeout(holdSeconds * 1_000);
  const endedAt = Date.now() - recordingStartedAt;
  cues.push({ startedAt, endedAt, text });
}

async function highlight(selector, milliseconds = 1_800) {
  await page.evaluate((targetSelector) => {
    const node = document.querySelector(targetSelector);
    if (!node) return;
    node.dataset.demoOutline = "true";
    node.style.outline = "4px solid #f7b32b";
    node.style.outlineOffset = "4px";
    node.scrollIntoView({ block: "center" });
  }, selector);
  await page.waitForTimeout(milliseconds);
  await page.evaluate((targetSelector) => {
    const node = document.querySelector(targetSelector);
    if (!node) return;
    node.style.outline = "";
    node.style.outlineOffset = "";
  }, selector);
}

try {
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.getByRole("heading", { level: 1, name: "控制面板" }).waitFor();

  await caption(
    "CourseJesus — AccessBridge: the real CourseJesus shell with an isolated public learning route.",
    8,
  );
  await caption(
    "This is an anonymous guest workspace. The public synthetic course is visible and management actions are hidden.",
    9,
  );
  await highlight(".course-card", 2_000);
  await caption(
    "The private control course is not returned. Guests cannot create, import, administer, or claim a real learner identity.",
    9,
  );

  await page
    .getByRole("navigation", { name: "主导航" })
    .getByRole("button", { name: "学习", exact: true })
    .click();
  await page
    .getByRole("heading", { level: 1, name: "AccessBridge 分步学习" })
    .waitFor();
  await caption(
    "The integrated Learn route adds three original bilingual lessons: stack/queue, graph search, and matrix transforms.",
    9,
  );

  await page.getByRole("button", { name: /矩阵变换/ }).click();
  await page.getByRole("heading", { level: 2, name: "矩阵变换" }).waitFor();
  await caption(
    "The matrix visual is computed from homogeneous column vectors: scale, then rotate, then translate.",
    9,
  );
  await highlight(".accessbridge-equivalence", 1_800);
  await caption(
    "The forward result is (1,3) and the reverse-order control ends at (-2,4). The answers come from the calculation.",
    9,
  );

  const source = page.getByText(/查看来源 AB-S1/).first();
  await source.click();
  await caption(
    "Source disclosure stays next to the teaching claim, so learners can inspect the basis instead of accepting an opaque answer.",
    8,
  );

  await page
    .getByRole("group", { name: /将 \(1,0\) 放大 2 倍/ })
    .getByRole("radio", { name: "(0,2)", exact: true })
    .check();
  await page
    .getByRole("group", { name: /再将 \(0,2\) 平移/ })
    .getByRole("radio", { name: "(1,3)", exact: true })
    .check();
  await page
    .getByRole("group", { name: /反序执行平移、旋转、缩放/ })
    .getByRole("radio", { name: "(-2,4)", exact: true })
    .check();
  await page.getByRole("button", { name: "检查答案" }).click();
  await page.locator(".accessbridge-practice p.correct").nth(2).waitFor();
  await caption(
    "Three short checks provide answer-specific reasoning. This is practice evidence, not an official CourseJesus grade.",
    9,
  );

  const accountButton = page
    .getByRole("navigation", { name: "主导航" })
    .getByRole("button", { name: "账户", exact: true });
  await accountButton.click();
  await page
    .getByRole("dialog", { name: "账户面板" })
    .getByRole("button", { name: "English" })
    .click();
  await page.getByRole("button", { name: "Close sidebar" }).click();
  await page.locator(".accessbridge-text-toggle").click();
  await page
    .getByRole("heading", { level: 1, name: "AccessBridge stepped learning" })
    .waitFor();
  await caption(
    "The same control changes interface, lesson, and practice language. Large text is an explicit learner choice.",
    8,
  );

  const downloadPromise = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download this offline practice" })
    .click();
  const download = await downloadPromise;
  const offlinePath = path.join(
    screenshotDirectory,
    "AccessBridge_matrix-transform_en.html",
  );
  await download.saveAs(offlinePath);
  await page.screenshot({
    path: path.join(screenshotDirectory, "final-demo-accessbridge-en.png"),
    fullPage: true,
  });
  await caption(
    "The selected lesson exports as one self-contained HTML file with no remote dependency, score write-back, or offline-AI claim.",
    9,
  );

  await page.goto(`file:///${offlinePath.replaceAll("\\", "/")}`);
  await caption(
    "With network access disabled, the downloaded practice still explains the transform and checks all three answers.",
    9,
  );

  await page.setContent(`<!doctype html>
    <html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
    <style>
      body{margin:0;min-height:100vh;display:grid;place-items:center;background:#102631;color:#f7faf9;font:22px/1.5 Arial,sans-serif}
      main{max-width:1050px;padding:56px 64px;border:2px solid #9dd8d0;border-radius:20px;background:#173540}
      h1{font-size:52px;line-height:1.08;margin:0 0 24px;color:#fff}p{margin:16px 0}code{color:#f7d784}
      .small{color:#c8d7dc;font-size:18px}
    </style></head><body><main>
      <h1>Verified locally. Boundaries stay visible.</h1>
      <p>Real production build + FastAPI UI extension + Google Chrome.</p>
      <p>Zero axe WCAG A/AA violations on tested surfaces; not full WCAG certification.</p>
      <p>Two guest contexts are isolated; authenticated production accounts and the owner-created representative course are still unverified.</p>
      <p class="small">No live Qwen, ComfyUI, EAS, GPU, production RAG/Agent, human review, or learning-outcome claim.</p>
    </main></body></html>`);
  await caption(
    "The local evidence covers build, tests, browser accessibility, and guest isolation. It does not claim the unverified production flow.",
    12,
  );

  await page.setContent(`<!doctype html>
    <html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
    <style>
      body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0b1d26;color:#eef5f4;font-family:Arial,sans-serif}
      main{max-width:1050px;padding:62px;border-radius:20px;background:#15333f;border:2px solid #f1b84b}
      h1{font-size:54px;margin:0 0 24px}p{font-size:24px;line-height:1.5}.status{color:#f6cf75}.small{color:#bfd0d5;font-size:18px}
    </style></head><body><main>
      <h1>CourseJesus — AccessBridge</h1>
      <p class="status">PARTIAL · Verified locally · NOT_SUBMITTED</p>
      <p>Next gate: owner creates one representative course and knowledge point, then the team records a truthful live/current generation and practice E2E.</p>
      <p class="small">Source publishes with rights retained. Third-party licenses remain intact.</p>
    </main></body></html>`);
  await caption(
    "Current status is partial and not submitted. The next concrete gate is the owner-created representative course and a live three-mode end-to-end record.",
    11,
  );
} finally {
  const video = page.video();
  await page.close();
  await context.close();
  await browser.close();

  if (video) {
    const recordedPath = await video.path();
    fs.copyFileSync(recordedPath, path.join(evidenceDirectory, "demo-raw.webm"));
  }

  const srt = cues
    .map(
      (cue, index) =>
        `${index + 1}\n${timestamp(cue.startedAt)} --> ${timestamp(cue.endedAt)}\n${cue.text}\n`,
    )
    .join("\n");
  fs.writeFileSync(
    path.join(evidenceDirectory, "demo-captions.srt"),
    srt.trim() + "\n",
    "utf8",
  );
}
