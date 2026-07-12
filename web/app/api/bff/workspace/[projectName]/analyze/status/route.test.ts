import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

const SAMPLE = {
  agent: "project_status",
  project_name: "Aurora",
  model_output: {
    structured: true,
    health_status: "green",
    key_findings: ["Projeto dentro do prazo"],
    recommendations: ["Manter cadência atual"],
  },
};

function paramsFor(projectName: string) {
  return { params: Promise.resolve({ projectName: encodeURIComponent(projectName) }) };
}

function requestWith(body: unknown) {
  return new Request("http://localhost/x", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("POST /api/bff/workspace/[projectName]/analyze/status", () => {
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
    const response = await POST(
      requestWith({ project_context: "contexto valido com mais de dez caracteres" }),
      paramsFor("Aurora"),
    );
    expect(response.status).toBe(503);
    expect(JSON.stringify(await response.json())).not.toContain("secret-key");
  });

  it("rejects context shorter than 10 characters before contacting the backend", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(requestWith({ project_context: "curto" }), paramsFor("Aurora"));
    expect(response.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects whitespace-only context", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(
      requestWith({ project_context: "                              " }),
      paramsFor("Aurora"),
    );
    expect(response.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("injects the decoded project_name from the route segment into the outbound body", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await POST(
      requestWith({ project_context: "contexto valido com mais de dez caracteres" }),
      paramsFor("Implantacao SAP S/4HANA"),
    );

    const [, init] = fetchMock.mock.calls[0];
    const sentBody = JSON.parse(String(init.body));
    expect(sentBody.project_name).toBe("Implantacao SAP S/4HANA");
    expect(sentBody.project_context).toBe("contexto valido com mais de dez caracteres");
  });

  it("proxies a successful backend response verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const response = await POST(
      requestWith({ project_context: "contexto valido com mais de dez caracteres" }),
      paramsFor("Aurora"),
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(SAMPLE);
  });

  it("maps a 429 from the backend to a specific rate-limit error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("rate limited", { status: 429 })),
    );

    const response = await POST(
      requestWith({ project_context: "contexto valido com mais de dez caracteres" }),
      paramsFor("Aurora"),
    );
    expect(response.status).toBe(429);
    const body = await response.json();
    expect(body.error).toBe("rate_limited");
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
        requestWith({ project_context: "contexto valido com mais de dez caracteres" }),
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
      requestWith({ project_context: "contexto valido com mais de dez caracteres" }),
      paramsFor("Aurora"),
    );
    expect(response.status).toBe(502);
    expect(JSON.stringify(await response.json())).not.toContain("secret-key");
  });
});
