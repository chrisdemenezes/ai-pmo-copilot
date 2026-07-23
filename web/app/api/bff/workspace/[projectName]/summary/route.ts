import { NextResponse } from "next/server";

import { institutionalHeaders, readSessionIdentity } from "@/lib/bff/domain-proxy";
import type { WorkspaceErrorBody, WorkspaceSummary } from "@/lib/workspace/types";

const BACKEND_TIMEOUT_MS = 8_000;

function errorResponse(body: WorkspaceErrorBody, status: number) {
  return NextResponse.json(body, { status });
}

export async function GET(
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

  // Next.js hands this route the raw (still URL-encoded) segment, same as
  // the page component -- decode once here before re-encoding for the
  // outbound backend call, or a "/" in the project name gets encoded twice.
  const { projectName: rawProjectName } = await params;
  const projectName = decodeURIComponent(rawProjectName);

  // project_name travels as a query parameter, not a path segment -- the
  // backend route was migrated off /projects/{project_name}/summary because
  // Starlette's path converter can't capture a literal "/" no matter how
  // the client encodes it. URLSearchParams.set() encodes correctly here,
  // matching the already-working /api/analyses BFF route.
  const backendUrlObj = new URL(`${backendUrl}/api/projects/summary`);
  backendUrlObj.searchParams.set("project_name", projectName);

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

    const data = (await backendResponse.json()) as WorkspaceSummary;
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
