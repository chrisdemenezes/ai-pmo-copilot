import { test, expect, request as playwrightRequest } from "@playwright/test";

const MOCK_BACKEND_URL = "http://localhost:4100";
const E2E_ORGANIZATION = "e2e-organization";
const E2E_EMAIL = "e2e@stratech.local";
const WORKSPACE_PASSWORD = "e2e-workspace-password";

async function setActionItemsScenario(scenario: "data" | "unavailable" | "timeout") {
  const ctx = await playwrightRequest.newContext();
  await ctx.post(`${MOCK_BACKEND_URL}/__control/workspace-scenario`, {
    data: { endpoint: "actionItems", scenario },
  });
  await ctx.dispose();
}

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
  await setActionItemsScenario("data");
});

test("redirects unauthenticated access to /actions to the login page", async ({ page }) => {
  await page.goto("/actions");
  await expect(page).toHaveURL(/\/entrar/);
});

// TIP-008, Incremento 2 -- Sidebar → "Ações" → itens de múltiplos projetos
// agrupados por urgência, sem escolher um projeto antes.
test("navigates via the Ações nav item to the portfolio view grouped by urgency", async ({
  page,
}) => {
  await login(page);

  await page.locator('a[href="/actions"]').filter({ visible: true }).first().click();
  await expect(page).toHaveURL(/\/actions/);
  await expect(page.getByRole("heading", { name: "Ações" })).toBeVisible();

  // Itens de mais de um projeto na mesma tela, cada cartão com seu projeto.
  await expect(page.getByText("Cobrar plano de contingência do fornecedor").first()).toBeVisible();
  await expect(page.getByText("Validar plano de cutover com o cliente")).toBeVisible();
  await expect(page.getByText("Aurora").first()).toBeVisible();
  await expect(page.getByText("Implantacao SAP S/4HANA").first()).toBeVisible();

  // Agrupamento fixo: atrasado sempre primeiro, contagem real na manchete.
  await expect(page.getByText("Atrasado", { exact: true })).toBeVisible();
  await expect(page.getByText("1 atrasada(s) · 2 vence(m) em breve")).toBeVisible();

  // O item mais urgente do portfólio inteiro destacado no topo, como texto.
  await expect(page.getByText("Próxima ação sugerida")).toBeVisible();
});

test("shows the error boundary when the backend fails, with retry", async ({ page }) => {
  await setActionItemsScenario("unavailable");

  await login(page);
  await page.goto("/actions");

  await expect(page.getByText("Não foi possível carregar as ações agora")).toBeVisible();
  await expect(page.getByRole("button", { name: "Tentar novamente" })).toBeVisible();
});
