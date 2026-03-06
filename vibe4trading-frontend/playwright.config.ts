import { defineConfig, devices } from "@playwright/test";

process.env.V4T_E2E_RUN_ID ??= `${Date.now()}-${process.pid}`;

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: {
    timeout: 20_000,
  },
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  globalSetup: require.resolve("./e2e/global-setup"),
  globalTeardown: require.resolve("./e2e/global-teardown"),
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
