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

const MOBILE_BREAKPOINT = 768;

/**
 * Sessions (item 5 -- resolves TD-010) -- end-to-end coverage of the full
 * Backend -> BFF -> Frontend chain. Logging in creates a server-side
 * session row this page can list and revoke.
 */

test("navigates from the sidebar to Sessões", async ({ page }) => {
  await login(page);

  const visibleNav = (await page.viewportSize())!.width < MOBILE_BREAKPOINT
    ? page.getByTestId("bottom-nav")
    : page.getByTestId("sidebar-nav");
  await visibleNav.locator('a[href="/administracao/sessoes"]').click();

  await expect(page).toHaveURL(/\/administracao\/sessoes/);
  await expect(page.getByRole("heading", { name: "Sessões" })).toBeVisible();
});

test("redirects unauthenticated access to /administracao/sessoes to the login page", async ({
  page,
}) => {
  await page.goto("/administracao/sessoes");
  await expect(page).toHaveURL(/\/entrar/);
});

test("lists the current login session", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/sessoes");

  // The session minted by this very login is listed as active.
  await expect(page.getByRole("row", { name: /Usuário #1/ })).toBeVisible();
});

test("revokes a session after confirming, and it disappears from the active list", async ({
  page,
}) => {
  await login(page);
  await page.goto("/administracao/sessoes");

  const row = page.getByRole("row", { name: /Usuário #1/ });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: "Revogar" }).click();

  const confirmDialog = page.getByRole("dialog").filter({ hasText: "Revogar" });
  await confirmDialog.getByRole("button", { name: "Revogar" }).click();

  await expect(page.getByText("Sessão revogada")).toBeVisible();
  // Revoked sessions drop out of the active list.
  await expect(page.getByText("Nenhuma sessão ativa no momento.")).toBeVisible();
});
