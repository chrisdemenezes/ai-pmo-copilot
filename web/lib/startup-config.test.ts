import { afterEach, describe, expect, it, vi } from "vitest";

import {
  StartupConfigError,
  collectStartupConfigProblems,
  resolveEnvironment,
  validateStartupConfig,
} from "./startup-config";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("resolveEnvironment", () => {
  it("defaults to dev when ENVIRONMENT is absent", () => {
    vi.stubEnv("ENVIRONMENT", undefined);
    expect(resolveEnvironment()).toBe("dev");
  });

  it.each(["dev", "staging", "production"])("accepts %s", (value) => {
    vi.stubEnv("ENVIRONMENT", value);
    expect(resolveEnvironment()).toBe(value);
  });

  it("is case-insensitive and trims whitespace", () => {
    vi.stubEnv("ENVIRONMENT", "  PRODUCTION  ");
    expect(resolveEnvironment()).toBe("production");
  });

  it("rejects an invalid value", () => {
    vi.stubEnv("ENVIRONMENT", "test");
    expect(() => resolveEnvironment()).toThrow(StartupConfigError);
  });
});

describe("dev", () => {
  it("has no problems regardless of missing config", () => {
    vi.stubEnv("SESSION_SECRET", undefined);
    vi.stubEnv("WORKSPACE_PASSWORD", undefined);
    vi.stubEnv("BACKEND_URL", undefined);
    vi.stubEnv("API_KEY", undefined);
    expect(collectStartupConfigProblems("dev")).toEqual([]);
    expect(() => validateStartupConfig("dev")).not.toThrow();
  });
});

describe.each(["staging", "production"] as const)("%s", (environment) => {
  function setValidEnv() {
    vi.stubEnv("SESSION_SECRET", "real-secret");
    vi.stubEnv("WORKSPACE_PASSWORD", "real-password");
    vi.stubEnv("BACKEND_URL", "http://api:8000");
    vi.stubEnv("API_KEY", "real-key");
  }

  it("has no problems when fully configured", () => {
    setValidEnv();
    expect(collectStartupConfigProblems(environment)).toEqual([]);
    expect(() => validateStartupConfig(environment)).not.toThrow();
  });

  it("flags a missing SESSION_SECRET", () => {
    setValidEnv();
    vi.stubEnv("SESSION_SECRET", undefined);
    expect(collectStartupConfigProblems(environment)).toEqual(
      expect.arrayContaining([expect.stringContaining("SESSION_SECRET")]),
    );
  });

  it("flags a missing WORKSPACE_PASSWORD", () => {
    setValidEnv();
    vi.stubEnv("WORKSPACE_PASSWORD", undefined);
    expect(collectStartupConfigProblems(environment)).toEqual(
      expect.arrayContaining([expect.stringContaining("WORKSPACE_PASSWORD")]),
    );
  });

  it("flags a missing BACKEND_URL", () => {
    setValidEnv();
    vi.stubEnv("BACKEND_URL", undefined);
    expect(collectStartupConfigProblems(environment)).toEqual(
      expect.arrayContaining([expect.stringContaining("BACKEND_URL")]),
    );
  });

  it("flags a missing API_KEY", () => {
    setValidEnv();
    vi.stubEnv("API_KEY", undefined);
    expect(collectStartupConfigProblems(environment)).toEqual(
      expect.arrayContaining([expect.stringContaining("API_KEY")]),
    );
  });

  it("throws with all problems when everything is missing", () => {
    vi.stubEnv("SESSION_SECRET", undefined);
    vi.stubEnv("WORKSPACE_PASSWORD", undefined);
    vi.stubEnv("BACKEND_URL", undefined);
    vi.stubEnv("API_KEY", undefined);
    expect(collectStartupConfigProblems(environment)).toHaveLength(4);
    expect(() => validateStartupConfig(environment)).toThrow(StartupConfigError);
  });
});
