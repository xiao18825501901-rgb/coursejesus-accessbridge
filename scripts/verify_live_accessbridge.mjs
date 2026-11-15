import fs from "node:fs";
import path from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { chromium } from "@playwright/test";

const root = path.resolve(import.meta.dirname, "..");
const evidenceDirectory = path.join(root, "evidence");
const screenshotsDirectory = path.join(evidenceDirectory, "screenshots");
const liveUrl =
  process.env.COMPETITION_LIVE_URL ||
  "https://coursejesus-accessbridge.netlify.app/";
const deployId = process.env.NETLIFY_DEPLOY_ID || null;
const chromeExecutable =
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

fs.mkdirSync(screenshotsDirectory, { recursive: true });

const browser = await chromium.launch({
  executablePath: chromeExecutable,
  headless: true,
});
const context = await browser.newContext({ acceptDownloads: true });
const page = await context.newPage();
const consoleErrors = [];
const pageErrors = [];
const failedRequests = [];
const apiRequests = [];

page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", (error) => pageErrors.push(error.message));
page.on("requestfailed", (request) => {
  failedRequests.push({
    url: request.url(),
    failure: request.failure()?.errorText || "unknown",
  });
});
page.on("request", (request) => {
  const url = new URL(request.url());
  if (
    url.pathname.includes("/ui-extension/api/") ||
    url.pathname.startsWith("/api/")
  ) {
    apiRequests.push(request.url());
  }
});

await page.setViewportSize({ width: 1280, height: 900 });
const response = await page.goto(liveUrl, {
  waitUntil: "networkidle",
  timeout: 60_000,
});
if (!response) throw new Error("The live page returned no HTTP response.");

await page
  .getByRole("heading", {
    level: 1,
    name: "AccessBridge 分步学习",
  })
  .waitFor();

const lessonButtons = page.locator(".accessbridge-lessons button");
const lessonCount = await lessonButtons.count();
if (lessonCount !== 3) {
  throw new Error(`Expected three lessons; found ${lessonCount}.`);
}

const desktopAccessibility = await new AxeBuilder({ page })
  .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
  .analyze();

await page.screenshot({
  path: path.join(screenshotsDirectory, "live-public-accessbridge.png"),
  fullPage: true,
});

const matrixButton = page.getByRole("button", { name: /矩阵变换/ });
await matrixButton.click();
const matrixHeadingVisible = await page
  .getByRole("heading", { level: 2, name: "矩阵变换" })
  .isVisible();
if (!matrixHeadingVisible) {
  throw new Error("The matrix lesson did not render after selection.");
}

const textToggle = page.locator(".accessbridge-text-toggle");
await textToggle.click();
if ((await textToggle.getAttribute("aria-pressed")) !== "true") {
  throw new Error("The large-text control did not become active.");
}

const sourceCount = await page.locator("details").count();
if (sourceCount < 1) {
  throw new Error("No expandable source disclosure was rendered.");
}

const downloadPromise = page.waitForEvent("download");
await page.getByRole("button", { name: "下载当前课离线练习" }).click();
const download = await downloadPromise;
const downloadedPath = await download.path();
if (!downloadedPath) {
  throw new Error("The offline practice download produced no local file.");
}
const downloadedHtml = fs.readFileSync(downloadedPath, "utf8");
if (!downloadedHtml.startsWith("<!doctype html>")) {
  throw new Error("The offline practice file is not self-contained HTML.");
}

await page.setViewportSize({ width: 390, height: 844 });
const overflow = await page.evaluate(
  () =>
    document.documentElement.scrollWidth -
    document.documentElement.clientWidth,
);
if (overflow > 1) {
  throw new Error(`Live mobile page overflows by ${overflow} CSS pixels.`);
}

const cookies = await context.cookies();
const localStorageKeys = await page.evaluate(() =>
  Object.keys(window.localStorage),
);
const sessionStorageKeys = await page.evaluate(() =>
  Object.keys(window.sessionStorage),
);

const headers = response.headers();
const evidence = {
  schema: "coursejesus.accessed-hacks.live-access.v1",
  status: "VERIFIED_LIVE",
  captured_at: new Date().toISOString(),
  url: liveUrl,
  netlify_site_id: "b1d3fb90-daad-42a3-962b-84608e74c2be",
  deploy_id: deployId,
  anonymous: true,
  http_status: response.status(),
  title: await page.title(),
  heading: await page.getByRole("heading", { level: 1 }).innerText(),
  lesson_count: lessonCount,
  matrix_lesson_rendered: matrixHeadingVisible,
  large_text_toggle_verified: true,
  expandable_source_count: sourceCount,
  offline_download: {
    suggested_filename: download.suggestedFilename(),
    self_contained_html_verified: true,
    bytes: Buffer.byteLength(downloadedHtml),
  },
  mobile_390_horizontal_overflow_css_px: overflow,
  axe: {
    version: (await import("axe-core/package.json", { with: { type: "json" } }))
      .default.version,
    wcag_a_aa_violations: desktopAccessibility.violations.map(
      (violation) => ({
        id: violation.id,
        impact: violation.impact,
        help: violation.help,
      }),
    ),
  },
  auth_state: {
    cookie_count: cookies.length,
    local_storage_keys: localStorageKeys,
    session_storage_keys: sessionStorageKeys,
  },
  console_errors: consoleErrors,
  page_errors: pageErrors,
  failed_requests: failedRequests,
  api_requests: apiRequests,
  security_headers: {
    strict_transport_security: Boolean(headers["strict-transport-security"]),
    x_content_type_options: headers["x-content-type-options"] || null,
    x_frame_options: headers["x-frame-options"] || null,
    referrer_policy: headers["referrer-policy"] || null,
  },
  screenshot: "evidence/screenshots/live-public-accessbridge.png",
  boundary:
    "The public host serves the deterministic API-independent AccessBridge learning surface. The complete FastAPI guest API is verified only in the isolated local runtime.",
};

if (
  response.status() !== 200 ||
  evidence.axe.wcag_a_aa_violations.length !== 0 ||
  consoleErrors.length !== 0 ||
  pageErrors.length !== 0 ||
  failedRequests.length !== 0 ||
  apiRequests.length !== 0
) {
  throw new Error(`Live verification failed:\n${JSON.stringify(evidence, null, 2)}`);
}

fs.writeFileSync(
  path.join(evidenceDirectory, "LIVE_ACCESS_EVIDENCE.json"),
  `${JSON.stringify(evidence, null, 2)}\n`,
);
console.log(JSON.stringify(evidence, null, 2));

await context.close();
await browser.close();
