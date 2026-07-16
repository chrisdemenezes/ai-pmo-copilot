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

async function setWorkspaceScenario(
  endpoint: "actionItems" | "latestRisks",
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
  await page.waitForURL(/\/dashboard/);
}

test.beforeEach(async () => {
  await resetFixtures();
  await setBackendScenario("data");
  await setWorkspaceScenario("actionItems", "data");
  await setWorkspaceScenario("latestRisks", "data");
});

test("redirects unauthenticated access to /aprendizados to the login page", async ({ page }) => {
  await page.goto("/aprendizados");
  await expect(page).toHaveURL(/\/entrar/);
});

// TIP-012 -- Sidebar -> "Aprendizados" -> Organizational Intelligence,
// mesma regra de entrada já cumprida por "Ações"/"Decisões".
test("navigates via the Aprendizados nav item to Organizational Intelligence", async ({
  page,
}) => {
  await login(page);

  await page.locator('a[href="/aprendizados"]').filter({ visible: true }).first().click();
  await expect(page).toHaveURL(/\/aprendizados/);
  await expect(page.getByRole("heading", { name: "Aprendizados" })).toBeVisible();
});

// A fixture compartilhada do mock só tem 2 projetos com workspace real
// (Aurora, Implantacao SAP S/4HANA) -- nenhum risco/ação real desta
// fixture atinge o limiar de 3+ projetos distintos (Journey §02). Prova
// honestamente o caminho real de ponta a ponta (hook -> agregação ->
// página) sem fabricar uma recorrência que a fixture compartilhada não
// produz naturalmente -- mesma disciplina já aplicada em Portfolio
// Intelligence (TIP-010) para o caso "risco a monitorar" não observável no
// mock. A recorrência real de 3+ projetos é verificada em Demo Mode (T10),
// que tem 6 projetos fictícios.
test("shows the honest empty state when no real pattern reaches the 3+ occurrence threshold", async ({
  page,
}) => {
  await login(page);
  await page.goto("/aprendizados");

  await expect(
    page.getByText("Nenhum aprendizado organizacional identificado no momento"),
  ).toBeVisible();
  await expect(page.getByText("Riscos recorrentes")).toHaveCount(0);
  await expect(page.getByText("Ações recorrentes")).toHaveCount(0);
});

test("degrades gracefully when risks fail to load, without blocking the actions read", async ({
  page,
}) => {
  await setWorkspaceScenario("latestRisks", "unavailable");

  await login(page);
  await page.goto("/aprendizados");

  await expect(
    page.getByText("Não foi possível carregar os riscos -- mostrando apenas ações recorrentes."),
  ).toBeVisible();
  // Nenhuma pergunta é respondida duas vezes -- a página continua no ar mesmo com 1 sinal indisponível.
  await expect(page.getByRole("heading", { name: "Aprendizados" })).toBeVisible();
});

test("degrades gracefully when actions fail to load, without blocking the risks read", async ({
  page,
}) => {
  await setWorkspaceScenario("actionItems", "unavailable");

  await login(page);
  await page.goto("/aprendizados");

  await expect(
    page.getByText("Não foi possível carregar as ações -- mostrando apenas riscos recorrentes."),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Aprendizados" })).toBeVisible();
});
