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
 * Convites (item 6, D-054) -- end-to-end coverage of the full Backend ->
 * BFF -> Frontend chain, including the public token-authenticated
 * acceptance flow that requires no session.
 */

test("navigates from the sidebar to Convites", async ({ page }) => {
  await login(page);

  const visibleNav = (await page.viewportSize())!.width < MOBILE_BREAKPOINT
    ? page.getByTestId("bottom-nav")
    : page.getByTestId("sidebar-nav");
  await visibleNav.locator('a[href="/administracao/convites"]').click();

  await expect(page).toHaveURL(/\/administracao\/convites/);
  await expect(page.getByRole("heading", { name: "Convites" })).toBeVisible();
});

test("redirects unauthenticated access to /administracao/convites to the login page", async ({
  page,
}) => {
  await page.goto("/administracao/convites");
  await expect(page).toHaveURL(/\/entrar/);
});

test("shows the empty state when no invitation exists", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/convites");
  await expect(page.getByText("Nenhum convite emitido ainda.")).toBeVisible();
});

test("creates an invitation, reveals the link once, then lists it as pending", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/convites");

  await page.getByRole("button", { name: "Novo convite" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("E-mail").fill("newcomer@example.com");
  await dialog.getByRole("combobox").click();
  await page.getByRole("option", { name: "viewer" }).click();
  await dialog.getByRole("button", { name: "Criar" }).click();

  // The invite link is revealed exactly once, on this response.
  await expect(dialog.getByText(/\/convite\/inv_/)).toBeVisible();
  await dialog.getByRole("button", { name: "Concluir" }).click();

  // The list now shows it as Pendente, masked (no token).
  await expect(page.getByRole("cell", { name: "newcomer@example.com" })).toBeVisible();
  await expect(page.getByText("Pendente")).toBeVisible();
});

test("cancels a pending invitation after confirming", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/convites");

  await page.getByRole("button", { name: "Novo convite" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("E-mail").fill("cancel-me@example.com");
  await dialog.getByRole("combobox").click();
  await page.getByRole("option", { name: "viewer" }).click();
  await dialog.getByRole("button", { name: "Criar" }).click();
  await dialog.getByRole("button", { name: "Concluir" }).click();

  const row = page.getByRole("row", { name: /cancel-me@example.com/ });
  await row.getByRole("button", { name: "Cancelar" }).click();

  const confirmDialog = page.getByRole("dialog").filter({ hasText: "Cancelar convite" });
  await confirmDialog.getByRole("button", { name: "Cancelar convite" }).click();

  await expect(page.getByText("Convite cancelado")).toBeVisible();
  await expect(page.getByText("Cancelado", { exact: true })).toBeVisible();
});

test("a new user accepts an invitation via the public page, with no session", async ({
  page,
  request,
}) => {
  // Seed a pending invitation directly through the mock backend admin API,
  // then exercise the public acceptance page as an unauthenticated visitor.
  const created = await request.post(`${MOCK_BACKEND_URL}/api/admin/invitations`, {
    headers: { "X-API-Key": "e2e-mock-api-key" },
    data: { email: "invited@example.com", role_name: "viewer" },
  });
  const body = await created.json();
  const token = body.plaintext_token as string;

  // No login -- the token in the URL is the authorization.
  await page.goto(`/convite/${token}`);
  await expect(page.getByTestId("invitation-summary")).toContainText("e2e-organization");
  await expect(page.getByTestId("invitation-summary")).toContainText("invited@example.com");

  await page.getByLabel("Seu nome").fill("Invited Person");
  await page.getByLabel("Senha").fill("a-strong-password");
  await page.getByRole("button", { name: "Aceitar e criar conta" }).click();

  // On success the invitee is sent to the login page.
  await expect(page).toHaveURL(/\/entrar/);
});
