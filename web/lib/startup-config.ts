/**
 * Startup Configuration Contract (W7-5, Technical Design
 * `docs/architecture/TECHNICAL-DESIGN-W7-5-DEPLOYMENT-ENVIRONMENT-RELEASE-DISCIPLINE.md`
 * S5/S7): frontend mirror of `src/api/startup_config.py`. Distinguishes
 * DEV from STAGING/PRODUCTION and fails the process closed, at boot, when
 * critical BFF configuration is missing outside dev.
 */

export type Environment = "dev" | "staging" | "production";

const VALID_ENVIRONMENTS: readonly Environment[] = ["dev", "staging", "production"];

export class StartupConfigError extends Error {}

export function resolveEnvironment(envVar = "ENVIRONMENT"): Environment {
  const raw = (process.env[envVar] ?? "dev").trim().toLowerCase();
  if (!VALID_ENVIRONMENTS.includes(raw as Environment)) {
    throw new StartupConfigError(`${envVar}=${JSON.stringify(raw)} is invalid. Expected one of ${VALID_ENVIRONMENTS}.`);
  }
  return raw as Environment;
}

export function collectStartupConfigProblems(environment: Environment): string[] {
  if (environment === "dev") {
    return [];
  }

  const problems: string[] = [];

  if (!process.env.SESSION_SECRET) {
    problems.push("SESSION_SECRET is not set (web/lib/session.ts would fail closed at request time instead of at boot).");
  }
  if (!process.env.WORKSPACE_PASSWORD) {
    problems.push("WORKSPACE_PASSWORD is not set.");
  }
  if (!process.env.BACKEND_URL) {
    problems.push("BACKEND_URL is not set (the BFF cannot reach the real API).");
  }
  if (!process.env.API_KEY) {
    problems.push("API_KEY is not set (the BFF cannot authenticate to the real API).");
  }

  return problems;
}

export function validateStartupConfig(environment: Environment): void {
  const problems = collectStartupConfigProblems(environment);
  if (problems.length > 0) {
    for (const problem of problems) {
      console.error(`Startup configuration error (ENVIRONMENT=${environment}): ${problem}`);
    }
    throw new StartupConfigError(
      `${problems.length} critical configuration problem(s) for ENVIRONMENT=${JSON.stringify(environment)}: ${problems.join("; ")}`,
    );
  }
}
