import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

describe("GET /api/bff/dashboard", () => {
  beforeEach(() => {
    vi.stubEnv("BACKEND_URL", "http://backend.test");
    vi.stubEnv("API_KEY", "secret-key");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("returns 503 without leaking detail when BACKEND_URL or API_KEY are unset", async () => {
    vi.stubEnv("API_KEY", "");
    const response = await GET();
    expect(response.status).toBe(503);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toContain("secret-key");
  });

  it("proxies a successful backend response verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const response = await GET();
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(SAMPLE);
  });

  it("sends X-API-Key to the backend but never echoes it back", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET();
    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Record<string, string>)["X-API-Key"]).toBe("secret-key");

    const rawBody = JSON.stringify(await response.json());
    expect(rawBody).not.toContain("secret-key");
    expect(response.headers.get("X-API-Key")).toBeNull();
  });

  it("returns 502 without leaking the key when the backend errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("boom", { status: 500 })));

    const response = await GET();
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

    const responsePromise = GET();
    await vi.advanceTimersByTimeAsync(8_000);
    const response = await responsePromise;
    expect(response.status).toBe(504);
  });
});
