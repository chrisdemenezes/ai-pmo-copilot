import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createSessionToken, resolveSessionIdentity, verifySessionToken } from "./session";

describe("session", () => {
  beforeEach(() => {
    vi.stubEnv("SESSION_SECRET", "test-secret");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.useRealTimers();
  });

  it("accepts a freshly issued token", () => {
    const { token } = createSessionToken(1, 2, "test-session");
    expect(verifySessionToken(token)).toBe(true);
  });

  it("resolves the full identity from a freshly issued token", () => {
    const { token } = createSessionToken(1, 2, "test-session");
    const identity = resolveSessionIdentity(token);
    expect(identity).not.toBeNull();
    expect(identity?.userId).toBe(1);
    expect(identity?.organizationId).toBe(2);
  });

  it("preserves the backend-issued session id instead of generating its own (item 5, TD-010)", () => {
    const backendSessionId = "b1946ac9-2b45-4f9c-9e2a-000000000000";
    const { token } = createSessionToken(7, 3, backendSessionId);
    expect(resolveSessionIdentity(token)?.sessionId).toBe(backendSessionId);
  });

  it("rejects a missing token", () => {
    expect(verifySessionToken(undefined)).toBe(false);
    expect(resolveSessionIdentity(undefined)).toBeNull();
  });

  it("rejects a tampered token", () => {
    const { token } = createSessionToken(1, 2, "test-session");
    const [sessionId, userId, organizationId, expiresAt] = token.split(".");
    expect(
      verifySessionToken(`${sessionId}.${userId}.${organizationId}.${expiresAt}.deadbeef`),
    ).toBe(false);
  });

  it("rejects a token signed with a different secret", () => {
    const { token } = createSessionToken(1, 2, "test-session");
    vi.stubEnv("SESSION_SECRET", "different-secret");
    expect(verifySessionToken(token)).toBe(false);
  });

  it("rejects an expired token", () => {
    vi.useFakeTimers();
    const { token } = createSessionToken(1, 2, "test-session");
    vi.advanceTimersByTime(13 * 60 * 60 * 1000);
    expect(verifySessionToken(token)).toBe(false);
  });
});
