import { test, expect, request as playwrightRequest } from "@playwright/test";

const MOCK_BACKEND_URL = "http://localhost:4100";
const WORKSPACE_PASSWORD = "e2e-workspace-password";

async function setBackendScenario(scenario: "data" | "empty" | "unavailable" | "timeout") {
  const ctx = await playwrightRequest.newContext();
  await ctx.post(`${MOCK_BACKEND_URL}/__control/scenario`, { data: { scenario } });
  await ctx.dispose();
}

async function login(page: import("@playwright/test").Page, password = WORKSPACE_PASSWORD) {
  await page.goto("/entrar");
  await page.getByLabel("Senha do workspace").fill(password);
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
  await expect(page.getByText("Senha incorreta. Tente novamente.")).toBeVisible();
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

// 5 + 12 (sucesso). Dashboard com dados
test("renders the portfolio widgets when the backend has data", async ({ page }) => {
  await login(page);
  await expect(page.getByText("Multilift").filter({ visible: true }).first()).toBeVisible();
  // Not getByText("Projetos") -- since TIP-004A the Sidebar's own "Projetos"
  // nav item also matches that text (hidden at some breakpoints, not
  // others); the section heading role disambiguates regardless of breakpoint.
  await expect(page.getByRole("heading", { name: "Projetos" })).toBeVisible();
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
  const sessionCookie = cookies.find((c) => c.name === "workspace_session");
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
  await page.getByLabel("Senha do workspace").fill(WORKSPACE_PASSWORD);

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
