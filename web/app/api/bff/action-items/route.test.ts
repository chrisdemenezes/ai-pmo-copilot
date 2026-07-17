import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

const SAMPLE = [
  {
    project_name: "Aurora",
    description: "Atualizar cronograma",
    owner: "Ana",
    due_date: "2026-07-15",
    source_analysis_id: 202,
    source_created_at: "2026-07-09T10:00:00Z",
  },
];

describe("GET /api/bff/action-items", () => {
  beforeEach(() => {
    vi.stubEnv("BACKEND_URL", "http://backend.test");
    vi.stubEnv("API_KEY", "secret-key");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("returns 503 without leaking detail when BACKEND_URL or API_KEY are unset", async () => {
    vi.stubEnv("API_KEY", "");
    const response = await GET(new Request("http://localhost/api/bff/action-items"));
    expect(response.status).toBe(503);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toContain("secret-key");
  });

  it("proxies a successful backend response verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const response = await GET(new Request("http://localhost/api/bff/action-items"));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(SAMPLE);
  });

  it("omits project_name from the backend call for the portfolio view", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await GET(new Request("http://localhost/api/bff/action-items"));

    const [calledUrl] = fetchMock.mock.calls[0];
    const url = new URL(String(calledUrl));
    expect(url.origin + url.pathname).toBe("http://backend.test/api/action-items");
    expect(url.searchParams.has("project_name")).toBe(false);
  });

  it.each([
    ["a slash", "Implantacao SAP S/4HANA"],
    ["spaces", "Migracao de Data Center"],
    ["accents", "Programa de Governança de Dados"],
  ])("forwards a project_name containing %s as a query param", async (_label, name) => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await GET(
      new Request(`http://localhost/api/bff/action-items?project_name=${encodeURIComponent(name)}`),
    );

    const [calledUrl] = fetchMock.mock.calls[0];
    const url = new URL(String(calledUrl));
    expect(url.searchParams.get("project_name")).toBe(name);
  });

  it("sends the API key in the X-API-Key header, never in the URL", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await GET(new Request("http://localhost/api/bff/action-items"));

    const [calledUrl, init] = fetchMock.mock.calls[0];
    expect(String(calledUrl)).not.toContain("secret-key");
    expect((init as RequestInit).headers).toEqual({ "X-API-Key": "secret-key" });
  });

  it("maps a backend error status to a 502 with the shared error shape", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "boom" }), { status: 500 })),
    );

    const response = await GET(new Request("http://localhost/api/bff/action-items"));
    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({
      error: "backend_error",
      detail: "Backend respondeu 500.",
    });
  });

  it("maps an aborted backend call to a 504 timeout body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(Object.assign(new Error("aborted"), { name: "AbortError" })),
    );

    const response = await GET(new Request("http://localhost/api/bff/action-items"));
    expect(response.status).toBe(504);
    expect(await response.json()).toEqual({
      error: "backend_timeout",
      detail: "Backend não respondeu a tempo.",
    });
  });

  it("maps a network failure to a 502 unavailable body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("ECONNREFUSED")));

    const response = await GET(new Request("http://localhost/api/bff/action-items"));
    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({
      error: "backend_unavailable",
      detail: "Não foi possível contatar o backend.",
    });
  });
});
