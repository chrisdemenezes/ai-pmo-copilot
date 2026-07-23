import { NextResponse } from "next/server";

import { institutionalHeaders, readSessionIdentity } from "@/lib/bff/domain-proxy";
import type { DashboardErrorBody, ProjectSummary } from "@/lib/dashboard/types";

const BACKEND_TIMEOUT_MS = 8_000;

function errorResponse(body: DashboardErrorBody, status: number) {
  return NextResponse.json(body, { status });
}

export async function GET(request: Request) {
  const backendUrl = process.env.BACKEND_URL;
  const apiKey = process.env.API_KEY;

  if (!backendUrl || !apiKey) {
    return errorResponse(
      { error: "bff_not_configured", detail: "BACKEND_URL ou API_KEY não configurados." },
      503,
    );
  }

  // Security Hardening Gate (C-1/C-2): /api/portfolio/summary now requires
  // RBAC + organization scope, same institutional headers every other
  // Domain BFF route already resolves from the session cookie.
  const identity = readSessionIdentity(request);
  if (identity === null) {
    return errorResponse({ error: "unauthorized", detail: "Sessão inválida ou expirada." }, 401);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);

  try {
    const backendResponse = await fetch(`${backendUrl}/api/portfolio/summary`, {
      headers: { "X-API-Key": apiKey, ...institutionalHeaders(identity) },
      signal: controller.signal,
      cache: "no-store",
    });

    if (!backendResponse.ok) {
      return errorResponse(
        {
          error: "backend_error",
          detail: `Backend respondeu ${backendResponse.status}.`,
        },
        502,
      );
    }

    const data = (await backendResponse.json()) as ProjectSummary[];
    return NextResponse.json(data);
  } catch (reason) {
    if (reason instanceof Error && reason.name === "AbortError") {
      return errorResponse(
        { error: "backend_timeout", detail: "Backend não respondeu a tempo." },
        504,
      );
    }
    return errorResponse(
      { error: "backend_unavailable", detail: "Não foi possível contatar o backend." },
      502,
    );
  } finally {
    clearTimeout(timeout);
  }
}
