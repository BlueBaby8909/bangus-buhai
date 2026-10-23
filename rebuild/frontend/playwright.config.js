import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  retries: 0,
  outputDir: "../.verification/browser-results",
  reporter: [["list"]],
  globalTeardown: "./e2e/teardown.js",
  use: {
    baseURL: "http://127.0.0.1:5189",
    channel: "msedge",
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command:
        "backend\\.venv\\Scripts\\python.exe -m backend.tests.browser_server",
      cwd: "..",
      url: "http://127.0.0.1:8019/health",
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command: "npm run dev -- --port 5189",
      url: "http://127.0.0.1:5189",
      env: { BB_API_PROXY_TARGET: "http://127.0.0.1:8019" },
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],
});
