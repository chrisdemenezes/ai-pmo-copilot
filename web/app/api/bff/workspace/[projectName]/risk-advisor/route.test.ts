import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authenticatedRequest } from "@/lib/bff/test-support";

import { POST } from "./route";

const SAMPLE = {
  answer: "O risco mais crítico é o atraso no fornecedor de middleware.",
  cited_analyses: [{ source_analysis_id: 7, source_created_at: "2026-07-10T14:00:00Z" }],
};

function paramsFor(projectName: string) {
  return { params: Promise.resolve({ projectName: encodeURIComponent(projectName) }) };
}

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

describe("POST /api/bff/workspace/[projectName]/risk-advisor", () => {
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
    const response = await POST(
      requestWith({ question: "Qual o risco mais crítico?" }),
      paramsFor("Aurora"),
    );
    expect(response.status).toBe(503);
    expect(JSON.stringify(await response.json())).not.toContain("secret-key");
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(
      requestWithoutSession({ question: "Qual o risco mais crítico?" }),
      paramsFor("Aurora"),
    );
    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({
      error: "unauthorized",
      detail: "Sessão inválida ou expirada.",
    });
  });

  it("rejects a question shorter than 3 characters before contacting the backend", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(requestWith({ question: "Oi" }), paramsFor("Aurora"));

    expect(response.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("injects the decoded project_name from the route segment into the outbound body", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await POST(
      requestWith({ question: "Qual o risco mais crítico?" }),
      paramsFor("Implantacao SAP S/4HANA"),
    );

    const [calledUrl, init] = fetchMock.mock.calls[0];
    expect(String(calledUrl)).toBe("http://backend.test/api/risk-advisor/ask");
    const sentBody = JSON.parse(String(init.body));
    expect(sentBody).toEqual({
      project_name: "Implantacao SAP S/4HANA",
      question: "Qual o risco mais crítico?",
    });
  });

  it("sends institutional headers resolved from the session cookie", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await POST(
      requestWith(
        { question: "Qual o risco mais crítico?" },
        { userId: 7, organizationId: 3 },
      ),
      paramsFor("Aurora"),
    );

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

    const response = await POST(
      requestWith({ question: "Qual o risco mais crítico?" }),
      paramsFor("Aurora"),
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(SAMPLE);
  });

  it("maps a 429 from the backend to a specific rate-limit error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("rate limited", { status: 429 })));

    const response = await POST(
      requestWith({ question: "Qual o risco mais crítico?" }),
      paramsFor("Aurora"),
    );
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

      const responsePromise = POST(
        requestWith({ question: "Qual o risco mais crítico?" }),
        paramsFor("Aurora"),
      );
      await vi.advanceTimersByTimeAsync(60_000);
      const response = await responsePromise;
      expect(response.status).toBe(504);
      expect(JSON.stringify(await response.json())).not.toContain("secret-key");
    } finally {
      vi.useRealTimers();
    }
  });

  it("returns 502 without leaking the key when the backend errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("boom", { status: 500 })));

    const response = await POST(
      requestWith({ question: "Qual o risco mais crítico?" }),
      paramsFor("Aurora"),
    );
    expect(response.status).toBe(502);
    expect(JSON.stringify(await response.json())).not.toContain("secret-key");
  });
});
