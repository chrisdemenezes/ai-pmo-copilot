import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("returns 503 without leaking detail when BACKEND_URL or API_KEY are unset", async () => {
    vi.stubEnv("API_KEY", "");
    const response = await GET(new Request("http://localhost/x"), paramsFor("Aurora"));
    expect(response.status).toBe(503);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toContain("secret-key");
  });

  it("proxies a successful backend response verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const response = await GET(new Request("http://localhost/x"), paramsFor("Aurora"));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(SAMPLE);
  });

  it("URL-encodes a project_name containing '/' before calling the backend", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await GET(new Request("http://localhost/x"), paramsFor("Implantacao SAP S/4HANA"));

    const [calledUrl] = fetchMock.mock.calls[0];
    expect(String(calledUrl)).toBe(
      "http://backend.test/api/projects/Implantacao%20SAP%20S%2F4HANA/summary",
    );
  });

  it("returns 502 without leaking the key when the backend errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("boom", { status: 500 })));

    const response = await GET(new Request("http://localhost/x"), paramsFor("Aurora"));
    expect(response.status).toBe(502);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toContain("secret-key");
  });
});
