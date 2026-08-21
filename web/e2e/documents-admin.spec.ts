import { test, expect, request as playwrightRequest } from "@playwright/test";

const MOCK_BACKEND_URL = "http://localhost:4100";
const E2E_ORGANIZATION = "e2e-organization";
const E2E_EMAIL = "e2e@stratech.local";
const WORKSPACE_PASSWORD = "e2e-workspace-password";
const MOBILE_BREAKPOINT = 768;

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
 * Document Ingestion (Wave 5, Epic W5-0) -- W7-7 Etapa 2 (Founder Decision,
 * Controlled Pilot Browser Baseline).
 *
 * Evidence boundary (mandated, not optional): this suite runs against
 * `e2e/mock-backend.mjs`, a standalone HTTP fixture -- never the real
 * FastAPI backend, never a real embedding/indexing pipeline. It proves the
 * Frontend -> BFF -> backend-route wiring and the two real validation rules
 * `src/api/routes/knowledge.py` enforces (empty file / non-UTF-8 file ->
 * 422), reusing that exact contract. It does NOT prove real document
 * ingestion, chunking, or vector indexing -- that is proven by the backend's
 * own pytest suite (`tests/test_document_upload_size_limit.py` and the
 * Knowledge Platform tests), never re-proven here.
 */

test("navigates from the sidebar to Documentos", async ({ page }) => {
  await login(page);

  const visibleNav = (await page.viewportSize())!.width < MOBILE_BREAKPOINT
    ? page.getByTestId("bottom-nav")
    : page.getByTestId("sidebar-nav");
  await visibleNav.locator('a[href="/administracao/documentos"]').click();

  await expect(page).toHaveURL(/\/administracao\/documentos/);
  await expect(page.getByRole("heading", { name: "Documentos" })).toBeVisible();
});

test("redirects unauthenticated access to /administracao/documentos to the login page", async ({
  page,
}) => {
  await page.goto("/administracao/documentos");
  await expect(page).toHaveURL(/\/entrar/);
});

test("shows the empty state when no document has been uploaded yet", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/documentos");

  await expect(page.getByText("Nenhum documento enviado ainda.")).toBeVisible();
});

test("uploads a valid document, shows success feedback, and lists it afterwards", async ({
  page,
}) => {
  await login(page);
  await page.goto("/administracao/documentos");

  await page.getByRole("button", { name: "Enviar documento" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Arquivo").setInputFiles({
    name: "playbook.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("# Playbook\n\nConteúdo real para o teste de upload."),
  });
  await dialog.getByLabel("Nome (opcional)").fill("Playbook E2E");
  await dialog.getByRole("button", { name: "Enviar" }).click();

  // Success feedback: the dialog closes itself only on a resolved mutation
  // (UploadDocumentDialog's onSuccess), so its disappearance IS the success
  // signal here -- there is no separate toast on this flow.
  await expect(dialog).not.toBeVisible();
  await expect(page.getByText("Playbook E2E")).toBeVisible();
  // exact: true -- "Trechos indexados" (Pacote E's column header) contains
  // "indexado" as a case-insensitive substring, colliding with the status
  // badge under Playwright's default substring match.
  await expect(page.getByText("Indexado", { exact: true })).toBeVisible();
});

test("rejects an empty file with the real backend validation message", async ({ page }) => {
  await login(page);
  await page.goto("/administracao/documentos");

  await page.getByRole("button", { name: "Enviar documento" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Arquivo").setInputFiles({
    name: "empty.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(""),
  });
  await dialog.getByRole("button", { name: "Enviar" }).click();

  await expect(dialog.getByRole("alert")).toHaveText("File is empty");
  await expect(dialog).toBeVisible();
  await expect(page.getByText("Nenhum documento enviado ainda.")).toBeVisible();
});
