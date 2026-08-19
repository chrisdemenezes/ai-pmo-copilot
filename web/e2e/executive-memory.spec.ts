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
});

// TIP-011, Incremento 1 (FS-010) -- "Persistiu": a fixture traz 2 análises de
// status consecutivas para o mesmo projeto, ambas "yellow" (Atenção), sem
// executar nenhuma análise nova. Prova o hook + memory-insights.ts + o chip
// de ponta a ponta contra o dado real do mock, silenciosamente (sem estado
// de carregamento próprio, sem competir com o conteúdo principal).
test("shows a Persistiu Executive Memory Insight when the same attention status repeats across the 2 most recent analyses", async ({
  page,
}) => {
  await login(page);
  await page.goto("/workspace/Implantacao%20SAP%20S%2F4HANA");

  const executiveBrief = page.locator("section", { has: page.getByText("Executive Brief") });
  await expect(executiveBrief.getByText("Persiste em Atenção (2ª análise seguida)")).toBeVisible();
});

// TIP-011, Incremento 1 -- "Mudou": reaproveita o fluxo já aprovado de
// Analisar Projeto (TIP-005). O mock sempre responde "green"; este projeto
// parte de "yellow" (id 301, a mais recente antes da submissão) -- a
// mudança real de estado deve aparecer como Insight, não apenas no badge.
//
// A raridade intermitente que existia aqui (TD-006, mesmo mecanismo do
// TD-004/005) foi fechada em useSubmitProjectStatus (use-submit-project-
// status.ts): `cancelQueries` roda antes de `invalidateQueries` em
// "workspace-latest"/"workspace-recent" para que um fetch inicial ainda em
// voo não engula mais a invalidação.
test("shows a Mudou Executive Memory Insight right after Analisar Projeto changes the health status", async ({
  page,
}) => {
  await login(page);
  await page.goto("/workspace/Implantacao%20SAP%20S%2F4HANA");

  await page.getByRole("button", { name: "Analisar Projeto" }).click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Contexto do projeto")
    .fill("Equipe recuperou o atraso no cronograma de testes na última sprint.");
  await dialog.getByRole("button", { name: "Executar Análise" }).click();

  await expect(page.getByText("Análise concluída")).toBeVisible();
  await expect(dialog).not.toBeVisible();

  const executiveBrief = page.locator("section", { has: page.getByText("Executive Brief") });
  await expect(executiveBrief.getByText("Mudou: Atenção → Saudável")).toBeVisible();
});

// TIP-011, Incremento 2 (FS-010) -- "Reapareceu": Aurora ganha uma análise de
// risco mais antiga (id 205) com a mesma descrição de atenção da já
// existente id 201 -- gera recorrência real sem mudar o que
// GET /api/risks/latest devolve para Aurora (a mais recente continua sendo
// 201, mesmo texto/probabilidade/impacto de sempre), então Decision
// Center/Portfolio Intelligence continuam intactos. Aurora só tem 1 análise
// de status, então o sinal de status permanece em silêncio (Silent
// Intelligence) -- prova as 2 coisas na mesma carga real: recorrência de
// risco aparecendo sozinha, e ausência de Mudou/Persistiu quando não há
// histórico de status suficiente.
test("shows a Reapareceu Executive Memory Insight when a high-attention risk recurs, with no status insight competing", async ({
  page,
}) => {
  await login(page);
  await page.goto("/workspace/Aurora");

  const executiveBrief = page.locator("section", { has: page.getByText("Executive Brief") });
  await expect(executiveBrief.getByText("Reapareceu: Atraso na entrega (2ª vez)")).toBeVisible();
  await expect(executiveBrief.getByText(/^Mudou:|^Persiste em/)).toHaveCount(0);
});
