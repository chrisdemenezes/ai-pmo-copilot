import { resolveEnvironment, validateStartupConfig } from "@/lib/startup-config";

/**
 * W7-5 Etapa 1: Next.js server-startup hook (stable since Next 15,
 * confirmed via `node_modules/next/dist/docs/`), runs once when the
 * server process boots -- the frontend's equivalent of the backend
 * lifespan's fail-fast check. Skipped on the edge runtime: this repo's
 * config never runs on it, and `process.env` access there is restricted.
 */
export function register() {
  if (process.env.NEXT_RUNTIME === "edge") {
    return;
  }
  validateStartupConfig(resolveEnvironment());
}
