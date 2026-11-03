import { defineConfig, devices } from "@playwright/test";

/** Expects the API on :8000 (seeded) and the site on :3000. CI starts both first. */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  retries: 0,
  reporter: [["list"]],
  use: { baseURL: "http://localhost:3000", trace: "retain-on-failure", locale: "en-IN" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
