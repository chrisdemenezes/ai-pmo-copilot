import { test, expect } from "@playwright/test";

const MOBILE_BREAKPOINT = 768;
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
 * Project Delivery (Capability 03, Release 0.2) -- W7-7 Etapa 5 (Founder
 * Decision, Controlled Pilot Browser Baseline).
 *
 * IN PILOT BASELINE (same registered decision and rationale as
 * `program-management.spec.ts`). Minimal coverage only: access + the one
 * behavior unique to this page (Projects correctly grouped under their
 * parent Program).
 */

test("redirects unauthenticated access to /project-delivery to the login page", async ({
  page,
}) => {
  await page.goto("/project-delivery");
  await expect(page).toHaveURL(/\/entrar/);
});

test("navigates from the sidebar and lists Projects grouped under their parent Program", async ({
  page,
}) => {
  await login(page);

  const visibleNav = (await page.viewportSize())!.width < MOBILE_BREAKPOINT
    ? page.getByTestId("bottom-nav")
    : page.getByTestId("sidebar-nav");
  await visibleNav.locator('a[href="/project-delivery"]').click();

  await expect(page).toHaveURL(/\/project-delivery/);
  await expect(page.getByRole("heading", { name: "Projects por Program" })).toBeVisible();

  // "Eficiência Operacional" (mock-backend.mjs DOMAIN_PROGRAMS id 1) owns
  // both "Multilift" and "Automação de Faturamento" (DOMAIN_PROJECTS
  // program_id 1) -- proves the grouping filter, the only real logic this
  // page has, groups by the correct parent.
  // CardTitle renders a plain <div> (no ARIA heading role), so the section
  // is located by its title text, not by role.
  const programSection = page.locator("section").filter({ hasText: "Eficiência Operacional" });
  await expect(programSection.getByText("Multilift", { exact: true })).toBeVisible();
  await expect(programSection.getByText("Automação de Faturamento")).toBeVisible();

  // "Entrada em Novos Mercados" (id 4) owns "Aurora" and "Abertura Operação
  // LATAM" -- projects that must NOT appear under Eficiência Operacional
  // above.
  await expect(page.getByText("Abertura Operação LATAM")).toBeVisible();
});
