import { test, expect, request as playwrightRequest } from "@playwright/test";

const MOCK_BACKEND_URL = "http://localhost:4100";
const WORKSPACE_PASSWORD = "e2e-workspace-password";

async function setBackendScenario(scenario: "data" | "empty" | "unavailable" | "timeout") {
  const ctx = await playwrightRequest.newContext();
  await ctx.post(`${MOCK_BACKEND_URL}/__control/scenario`, { data: { scenario } });
  await ctx.dispose();
}

async function resetFixtures() {
  const ctx = await playwrightRequest.newContext();
  await ctx.post(`${MOCK_BACKEND_URL}/__control/reset-fixtures`);
  await ctx.dispose();
}

async function login(page: import("@playwright/test").Page) {
  await page.goto("/entrar");
  await page.getByLabel("Senha do workspace").fill(WORKSPACE_PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL(/\/dashboard/);
}

test.beforeEach(async () => {
  await resetFixtures();
  await setBackendScenario("data");
});

test("redirects unauthenticated access to /decisions to the login page", async ({ page }) => {
  await page.goto("/decisions");
  await expect(page).toHaveURL(/\/entrar/);
});

// TIP-009, Incremento 1 -- Executive Decision Queue com sinal de Status,
// ponta a ponta (usePortfolioSummary já real -> decision-queue.ts ->
// Executive Decision Card), zero leitura nova de backend.
test("shows the Executive Decision Queue ordered by window, filtered to projects that need a decision", async ({
  page,
}) => {
  await login(page);
  await page.goto("/decisions");

  await expect(page.getByRole("heading", { name: "Decisões" })).toBeVisible();

  // Multilift (red) -> "Hoje"; Implantacao SAP (yellow) -> "Esta semana";
  // Aurora (green) nunca aparece -- Princípio de Atenção.
  await expect(page.getByRole("heading", { name: "Multilift" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Implantacao SAP S/4HANA" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Aurora" })).not.toBeVisible();

  await expect(page.getByText("Status: Crítico")).toBeVisible();
  await expect(page.getByText("Status: Atenção")).toBeVisible();
  await expect(page.getByText("Escalar ao patrocinador").first()).toBeVisible();
  await expect(page.getByText("Acompanhar de perto").first()).toBeVisible();

  // Ordem fixa: Multilift ("Hoje") antes de SAP ("Esta semana").
  const headings = page.getByRole("heading", { level: 3 });
  await expect(headings.first()).toHaveText("Multilift");
});

test("clicking a decision navigates to the project's Workspace", async ({ page }) => {
  await login(page);
  await page.goto("/decisions");

  await page.getByRole("link", { name: /Multilift/ }).click();
  await expect(page).toHaveURL(/\/workspace\/Multilift/);
});

test("shows the affirmative empty state when no project needs a decision", async ({ page }) => {
  await setBackendScenario("empty");

  await login(page);
  await page.goto("/decisions");

  await expect(page.getByText("Nenhuma decisão pendente")).toBeVisible();
  await expect(page.getByText("Todo o portfólio está no curso esperado.")).toBeVisible();
});

test("shows the error state when the backend fails, with retry", async ({ page }) => {
  await setBackendScenario("unavailable");

  await login(page);
  await page.goto("/decisions");

  await expect(page.getByText("Não foi possível carregar as decisões agora")).toBeVisible();
  await expect(page.getByRole("button", { name: "Tentar novamente" })).toBeVisible();
});
