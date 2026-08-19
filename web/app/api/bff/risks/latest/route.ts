import { NextResponse } from "next/server";

import { institutionalHeaders, readSessionIdentity } from "@/lib/bff/domain-proxy";
import type { LatestRiskItem } from "@/lib/decision-center/types";
import type { WorkspaceErrorBody } from "@/lib/workspace/types";

const BACKEND_TIMEOUT_MS = 8_000;

function errorResponse(body: WorkspaceErrorBody, status: number) {
  return NextResponse.json(body, { status });
}

/**
 * Single BFF route for both views of GET /api/risks/latest (FS-008 §3.3):
 * project_name present = Workspace scope, absent = portfolio scope -- same
 * mechanism as /api/bff/action-items.
 */
export async function GET(request: Request) {
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

  const incoming = new URL(request.url);
  const projectName = incoming.searchParams.get("project_name");
  const projectId = incoming.searchParams.get("project_id");
  const backendUrlObj = new URL(`${backendUrl}/api/risks/latest`);
  if (projectName !== null) {
    backendUrlObj.searchParams.set("project_name", projectName);
  }
  // TD-008 Fase 3b, Etapa 2 (dual-key): encaminha o project_id quando o
  // cliente o fornece, coexistindo com project_name. Aditivo.
  if (projectId !== null) {
    backendUrlObj.searchParams.set("project_id", projectId);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);

  try {
    const backendResponse = await fetch(backendUrlObj, {
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

    const data = (await backendResponse.json()) as LatestRiskItem[];
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
