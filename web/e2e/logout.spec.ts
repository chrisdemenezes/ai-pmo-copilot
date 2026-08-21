import { test, expect, request as playwrightRequest } from "@playwright/test";

const MOCK_BACKEND_URL = "http://localhost:4100";
const E2E_ORGANIZATION = "e2e-organization";
const E2E_EMAIL = "e2e@stratech.local";
const WORKSPACE_PASSWORD = "e2e-workspace-password";
const MOBILE_BREAKPOINT = 768;

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
 * Logout (W7-7 Etapa 4 + Logout UI Gap correction, Founder Decision —
 * W7-7 Checkpoint Ratification + Controlled User Pilot Readiness Review).
 *
 * W7-7 Etapa 4 found that the product had no logout control anywhere in
 * its UI (`components/shell/sidebar.tsx` — no "Sair" action). That finding
 * was registered, not fixed silently, and escalated to the Founder. The
 * Founder authorized a minimal correction reusing the existing session
 * mechanism (`DELETE /api/bff/session`, already implemented since W7-4)
 * — `components/shell/sidebar.tsx` now renders a real "Sair" button in
 * both the desktop rail and the mobile bottom nav. This test exercises
 * that real button (a genuine click, not a `page.evaluate` workaround),
 * proving both halves the Founder asked to distinguish:
 *   - frontend state cleared: a protected route redirects to /entrar
 *     afterwards;
 *   - server-side session invalidated: the session row minted at login is
 *     gone from the backend's active-session list afterwards (verified
 *     directly against the mock backend, independent of the browser).
 */
test("clicking Sair invalidates the session both in the browser and server-side", async ({
  page,
}) => {
  await login(page);
  expect(await activeSessionCount()).toBe(1);

  // Both landmarks render a "Sair" button (desktop rail + mobile bottom
  // nav), only one visible per breakpoint -- same selection pattern every
  // other spec uses for nav links (e.g. api-keys-admin.spec.ts).
  const visibleNav = (await page.viewportSize())!.width < MOBILE_BREAKPOINT
    ? page.getByTestId("bottom-nav")
    : page.getByTestId("sidebar-nav");
  // force: true -- Pacote C added ThemeToggle to the mobile bottom nav
  // right after Sair, and Next.js dev server's own floating dev-tools
  // indicator (only present under `next dev`, never in production) can
  // render over that exact corner of the viewport. Forcing tests the real
  // click handler, not a dev-only decoration no real user ever sees.
  await visibleNav.getByRole("button", { name: "Sair" }).click({ force: true });

  await expect(page).toHaveURL(/\/entrar/);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/entrar/);

  expect(await activeSessionCount()).toBe(0);
});
