import { NextResponse } from "next/server";

import { institutionalHeaders, readSessionIdentity } from "@/lib/bff/domain-proxy";
import type { AnalyzeMeetingIntelligenceResponse, WorkspaceErrorBody } from "@/lib/workspace/types";

// Same convention as .../analyze/status and .../analyze/risk (TIP-005/006).
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

  // Security Hardening Gate (C-1/C-2): the backend now requires RBAC +
  // organization scope on this route.
  const identity = readSessionIdentity(request);
  if (identity === null) {
    return errorResponse({ error: "unauthorized", detail: "Sessão inválida ou expirada." }, 401);
  }

  const { projectName: rawProjectName } = await params;
  const projectName = decodeURIComponent(rawProjectName);

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return errorResponse({ error: "invalid_request", detail: "Corpo da requisição inválido." }, 400);
  }

  // The client sends the same { project_context } shape as the other 2
  // analyze routes -- consistent hook contract across all 3 Capabilities.
  // Only here, at the single point that talks to the real backend, does it
  // become "transcript" (src/api/routes/intelligence.py's
  // MeetingAnalysisRequest), the one field-name asymmetry among the 3
  // agents (FS-006 §2.3) -- isolated to this BFF route on purpose.
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
    const backendResponse = await fetch(`${backendUrl}/api/meetings/analyze`, {
      method: "POST",
      headers: {
        "X-API-Key": apiKey,
        "Content-Type": "application/json",
        ...institutionalHeaders(identity),
      },
      body: JSON.stringify({ transcript: projectContext, project_name: projectName }),
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

    const data = (await backendResponse.json()) as AnalyzeMeetingIntelligenceResponse;
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
