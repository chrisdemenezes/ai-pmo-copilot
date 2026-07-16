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
// Compartilha uma raridade intermitente já documentada na Decision Center
// (TIP-009): se o fetch inicial de "workspace-latest"/"workspace-recent"
// ainda está em voo no instante em que a mutação invalida as queries, o
// React Query não dispara um segundo fetch (já há um em voo) -- a
// invalidação é "engolida" pela resolução do fetch obsoleto. Pré-existente
// (mesmo mecanismo do use-workspace-latest.ts do TIP-004/005), não
// introduzido por este Incremento -- fora de escopo reabrir aqui.
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

// Silent Intelligence (UX Flow §5-6, FS-010 §4): sem histórico suficiente
// (Aurora tem só 1 análise de status na fixture), o Brief permanece
// exatamente como sempre foi -- nenhum Insight, nenhum espaço reservado.
test("shows no Executive Memory Insight when there is no real 'before' to compare against", async ({
  page,
}) => {
  await login(page);
  await page.goto("/workspace/Aurora");

  const executiveBrief = page.locator("section", { has: page.getByText("Executive Brief") });
  await expect(executiveBrief.getByText(/^Mudou:|^Persiste em/)).toHaveCount(0);
});
