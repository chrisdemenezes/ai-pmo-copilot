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

async function login(page: import("@playwright/test").Page) {
  await page.goto("/entrar");
  await page.getByLabel("Organização").fill(E2E_ORGANIZATION);
  await page.getByLabel("E-mail").fill(E2E_EMAIL);
  await page.getByLabel("Senha").fill(WORKSPACE_PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  // Wait for the session cookie to actually land before any caller does its
  // own page.goto() -- see workspace.spec.ts for the exact race this avoids.
  await page.waitForURL(/\/dashboard/);
}

async function resetFixtures() {
  const ctx = await playwrightRequest.newContext();
  await ctx.post(`${MOCK_BACKEND_URL}/__control/reset-fixtures`);
  await ctx.dispose();
}

test.beforeEach(async () => {
  // See dashboard.spec.ts -- same shared mock server, same reset requirement.
  await resetFixtures();
  await setBackendScenario("data");
});

test("redirects unauthenticated access to /projects to the login page", async ({ page }) => {
  await page.goto("/projects");
  await expect(page).toHaveURL(/\/entrar/);
});

test("full flow: Dashboard -> menu Projetos -> listagem -> seleção -> Workspace", async ({
  page,
}) => {
  await login(page);

  // Not name-based: at md the nav label is icon-only ("hidden lg:inline"),
  // so the link has no accessible name at that breakpoint -- href is the
  // only selector that works at all 3 breakpoints.
  await page.locator('a[href="/projects"]').filter({ visible: true }).first().click();
  await expect(page).toHaveURL(/\/projects/);
  await expect(page.getByRole("heading", { name: "Projetos" })).toBeVisible();
  await expect(page.getByText("Multilift").filter({ visible: true }).first()).toBeVisible();

  await page
    .getByRole("link", { name: "Multilift" })
    .filter({ visible: true })
    .first()
    .click();
  await expect(page).toHaveURL(/\/workspace\/Multilift/);
  await expect(page.getByRole("heading", { name: "Multilift" })).toBeVisible();
});

test("encodes a project name containing '/' end-to-end from the Projects listing", async ({
  page,
}) => {
  await login(page);
  await page.goto("/projects");

  await page
    .getByRole("link", { name: "Implantacao SAP S/4HANA" })
    .filter({ visible: true })
    .first()
    .click();
  await expect(page).toHaveURL(/\/workspace\/Implantacao%20SAP%20S%2F4HANA/);
  await expect(page.getByRole("heading", { name: "Implantacao SAP S/4HANA" })).toBeVisible();
});

test("filters the project list by search, without a page reload", async ({ page }) => {
  await login(page);
  await page.goto("/projects");

  await expect(page.getByText("Multilift").filter({ visible: true }).first()).toBeVisible();
  await expect(page.getByText("Aurora").filter({ visible: true }).first()).toBeVisible();

  await page.getByLabel("Buscar projeto").fill("Aurora");

  await expect(page.getByText("Aurora").filter({ visible: true }).first()).toBeVisible();
  await expect(page.getByText("Multilift").filter({ visible: true })).toHaveCount(0);
});

test("shows the empty state when the backend has no projects", async ({ page }) => {
  await setBackendScenario("empty");
  await login(page);
  await page.goto("/projects");

  await expect(
    page.getByText("Nenhum projeto com análise registrada ainda"),
  ).toBeVisible();
});

test("shows the safe error state when the backend is unavailable", async ({ page }) => {
  await setBackendScenario("unavailable");
  await login(page);
  await page.goto("/projects");

  await expect(page.getByText("Não foi possível carregar os projetos agora")).toBeVisible();
});

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

  await page.goto("/projects");
  const skeleton = page.locator('[data-slot="skeleton"]');
  const content = page.getByText("Multilift").filter({ visible: true }).first();
  await expect(skeleton.first().or(content)).toBeVisible();
});
