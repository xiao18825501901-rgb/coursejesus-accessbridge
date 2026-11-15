import { execFileSync } from "node:child_process";
import path from "node:path";

import { defineConfig } from "@playwright/test";

/**
 * Native-browser acceptance for the complete CourseJesus competition copy.
 *
 * The suite runs the real production web build and the real FastAPI UI
 * extension against a fresh SQLite database. Only identity and model-provider
 * boundaries are synthetic: the browser obtains ordinary signed guest tokens
 * from the application and every course read goes over HTTP.
 */

const repositoryRoot = process.cwd();
const pythonExecutable = path.join(
  repositoryRoot,
  ".venv",
  "Scripts",
  "python.exe",
);
const runId = `${process.pid}-${Date.now()}`;
const dataDirectory = path.join(
  repositoryRoot,
  "runtime",
  `competition-browser-${runId}`,
);
const databasePath = path.join(dataDirectory, "rag.sqlite3");
const uploadDirectory = path.join(dataDirectory, "uploads");
const uiDataDirectory = path.join(dataDirectory, "ui-extension");
const backendUrl = "http://127.0.0.1:15274";
const webUrl = "http://127.0.0.1:15273";
const chromeExecutable = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

execFileSync(
  pythonExecutable,
  [path.join(repositoryRoot, "scripts", "prepare_competition_browser.py"), dataDirectory],
  { cwd: repositoryRoot, stdio: "inherit" },
);

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "competition-public-guest.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  timeout: 180_000,
  expect: { timeout: 25_000 },
  use: {
    baseURL: webUrl,
    browserName: "chromium",
    launchOptions: { executablePath: chromeExecutable },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `"${pythonExecutable}" -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 15274`,
      cwd: path.join(repositoryRoot, "services", "rag-api"),
      env: {
        ...process.env,
        APP_ENV: "test",
        CMUI_ENV: "test",
        V3_ENABLED: "true",
        UI_EXTENSION_ENABLED: "true",
        CMUI_DATA_DIR: uiDataDirectory,
        CMUI_VERIFICATION_SECRET: "competition-browser-verification-secret",
        GUEST_SESSION_SECRET: "competition-browser-guest-session-secret",
        GUEST_SESSION_TTL_SECONDS: "900",
        CMUI_PROVIDER_MODE: "test",
        RAG_PROVIDER_MODE: "deterministic",
        CMUI_ALLOWED_ORIGINS: webUrl,
        WEB_ORIGIN: webUrl,
        AUTH_TEST_USER_ID: "competition-browser-owner",
        ADMIN_USER_IDS: "",
        RAG_DATABASE_PATH: databasePath,
        RAG_UPLOAD_DIR: uploadDirectory,
        VISUAL_ENGINE_ENABLED: "true",
        VISUAL_PROVIDER: "mock",
        VISUAL_AUTO_ENABLED: "false",
        VISUAL_VIDEO_ENABLED: "false",
        AUTO_KNOWLEDGE_MAP_ENABLED: "false",
      },
      url: `${backendUrl}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "ignore",
      stderr: "ignore",
    },
    {
      command: `"${process.execPath}" "${path.join(repositoryRoot, "scripts", "serve_web_dist.mjs")}" "${path.join(repositoryRoot, "apps", "web", "dist")}" 15273`,
      cwd: repositoryRoot,
      env: {
        ...process.env,
        COURSEMATE_API_PROXY: backendUrl,
      },
      url: `${webUrl}/ui-extension/`,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "ignore",
      stderr: "ignore",
    },
  ],
});
