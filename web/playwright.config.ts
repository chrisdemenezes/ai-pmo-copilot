import fs from "fs";
import { defineConfig, devices } from "@playwright/test";

const PORT = 3100;
const MOCK_BACKEND_PORT = 4100;

// W7-5 Etapa 6: lets `smoke.spec.ts` target a real environment (e.g.
// staging) instead of always being pinned to `localhost:3100`. Unset by
// default -- every existing spec keeps running exactly as before, against
// the local dev server + mock backend below.
const EXTERNAL_BASE_URL = process.env.PLAYWRIGHT_BASE_URL;

// This exact path only exists in this project's preconfigured sandbox images
// (see AGENTS.md system prompt); CI and other machines fall back to whatever
// Chromium `npx playwright install` puts on PATH for them.
const SANDBOX_CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const launchOptions = fs.existsSync(SANDBOX_CHROMIUM) ? { executablePath: SANDBOX_CHROMIUM } : {};

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: EXTERNAL_BASE_URL ?? `http://localhost:${PORT}`,
  },
  // When PLAYWRIGHT_BASE_URL points at a real environment, Playwright must
  // run against it as-is -- never spin up a local dev server/mock backend
  // that would shadow it.
  webServer: EXTERNAL_BASE_URL
    ? undefined
    : [
        {
          command: "node e2e/mock-backend.mjs",
          port: MOCK_BACKEND_PORT,
          env: { MOCK_BACKEND_PORT: String(MOCK_BACKEND_PORT) },
          reuseExistingServer: !process.env.CI,
        },
        {
          command: `npx next dev -p ${PORT}`,
          port: PORT,
          env: {
            BACKEND_URL: `http://localhost:${MOCK_BACKEND_PORT}`,
            API_KEY: "e2e-secret-key",
            SESSION_SECRET: "e2e-session-secret-not-for-production",
          },
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
      ],
  projects: [
    {
      name: "mobile",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 375, height: 812 },
        launchOptions,
      },
    },
    {
      name: "md",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 900, height: 800 },
        launchOptions,
      },
    },
    {
      name: "lg",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 900 },
        launchOptions,
      },
    },
  ],
});
