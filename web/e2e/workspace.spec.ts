import { test, expect, request as playwrightRequest } from "@playwright/test";

const MOCK_BACKEND_URL = "http://localhost:4100";
const WORKSPACE_PASSWORD = "e2e-workspace-password";

async function setBackendScenario(scenario: "data" | "empty" | "unavailable" | "timeout") {
  const ctx = await playwrightRequest.newContext();
  await ctx.post(`${MOCK_BACKEND_URL}/__control/scenario`, { data: { scenario } });
  await ctx.dispose();
}

async function setWorkspaceScenario(
  endpoint:
    | "summary"
    | "analyses"
    | "detail"
    | "analyze"
    | "analyzeRisk"
    | "analyzeMeeting"
    | "actionItems",
  scenario: "data" | "unavailable" | "timeout" | "rate_limited",
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

async function resetFixtures() {
  const ctx = await playwrightRequest.newContext();
  await ctx.post(`${MOCK_BACKEND_URL}/__control/reset-fixtures`);
  await ctx.dispose();
}

test.beforeEach(async () => {
  // /api/projects/analyze (TIP-005) mutates the mock's fixture data in
  // place, and the mock server process is shared across every spec file and
  // breakpoint project in the run -- reset before every test, not just this
  // file's, so a previous "Analisar Projeto" success never leaks forward.
  await resetFixtures();
  await setBackendScenario("data");
  await setWorkspaceScenario("summary", "data");
  await setWorkspaceScenario("analyses", "data");
  await setWorkspaceScenario("detail", "data");
  await setWorkspaceScenario("analyze", "data");
  await setWorkspaceScenario("analyzeRisk", "data");
  await setWorkspaceScenario("analyzeMeeting", "data");
  await setWorkspaceScenario("actionItems", "data");
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

test("Riscos and Comunicação sections render real content from the mocked analyses", async ({
  page,
}) => {
  await login(page);
  await page.goto("/workspace/Aurora");

  await expect(page.getByText("Atraso na entrega")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Comunicação" })).toBeVisible();
  // .first(): desde TIP-008 o mesmo item também aparece na seção "Ações".
  await expect(page.getByText("Atualizar cronograma").first()).toBeVisible();
  await expect(page.getByText("Adiar o go-live em 1 semana")).toBeVisible();
  await expect(page.getByText("Manter cadência atual")).toBeVisible();
});

// TIP-008, Incremento 1 -- seção "Ações" do Workspace, de ponta a ponta
// (backend → BFF → hook → action-momentum → componente).
test("Ações section shows the project's meeting commitments grouped by urgency", async ({
  page,
}) => {
  await login(page);
  await page.goto("/workspace/Aurora");

  const section = page.locator("section", { has: page.locator("#actions-heading") });
  await section.scrollIntoViewIfNeeded();

  // "O que exige minha atenção hoje?" -- contagem real: 1 atrasada (reunião
  // 204) e 1 vencendo em breve (reunião 202), nunca uma nota inventada.
  await expect(section.getByText("1 atrasada(s) · 1 vence(m) em breve")).toBeVisible();

  // Agrupamento fixo por urgência, atrasado sempre primeiro.
  await expect(section.getByText("Atrasado", { exact: true })).toBeVisible();
  await expect(
    section.getByText("Cobrar plano de contingência do fornecedor").first(),
  ).toBeVisible();
  await expect(section.getByText("Vence em breve", { exact: true })).toBeVisible();
  await expect(section.getByText("Atualizar cronograma", { exact: true })).toBeVisible();
  await expect(section.getByText("Sem prazo", { exact: true })).toBeVisible();
  await expect(section.getByText("Documentar acordos da reunião")).toBeVisible();
});

test("clicking an action item opens its meeting analysis of origin", async ({ page }) => {
  await login(page);
  await page.goto("/workspace/Aurora");

  const section = page.locator("section", { has: page.locator("#actions-heading") });
  await section.scrollIntoViewIfNeeded();
  await section.getByRole("button", { name: /Documentar acordos da reunião/ }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("Reunião de alinhamento com o fornecedor.")).toBeVisible();
});

// TIP-008 Incremento 3 -- linha de contexto nos 3 Briefs (FS-007 §2.7):
// mesma contagem de atenção da seção "Ações", nunca o total bruto.
test("the 3 Briefs show the same actions context line the Ações section shows", async ({
  page,
}) => {
  await login(page);
  await page.goto("/workspace/Aurora");

  const executiveBrief = page.locator("section", { has: page.getByText("Executive Brief") });
  const risks = page.locator("section", { has: page.locator("#risks-heading") });
  const communication = page.locator("section", { has: page.locator("#communication-heading") });

  await expect(executiveBrief.getByText("2 ações exigem atenção")).toBeVisible();
  await expect(risks.getByText("2 ações exigem atenção")).toBeVisible();
  await expect(communication.getByText("2 ações exigem atenção")).toBeVisible();

  // A mesma contagem aparece na própria seção "Ações", como manchete real.
  const actionsSection = page.locator("section", { has: page.locator("#actions-heading") });
  await actionsSection.scrollIntoViewIfNeeded();
  await expect(actionsSection.getByText("1 atrasada(s) · 1 vence(m) em breve")).toBeVisible();
});

test("omits the actions context line from the 3 Briefs when nothing needs attention", async ({
  page,
}) => {
  await login(page);
  await page.goto("/workspace/Implantacao%20SAP%20S%2F4HANA");

  // Este projeto não tem reunião fixture (nenhum item de ação) -- contagem
  // de atenção é 0, a linha deve estar ausente nos 3 Briefs.
  await expect(page.getByText(/ações exigem atenção|ação exige atenção/)).toHaveCount(0);
});

test("a failing Ações section does not block the other Workspace panels", async ({ page }) => {
  await setWorkspaceScenario("actionItems", "unavailable");

  await login(page);
  await page.goto("/workspace/Aurora");

  await expect(page.getByText("Não foi possível carregar as ações.")).toBeVisible();
  // Painel C (Riscos) continua renderizando dado real.
  await expect(page.getByText("Atraso na entrega")).toBeVisible();
});

test("opening an item in Histórico completo shows its detail in a dialog", async ({ page }) => {
  await login(page);
  await page.goto("/workspace/Aurora");

  await page.getByRole("heading", { name: "Histórico completo" }).scrollIntoViewIfNeeded();
  const historyButtons = page.locator('button:has-text("Risco")');
  await historyButtons.first().click();

  await expect(page.getByRole("dialog")).toBeVisible();
});

// TIP-005 -- "Analisar Projeto" (Project Status), a jornada de 11 passos da
// FS-005 §4, ponta a ponta contra o mock: abrir projeto -> "Analisar
// Projeto" -> Tipo de análise (Status Executivo, já implícito) -> contexto
// -> executar -> loading/sucesso -> painéis atualizados sem reload ->
// Dashboard reflete o resultado na próxima navegação.
test.describe("Analisar Projeto (TIP-005)", () => {
  test("runs a full Project Status analysis and reflects it in the Workspace and the Dashboard", async ({
    page,
  }) => {
    await login(page);
    // Starts "Atenção" (yellow) -- the mock always answers a successful
    // analysis with health_status "green", so this project makes the
    // before/after state change visible, not just present.
    await page.goto("/workspace/Implantacao%20SAP%20S%2F4HANA");
    await expect(page.getByText("Atenção").first()).toBeVisible();

    await page.getByRole("button", { name: "Analisar Projeto" }).click();
    const dialog = page.getByRole("dialog");
    // Pergunta -> Capability -> Executor (FS-006 §2.1): the user sees only
    // the question, never the technical/agent name.
    await expect(dialog.getByRole("tab", { name: "Como está o projeto?" })).toBeVisible();
    await expect(dialog.getByText("project_status", { exact: false })).toHaveCount(0);

    await dialog
      .getByLabel("Contexto do projeto")
      .fill("Equipe recuperou o atraso no cronograma de testes na última sprint.");
    await dialog.getByRole("button", { name: "Executar Análise" }).click();

    await expect(page.getByText("Análise concluída")).toBeVisible();
    await expect(dialog).not.toBeVisible();

    // Workspace reflects the new result without a manual reload.
    await expect(page.getByText("Saudável").first()).toBeVisible();
    await expect(
      page.getByText("Cronograma recuperado após a última análise"),
    ).toBeVisible();

    // Dashboard reflects it too, on the next client-side navigation --
    // same shared QueryClient, no WebSocket/polling (FS-005 §3). href-based
    // locator, filtered to visible: the Sidebar (md+) and the mobile bottom
    // tab bar both render a[href="/dashboard"] simultaneously, one of them
    // always display:none at any given breakpoint (TIP-004A precedent).
    await page.locator('a[href="/dashboard"]').filter({ visible: true }).first().click();
    await expect(page).toHaveURL(/\/dashboard/);
    // ProjectHealthGrid renders both a desktop table and a mobile card list
    // simultaneously (one always display:none); scope to whichever is
    // actually visible at this breakpoint instead of assuming the table.
    // "Implantacao SAP S/4HANA" is the only "Atenção" (yellow) project in
    // the fixture, so its absence after the analysis is an unambiguous,
    // breakpoint-independent signal that the Dashboard picked up the change.
    const visibleGrid = page
      .locator('[data-testid="project-table"], [data-testid="project-cards"]')
      .filter({ visible: true });
    await expect(visibleGrid.getByText("Atenção")).toHaveCount(0);
  });

  test("keeps Executar Análise disabled below the 10-character minimum", async ({ page }) => {
    await login(page);
    await page.goto("/workspace/Aurora");

    await page.getByRole("button", { name: "Analisar Projeto" }).click();
    const dialog = page.getByRole("dialog");
    const submit = dialog.getByRole("button", { name: "Executar Análise" });
    await expect(submit).toBeDisabled();

    await dialog.getByLabel("Contexto do projeto").fill("curto");
    await expect(submit).toBeDisabled();
  });

  test("on failure, keeps the modal open and preserves the typed context", async ({ page }) => {
    await setWorkspaceScenario("analyze", "rate_limited");
    await login(page);
    await page.goto("/workspace/Aurora");

    await page.getByRole("button", { name: "Analisar Projeto" }).click();
    const dialog = page.getByRole("dialog");
    const context = "Contexto detalhado o suficiente para passar da validação de tamanho mínimo.";
    await dialog.getByLabel("Contexto do projeto").fill(context);
    await dialog.getByRole("button", { name: "Executar Análise" }).click();

    await expect(dialog).toBeVisible();
    await expect(dialog.getByLabel("Contexto do projeto")).toHaveValue(context);
    await expect(
      dialog.getByText("Muitas análises em pouco tempo. Aguarde e tente novamente."),
    ).toBeVisible();
  });
});

// TIP-006 -- segundo agente (Avaliação de Riscos), mesmo padrão do Status
// Executivo (TIP-005/TIP-005A): mesmo Dialog, agora com Tabs (Design System
// já existente) porque há 2 opções reais; mesmo Executive Brief + Decision
// Momentum, aplicado à zona de atenção real da matriz probabilidade x
// impacto em vez de health_status.
test.describe("Avaliação de Riscos (TIP-006)", () => {
  test("runs a full risk analysis via the Avaliação de Riscos tab and reflects it in the Workspace and the Dashboard", async ({
    page,
  }) => {
    await login(page);
    await page.goto("/workspace/Aurora");

    await page.getByRole("button", { name: "Analisar Projeto" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("tab", { name: "Quais riscos exigem atenção?" }).click();
    await dialog
      .getByLabel("Contexto do projeto")
      .fill("Fornecedor de middleware sinalizou atraso na integração fiscal.");
    await dialog.getByRole("button", { name: "Executar Análise" }).click();

    await expect(page.getByText("Análise concluída")).toBeVisible();
    await expect(dialog).not.toBeVisible();

    // Riscos panel reflects the new result without a manual reload --
    // the high-attention risk promoted, the low one demoted, real data.
    await expect(page.getByText("Riscos que exigem atenção")).toBeVisible();
    await expect(
      page.getByText("Atraso no fornecedor de middleware compromete o go-live"),
    ).toBeVisible();
    await expect(page.getByText("Também identificado")).toBeVisible();
    await expect(page.getByText("Priorizar mitigação imediata")).toBeVisible();
    await expect(
      page.getByText("Escalar o atraso do fornecedor ao comitê executivo"),
    ).toBeVisible();

    // Dashboard reflects it too, on the next client-side navigation -- the
    // portfolio-wide "Riscos identificados" strip is a single instance (not
    // duplicated per breakpoint like the grid), so the exact new total
    // (Multilift 3 + Aurora 0+2 + Implantacao SAP 1 = 6) is an unambiguous
    // signal that this specific submission's 2 risks were counted.
    await page.locator('a[href="/dashboard"]').filter({ visible: true }).first().click();
    await expect(page).toHaveURL(/\/dashboard/);
    const riscosCard = page.getByText("Riscos identificados").locator("xpath=..");
    await expect(riscosCard.getByText("6")).toBeVisible();
  });

  test("on failure while on the Avaliação de Riscos tab, keeps the modal open and preserves the typed context", async ({
    page,
  }) => {
    await setWorkspaceScenario("analyzeRisk", "rate_limited");
    await login(page);
    await page.goto("/workspace/Aurora");

    await page.getByRole("button", { name: "Analisar Projeto" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("tab", { name: "Quais riscos exigem atenção?" }).click();
    const context = "Contexto detalhado o suficiente para passar da validação de tamanho mínimo.";
    await dialog.getByLabel("Contexto do projeto").fill(context);
    await dialog.getByRole("button", { name: "Executar Análise" }).click();

    await expect(dialog).toBeVisible();
    await expect(dialog.getByLabel("Contexto do projeto")).toHaveValue(context);
    await expect(
      dialog.getByText("Muitas análises em pouco tempo. Aguarde e tente novamente."),
    ).toBeVisible();
  });
});

// TIP-007 -- terceiro agente (Meeting Intelligence / Comunicação), mesmo
// padrão dos 2 anteriores: mesmo Dialog, agora com 3 Tabs em forma de
// pergunta (FS-006 §2.1 -- Pergunta -> Capability -> Executor), mesmo
// Executive Brief + Decision Momentum, aplicado à Hierarquia Executiva
// (Impacto, O que mudou, Pontos de atenção, Decisões tomadas,
// Responsabilidades, Dependências, Próximo passo).
test.describe("O que mudou na última reunião? (TIP-007)", () => {
  test("runs a full meeting analysis via the 3rd tab and reflects it in the Workspace and the Dashboard", async ({
    page,
  }) => {
    await login(page);
    await page.goto("/workspace/Aurora");

    await page.getByRole("button", { name: "Analisar Projeto" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("tab", { name: "O que mudou na última reunião?" }).click();
    await expect(dialog.getByLabel("Contexto da reunião")).toBeVisible();
    // Goal-oriented language only -- neither the agent name nor the
    // backend's own field name for this agent ever appears.
    await expect(dialog.getByText("meeting_intelligence", { exact: false })).toHaveCount(0);
    await expect(dialog.getByText("transcript", { exact: false })).toHaveCount(0);

    await dialog
      .getByLabel("Contexto da reunião")
      .fill("Ata da reunião semanal: fornecedor confirmou atraso adicional na integração fiscal.");
    await dialog.getByRole("button", { name: "Executar Análise" }).click();

    await expect(page.getByText("Análise concluída")).toBeVisible();
    await expect(dialog).not.toBeVisible();

    // Comunicação reflects the new result without a manual reload, in the
    // Executive Hierarchy order approved in the User Journey.
    await expect(page.getByRole("heading", { name: "Comunicação" })).toBeVisible();
    await expect(page.getByText("O que mudou")).toBeVisible();
    await expect(
      page.getByText("Fornecedor confirmou atraso adicional na integração fiscal, sem plano de contingência apresentado."),
    ).toBeVisible();
    await expect(page.getByText("Pontos de atenção")).toBeVisible();
    await expect(
      page.getByText("Fornecedor sem plano de contingência para o atraso na integração fiscal"),
    ).toBeVisible();
    await expect(page.getByText("Escalar o atraso ao comitê executivo antes do próximo go-live")).toBeVisible();
    await expect(page.getByText("Solicitar plano de contingência formal ao fornecedor")).toBeVisible();
    await expect(page.getByText("Aprovação do comitê executivo para replanejar o go-live")).toBeVisible();
    // Próximo passo: issues > 0, so the real, existing next step is suggested.
    await expect(page.getByText("Executar Avaliação de Riscos")).toBeVisible();

    // Dashboard reflects it too -- "Ações pendentes" strip is a single
    // instance, so the exact new total (Multilift 2 + Aurora 1+2 +
    // Implantacao SAP 1 = 6) is unambiguous.
    await page.locator('a[href="/dashboard"]').filter({ visible: true }).first().click();
    await expect(page).toHaveURL(/\/dashboard/);
    const acoesCard = page.getByText("Ações pendentes").locator("xpath=..");
    await expect(acoesCard.getByText("6")).toBeVisible();
  });

  test("on failure on the meeting tab, keeps the modal open and preserves the typed context", async ({
    page,
  }) => {
    await setWorkspaceScenario("analyzeMeeting", "rate_limited");
    await login(page);
    await page.goto("/workspace/Aurora");

    await page.getByRole("button", { name: "Analisar Projeto" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("tab", { name: "O que mudou na última reunião?" }).click();
    const context = "Contexto detalhado o suficiente para passar da validação de tamanho mínimo.";
    await dialog.getByLabel("Contexto da reunião").fill(context);
    await dialog.getByRole("button", { name: "Executar Análise" }).click();

    await expect(dialog).toBeVisible();
    await expect(dialog.getByLabel("Contexto da reunião")).toHaveValue(context);
    await expect(
      dialog.getByText("Muitas análises em pouco tempo. Aguarde e tente novamente."),
    ).toBeVisible();
  });
});
