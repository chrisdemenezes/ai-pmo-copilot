import { NextResponse } from "next/server";

import type { AnalyzeRiskReviewResponse, WorkspaceErrorBody } from "@/lib/workspace/types";

// Same convention as .../analyze/status/route.ts (TIP-005): 60s, not the 8s
// used by fast DB-only reads, because the LLM call behind /api/risks/analyze
// has no timeout of its own.
const BACKEND_TIMEOUT_MS = 60_000;
const MIN_LENGTH = 10;
const MAX_LENGTH = 20000;

function errorResponse(body: WorkspaceErrorBody, status: number) {
  return NextResponse.json(body, { status });
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ projectName: string }> },
) {
  const backendUrl = process.env.BACKEND_URL;
  const apiKey = process.env.API_KEY;

  if (!backendUrl || !apiKey) {
    return errorResponse(
      { error: "bff_not_configured", detail: "BACKEND_URL ou API_KEY não configurados." },
      503,
    );
  }

  const { projectName: rawProjectName } = await params;
  const projectName = decodeURIComponent(rawProjectName);

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return errorResponse({ error: "invalid_request", detail: "Corpo da requisição inválido." }, 400);
  }

  const projectContext =
    typeof body === "object" && body !== null && "project_context" in body
      ? (body as { project_context: unknown }).project_context
      : undefined;

  if (typeof projectContext !== "string") {
    return errorResponse(
      { error: "invalid_request", detail: "project_context é obrigatório." },
      400,
    );
  }
  if (projectContext.trim().length === 0 || projectContext.length < MIN_LENGTH || projectContext.length > MAX_LENGTH) {
    return errorResponse(
      {
        error: "invalid_request",
        detail: `project_context deve ter entre ${MIN_LENGTH} e ${MAX_LENGTH} caracteres.`,
      },
      400,
    );
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);

  try {
    const backendResponse = await fetch(`${backendUrl}/api/risks/analyze`, {
      method: "POST",
      headers: { "X-API-Key": apiKey, "Content-Type": "application/json" },
      body: JSON.stringify({ project_context: projectContext, project_name: projectName }),
      signal: controller.signal,
      cache: "no-store",
    });

    if (!backendResponse.ok) {
      if (backendResponse.status === 429) {
        return errorResponse(
          { error: "rate_limited", detail: "Muitas análises em pouco tempo. Aguarde e tente novamente." },
          429,
        );
      }
      if (backendResponse.status === 422 || backendResponse.status === 400) {
        return errorResponse(
          { error: "invalid_request", detail: "Contexto inválido para análise." },
          400,
        );
      }
      return errorResponse(
        { error: "backend_error", detail: `Backend respondeu ${backendResponse.status}.` },
        502,
      );
    }

    const data = (await backendResponse.json()) as AnalyzeRiskReviewResponse;
    return NextResponse.json(data);
  } catch (reason) {
    if (reason instanceof Error && reason.name === "AbortError") {
      return errorResponse(
        { error: "backend_timeout", detail: "A análise demorou mais que o esperado. Tente novamente." },
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
