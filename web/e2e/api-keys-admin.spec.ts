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
 * API Keys (D-051, Enterprise Administration) -- end-to-end coverage of
 * the full Backend -> BFF -> Frontend chain. A foundational credential
 * alongside Users/Roles/Auditoria, not an Integration Hub artifact.
 */

test("navigates from the sidebar to Chaves de API", async ({ page }) => {
  await login(page);

  const visibleNav = (await page.viewportSize())!.width < MOBILE_BREAKPOINT
    ? page.getByTestId("bottom-nav")
    : page.getByTestId("sidebar-nav");
  await visibleNav.locator('a[href="/administracao/api-keys"]').click();

  await expect(page).toHaveURL(/\/administracao\/api-keys/);
  await expect(page.getByRole("heading", { name: "Chaves de API" })).toBeVisible();
});

test("redirects unauthenticated access to /administracao/api-keys to the login page", async ({
  page,
}) => {
  await page.goto("/administracao/api-keys");
  await expect(page).toHaveURL(/\/entrar/);
});

test("shows the empty state when no key has been created yet", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/api-keys");

  await expect(page.getByText("Nenhuma chave de API criada ainda.")).toBeVisible();
});

test("creates a key, reveals the plaintext exactly once, then lists it masked", async ({
  page,
}) => {
  await login(page);
  await page.goto("/administracao/api-keys");

  await page.getByRole("button", { name: "Nova chave" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Nome").fill("CI pipeline");
  await dialog.getByRole("button", { name: "Criar" }).click();

  await expect(dialog.getByText("Chave criada")).toBeVisible();
  const revealedKey = await dialog.locator("code").textContent();
  expect(revealedKey).toMatch(/^sk_live_/);

  await dialog.getByRole("button", { name: "Concluir" }).click();
  await expect(dialog).not.toBeVisible();

  const row = page.getByRole("row", { name: /CI pipeline/ });
  await expect(row).toBeVisible();
  await expect(row.getByText("Ativa")).toBeVisible();
  await expect(row.getByText("Nunca usada")).toBeVisible();
  // The list view never shows the full plaintext key again.
  await expect(page.getByText(revealedKey!)).not.toBeVisible();
});

test("copies the plaintext key to the clipboard", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await login(page);
  await page.goto("/administracao/api-keys");

  await page.getByRole("button", { name: "Nova chave" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Nome").fill("CI pipeline");
  await dialog.getByRole("button", { name: "Criar" }).click();
  const revealedKey = await dialog.locator("code").textContent();

  await dialog.getByRole("button", { name: "Copiar" }).click();

  await expect(page.getByText("Chave copiada")).toBeVisible();
  const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
  expect(clipboardText).toBe(revealedKey);
});

test("revokes a key after confirming, and it can no longer be revoked twice", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/api-keys");

  await page.getByRole("button", { name: "Nova chave" }).click();
  const createDialog = page.getByRole("dialog");
  await createDialog.getByLabel("Nome").fill("CI pipeline");
  await createDialog.getByRole("button", { name: "Criar" }).click();
  await createDialog.getByRole("button", { name: "Concluir" }).click();

  const row = page.getByRole("row", { name: /CI pipeline/ });
  await row.getByRole("button", { name: "Revogar" }).click();

  const confirmDialog = page.getByRole("dialog").filter({ hasText: "Revogar" });
  await confirmDialog.getByRole("button", { name: "Revogar" }).click();

  await expect(page.getByText("Chave revogada")).toBeVisible();
  await expect(row.getByText("Revogada")).toBeVisible();
  await expect(row.getByRole("button", { name: "Revogar" })).not.toBeVisible();
});
