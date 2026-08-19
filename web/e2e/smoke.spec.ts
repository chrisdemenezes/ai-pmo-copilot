import { test, expect } from "@playwright/test";

/**
 * W7-5 Etapa 6: minimal post-deploy smoke test, distinct from the full E2E
 * suite (Technical Design S13: "não transformar smoke tests em nova suíte
 * funcional completa"). Runs against whatever `baseURL` is configured --
 * the local dev server by default, or a real environment via
 * `PLAYWRIGHT_BASE_URL` (see playwright.config.ts). No credential is
 * hardcoded: the authenticated check only runs when SMOKE_LOGIN_* env vars
 * are supplied at invocation time, and is skipped otherwise.
 */

const backendUrl = process.env.SMOKE_BACKEND_URL;
const loginEmail = process.env.SMOKE_LOGIN_EMAIL;
const loginPassword = process.env.SMOKE_LOGIN_PASSWORD;
const loginOrganization = process.env.SMOKE_LOGIN_ORGANIZATION;

test.describe("smoke", () => {
  test("the application is reachable", async ({ page }) => {
    const response = await page.goto("/entrar");
    expect(response?.ok()).toBe(true);
    await expect(page.getByRole("button", { name: "Entrar" })).toBeVisible();
  });

  test("the frontend's own health endpoint reports healthy", async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/api/health`);
    expect(response.ok()).toBe(true);
    const body = await response.json();
    expect(body.status).toBe("healthy");
  });

  test("backend readiness is green", async ({ request }) => {
    test.skip(!backendUrl, "SMOKE_BACKEND_URL not set -- skipping backend readiness check");
    const response = await request.get(`${backendUrl}/ready`);
    expect(response.ok()).toBe(true);
    const body = await response.json();
    expect(body.status).toBe("ready");
  });

  test("basic authentication reaches a functional endpoint", async ({ page }) => {
    test.skip(
      !loginEmail || !loginPassword || !loginOrganization,
      "SMOKE_LOGIN_* not set -- skipping authenticated check",
    );
    await page.goto("/entrar");
    await page.getByLabel("Organização").fill(loginOrganization!);
    await page.getByLabel("E-mail").fill(loginEmail!);
    await page.getByLabel("Senha").fill(loginPassword!);
    await page.getByRole("button", { name: "Entrar" }).click();
    await expect(page).not.toHaveURL(/\/entrar/);
  });
});
