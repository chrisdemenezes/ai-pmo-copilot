import { defineConfig, devices } from "@playwright/test";

const PORT = 3100;
const MOCK_BACKEND_PORT = 4100;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
  },
  webServer: [
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
        WORKSPACE_PASSWORD: "e2e-workspace-password",
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
        launchOptions: { executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" },
      },
    },
    {
      name: "md",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 900, height: 800 },
        launchOptions: { executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" },
      },
    },
    {
      name: "lg",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 900 },
        launchOptions: { executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" },
      },
    },
  ],
});
