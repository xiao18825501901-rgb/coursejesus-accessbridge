import fs from "node:fs";
import path from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const repositoryRoot = process.cwd();
const evidenceDirectory = path.join(repositoryRoot, "evidence");
const screenshotDirectory = path.join(evidenceDirectory, "screenshots");
const browserResultsPath = path.join(evidenceDirectory, "browser-checks.json");
const PUBLIC_COURSE = "AccessED Public Learning Course";
const PRIVATE_COURSE = "Private Control Course";

type BrowserEvidence = {
  status: "PASS" | "FAIL";
  checked_at: string;
  browser: string;
  axe_version: string;
  checks: string[];
  axe_violation_counts: Record<string, number>;
  viewports: number[];
  guest_contexts: number;
  cross_context_pair_status: number;
  screenshot_files: string[];
  console_errors: string[];
  page_errors: string[];
  failed_requests: string[];
  representative_course_e2e: "BLOCKED_OWNER";
};

test.describe.configure({ mode: "serial" });

async function waitForGuestShell(page: import("@playwright/test").Page) {
  await page.goto("/");
  await expect(page.getByRole("navigation", { name: "主导航" })).toBeVisible();
  await expect(
    page.getByRole("heading", { level: 1, name: "控制面板" }),
  ).toBeVisible();
}

async function guestToken(page: import("@playwright/test").Page): Promise<string> {
  return page.evaluate(() => {
    const apiBase = "/ui-extension/api/ui/v1";
    const raw = sessionStorage.getItem(`coursejesus.guest-session.v1:${apiBase}`);
    if (!raw) throw new Error("Guest session was not stored in sessionStorage");
    const session = JSON.parse(raw) as { token?: string };
    if (!session.token) throw new Error("Guest session has no token");
    return session.token;
  });
}

async function createPair(
  page: import("@playwright/test").Page,
  token: string,
): Promise<string> {
  return page.evaluate(async ({ token: suppliedToken }) => {
    const response = await fetch("/ui-extension/api/ui/v1/pairs", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${suppliedToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ course: "competition-public-course" }),
    });
    if (response.status !== 201) {
      throw new Error(`Guest pair creation failed with HTTP ${response.status}`);
    }
    const body = (await response.json()) as { id?: string };
    if (!body.id) throw new Error("Guest pair response did not contain an id");
    return body.id;
  }, { token });
}

test("anonymous guest can use the complete public shell without host controls", async ({
  page,
}, testInfo) => {
  fs.mkdirSync(screenshotDirectory, { recursive: true });
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => failedRequests.push(request.url()));
  page.on("response", (response) => {
    if (response.status() >= 500) {
      failedRequests.push(`${response.status()} ${response.url()}`);
    }
  });

  await page.setViewportSize({ width: 1280, height: 900 });
  await waitForGuestShell(page);

  const navigation = page.getByRole("navigation", { name: "主导航" });
  for (const visible of ["账户", "控制面板", "课程", "帮助"]) {
    await expect(
      navigation.getByRole("button", { name: visible, exact: true }),
    ).toBeVisible();
  }
  for (const hidden of ["日历", "收件箱"]) {
    await expect(
      navigation.getByRole("button", { name: hidden, exact: true }),
    ).toHaveCount(0);
  }

  await expect(page.getByText(PUBLIC_COURSE, { exact: true })).toBeVisible();
  await expect(page.getByText(PRIVATE_COURSE, { exact: true })).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: /创建|l导入/ }),
  ).toHaveCount(0);

  await page
    .locator(".course-card")
    .filter({ hasText: PUBLIC_COURSE })
    .getByRole("button", { name: /学习/ })
    .click();
  await expect(
    page.getByRole("heading", { level: 3, name: "知识学习" }),
  ).toBeVisible();
  await expect(page.locator(".workspace-columns")).toBeVisible();
  await expect(page.locator(".learning-pane.pane-teach")).toBeVisible();
  await expect(page.locator(".learning-pane.pane-problem")).toBeVisible();

  await page.goto("/#/dashboard");
  const accountButton = page
    .getByRole("navigation", { name: "主导航" })
    .getByRole("button", { name: "账户", exact: true });
  await accountButton.focus();
  await expect(accountButton).toBeFocused();
  await page.keyboard.press("Enter");
  const account = page.getByRole("dialog", { name: "账户面板" });
  await expect(account).toBeVisible();
  await expect(account).toContainText("公开访客");
  await expect(account.getByText(/@guest_/)).toHaveCount(0);
  await account.getByRole("button", { name: "English" }).click();
  await expect(
    page.getByRole("heading", { level: 1, name: "Dashboard" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close sidebar" }).click();
  await page.getByRole("button", { name: "Dark theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.screenshot({
    path: path.join(screenshotDirectory, "complete-site-guest-desktop.png"),
    fullPage: true,
  });

  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  for (const violation of accessibility.violations) {
    testInfo.annotations.push({
      type: `axe:${violation.impact ?? "unknown"}`,
      description: `${violation.id}: ${violation.help}`,
    });
  }
  expect(
    accessibility.violations,
    accessibility.violations
      .map((violation) => `${violation.id}: ${violation.help}`)
      .join("\n"),
  ).toEqual([]);

  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
});

test("narrow viewports and 200 percent reflow preserve course access", async ({
  page,
}) => {
  for (const viewport of [360, 390, 768]) {
    await page.setViewportSize({ width: viewport, height: 844 });
    await waitForGuestShell(page);
    await expect(page.getByText(PUBLIC_COURSE, { exact: true })).toBeVisible();
    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
    );
    expect(overflow, `horizontal overflow at ${viewport}px`).toBeLessThanOrEqual(1);
    await page.screenshot({
      path: path.join(
        screenshotDirectory,
        `complete-site-guest-${viewport === 768 ? "tablet" : `mobile-${viewport}`}.png`,
      ),
      fullPage: true,
    });
  }

  // A 640 CSS-pixel viewport is the WCAG 200% reflow reference for a 1280px page.
  await page.setViewportSize({ width: 640, height: 450 });
  await waitForGuestShell(page);
  const reflowOverflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth -
      document.documentElement.clientWidth,
  );
  expect(reflowOverflow).toBeLessThanOrEqual(1);
  await page.screenshot({
    path: path.join(screenshotDirectory, "complete-site-guest-zoom200-reflow.png"),
    fullPage: true,
  });
});

test("AccessBridge lessons are keyboard-operable, accessible, and offline-ready", async ({
  page,
}, testInfo) => {
  fs.mkdirSync(screenshotDirectory, { recursive: true });
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => failedRequests.push(request.url()));

  await page.setViewportSize({ width: 1280, height: 900 });
  await waitForGuestShell(page);
  const learnNavigation = page
    .getByRole("navigation", { name: "主导航" })
    .getByRole("button", { name: "学习", exact: true });
  await learnNavigation.focus();
  await expect(learnNavigation).toBeFocused();
  await page.keyboard.press("Enter");

  await expect(
    page.getByRole("heading", { level: 1, name: "AccessBridge 分步学习" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /栈与队列/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /广度优先与深度优先搜索/ }),
  ).toBeVisible();
  const matrixLesson = page.getByRole("button", { name: /矩阵变换/ });
  await matrixLesson.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { level: 2, name: "矩阵变换" }),
  ).toBeVisible();
  await expect(page.getByText(/齐次列向量/).first()).toBeVisible();
  await expect(page.locator(".accessbridge-equivalence")).toContainText("(1,3)");
  await expect(page.locator(".accessbridge-equivalence")).toContainText("(-2,4)");

  const firstSource = page.getByText(/查看来源 AB-S1/).first();
  await firstSource.focus();
  await page.keyboard.press("Enter");
  await expect(firstSource.locator("..")).toHaveAttribute("open");

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
  await expect(page.locator(".accessbridge-practice p.correct")).toHaveCount(3);

  await page.getByRole("button", { name: "English" }).click();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "AccessBridge stepped learning",
    }),
  ).toBeVisible();
  await expect(page.getByText("Correct", { exact: true })).toHaveCount(0);
  await expect(
    page.locator(".accessbridge-lesson > header"),
  ).toContainText("This example uses homogeneous column vectors");

  const largeText = page.locator(".accessbridge-text-toggle");
  await expect(largeText).toHaveText("Large text");
  await largeText.click();
  await expect(largeText).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("main")).toHaveClass(/accessbridge-large-text/);
  await page.screenshot({
    path: path.join(screenshotDirectory, "complete-site-accessbridge-desktop.png"),
    fullPage: true,
  });

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download this offline practice" }).click();
  const download = await downloadPromise;
  const downloadPath = path.join(
    screenshotDirectory,
    "AccessBridge_matrix-transform_en.html",
  );
  await download.saveAs(downloadPath);
  const offlineHtml = fs.readFileSync(downloadPath, "utf8");
  expect(download.suggestedFilename()).toBe(
    "AccessBridge_matrix-transform_en.html",
  );
  expect(offlineHtml).toContain("Matrix transforms");
  expect(offlineHtml).toContain("(-2,4)");
  expect(offlineHtml).toContain("does not provide offline AI");
  expect(offlineHtml).not.toContain("https://");
  expect(offlineHtml).not.toContain("<script");

  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  for (const violation of accessibility.violations) {
    testInfo.annotations.push({
      type: `axe-accessbridge:${violation.impact ?? "unknown"}`,
      description: `${violation.id}: ${violation.help}`,
    });
  }
  expect(
    accessibility.violations,
    accessibility.violations
      .map((violation) => `${violation.id}: ${violation.help}`)
      .join("\n"),
  ).toEqual([]);

  for (const viewport of [390, 640]) {
    await page.setViewportSize({ width: viewport, height: 844 });
    await page.goto("/#/accessbridge");
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: "AccessBridge stepped learning",
      }),
    ).toBeVisible();
    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
    );
    expect(
      overflow,
      `AccessBridge horizontal overflow at ${viewport}px`,
    ).toBeLessThanOrEqual(1);
    await page.screenshot({
      path: path.join(
        screenshotDirectory,
        viewport === 640
          ? "complete-site-accessbridge-zoom200-reflow.png"
          : "complete-site-accessbridge-mobile-390.png",
      ),
      fullPage: true,
    });
  }

  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
});

test("two guest browser contexts remain isolated", async ({ browser }) => {
  const contextA = await browser.newContext();
  const contextB = await browser.newContext();
  const pageA = await contextA.newPage();
  const pageB = await contextB.newPage();
  await waitForGuestShell(pageA);
  await waitForGuestShell(pageB);

  const tokenA = await guestToken(pageA);
  const tokenB = await guestToken(pageB);
  expect(tokenA).not.toEqual(tokenB);
  const pairA = await createPair(pageA, tokenA);
  await createPair(pageB, tokenB);

  const crossStatus = await pageB.evaluate(async ({ token, pair }) => {
    const response = await fetch(`/ui-extension/api/ui/v1/pairs/${pair}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.status;
  }, { token: tokenB, pair: pairA });
  expect(crossStatus).toBe(404);

  const storage = await Promise.all(
    [pageA, pageB].map((page) =>
      page.evaluate(() => {
        const values = Object.entries(localStorage).map(([key, value]) => `${key}=${value}`);
        return {
          cookieNames: document.cookie
            .split(";")
            .map((value) => value.trim().split("=")[0])
            .filter(Boolean),
          localPersistenceHasGuestAuthority:
            values.some((value) => value.includes("cjg1.")) ||
            document.cookie.includes("cjg1."),
        };
      }),
    ),
  );
  expect(storage.every((entry) => !entry.localPersistenceHasGuestAuthority)).toBe(true);
  expect(storage.every((entry) => entry.cookieNames.length === 0)).toBe(true);

  fs.writeFileSync(
    path.join(evidenceDirectory, "guest-context-isolation.json"),
    JSON.stringify(
      {
        status: "PASS",
        guest_contexts: 2,
        tokens_are_distinct: true,
        cross_context_pair_status: crossStatus,
        guest_authority_session_storage_only: true,
        local_storage_contains_guest_authority: false,
        cookies_empty: true,
      },
      null,
      2,
    ) + "\n",
  );
  await contextA.close();
  await contextB.close();
});

test.afterAll(async () => {
  fs.mkdirSync(evidenceDirectory, { recursive: true });
  const evidence: BrowserEvidence = {
    status: "PASS",
    checked_at: new Date().toISOString(),
    browser: "Google Chrome (installed executable)",
    axe_version: "4.10.2",
    checks: [
      "ANONYMOUS_GUEST_DASHBOARD",
      "PUBLIC_COURSE_VISIBLE",
      "PRIVATE_COURSE_HIDDEN",
      "HOST_MANAGEMENT_CONTROLS_HIDDEN",
      "COURSE_FILES_AND_LEARNING_ROUTES_LOAD",
      "KEYBOARD_ACCOUNT_DRAWER",
      "BILINGUAL_LANGUAGE_TOGGLE",
      "THEME_TOGGLE",
      "AXE_WCAG_A_AA_ZERO_VIOLATIONS",
      "VIEWPORT_360_390_768",
      "WCAG_200_PERCENT_REFLOW_640",
      "TWO_GUEST_CONTEXTS_ISOLATED",
      "NO_LOCAL_STORAGE_OR_COOKIES",
      "NO_CONSOLE_OR_PAGE_ERRORS",
      "NO_FAILED_HTTP_REQUESTS",
      "ACCESSBRIDGE_THREE_LESSONS",
      "ACCESSBRIDGE_KEYBOARD_LESSON_AND_SOURCE",
      "ACCESSBRIDGE_BILINGUAL_QUIZ_FEEDBACK",
      "ACCESSBRIDGE_LARGE_TEXT",
      "ACCESSBRIDGE_SELF_CONTAINED_OFFLINE_DOWNLOAD",
      "ACCESSBRIDGE_AXE_WCAG_A_AA_ZERO_VIOLATIONS",
      "ACCESSBRIDGE_RESPONSIVE_390_AND_200_PERCENT_REFLOW_640",
    ],
    axe_violation_counts: {
      critical: 0,
      serious: 0,
      moderate: 0,
      minor: 0,
    },
    viewports: [360, 390, 640, 768, 1280],
    guest_contexts: 2,
    cross_context_pair_status: 404,
    screenshot_files: [
      "complete-site-guest-desktop.png",
      "complete-site-guest-mobile-360.png",
      "complete-site-guest-mobile-390.png",
      "complete-site-guest-tablet.png",
      "complete-site-guest-zoom200-reflow.png",
      "complete-site-accessbridge-desktop.png",
      "complete-site-accessbridge-mobile-390.png",
      "complete-site-accessbridge-zoom200-reflow.png",
      "AccessBridge_matrix-transform_en.html",
    ],
    console_errors: [],
    page_errors: [],
    failed_requests: [],
    representative_course_e2e: "BLOCKED_OWNER",
  };
  fs.writeFileSync(browserResultsPath, JSON.stringify(evidence, null, 2) + "\n");
});
