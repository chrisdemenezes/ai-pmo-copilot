import { NextResponse } from "next/server";

import { institutionalHeaders, readSessionIdentity } from "@/lib/bff/domain-proxy";
import type { DashboardErrorBody, ExecutiveNarrativeResponse } from "@/lib/dashboard/types";

// Executive Narrative selects every Advisor eligible for the declared
// scope (Technical Design -- Executive Narrative §4) -- up to 7 sequential
// Advisor calls plus one Síntese under scope=organization, more than
// Decision Support's typical 2-3 (TECHNICAL-DESIGN-DECISION-SUPPORT.md
// §10). Starts at the same 120s already proven for Decision Support;
// revisited with real measurement in the Etapa 3 Executive Evidence
// (Founder mandate, "Performance").
const BACKEND_TIMEOUT_MS = 120_000;

function errorResponse(body: DashboardErrorBody, status: number) {
  return NextResponse.json(body, { status });
}

export async function POST(request: Request) {
  const backendUrl = process.env.BACKEND_URL;
  const apiKey = process.env.API_KEY;

  if (!backendUrl || !apiKey) {
    return errorResponse(
      { error: "bff_not_configured", detail: "BACKEND_URL ou API_KEY não configurados." },
      503,
    );
  }

  const identity = readSessionIdentity(request);
  if (identity === null) {
    return errorResponse({ error: "unauthorized", detail: "Sessão inválida ou expirada." }, 401);
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return errorResponse({ error: "invalid_request", detail: "Corpo da requisição inválido." }, 400);
  }

  // Executive Narrative never accepts a free-text question -- only `scope`
  // (Technical Design §2/§5.2). scope is required (Executive Intelligence
  // Explicit Scope, Vision Princípio 13) -- absence is never interpreted as
  // organization scope. Full combination validation (project_id required
  // for "project", etc.) is the backend's own contract (422); this BFF
  // only rejects the structurally impossible case of a missing/non-object
  // scope.
  const scope =
    typeof body === "object" && body !== null && "scope" in body
      ? (body as { scope: unknown }).scope
      : undefined;

  if (typeof scope !== "object" || scope === null) {
    return errorResponse({ error: "invalid_request", detail: "scope é obrigatório." }, 400);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);

  try {
    const backendResponse = await fetch(`${backendUrl}/api/executive-narrative/generate`, {
      method: "POST",
      headers: {
        "X-API-Key": apiKey,
        "Content-Type": "application/json",
        ...institutionalHeaders(identity),
      },
      body: JSON.stringify({ scope }),
      signal: controller.signal,
      cache: "no-store",
    });

    if (!backendResponse.ok) {
      if (backendResponse.status === 429) {
        return errorResponse(
          { error: "rate_limited", detail: "Muitas solicitações em pouco tempo. Aguarde e tente novamente." },
          429,
        );
      }
      if (backendResponse.status === 404) {
        return errorResponse(
          { error: "scope_not_found", detail: "Projeto ou portfólio não encontrado." },
          404,
        );
      }
      if (backendResponse.status === 422 || backendResponse.status === 400) {
        return errorResponse({ error: "invalid_request", detail: "Escopo inválido." }, 400);
      }
      return errorResponse(
        { error: "backend_error", detail: `Backend respondeu ${backendResponse.status}.` },
        502,
      );
    }

    const data = (await backendResponse.json()) as ExecutiveNarrativeResponse;
    return NextResponse.json(data);
  } catch (reason) {
    if (reason instanceof Error && reason.name === "AbortError") {
      return errorResponse(
        { error: "backend_timeout", detail: "A resposta demorou mais que o esperado. Tente novamente." },
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
