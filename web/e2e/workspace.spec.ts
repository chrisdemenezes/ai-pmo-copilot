import { test, expect, request as playwrightRequest } from "@playwright/test";

const MOCK_BACKEND_URL = "http://localhost:4100";
const WORKSPACE_PASSWORD = "e2e-workspace-password";

async function setBackendScenario(scenario: "data" | "empty" | "unavailable" | "timeout") {
  const ctx = await playwrightRequest.newContext();
  await ctx.post(`${MOCK_BACKEND_URL}/__control/scenario`, { data: { scenario } });
  await ctx.dispose();
}

async function setWorkspaceScenario(
  endpoint: "summary" | "analyses" | "detail",
  scenario: "data" | "unavailable" | "timeout",
) {
  const ctx = await playwrightRequest.newContext();
  await ctx.post(`${MOCK_BACKEND_URL}/__control/workspace-scenario`, {
    data: { endpoint, scenario },
  });
  await ctx.dispose();
}

async function login(page: import("@playwright/test").Page) {
  await page.goto("/entrar");
  await page.getByLabel("Senha do workspace").fill(WORKSPACE_PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  // Wait for the session cookie to actually land before any caller does its
  // own page.goto() -- a plain click() only waits for the click itself, not
  // for the redirect that follows it, so a goto() fired right after could
  // race the session cookie and bounce straight back to /entrar.
  await page.waitForURL(/\/dashboard/);
}

test.beforeEach(async () => {
  await setBackendScenario("data");
  await setWorkspaceScenario("summary", "data");
  await setWorkspaceScenario("analyses", "data");
  await setWorkspaceScenario("detail", "data");
});

test("redirects unauthenticated access to /workspace/:projectName to the login page", async ({
  page,
}) => {
  await page.goto("/workspace/Aurora");
  await expect(page).toHaveURL(/\/entrar/);
});

test("navigates from a Dashboard row to its Workspace", async ({ page }) => {
  await login(page);
  await page.getByRole("link", { name: "Aurora" }).first().click();
  await expect(page).toHaveURL(/\/workspace\/Aurora/);
  await expect(page.getByRole("heading", { name: "Aurora" })).toBeVisible();
});

// Real hazard already hit once this Release (curl to
// /api/projects/{name}/summary broke on an unencoded "/"). This confirms
// the full chain -- Dashboard link -> dynamic route -> 3 BFF calls -- stays
// correct end-to-end for a project name containing "/".
test("encodes a project name containing '/' end-to-end", async ({ page }) => {
  await login(page);
  await page.getByRole("link", { name: "Implantacao SAP S/4HANA" }).first().click();
  await expect(page).toHaveURL(/\/workspace\/Implantacao%20SAP%20S%2F4HANA/);
  await expect(page.getByRole("heading", { name: "Implantacao SAP S/4HANA" })).toBeVisible();
  // Executive Summary counts (Painel A) prove GET .../summary resolved despite the slash.
  await expect(page.getByText("Atenção").first()).toBeVisible();
});

test("each Workspace panel loads independently -- a failing panel does not block the others", async ({
  page,
}) => {
  await setWorkspaceScenario("summary", "unavailable");

  await login(page);
  await page.goto("/workspace/Aurora");

  // Painel A (Cabeçalho / contagens) fails...
  await expect(page.getByText("Não foi possível carregar as contagens.")).toBeVisible();
  // ...while Painel B (Intelligence Timeline) and Painel C (Riscos) still render real data.
  await expect(page.getByText("Atraso na entrega")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Intelligence Timeline" })).toBeVisible();
});

test("Riscos, Ações and Decisões sections render real content from the mocked analyses", async ({
  page,
}) => {
  await login(page);
  await page.goto("/workspace/Aurora");

  await expect(page.getByText("Atraso na entrega")).toBeVisible();
  await expect(page.getByText("Atualizar cronograma")).toBeVisible();
  await expect(page.getByText("Adiar o go-live em 1 semana")).toBeVisible();
  await expect(page.getByText("Manter cadência atual")).toBeVisible();
});

test("opening an item in Histórico completo shows its detail in a dialog", async ({ page }) => {
  await login(page);
  await page.goto("/workspace/Aurora");

  await page.getByRole("heading", { name: "Histórico completo" }).scrollIntoViewIfNeeded();
  const historyButtons = page.locator('button:has-text("Risco")');
  await historyButtons.first().click();

  await expect(page.getByRole("dialog")).toBeVisible();
});
