import { test, expect, request as playwrightRequest } from "@playwright/test";

const MOCK_BACKEND_URL = "http://localhost:4100";
const E2E_ORGANIZATION = "e2e-organization";
const E2E_EMAIL = "e2e@stratech.local";
const WORKSPACE_PASSWORD = "e2e-workspace-password";

async function resetFixtures() {
  const ctx = await playwrightRequest.newContext();
  await ctx.post(`${MOCK_BACKEND_URL}/__control/reset-fixtures`);
  await ctx.dispose();
}

async function activeSessionCount(): Promise<number> {
  const ctx = await playwrightRequest.newContext();
  const response = await ctx.get(`${MOCK_BACKEND_URL}/api/admin/sessions`);
  const sessions = (await response.json()) as unknown[];
  await ctx.dispose();
  return sessions.length;
}

async function login(page: import("@playwright/test").Page) {
  await page.goto("/entrar");
  await page.getByLabel("Organização").fill(E2E_ORGANIZATION);
  await page.getByLabel("E-mail").fill(E2E_EMAIL);
  await page.getByLabel("Senha").fill(WORKSPACE_PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL(/\/dashboard/);
}

test.beforeEach(async () => {
  await resetFixtures();
});

/**
 * Logout (W7-7 Etapa 4, Founder Decision, Controlled Pilot Browser
 * Baseline).
 *
 * Real, registered finding from this Etapa's mandatory pre-implementation
 * inspection: the product has no logout control anywhere in its UI today
 * (`components/shell/sidebar.tsx`/`header.tsx` -- no "Sair" action, no user
 * menu). `DELETE /api/bff/session` is real, implemented, and unit-tested
 * (`web/lib/session.test.ts`), but nothing in the browser ever calls it. Per
 * the Architectural Preservation mandate ("STOP, diagnose, present the
 * finding, do NOT fix silently"), this mission does not add a logout
 * button -- that would be a product/UX change outside an E2E-baseline
 * mission's scope. This test instead exercises the real, already-shipped
 * logout mechanism directly from the browser context (the exact call a
 * future "Sair" control would make), and proves both halves the Founder
 * asked to distinguish:
 *   - frontend state cleared: a protected route redirects to /entrar
 *     afterwards;
 *   - server-side session invalidated: the session row minted at login is
 *     gone from the backend's active-session list afterwards (verified
 *     directly against the mock backend, independent of the browser).
 */
test("logout invalidates the session both in the browser and server-side", async ({ page }) => {
  await login(page);
  expect(await activeSessionCount()).toBe(1);

  await page.evaluate(() => fetch("/api/bff/session", { method: "DELETE" }));

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/entrar/);

  expect(await activeSessionCount()).toBe(0);
});
