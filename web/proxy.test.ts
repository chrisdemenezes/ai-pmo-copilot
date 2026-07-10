import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { proxy } from "./proxy";
import { createSessionToken, SESSION_COOKIE_NAME } from "@/lib/session";

function requestFor(path: string, cookie?: string) {
  const request = new NextRequest(new URL(path, "http://localhost:3000"));
  if (cookie) {
    request.cookies.set(SESSION_COOKIE_NAME, cookie);
  }
  return request;
}

describe("proxy", () => {
  beforeEach(() => {
    vi.stubEnv("SESSION_SECRET", "test-secret");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("redirects /dashboard to /entrar when there is no session cookie", async () => {
    const response = proxy(requestFor("/dashboard"));
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/entrar");
  });

  it("passes /dashboard through with a valid session cookie", async () => {
    const { token } = createSessionToken();
    const response = proxy(requestFor("/dashboard", token));
    expect(response.status).toBe(200);
  });

  it("returns 401 JSON (not a redirect) for unauthenticated /api/bff/* calls", async () => {
    const response = proxy(requestFor("/api/bff/dashboard"));
    expect(response.status).toBe(401);
    const body = await response.json();
    expect(body.error).toBe("unauthenticated");
  });

  it("always lets /api/bff/session through, session or not", async () => {
    const response = proxy(requestFor("/api/bff/session"));
    expect(response.status).toBe(200);
  });

  it("bypasses the gate entirely when the emergency kill switch is set", async () => {
    vi.stubEnv("DISABLE_WORKSPACE_SESSION_GATE", "true");
    const response = proxy(requestFor("/dashboard"));
    expect(response.status).toBe(200);
  });
});
