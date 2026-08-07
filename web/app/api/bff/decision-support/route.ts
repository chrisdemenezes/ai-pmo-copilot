import { NextResponse } from "next/server";

import { institutionalHeaders, readSessionIdentity } from "@/lib/bff/domain-proxy";
import type { DashboardErrorBody, DecisionSupportResponse } from "@/lib/dashboard/types";

// Decision Support may invoke up to 2-3 Advisors sequentially plus one
// Síntese call (TECHNICAL-DESIGN-DECISION-SUPPORT.md §10) -- longer than
// the single-LLM-call 60s already used by .../risk-advisor/route.ts.
const BACKEND_TIMEOUT_MS = 120_000;
const MIN_LENGTH = 3;
const MAX_LENGTH = 2000;

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

  const question =
    typeof body === "object" && body !== null && "question" in body
      ? (body as { question: unknown }).question
      : undefined;
  const scope =
    typeof body === "object" && body !== null && "scope" in body
      ? (body as { scope: unknown }).scope
      : undefined;

  if (typeof question !== "string") {
    return errorResponse({ error: "invalid_request", detail: "question é obrigatório." }, 400);
  }
  if (question.trim().length === 0 || question.length < MIN_LENGTH || question.length > MAX_LENGTH) {
    return errorResponse(
      {
        error: "invalid_request",
        detail: `question deve ter entre ${MIN_LENGTH} e ${MAX_LENGTH} caracteres.`,
      },
      400,
    );
  }
  // scope is required (Executive Intelligence Explicit Scope, Vision
  // Princípio 13) -- absence is never interpreted as organization scope.
  // Full combination validation (project_id required for "project", etc.)
  // is the backend's own contract (422); this BFF only rejects the
  // structurally impossible case of a missing/non-object scope.
  if (typeof scope !== "object" || scope === null) {
    return errorResponse({ error: "invalid_request", detail: "scope é obrigatório." }, 400);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);

  try {
    const backendResponse = await fetch(`${backendUrl}/api/decision-support/ask`, {
      method: "POST",
      headers: {
        "X-API-Key": apiKey,
        "Content-Type": "application/json",
        ...institutionalHeaders(identity),
      },
      body: JSON.stringify({ question, scope }),
      signal: controller.signal,
      cache: "no-store",
    });

    if (!backendResponse.ok) {
      if (backendResponse.status === 429) {
        return errorResponse(
          { error: "rate_limited", detail: "Muitas perguntas em pouco tempo. Aguarde e tente novamente." },
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
        return errorResponse({ error: "invalid_request", detail: "Pergunta ou escopo inválido." }, 400);
      }
      return errorResponse(
        { error: "backend_error", detail: `Backend respondeu ${backendResponse.status}.` },
        502,
      );
    }

    const data = (await backendResponse.json()) as DecisionSupportResponse;
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
