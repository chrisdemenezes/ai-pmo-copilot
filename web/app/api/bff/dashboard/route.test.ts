import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authenticatedRequest } from "@/lib/bff/test-support";

import { GET } from "./route";

const SAMPLE: unknown = [
  {
    project_name: "Multilift",
    total_analyses: 3,
    open_risks: 2,
    pending_action_items: 1,
    latest_health_status: "yellow",
  },
];

const URL = "http://localhost/api/bff/dashboard";

describe("GET /api/bff/dashboard", () => {
  beforeEach(() => {
    vi.stubEnv("BACKEND_URL", "http://backend.test");
    vi.stubEnv("API_KEY", "secret-key");
    vi.stubEnv("SESSION_SECRET", "test-secret");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("returns 503 without leaking detail when BACKEND_URL or API_KEY are unset", async () => {
    vi.stubEnv("API_KEY", "");
    const response = await GET(authenticatedRequest(URL));
    expect(response.status).toBe(503);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toContain("secret-key");
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new Request(URL));
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

    const response = await GET(authenticatedRequest(URL));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(SAMPLE);
  });

  it("sends X-API-Key and institutional headers to the backend but never echoes the key back", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET(authenticatedRequest(URL, {}, { userId: 7, organizationId: 3 }));
    const [, init] = fetchMock.mock.calls[0];
    const headers = init.headers as Record<string, string>;
    expect(headers["X-API-Key"]).toBe("secret-key");
    expect(headers["X-Stratech-User-Id"]).toBe("7");
    expect(headers["X-Stratech-Organization-Id"]).toBe("3");
    expect(headers["X-Stratech-Session-Id"]).toBeTruthy();

    const rawBody = JSON.stringify(await response.json());
    expect(rawBody).not.toContain("secret-key");
    expect(response.headers.get("X-API-Key")).toBeNull();
  });

  it("returns 502 without leaking the key when the backend errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("boom", { status: 500 })));

    const response = await GET(authenticatedRequest(URL));
    expect(response.status).toBe(502);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toContain("secret-key");
  });

  it("returns 504 on timeout", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((_url: string, init: RequestInit) => {
        return new Promise((_resolve, reject) => {
          init.signal?.addEventListener("abort", () => {
            const error = new Error("aborted");
            error.name = "AbortError";
            reject(error);
          });
        });
      }),
    );

    const responsePromise = GET(authenticatedRequest(URL));
    await vi.advanceTimersByTimeAsync(8_000);
    const response = await responsePromise;
    expect(response.status).toBe(504);
  });
});
