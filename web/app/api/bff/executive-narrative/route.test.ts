import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authenticatedRequest } from "@/lib/bff/test-support";

import { POST } from "./route";

const SAMPLE = {
  capability: "executive_narrative",
  scope: { type: "project", project_id: 42, portfolio_id: null },
  insufficient_basis: false,
  insufficient_basis_reason: null,
  narrative: "Síntese executiva: risco de escalação identificado, entrega em andamento.",
  advisors_used: ["risk_advisor", "delivery_advisor"],
  citations: [{ advisor_name: "risk_advisor", source_type: "analysis_record", source_id: 7, source_label: "Risk 7" }],
  composition_trace: {
    selection_signals: ["risk_advisor", "delivery_advisor"],
    selected_advisor_names: ["risk_advisor", "delivery_advisor"],
    advisors_used: [
      { advisor_name: "risk_advisor", had_evidence: true },
      { advisor_name: "delivery_advisor", had_evidence: true },
    ],
    correlations: [{ advisor_names: ["delivery_advisor", "risk_advisor"], is_structural_pair: true }],
    synthesis_source_advisor_names: ["risk_advisor", "delivery_advisor"],
  },
};

function requestWith(body: unknown, identity?: { userId: number; organizationId: number }) {
  return authenticatedRequest(
    "http://localhost/x",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
    identity,
  );
}

function requestWithoutSession(body: unknown) {
  return new Request("http://localhost/x", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("POST /api/bff/executive-narrative", () => {
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
    const response = await POST(requestWith({ scope: { type: "organization" } }));
    expect(response.status).toBe(503);
    expect(JSON.stringify(await response.json())).not.toContain("secret-key");
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(requestWithoutSession({ scope: { type: "organization" } }));
    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({
      error: "unauthorized",
      detail: "Sessão inválida ou expirada.",
    });
  });

  it("rejects a request with no scope before contacting the backend (Explicit Scope, Vision Princípio 13)", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(requestWith({}));

    expect(response.status).toBe(400);
    expect((await response.json()).error).toBe("invalid_request");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards only the scope to the backend -- never a question field, even if the client sends one", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await POST(
      requestWith({
        // A misbehaving client sending `question` -- the BFF's contract has
        // no such field and must never forward it (Technical Design §2).
        question: "isto deveria ser ignorado",
        scope: { type: "project", project_id: 42 },
      }),
    );

    const [calledUrl, init] = fetchMock.mock.calls[0];
    expect(String(calledUrl)).toBe("http://backend.test/api/executive-narrative/generate");
    const sentBody = JSON.parse(String(init.body));
    expect(sentBody).toEqual({ scope: { type: "project", project_id: 42 } });
  });

  it("sends institutional headers resolved from the session cookie", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await POST(requestWith({ scope: { type: "organization" } }, { userId: 7, organizationId: 3 }));

    const [, init] = fetchMock.mock.calls[0];
    const headers = init.headers as Record<string, string>;
    expect(headers["X-Stratech-User-Id"]).toBe("7");
    expect(headers["X-Stratech-Organization-Id"]).toBe("3");
  });

  it("proxies a successful backend response verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const response = await POST(requestWith({ scope: { type: "organization" } }));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(SAMPLE);
  });

  it("maps a 404 from the backend to a scope_not_found error (cross-tenant/nonexistent Project or Portfolio)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not found", { status: 404 })));

    const response = await POST(requestWith({ scope: { type: "portfolio", portfolio_id: 999 } }));
    expect(response.status).toBe(404);
    expect((await response.json()).error).toBe("scope_not_found");
  });

  it("maps a 422 from the backend to invalid_request", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("unprocessable", { status: 422 })));

    const response = await POST(requestWith({ scope: { type: "project", project_id: 1 } }));
    expect(response.status).toBe(400);
    expect((await response.json()).error).toBe("invalid_request");
  });

  it("maps a 429 from the backend to a specific rate-limit error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("rate limited", { status: 429 })));

    const response = await POST(requestWith({ scope: { type: "organization" } }));
    expect(response.status).toBe(429);
    expect((await response.json()).error).toBe("rate_limited");
  });

  it("returns 504 without leaking the key when the backend times out", async () => {
    vi.useFakeTimers();
    try {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockImplementation((_url: string, init: { signal: AbortSignal }) => {
          return new Promise((_resolve, reject) => {
            init.signal.addEventListener("abort", () => {
              const err = new Error("aborted");
              err.name = "AbortError";
              reject(err);
            });
          });
        }),
      );

      const responsePromise = POST(requestWith({ scope: { type: "organization" } }));
      await vi.advanceTimersByTimeAsync(120_000);
      const response = await responsePromise;
      expect(response.status).toBe(504);
      expect(JSON.stringify(await response.json())).not.toContain("secret-key");
    } finally {
      vi.useRealTimers();
    }
  });

  it("returns 502 without leaking the key when the backend errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("boom", { status: 500 })));

    const response = await POST(requestWith({ scope: { type: "organization" } }));
    expect(response.status).toBe(502);
    expect(JSON.stringify(await response.json())).not.toContain("secret-key");
  });
});
