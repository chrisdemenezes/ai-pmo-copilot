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

// V1 Product & Capability Completion, Pacote A: Decision Support e
// Executive Narrative deixaram de viver em /dashboard e ganharam esta
// rota dedicada -- login() aqui navega explicitamente para ela em vez de
// aceitar o destino padrão pós-login (/dashboard).
async function login(page: import("@playwright/test").Page) {
  await page.goto("/entrar");
  await page.getByLabel("Organização").fill(E2E_ORGANIZATION);
  await page.getByLabel("E-mail").fill(E2E_EMAIL);
  await page.getByLabel("Senha").fill(WORKSPACE_PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL(/\/dashboard/);
  await page.goto("/inteligencia-executiva");
}

test.beforeEach(async () => {
  await resetFixtures();
  await setBackendScenario("data");
  await setLatestRisksScenario("data");
});

test("redirects unauthenticated access to /inteligencia-executiva to the login page", async ({ page }) => {
  await page.goto("/inteligencia-executiva");
  await expect(page).toHaveURL(/\/entrar/);
});

test("navigates via the Inteligência Executiva nav item to the dedicated page", async ({ page }) => {
  await page.goto("/entrar");
  await page.getByLabel("Organização").fill(E2E_ORGANIZATION);
  await page.getByLabel("E-mail").fill(E2E_EMAIL);
  await page.getByLabel("Senha").fill(WORKSPACE_PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL(/\/dashboard/);

  await page.locator("main").getByRole("link", { name: /^Inteligência Executiva/ }).click();
  await expect(page).toHaveURL(/\/inteligencia-executiva/);
  await expect(page.getByRole("heading", { name: "Inteligência Executiva" })).toBeVisible();
});

// Wave 6 -- Decision Support: end-to-end proof of the full chain mandated
// by the Founder -- usuário → pergunta executiva → Decision Support →
// Executive Orchestrator → Advisors → resposta integrada -- through the
// real UI (backend → BFF → hook → panel), citing evidence and naming the
// Advisors that produced the synthesis.
test("Decision Support answers an executive question with organization scope, citing its Advisors", async ({
  page,
}) => {
  await login(page);

  const section = page.locator("section", { has: page.getByRole("heading", { name: "Decision Support" }) });
  await section.scrollIntoViewIfNeeded();
  await section.getByLabel("Pergunta executiva").fill("Existe risco relevante para a entrega?");

  await section.getByRole("combobox", { name: "Escopo" }).click();
  await page.getByRole("option", { name: "Organização" }).click();

  await section.getByRole("button", { name: "Perguntar" }).click();

  await expect(section.getByText(/Existe risco de escalação/)).toBeVisible();
  // { exact: true } disambiguates from the citation list item's own text
  // ("risk_advisor: Análise de risco #201"), never a strict-mode collision.
  await expect(section.getByText("risk_advisor", { exact: true })).toBeVisible();
  await expect(section.getByText("delivery_advisor", { exact: true })).toBeVisible();
  await expect(section.getByText(/Análise de risco/)).toBeVisible();
  // Composition Trace (Founder Decision -- Wave 6 Final Consolidation
  // Actions, D-165): risk_advisor/delivery_advisor form a declared
  // structural pair -- presented as a possible conflict, never
  // automatically resolved.
  await expect(section.getByText("Como esta resposta foi construída")).toBeVisible();
  await expect(section.getByText(/Possíveis conflitos identificados/)).toBeVisible();
  await expect(section.getByText(/nunca resolvidos automaticamente/)).toBeVisible();
});

// Explicit Scope (Vision, Princípio 13): "Organização" is never the
// starting state -- the question can be typed, but the panel must not
// allow submission until a scope is explicitly chosen.
test("Decision Support never submits without an explicitly chosen scope", async ({ page }) => {
  await login(page);

  const section = page.locator("section", { has: page.getByRole("heading", { name: "Decision Support" }) });
  await section.scrollIntoViewIfNeeded();
  await section.getByLabel("Pergunta executiva").fill("Existe risco relevante para a entrega?");

  await expect(section.getByRole("button", { name: "Perguntar" })).toBeDisabled();
});

// Base Insuficiente: declared explicitly, never a blank or invented answer.
test("Decision Support declares Base Insuficiente for a question no Advisor can answer", async ({
  page,
}) => {
  await login(page);

  const section = page.locator("section", { has: page.getByRole("heading", { name: "Decision Support" }) });
  await section.scrollIntoViewIfNeeded();
  await section.getByLabel("Pergunta executiva").fill("Qual a previsão do tempo hoje?");

  await section.getByRole("combobox", { name: "Escopo" }).click();
  await page.getByRole("option", { name: "Organização" }).click();
  await section.getByRole("button", { name: "Perguntar" }).click();

  await expect(section.getByText("Base insuficiente")).toBeVisible();
});

// Wave 6 -- Executive Narrative: end-to-end proof of the full chain
// mandated by the Founder -- usuário → Inteligência Executiva → BFF →
// Executive Narrative → Executive Orchestrator → Advisors elegíveis →
// Correlação → Síntese → Executive Intelligence Result → Narrative --
// through the real UI, citing evidence and naming the Advisors selected
// for the declared scope. No free-text question exists on this panel at
// all (Technical Design -- Executive Narrative, §2).
test("Executive Narrative generates a narrative with organization scope, naming its Advisors", async ({
  page,
}) => {
  await login(page);

  const section = page.locator("section", {
    has: page.getByRole("heading", { name: "Narrativa Executiva" }),
  });
  await section.scrollIntoViewIfNeeded();

  await section.getByRole("combobox", { name: "Escopo" }).click();
  await page.getByRole("option", { name: "Organização" }).click();
  await section.getByRole("button", { name: "Gerar Narrativa" }).click();

  await expect(section.getByText(/Estado executivo da organização/)).toBeVisible();
  // { exact: true } disambiguates from the citation list item's own text.
  await expect(section.getByText("risk_advisor", { exact: true })).toBeVisible();
  await expect(section.getByText("delivery_advisor", { exact: true })).toBeVisible();
  // pmo_advisor é elegível apenas sob scope=organization -- nunca
  // selecionado por Decision Support para uma pergunta lexicalmente
  // restrita a risco/entrega (prova indireta de não-aliasing, reforçada
  // no teste dedicado abaixo).
  await expect(section.getByText("pmo_advisor", { exact: true })).toBeVisible();
  await expect(section.getByText(/Análise de risco/)).toBeVisible();
  // Composition Trace visível (Founder Decision -- Wave 6 Final
  // Consolidation Actions, D-165) -- mesmo painel, nenhuma rota/tela nova.
  await expect(section.getByText("Como esta resposta foi construída")).toBeVisible();
  await expect(section.getByText(/Possíveis conflitos identificados/)).toBeVisible();
});

// Explicit Scope (Vision, Princípio 13): "Organização" is never the
// starting state -- the panel must not allow submission until a scope is
// explicitly chosen. Unlike Decision Support, there is no question field
// to fill first -- the button starts disabled with nothing else to type.
test("Executive Narrative never submits without an explicitly chosen scope", async ({ page }) => {
  await login(page);

  const section = page.locator("section", {
    has: page.getByRole("heading", { name: "Narrativa Executiva" }),
  });
  await section.scrollIntoViewIfNeeded();

  await expect(section.getByRole("button", { name: "Gerar Narrativa" })).toBeDisabled();
});

// Base Insuficiente: a Project with zero seeded evidence -- both
// risk_advisor and delivery_advisor are selected but neither gathers
// anything, declared explicitly, never a blank or invented narrative.
test("Executive Narrative declares Base Insuficiente for a project scope with no evidence", async ({
  page,
}) => {
  await login(page);

  const section = page.locator("section", {
    has: page.getByRole("heading", { name: "Narrativa Executiva" }),
  });
  await section.scrollIntoViewIfNeeded();

  await section.getByRole("combobox", { name: "Escopo" }).click();
  await page.getByRole("option", { name: "Projeto" }).click();
  await section.getByRole("combobox", { name: "Projeto" }).click();
  await page.getByRole("option", { name: "Automação de Faturamento" }).click();
  await section.getByRole("button", { name: "Gerar Narrativa" }).click();

  await expect(section.getByText("Base insuficiente")).toBeVisible();
});

// Wave 6 -- Executive Narrative scope behavior: scope=portfolio selects
// exclusively portfolio_advisor, distinct from both the project scope
// (risk_advisor+delivery_advisor) and the organization scope (7 Advisors)
// already proven above -- the three scopes are structurally distinct
// through the real UI, not just at the API layer.
test("Executive Narrative with portfolio scope selects only portfolio_advisor", async ({ page }) => {
  await login(page);

  const section = page.locator("section", {
    has: page.getByRole("heading", { name: "Narrativa Executiva" }),
  });
  await section.scrollIntoViewIfNeeded();

  await section.getByRole("combobox", { name: "Escopo" }).click();
  await page.getByRole("option", { name: "Portfólio" }).click();
  await section.getByRole("combobox", { name: "Portfólio" }).click();
  await page.getByRole("option", { name: "Portfólio Corporativo" }).click();
  await section.getByRole("button", { name: "Gerar Narrativa" }).click();

  await expect(section.getByText("portfolio_advisor", { exact: true })).toBeVisible();
  await expect(section.getByText("risk_advisor", { exact: true })).not.toBeVisible();
});

// Non-aliasing (Founder -- Technical Design Executive Narrative, §2): the
// same organization, the same underlying data, but Decision Support's
// lexically narrow question selects only risk_advisor+delivery_advisor,
// while Executive Narrative's organization scope selects every eligible
// Advisor (7) -- structurally distinct sets produced by two different
// selection mechanisms, proven side by side in the real UI.
test("Decision Support and Executive Narrative select structurally different Advisor sets for the same scope", async ({
  page,
}) => {
  await login(page);

  const decisionSupportSection = page.locator("section", {
    has: page.getByRole("heading", { name: "Decision Support" }),
  });
  await decisionSupportSection.scrollIntoViewIfNeeded();
  await decisionSupportSection.getByLabel("Pergunta executiva").fill("Existe risco relevante para a entrega?");
  await decisionSupportSection.getByRole("combobox", { name: "Escopo" }).click();
  await page.getByRole("option", { name: "Organização" }).click();
  await decisionSupportSection.getByRole("button", { name: "Perguntar" }).click();
  await expect(decisionSupportSection.getByText("risk_advisor", { exact: true })).toBeVisible();
  await expect(decisionSupportSection.getByText("pmo_advisor", { exact: true })).not.toBeVisible();

  const narrativeSection = page.locator("section", {
    has: page.getByRole("heading", { name: "Narrativa Executiva" }),
  });
  await narrativeSection.scrollIntoViewIfNeeded();
  await narrativeSection.getByRole("combobox", { name: "Escopo" }).click();
  await page.getByRole("option", { name: "Organização" }).click();
  await narrativeSection.getByRole("button", { name: "Gerar Narrativa" }).click();
  await expect(narrativeSection.getByText("risk_advisor", { exact: true })).toBeVisible();
  await expect(narrativeSection.getByText("pmo_advisor", { exact: true })).toBeVisible();
});
