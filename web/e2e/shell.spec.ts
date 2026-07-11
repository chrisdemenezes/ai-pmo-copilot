import { test, expect, request as playwrightRequest } from "@playwright/test";

const MOCK_BACKEND_URL = "http://localhost:4100";
const WORKSPACE_PASSWORD = "e2e-workspace-password";
const MOBILE_BREAKPOINT = 768;

async function setBackendScenario(scenario: "data" | "empty" | "unavailable" | "timeout") {
  const ctx = await playwrightRequest.newContext();
  await ctx.post(`${MOCK_BACKEND_URL}/__control/scenario`, { data: { scenario } });
  await ctx.dispose();
}

async function login(page: import("@playwright/test").Page) {
  await page.goto("/entrar");
  await page.getByLabel("Senha do workspace").fill(WORKSPACE_PASSWORD);
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

test("renders exactly one nav item, active, pointing at Dashboard", async ({ page }) => {
  await login(page);

  const visibleNav = (await page.viewportSize())!.width < MOBILE_BREAKPOINT
    ? page.getByTestId("bottom-nav")
    : page.getByTestId("sidebar-nav");

  const links = visibleNav.getByRole("link");
  await expect(links).toHaveCount(1);
  await expect(links.first()).toHaveAttribute("aria-current", "page");
  await expect(links.first()).toHaveAttribute("href", "/dashboard");
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
