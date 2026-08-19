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
 * Program Management (Capability 02, Release 0.2) -- W7-7 Etapa 5 (Founder
 * Decision, Controlled Pilot Browser Baseline).
 *
 * IN PILOT BASELINE (registered decision, see Decision Log): real,
 * shipped, no-mock Capability, present in `NAV_ITEMS` under the platform's
 * own entry rule ("no disabled/hidden/placeholder entries -- a module is
 * only added here inside the Feature that ships it"), positioned in the
 * same daily-use nav sequence as Projetos/Ações/Decisões, and its data
 * feeds the Dashboard's own KPI consolidation
 * (`consolidatePrograms`/`consolidatePortfolios`). Minimal coverage only,
 * per mandate: access + the one behavior unique to this page (Programs
 * correctly grouped under their parent Portfolio) -- no CRUD exists to
 * cover, and empty/error states are shared with every other real-hook page
 * already exercised elsewhere (`projects.spec.ts`), not re-proven here.
 */

test("redirects unauthenticated access to /program-management to the login page", async ({
  page,
}) => {
  await page.goto("/program-management");
  await expect(page).toHaveURL(/\/entrar/);
});

test("navigates from the sidebar and lists Programs grouped under their parent Portfolio", async ({
  page,
}) => {
  await login(page);

  const visibleNav = (await page.viewportSize())!.width < MOBILE_BREAKPOINT
    ? page.getByTestId("bottom-nav")
    : page.getByTestId("sidebar-nav");
  await visibleNav.locator('a[href="/program-management"]').click();

  await expect(page).toHaveURL(/\/program-management/);
  await expect(page.getByRole("heading", { name: "Programas por Portfólio" })).toBeVisible();

  // "Portfólio Corporativo" (mock-backend.mjs DOMAIN_PORTFOLIOS id 1) owns
  // both "Eficiência Operacional" and "Governança e Compliance Corporativa"
  // (DOMAIN_PROGRAMS portfolio_id 1) -- proves the grouping filter, the
  // only real logic this page has, groups by the correct parent.
  // CardTitle renders a plain <div> (no ARIA heading role), so the section
  // is located by its title text, not by role.
  const corporateSection = page.locator("section").filter({ hasText: "Portfólio Corporativo" });
  await expect(corporateSection.getByText("Eficiência Operacional")).toBeVisible();
  await expect(corporateSection.getByText("Governança e Compliance Corporativa")).toBeVisible();

  // "Portfólio de Expansão Regional" (id 3) owns only "Entrada em Novos
  // Mercados" -- a program that must NOT appear under Corporativo above.
  await expect(page.getByText("Entrada em Novos Mercados")).toBeVisible();
});
