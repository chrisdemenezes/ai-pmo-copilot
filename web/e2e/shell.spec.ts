import { test, expect, request as playwrightRequest } from "@playwright/test";

const MOCK_BACKEND_URL = "http://localhost:4100";
const E2E_ORGANIZATION = "e2e-organization";
const E2E_EMAIL = "e2e@stratech.local";
const WORKSPACE_PASSWORD = "e2e-workspace-password";
const MOBILE_BREAKPOINT = 768;

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
}

test.beforeEach(async () => {
  await setBackendScenario("data");
});

test("redirects the root route to /entrar when unauthenticated", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/entrar/);
});

test("redirects the root route to /dashboard when authenticated", async ({ page }) => {
  await login(page);
  await page.goto("/");
  await expect(page).toHaveURL(/\/dashboard/);
});

test("renders exactly fourteen nav items, only Dashboard active on /dashboard", async ({ page }) => {
  await login(page);

  const visibleNav = (await page.viewportSize())!.width < MOBILE_BREAKPOINT
    ? page.getByTestId("bottom-nav")
    : page.getByTestId("sidebar-nav");

  const links = visibleNav.getByRole("link");
  await expect(links).toHaveCount(14);
  await expect(links.first()).toHaveAttribute("aria-current", "page");
  await expect(links.first()).toHaveAttribute("href", "/dashboard");
  await expect(links.nth(1)).not.toHaveAttribute("aria-current", "page");
  await expect(links.nth(1)).toHaveAttribute("href", "/portfolio");
  await expect(links.nth(2)).not.toHaveAttribute("aria-current", "page");
  await expect(links.nth(2)).toHaveAttribute("href", "/projects");
  await expect(links.nth(3)).not.toHaveAttribute("aria-current", "page");
  await expect(links.nth(3)).toHaveAttribute("href", "/program-management");
  await expect(links.nth(4)).not.toHaveAttribute("aria-current", "page");
  await expect(links.nth(4)).toHaveAttribute("href", "/project-delivery");
  await expect(links.nth(5)).not.toHaveAttribute("aria-current", "page");
  await expect(links.nth(5)).toHaveAttribute("href", "/actions");
  await expect(links.nth(6)).not.toHaveAttribute("aria-current", "page");
  await expect(links.nth(6)).toHaveAttribute("href", "/decisions");
  await expect(links.nth(7)).not.toHaveAttribute("aria-current", "page");
  await expect(links.nth(7)).toHaveAttribute("href", "/aprendizados");
  await expect(links.nth(8)).not.toHaveAttribute("aria-current", "page");
  await expect(links.nth(8)).toHaveAttribute("href", "/administracao/usuarios");
  await expect(links.nth(9)).not.toHaveAttribute("aria-current", "page");
  await expect(links.nth(9)).toHaveAttribute("href", "/administracao/api-keys");
  await expect(links.nth(10)).not.toHaveAttribute("aria-current", "page");
  await expect(links.nth(10)).toHaveAttribute("href", "/administracao/sessoes");
  await expect(links.nth(11)).not.toHaveAttribute("aria-current", "page");
  await expect(links.nth(11)).toHaveAttribute("href", "/administracao/convites");
  await expect(links.nth(12)).not.toHaveAttribute("aria-current", "page");
  await expect(links.nth(12)).toHaveAttribute("href", "/administracao/documentos");
  await expect(links.nth(13)).not.toHaveAttribute("aria-current", "page");
  await expect(links.nth(13)).toHaveAttribute("href", "/mission-control");
});

test("shows the sidebar shape appropriate to the current breakpoint", async ({ page }) => {
  await login(page);
  const width = (await page.viewportSize())!.width;

  if (width < MOBILE_BREAKPOINT) {
    await expect(page.getByTestId("bottom-nav")).toBeVisible();
    await expect(page.getByTestId("sidebar-nav")).not.toBeVisible();
  } else {
    await expect(page.getByTestId("sidebar-nav")).toBeVisible();
    await expect(page.getByTestId("bottom-nav")).not.toBeVisible();
  }
});

test("the bottom nav bar does not overlap the last scrollable content on mobile", async ({
  page,
}) => {
  const width = (await page.viewportSize())!.width;
  test.skip(width >= MOBILE_BREAKPOINT, "mobile-only check");

  await login(page);
  const heading = page.getByRole("heading", { name: "Dashboard Executivo" });
  await expect(heading).toBeVisible();

  const bottomNavBox = await page.getByTestId("bottom-nav").boundingBox();
  const headingBox = await heading.boundingBox();
  expect(bottomNavBox).not.toBeNull();
  expect(headingBox).not.toBeNull();
  // Sanity check that the bottom bar sits at the foot of the viewport, not
  // stacked on top of page content.
  expect(bottomNavBox!.y).toBeGreaterThan(headingBox!.y);
});

/**
 * F6 (Local V1 Pilot Hardening Review, D-210/D-211): the desktop sidebar
 * (md/lg) used to grow past the viewport along with page content -- "Sair"
 * was only reachable by scrolling the entire page, not just the sidebar.
 * AppShell's outer container now caps at min-h-screen (was min-h-full) and
 * the sidebar is md:sticky md:top-0 md:h-screen. This test forces real
 * page-content overflow (independent of any one page's current fixture
 * data, which can change size over time) and proves the sidebar -- and the
 * "Sair" button inside it -- never leaves the viewport while the page
 * itself scrolls, on every affected breakpoint. Mobile is out of scope
 * here: it already uses genuine position:fixed, covered by the test above.
 */
test("keeps the sidebar pinned to the viewport while page content scrolls (md/lg)", async ({
  page,
}) => {
  const width = (await page.viewportSize())!.width;
  test.skip(width < MOBILE_BREAKPOINT, "md/lg-only check -- mobile uses position:fixed instead");

  await login(page);
  const sidebar = page.getByTestId("sidebar-nav");
  await expect(sidebar).toBeVisible();

  // Force overflow deterministically instead of depending on how much
  // content any one page happens to render today -- appended inside
  // app-content (AppShell's real children slot), matching where actual
  // page content grows, so the AppShell flex row genuinely grows past the
  // viewport just like it would with real tall content.
  await page.evaluate(() => {
    const spacer = document.createElement("div");
    spacer.setAttribute("data-testid", "e2e-scroll-spacer");
    spacer.style.height = "3000px";
    document.querySelector('[data-testid="app-content"]')!.appendChild(spacer);
  });

  const sidebarBoxBefore = await sidebar.boundingBox();
  expect(sidebarBoxBefore).not.toBeNull();
  expect(sidebarBoxBefore!.y).toBe(0);

  // Scroll comfortably inside the spacer (not to the exact bottom of the
  // page, which would leave only a sliver of it in view and make the
  // in-viewport check flaky). window.scrollTo (not page.mouse.wheel) so the
  // scroll always targets the page regardless of cursor position -- the
  // sidebar itself now carries md:overflow-y-auto, so a wheel event over it
  // would scroll the sidebar's own (empty) overflow instead of the page.
  await page.evaluate(() => {
    const spacer = document.querySelector('[data-testid="e2e-scroll-spacer"]') as HTMLElement;
    window.scrollTo(0, spacer.offsetTop + 500);
  });
  await expect(page.getByTestId("e2e-scroll-spacer")).toBeInViewport();

  // The sidebar must still be pinned at the top of the viewport, not
  // scrolled away with the rest of the page. Sub-pixel tolerance: browsers
  // can report a fraction of a pixel of drift on a sticky element depending
  // on scroll position, with no visible/functional effect.
  const sidebarBoxAfter = await sidebar.boundingBox();
  expect(sidebarBoxAfter).not.toBeNull();
  expect(Math.abs(sidebarBoxAfter!.y)).toBeLessThan(1);
  await expect(sidebar).toBeVisible();

  const logoutButton = sidebar.getByRole("button", { name: "Sair" });
  await expect(logoutButton).toBeVisible();
  await expect(logoutButton).toBeInViewport();
});
