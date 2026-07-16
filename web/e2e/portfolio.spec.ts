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

async function setLatestRisksScenario(scenario: "data" | "unavailable" | "timeout") {
  const ctx = await playwrightRequest.newContext();
  await ctx.post(`${MOCK_BACKEND_URL}/__control/workspace-scenario`, {
    data: { endpoint: "latestRisks", scenario },
  });
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
  await setLatestRisksScenario("data");
});

test("redirects unauthenticated access to /portfolio to the login page", async ({ page }) => {
  await page.goto("/portfolio");
  await expect(page).toHaveURL(/\/entrar/);
});

// TIP-010, Incremento 1 -- Executive Portfolio View cobrindo o portfólio
// inteiro (diferente da Executive Decision Queue, que filtra): todo
// projeto aparece, em exatamente uma camada.
test("shows the whole portfolio organized in layers, ordered decision-today before decision-this-week", async ({
  page,
}) => {
  await login(page);
  await page.goto("/portfolio");

  await expect(page.getByRole("heading", { name: "Portfólio" })).toBeVisible();

  // Multilift (status red) e Aurora (risco em atenção, status green) -> "hoje";
  // Implantacao SAP (status yellow) -> "esta semana". Nenhum projeto ausente.
  await expect(page.getByRole("heading", { name: "Multilift" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Aurora" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Implantacao SAP S/4HANA" })).toBeVisible();

  await expect(page.getByText("Decisão pendente hoje").first()).toBeVisible();
  await expect(page.getByText("Decisão pendente esta semana")).toBeVisible();

  const headings = page.getByRole("heading", { level: 3 });
  await expect(headings.nth(0)).toHaveText("Aurora");
  await expect(headings.nth(1)).toHaveText("Multilift");
  await expect(headings.nth(2)).toHaveText("Implantacao SAP S/4HANA");
});

test("a failing Risco signal degrades gracefully without blocking Status-derived layers", async ({ page }) => {
  await setLatestRisksScenario("unavailable");

  await login(page);
  await page.goto("/portfolio");

  await expect(
    page.getByText("Não foi possível carregar os riscos -- mostrando apenas o sinal de Status."),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Multilift" })).toBeVisible();
});

test("clicking a project with a pending decision navigates to the Executive Decision Queue", async ({ page }) => {
  await login(page);
  await page.goto("/portfolio");

  await page.getByRole("link", { name: /Multilift/ }).click();
  await expect(page).toHaveURL(/\/decisions/);
});

test("shows the safe error state when the backend is unavailable", async ({ page }) => {
  await setBackendScenario("unavailable");

  await login(page);
  await page.goto("/portfolio");

  await expect(page.getByText("Não foi possível carregar o portfólio agora")).toBeVisible();
});

// TIP-010 Incremento 3 -- Sidebar -> "Priorização" -> Executive Portfolio
// View, mesma regra de entrada já cumprida por "Ações"/"Decisões".
test("navigates via the Priorização nav item to the Executive Portfolio View", async ({ page }) => {
  await login(page);

  await page.locator('a[href="/portfolio"]').filter({ visible: true }).first().click();
  await expect(page).toHaveURL(/\/portfolio/);
  await expect(page.getByRole("heading", { name: "Portfólio" })).toBeVisible();
});
