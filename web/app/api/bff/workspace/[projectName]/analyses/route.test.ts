import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

const SAMPLE = [
  { id: 1, kind: "risk", project_name: "Aurora", created_at: "2026-07-01T10:00:00Z" },
];

// Next.js hands route handlers the raw, still-encoded route segment.
function paramsFor(projectName: string) {
  return { params: Promise.resolve({ projectName: encodeURIComponent(projectName) }) };
}

describe("GET /api/bff/workspace/[projectName]/analyses", () => {
  beforeEach(() => {
    vi.stubEnv("BACKEND_URL", "http://backend.test");
    vi.stubEnv("API_KEY", "secret-key");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("proxies a successful backend response verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const response = await GET(
      new Request("http://localhost/api/bff/workspace/Aurora/analyses"),
      paramsFor("Aurora"),
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(SAMPLE);
  });

  it("URL-encodes project_name and forwards kind/limit query params", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await GET(
      new Request(
        "http://localhost/api/bff/workspace/Implantacao%20SAP%20S%2F4HANA/analyses?kind=risk&limit=1",
      ),
      paramsFor("Implantacao SAP S/4HANA"),
    );

    const [calledUrl] = fetchMock.mock.calls[0];
    const url = new URL(String(calledUrl));
    expect(url.origin + url.pathname).toBe("http://backend.test/api/analyses");
    expect(url.searchParams.get("project_name")).toBe("Implantacao SAP S/4HANA");
    expect(url.searchParams.get("kind")).toBe("risk");
    expect(url.searchParams.get("limit")).toBe("1");
  });

  it("does not forward unrecognized query params", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await GET(
      new Request("http://localhost/api/bff/workspace/Aurora/analyses?evil=1"),
      paramsFor("Aurora"),
    );

    const [calledUrl] = fetchMock.mock.calls[0];
    const url = new URL(String(calledUrl));
    expect(url.searchParams.get("evil")).toBeNull();
  });

  it("returns 502 without leaking the key when the backend errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("boom", { status: 500 })));

    const response = await GET(
      new Request("http://localhost/api/bff/workspace/Aurora/analyses"),
      paramsFor("Aurora"),
    );
    expect(response.status).toBe(502);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toContain("secret-key");
  });
});
