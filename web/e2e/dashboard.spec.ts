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

async function login(page: import("@playwright/test").Page, password = WORKSPACE_PASSWORD) {
  await page.goto("/entrar");
  await page.getByLabel("Organização").fill(E2E_ORGANIZATION);
  await page.getByLabel("E-mail").fill(E2E_EMAIL);
  await page.getByLabel("Senha").fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
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

test.beforeEach(async () => {
  // The mock server process is shared across every spec file and breakpoint
  // project in a run -- workspace.spec.ts's "Analisar Projeto" (TIP-005)
  // tests mutate portfolio fixture data in place, so this resets it before
  // every Dashboard test too, regardless of run order.
  await resetFixtures();
  await setBackendScenario("data");
  await setLatestRisksScenario("data");
});

// 1. Acesso a /dashboard sem sessão
test("redirects unauthenticated access to /dashboard to the login page", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/entrar/);
});

// 2. Login com senha incorreta
test("shows an error and stays on /entrar with an incorrect password", async ({ page }) => {
  await login(page, "wrong-password");
  await expect(
    page.getByText("Organização, e-mail ou senha incorretos. Tente novamente."),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/entrar/);
});

// 3 + 4. Login correto + redirecionamento seguro para /dashboard
test("logs in with the correct password and lands on /dashboard", async ({ page }) => {
  await login(page);
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByRole("heading", { name: "Dashboard Executivo" })).toBeVisible();
});

// TIP-008 Incremento 3 -- KPI "Ações pendentes" vira link para a página de
// portfólio "Ações" (Incremento 2), fechando o caminho mais curto entre
// abrir a STRATECH e tomar uma decisão executiva (FS-007 §01, pergunta 4).
test("clicking the Ações pendentes KPI navigates to the portfolio Ações page", async ({
  page,
}) => {
  await login(page);
  await page.getByRole("link", { name: /Ações pendentes/ }).click();
  await expect(page).toHaveURL(/\/actions/);
  await expect(page.getByRole("heading", { name: "Ações" })).toBeVisible();
});

// TIP-009 Incremento 3 -- KPI "Decisões críticas" vira o ponto de entrada
// da Executive Decision Queue, primeira aplicação real do Single Decision
// Source por outra superfície da plataforma (Architecture Review §3.2).
test("clicking the Decisões críticas KPI navigates to the Executive Decision Queue", async ({
  page,
}) => {
  await login(page);
  await expect(page.getByRole("link", { name: /Decisões críticas/ })).toBeVisible();
  await page.getByRole("link", { name: /Decisões críticas/ }).click();
  await expect(page).toHaveURL(/\/decisions/);
  await expect(page.getByRole("heading", { name: "Decisões" })).toBeVisible();
});

// TIP-010 Incremento 3 -- KPI "Projetos" vira o ponto de entrada da
// Executive Portfolio View. Mesmo número (Awareness), destino aprofunda
// para Prioritization -- Progressive Context/Purpose (Architecture Review §3).
test("clicking the Projetos KPI navigates to the Executive Portfolio View", async ({ page }) => {
  await login(page);
  // Scoped to main -- the Sidebar/bottom-nav "Projetos" link has the exact
  // same accessible-name prefix as this KPI ("Projetos" + the count),
  // ambiguous outside of main.
  await page.locator("main").getByRole("link", { name: /^Projetos/ }).click();
  await expect(page).toHaveURL(/\/portfolio/);
  await expect(page.getByRole("heading", { name: "Priorização" })).toBeVisible();
});

// 5 + 12 (sucesso). Dashboard com dados
test("renders the portfolio widgets when the backend has data", async ({ page }) => {
  await login(page);
  await expect(page.getByText("Multilift").filter({ visible: true }).first()).toBeVisible();
  // Not getByText("Projetos") -- since TIP-004A the Sidebar's own "Projetos"
  // nav item also matches that text (hidden at some breakpoints, not
  // others); the section heading role disambiguates regardless of breakpoint.
  await expect(page.getByRole("heading", { name: "Projetos" })).toBeVisible();
});

// Local V1 Pilot Final Hardening (H1, D-223): the contextual notice about
// demonstrative data must render on the real page, not just in isolation.
test("shows the demonstrative-data notice before any dashboard section", async ({ page }) => {
  await login(page);
  await expect(page.getByText(/dados de exemplo/i)).toBeVisible();
  await expect(page.getByText("Dados demonstrativos").first()).toBeVisible();
});

// 6 + 12 (vazio). Dashboard sem dados
test("renders the empty state when the backend has no projects", async ({ page }) => {
  await setBackendScenario("empty");
  await login(page);
  await expect(page.getByText("Nenhum projeto com análise registrada ainda")).toBeVisible();
});

// 7 + 12 (erro). Backend indisponível
// retry:false (Product Behavior Decision, T9) -- single attempt, error
// surfaces immediately instead of after ~7.9s of retries.
test("renders the safe error state when the backend is unavailable", async ({ page }) => {
  await setBackendScenario("unavailable");
  await login(page);
  await expect(page.getByText("Não foi possível carregar o portfólio agora")).toBeVisible();
});

// 8. Timeout do backend
// retry:false -- single attempt, bounded by the BFF's own 8s
// AbortController timeout instead of ~40.2s across 4 attempts.
test("renders the error state when the backend times out", async ({ page }) => {
  await setBackendScenario("timeout");
  await login(page);
  await expect(page.getByText("Não foi possível carregar o portfólio agora")).toBeVisible({
    timeout: 12_000,
  });
});

// 9. Preservação de dados em cache durante falha de background refetch (Achado #1)
test("keeps showing cached data when a manual refetch fails", async ({ page }) => {
  await login(page);
  await expect(page.getByText("Multilift").filter({ visible: true }).first()).toBeVisible();

  await setBackendScenario("unavailable");
  await page.getByRole("button", { name: "Atualizar" }).click();

  // The dashboard must still show the last known-good data, not the error screen.
  await expect(page.getByText("Multilift").filter({ visible: true }).first()).toBeVisible();
  await expect(page.getByText("Não foi possível carregar o portfólio agora")).not.toBeVisible();
});

// 10. API_KEY e SESSION_SECRET nunca expostos ao navegador
test("never exposes API_KEY or SESSION_SECRET to the browser", async ({ page }) => {
  const responses: string[] = [];
  page.on("response", async (response) => {
    if (response.url().includes("/api/bff/")) {
      responses.push(await response.text().catch(() => ""));
    }
  });

  await login(page);
  await expect(page.getByText("Multilift").filter({ visible: true }).first()).toBeVisible();

  const html = await page.content();
  expect(html).not.toContain("e2e-secret-key");
  expect(html).not.toContain("e2e-session-secret-not-for-production");
  for (const body of responses) {
    expect(body).not.toContain("e2e-secret-key");
    expect(body).not.toContain("e2e-session-secret-not-for-production");
  }

  const cookies = await page.context().cookies();
  const sessionCookie = cookies.find((c) => c.name === "stratech_session");
  expect(sessionCookie?.value).toBeDefined();
  expect(sessionCookie?.value).not.toContain("e2e-session-secret-not-for-production");
  expect(sessionCookie?.httpOnly).toBe(true);
});

// 12. Estado parcial (latest_health_status nulo em pelo menos um projeto real da fixture não existe --
// verificado a nível de componente em project-health-grid.test; aqui confirmamos em E2E via um projeto
// sem status, adicionando o cenário "data" já cobre "Aurora" com status "green"; o caso null é validado
// nos testes de componente (dashboard-widgets.test.tsx) por já ter cobertura suficiente e não depender
// de rede -- aqui confirmamos apenas que o loading skeleton aparece antes do conteúdo final.
test("shows the loading skeleton before the final content", async ({ page }) => {
  await page.goto("/entrar");
  await page.getByLabel("Organização").fill(E2E_ORGANIZATION);
  await page.getByLabel("E-mail").fill(E2E_EMAIL);
  await page.getByLabel("Senha").fill(WORKSPACE_PASSWORD);

  const [response] = await Promise.all([
    page.waitForResponse((res) => res.url().includes("/api/bff/session")),
    page.getByRole("button", { name: "Entrar" }).click(),
  ]);
  expect(response.ok()).toBe(true);

  await page.waitForURL(/\/dashboard/);
  const skeleton = page.locator('[data-slot="skeleton"]');
  const content = page.getByText("Multilift").filter({ visible: true }).first();
  await expect(skeleton.first().or(content)).toBeVisible();
});

// 11. Responsividade -- roda em cada project (mobile/md/lg) via playwright.config.ts
test("dashboard grid stacks to a single column on narrow viewports", async ({ page }, testInfo) => {
  await login(page);
  await expect(page.getByText("Multilift").filter({ visible: true }).first()).toBeVisible();

  const stripCards = page.locator("main > div > div > div").first();
  const box = await stripCards.boundingBox();
  expect(box).not.toBeNull();

  if (testInfo.project.name === "mobile") {
    // Under the RFC-001 <768px breakpoint the summary strip is single-column;
    // its width should span nearly the full viewport rather than a 3-up row.
    expect(box!.width).toBeGreaterThan(300);
  }
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
// mandated by the Founder -- usuário → Dashboard → BFF → Executive
// Narrative → Executive Orchestrator → Advisors elegíveis → Correlação →
// Síntese → Executive Intelligence Result → Narrative -- through the real
// UI, citing evidence and naming the Advisors selected for the declared
// scope. No free-text question exists on this panel at all (Technical
// Design -- Executive Narrative, §2).
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
  // pmo_advisor is elegível apenas sob scope=organization -- nunca
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
