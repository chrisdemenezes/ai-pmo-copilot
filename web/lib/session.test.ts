import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createSessionToken, verifySessionToken, verifyWorkspacePassword } from "./session";

describe("session", () => {
  beforeEach(() => {
    vi.stubEnv("SESSION_SECRET", "test-secret");
    vi.stubEnv("WORKSPACE_PASSWORD", "correct-horse");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.useRealTimers();
  });

  it("accepts a freshly issued token", () => {
    const { token } = createSessionToken();
    expect(verifySessionToken(token)).toBe(true);
  });

  it("rejects a missing token", () => {
    expect(verifySessionToken(undefined)).toBe(false);
  });

  it("rejects a tampered token", () => {
    const { token } = createSessionToken();
    const [payload] = token.split(".");
    expect(verifySessionToken(`${payload}.deadbeef`)).toBe(false);
  });

  it("rejects a token signed with a different secret", () => {
    const { token } = createSessionToken();
    vi.stubEnv("SESSION_SECRET", "different-secret");
    expect(verifySessionToken(token)).toBe(false);
  });

  it("rejects an expired token", () => {
    vi.useFakeTimers();
    const { token } = createSessionToken();
    vi.advanceTimersByTime(13 * 60 * 60 * 1000);
    expect(verifySessionToken(token)).toBe(false);
  });

  it("accepts the correct workspace password", () => {
    expect(verifyWorkspacePassword("correct-horse")).toBe(true);
  });

  it("rejects an incorrect workspace password", () => {
    expect(verifyWorkspacePassword("wrong")).toBe(false);
  });

  it("rejects any password when WORKSPACE_PASSWORD is unset", () => {
    vi.stubEnv("WORKSPACE_PASSWORD", "");
    expect(verifyWorkspacePassword("")).toBe(false);
  });
});
