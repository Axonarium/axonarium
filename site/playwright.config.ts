import { defineConfig, devices } from "@playwright/test";

// The accessibility budget (sprint 3.5, ADR 0025): every page type at phone and desktop sizes, against a production
// build (`npm run build`) that read the deploy's snapshot (snapshot/snapshot.json). Run with `npm run e2e`.
export default defineConfig({
  testDir: "e2e",
  testMatch: "**/*.e2e.ts", // not *.test.ts, which Vitest runs
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  timeout: 60_000, // axe on the explore page's full table takes a while on a CI runner
  reporter: process.env.CI ? [["list"], ["github"]] : "list",
  use: {
    baseURL: "http://localhost:3100",
    // A browser already on the machine, when Playwright's own can't be downloaded (as in some sandboxes).
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined },
  },
  projects: [
    { name: "phone", use: { ...devices["Pixel 7"] } },
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "npm run start -- -p 3100",
    url: "http://localhost:3100",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
