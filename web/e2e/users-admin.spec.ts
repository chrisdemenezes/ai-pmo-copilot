import { test, expect, request as playwrightRequest } from "@playwright/test";

const MOCK_BACKEND_URL = "http://localhost:4100";
const E2E_ORGANIZATION = "e2e-organization";
const E2E_EMAIL = "e2e@stratech.local";
const WORKSPACE_PASSWORD = "e2e-workspace-password";

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
});

/**
 * User Management (Enterprise Administration Capability, Wave 2) --
 * end-to-end coverage of the full Backend -> BFF -> Frontend chain:
 * list/search/filter, create, edit, activate/deactivate, assign/remove
 * role, and the governance guards (self-deactivation, last active admin).
 * Fixtures: e2e/mock-backend.mjs's ADMIN_USERS (id 1 "Ana Souza",
 * organization_admin, active; id 2 "Bruno Castro", pmo, active; id 3
 * "Carla Mendes", viewer, inactive). The E2E login always resolves to
 * user_id 1 -- i.e. "Ana Souza" is always the logged-in actor here.
 */

const MOBILE_BREAKPOINT = 768;

test("navigates from the sidebar to Administração", async ({ page }) => {
  await login(page);

  // At md (768-1023px) the sidebar is an icon-only rail (label hidden
  // until lg) -- same convention as shell.spec.ts's breakpoint-aware nav
  // locator, since a name-based lookup only works where the label is
  // actually visible.
  const visibleNav = (await page.viewportSize())!.width < MOBILE_BREAKPOINT
    ? page.getByTestId("bottom-nav")
    : page.getByTestId("sidebar-nav");
  await visibleNav.locator('a[href="/administracao/usuarios"]').click();

  await expect(page).toHaveURL(/\/administracao\/usuarios/);
  await expect(page.getByRole("heading", { name: "Usuários" })).toBeVisible();
});

test("lists the seeded users with name, email, status and roles", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/usuarios");

  const anaRow = page.getByRole("row", { name: /Ana Souza/ });
  const carlaRow = page.getByRole("row", { name: /Carla Mendes/ });
  await expect(anaRow).toBeVisible();
  await expect(carlaRow).toBeVisible();
  await expect(page.getByText("ana.admin@example.com")).toBeVisible();

  await expect(carlaRow.getByText("Inativo")).toBeVisible();
  await expect(anaRow.getByText("Ativo")).toBeVisible();
  await expect(anaRow.getByText("organization_admin")).toBeVisible();
});

test("searches by name and by email, without a page reload", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/usuarios");

  await page.getByLabel("Pesquisar usuários").fill("bruno");
  await expect(page.getByRole("row", { name: /Bruno Castro/ })).toBeVisible();
  await expect(page.getByRole("row", { name: /Ana Souza/ })).not.toBeVisible();

  await page.getByLabel("Pesquisar usuários").fill("carla.viewer@example.com");
  await expect(page.getByRole("row", { name: /Carla Mendes/ })).toBeVisible();
  await expect(page.getByRole("row", { name: /Bruno Castro/ })).not.toBeVisible();
});

test("filters by status", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/usuarios");

  await page.getByLabel("Filtrar por status").click();
  await page.getByRole("option", { name: "Inativos" }).click();

  await expect(page.getByRole("row", { name: /Carla Mendes/ })).toBeVisible();
  await expect(page.getByRole("row", { name: /Ana Souza/ })).not.toBeVisible();
});

test("filters by role", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/usuarios");

  await page.getByLabel("Filtrar por papel").click();
  await page.getByRole("option", { name: "pmo", exact: true }).click();

  await expect(page.getByRole("row", { name: /Bruno Castro/ })).toBeVisible();
  await expect(page.getByRole("row", { name: /Ana Souza/ })).not.toBeVisible();
});

test("shows the empty state when no user matches the search", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/usuarios");

  await page.getByLabel("Pesquisar usuários").fill("ninguem-com-este-nome");
  await expect(page.getByText("Nenhum usuário corresponde à busca/filtros atuais.")).toBeVisible();
});

test("creates a user end to end (Backend -> BFF -> Frontend)", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/usuarios");

  await page.getByRole("button", { name: "Novo usuário" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("E-mail").fill("nova.pessoa@example.com");
  await dialog.getByLabel("Nome").fill("Nova Pessoa");
  await dialog.getByLabel("Senha inicial").fill("uma-senha-forte");
  await dialog.getByLabel("Papel", { exact: true }).click();
  await page.getByRole("option", { name: "viewer" }).click();
  await dialog.getByRole("button", { name: "Cadastrar" }).click();

  await expect(page.getByText("Usuário cadastrado")).toBeVisible();
  await expect(page.getByRole("row", { name: /Nova Pessoa/ })).toBeVisible();
});

test("rejects creating a user with a duplicate e-mail (case-insensitive)", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/usuarios");

  await page.getByRole("button", { name: "Novo usuário" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("E-mail").fill("ANA.ADMIN@Example.com");
  await dialog.getByLabel("Nome").fill("Duplicada");
  await dialog.getByLabel("Senha inicial").fill("uma-senha-forte");
  await dialog.getByLabel("Papel", { exact: true }).click();
  await page.getByRole("option", { name: "viewer" }).click();
  await dialog.getByRole("button", { name: "Cadastrar" }).click();

  await expect(dialog.getByRole("alert")).toContainText(/already exists/i);
});

test("edits a user's name and email", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/usuarios");

  const bruno = page.getByRole("row", { name: /Bruno Castro/ });
  await bruno.getByRole("button", { name: /Editar/ }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Nome").fill("Bruno C. Silva");
  await dialog.getByRole("button", { name: "Salvar" }).click();

  await expect(page.getByText("Usuário atualizado")).toBeVisible();
  await expect(page.getByRole("row", { name: /Bruno C\. Silva/ })).toBeVisible();
});

test("activates an inactive user", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/usuarios");

  const carla = page.getByRole("row", { name: /Carla Mendes/ });
  await carla.getByRole("button", { name: "Ativar" }).click();

  await expect(page.getByText("Usuário ativado")).toBeVisible();
  await expect(carla.getByText("Ativo")).toBeVisible();
});

test("deactivates a user after confirming the sensitive operation", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/usuarios");

  const bruno = page.getByRole("row", { name: /Bruno Castro/ });
  await bruno.getByRole("button", { name: "Inativar" }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText(/Inativar Bruno Castro\?/)).toBeVisible();
  await dialog.getByRole("button", { name: "Inativar" }).click();

  await expect(page.getByText("Usuário inativado")).toBeVisible();
  await expect(bruno.getByText("Inativo")).toBeVisible();
});

test("an administrator cannot deactivate their own account", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/usuarios");

  // The logged-in actor (user_id 1) is Ana Souza, the sole active admin.
  const ana = page.getByRole("row", { name: /Ana Souza/ });
  await ana.getByRole("button", { name: "Inativar" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Inativar" }).click();

  await expect(dialog.getByRole("alert")).toContainText(/cannot deactivate their own account/i);
});

test("assigns and removes a role", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/usuarios");

  const carla = page.getByRole("row", { name: /Carla Mendes/ });
  await carla.getByRole("button", { name: /Papéis/ }).click();

  const rolesDialog = page.getByRole("dialog");
  await expect(rolesDialog.getByText("viewer")).toBeVisible();

  await rolesDialog.getByLabel("Atribuir novo papel").click();
  await page.getByRole("option", { name: "pmo" }).click();
  await rolesDialog.getByRole("button", { name: "Atribuir" }).click();
  await expect(page.getByText("Papel atribuído")).toBeVisible();

  await rolesDialog.getByRole("button", { name: "Remover papel viewer" }).click();
  const confirmDialog = page.getByRole("dialog").filter({ hasText: "Remover papel" });
  await confirmDialog.getByRole("button", { name: "Remover" }).click();
  await expect(page.getByText("Papel removido")).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(carla.getByText("pmo")).toBeVisible();
});
