import { test, expect, request as playwrightRequest } from "@playwright/test";

const MOCK_BACKEND_URL = "http://localhost:4100";
const E2E_ORGANIZATION = "e2e-organization";
const E2E_EMAIL = "e2e@stratech.local";
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

async function setLatestRisksScenario(scenario: "data" | "unavailable" | "timeout") {
  const ctx = await playwrightRequest.newContext();
  await ctx.post(`${MOCK_BACKEND_URL}/__control/workspace-scenario`, {
    data: { endpoint: "latestRisks", scenario },
  });
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
  await setBackendScenario("data");
  await setLatestRisksScenario("data");
});

test("redirects unauthenticated access to /decisions to the login page", async ({ page }) => {
  await page.goto("/decisions");
  await expect(page).toHaveURL(/\/entrar/);
});

// TIP-009, Incremento 1+2 -- Executive Decision Queue combinando Status
// (usePortfolioSummary, já real) e Risco (useLatestRisks, novo nesta
// Capability) -> decision-queue.ts -> Executive Decision Card.
test("shows the Executive Decision Queue ordered by window, combining Status and Risco, filtered to projects that need a decision", async ({
  page,
}) => {
  await login(page);
  await page.goto("/decisions");

  await expect(page.getByRole("heading", { name: "Decisões" })).toBeVisible();

  // Multilift (status red) e Aurora (risco em atenção, status green) -> "Hoje";
  // Implantacao SAP (status yellow) -> "Esta semana"; nenhum projeto some.
  await expect(page.getByRole("heading", { name: "Multilift" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Aurora" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Implantacao SAP S/4HANA" })).toBeVisible();

  await expect(page.getByText("Status: Crítico")).toBeVisible();
  await expect(page.getByText("Status: Atenção")).toBeVisible();
  await expect(page.getByText("1 risco(s) na zona de atenção")).toBeVisible();
  await expect(page.getByText("Escalar ao patrocinador").first()).toBeVisible();
  await expect(page.getByText("Acompanhar de perto").first()).toBeVisible();
  await expect(page.getByText("Priorizar mitigação imediata").first()).toBeVisible();

  // Ordem fixa: entradas "Hoje" (Aurora, Multilift, alfabética) antes de
  // "Esta semana" (SAP).
  const headings = page.getByRole("heading", { level: 3 });
  await expect(headings.nth(0)).toHaveText("Aurora");
  await expect(headings.nth(1)).toHaveText("Multilift");
  await expect(headings.nth(2)).toHaveText("Implantacao SAP S/4HANA");
});

test("a failing Risco signal degrades gracefully without blocking Status decisions", async ({
  page,
}) => {
  await setLatestRisksScenario("unavailable");

  await login(page);
  await page.goto("/decisions");

  await expect(
    page.getByText("Não foi possível carregar os riscos -- mostrando decisões de Status."),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Multilift" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Implantacao SAP S/4HANA" })).toBeVisible();
});

// TIP-009 Incremento 3 -- Sidebar → "Decisões" → Executive Decision Queue,
// mesma regra de entrada já cumprida por "Ações" (TIP-008 Incremento 2).
test("navigates via the Decisões nav item to the Executive Decision Queue", async ({ page }) => {
  await login(page);

  await page.locator('a[href="/decisions"]').filter({ visible: true }).first().click();
  await expect(page).toHaveURL(/\/decisions/);
  await expect(page.getByRole("heading", { name: "Decisões" })).toBeVisible();
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
