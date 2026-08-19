import { test, expect } from "@playwright/test";

const E2E_ORGANIZATION = "e2e-organization";
const E2E_EMAIL = "e2e@stratech.local";
const WORKSPACE_PASSWORD = "e2e-workspace-password";

async function login(page: import("@playwright/test").Page) {
  await page.goto("/entrar");
  await page.getByLabel("Organização").fill(E2E_ORGANIZATION);
  await page.getByLabel("E-mail").fill(E2E_EMAIL);
  await page.getByLabel("Senha").fill(WORKSPACE_PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL(/\/dashboard/);
}

/**
 * Mission Control (Sprint 1, Diretriz Complementar) -- W7-7 Etapa 3
 * (Founder Decision, Controlled Pilot Browser Baseline).
 *
 * Minimal by design: the page is entirely static mock data
 * (`web/lib/mock/mission-control-data.ts`, no fetch/hook), so there is no
 * loading/error/empty state to prove -- only that an authenticated user
 * reaches it and the essential executive sections actually render. The
 * page's own docstring documents its one real permission fact: access is
 * "authenticated", not yet "Founder"-scoped (RBAC is Épico 3, Not Started)
 * -- that IS the relevant permission behavior today, asserted below rather
 * than an invented restriction the product doesn't have yet.
 */

test("redirects unauthenticated access to /mission-control to the login page", async ({
  page,
}) => {
  await page.goto("/mission-control");
  await expect(page).toHaveURL(/\/entrar/);
});

test("renders the Founder panel with its essential executive sections for any authenticated user", async ({
  page,
}) => {
  await login(page);
  await page.goto("/mission-control");

  await expect(page.getByRole("heading", { name: "Painel do Founder" })).toBeVisible();
  // Documents the real, current permission state (not yet Founder-restricted)
  // instead of asserting a restriction the product doesn't implement yet.
  await expect(page.getByText("Acesso não restrito ainda — RBAC no Épico 3")).toBeVisible();

  await expect(page.getByRole("heading", { name: "Product Pulse" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Enterprise Program — Waves" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Decision Log — recentes" })).toBeVisible();
});
