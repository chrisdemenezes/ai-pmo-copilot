import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

const SAMPLE = {
  id: 7,
  kind: "risk",
  project_name: "Aurora",
  created_at: "2026-07-01T10:00:00Z",
  payload: { agent: "risk_review", project_name: "Aurora", model_output: { structured: true, risks: [] } },
};

function paramsFor(projectName: string, analysisId: string) {
  return { params: Promise.resolve({ projectName, analysisId }) };
}

describe("GET /api/bff/workspace/[projectName]/analyses/[analysisId]", () => {
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

    const response = await GET(new Request("http://localhost/x"), paramsFor("Aurora", "7"));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(SAMPLE);
  });

  it("maps a backend 404 to a safe not_found body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Analysis not found" }), { status: 404 })),
    );

    const response = await GET(new Request("http://localhost/x"), paramsFor("Aurora", "999"));
    expect(response.status).toBe(404);
    const body = await response.json();
    expect(body.error).toBe("not_found");
  });

  it("returns 502 without leaking the key on other backend errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("boom", { status: 500 })));

    const response = await GET(new Request("http://localhost/x"), paramsFor("Aurora", "7"));
    expect(response.status).toBe(502);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toContain("secret-key");
  });
});
