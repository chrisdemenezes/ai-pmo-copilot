import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("GET /api/health", () => {
  it("reports healthy with an unknown release by default", async () => {
    vi.stubEnv("RELEASE_SHA", undefined);
    const response = await GET();
    const body = await response.json();
    expect(body).toEqual({ status: "healthy", service: "STRATECH Frontend", release: "unknown" });
  });

  it("reports the configured release SHA", async () => {
    vi.stubEnv("RELEASE_SHA", "abc1234");
    const response = await GET();
    const body = await response.json();
    expect(body.release).toBe("abc1234");
  });
});
