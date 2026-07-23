import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authenticatedRequest } from "@/lib/bff/test-support";

import { GET } from "./route";

const SAMPLE = {
  project_name: "Implantacao SAP S/4HANA",
  total_analyses: 3,
  open_risks: 2,
  pending_action_items: 1,
  latest_health_status: "red",
};

// Next.js hands route handlers the raw, still-encoded route segment (not
// the decoded name) -- encode here so these tests match real runtime
// behavior, exactly the gap that let a double-encoding bug through E2E.
function paramsFor(projectName: string) {
  return { params: Promise.resolve({ projectName: encodeURIComponent(projectName) }) };
}

describe("GET /api/bff/workspace/[projectName]/summary", () => {
  beforeEach(() => {
    vi.stubEnv("BACKEND_URL", "http://backend.test");
    vi.stubEnv("API_KEY", "secret-key");
    vi.stubEnv("SESSION_SECRET", "test-secret");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("returns 503 without leaking detail when BACKEND_URL or API_KEY are unset", async () => {
    vi.stubEnv("API_KEY", "");
    const response = await GET(authenticatedRequest("http://localhost/x"), paramsFor("Aurora"));
    expect(response.status).toBe(503);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toContain("secret-key");
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new Request("http://localhost/x"), paramsFor("Aurora"));
    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({
      error: "unauthorized",
      detail: "Sessão inválida ou expirada.",
    });
  });

  it("proxies a successful backend response verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const response = await GET(authenticatedRequest("http://localhost/x"), paramsFor("Aurora"));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(SAMPLE);
  });

  // Migrated off /api/projects/{project_name}/summary (path segment) to
  // /api/projects/summary?project_name=... (query param) -- Starlette's
  // path converter can't capture a literal "/" no matter how the client
  // encodes it; query params don't have that restriction. Each case below
  // is a character class the Product Owner asked to see covered explicitly.
  it("sends project_name as a query param to /api/projects/summary, not a path segment", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await GET(authenticatedRequest("http://localhost/x"), paramsFor("Implantacao SAP S/4HANA"));

    const [calledUrl] = fetchMock.mock.calls[0];
    const url = new URL(String(calledUrl));
    expect(url.origin + url.pathname).toBe("http://backend.test/api/projects/summary");
    expect(url.searchParams.get("project_name")).toBe("Implantacao SAP S/4HANA");
  });

  it.each([
    ["a slash", "Implantacao SAP S/4HANA"],
    ["spaces", "Migracao de Data Center"],
    ["accents", "Programa de Governança de Dados"],
  ])("round-trips a project_name containing %s", async (_label, name) => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ ...SAMPLE, project_name: name }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await GET(authenticatedRequest("http://localhost/x"), paramsFor(name));

    const [calledUrl] = fetchMock.mock.calls[0];
    expect(new URL(String(calledUrl)).searchParams.get("project_name")).toBe(name);
  });

  it("handles a manually percent-encoded route segment (%20 and %2F), not just encodeURIComponent output", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await GET(authenticatedRequest("http://localhost/x"), {
      params: Promise.resolve({ projectName: "Implantacao%20SAP%20S%2F4HANA" }),
    });

    const [calledUrl] = fetchMock.mock.calls[0];
    expect(new URL(String(calledUrl)).searchParams.get("project_name")).toBe(
      "Implantacao SAP S/4HANA",
    );
  });

  it("sends institutional headers resolved from the session cookie", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await GET(
      authenticatedRequest("http://localhost/x", {}, { userId: 7, organizationId: 3 }),
      paramsFor("Aurora"),
    );

    const [, init] = fetchMock.mock.calls[0];
    const headers = init.headers as Record<string, string>;
    expect(headers["X-Stratech-User-Id"]).toBe("7");
    expect(headers["X-Stratech-Organization-Id"]).toBe("3");
  });

  it("returns 502 without leaking the key when the backend errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("boom", { status: 500 })));

    const response = await GET(authenticatedRequest("http://localhost/x"), paramsFor("Aurora"));
    expect(response.status).toBe(502);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toContain("secret-key");
  });
});
