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
    const { token } = createSessionToken(1, 2);
    expect(verifySessionToken(token)).toBe(true);
  });

  it("resolves the full identity from a freshly issued token", () => {
    const { token } = createSessionToken(1, 2);
    const identity = resolveSessionIdentity(token);
    expect(identity).not.toBeNull();
    expect(identity?.userId).toBe(1);
    expect(identity?.organizationId).toBe(2);
  });

  it("rejects a missing token", () => {
    expect(verifySessionToken(undefined)).toBe(false);
    expect(resolveSessionIdentity(undefined)).toBeNull();
  });

  it("rejects a tampered token", () => {
    const { token } = createSessionToken(1, 2);
    const [sessionId, userId, organizationId, expiresAt] = token.split(".");
    expect(
      verifySessionToken(`${sessionId}.${userId}.${organizationId}.${expiresAt}.deadbeef`),
    ).toBe(false);
  });

  it("rejects a token signed with a different secret", () => {
    const { token } = createSessionToken(1, 2);
    vi.stubEnv("SESSION_SECRET", "different-secret");
    expect(verifySessionToken(token)).toBe(false);
  });

  it("rejects an expired token", () => {
    vi.useFakeTimers();
    const { token } = createSessionToken(1, 2);
    vi.advanceTimersByTime(13 * 60 * 60 * 1000);
    expect(verifySessionToken(token)).toBe(false);
  });
});
