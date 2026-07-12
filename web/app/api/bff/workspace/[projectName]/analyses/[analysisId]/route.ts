import { NextResponse } from "next/server";

import type { AnalysisDetail, WorkspaceErrorBody } from "@/lib/workspace/types";

const BACKEND_TIMEOUT_MS = 8_000;

function errorResponse(body: WorkspaceErrorBody, status: number) {
  return NextResponse.json(body, { status });
}

// projectName is not sent to the backend here -- GET /api/analyses/{id}
// (src/api/routes/intelligence.py:162) is not itself scoped by project, and
// the id is only reachable from the analyses list that already was. Kept in
// the route path purely so the URL stays workspace-scoped and consistent
// with the other 2 BFF routes.
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ projectName: string; analysisId: string }> },
) {
  const backendUrl = process.env.BACKEND_URL;
  const apiKey = process.env.API_KEY;

  if (!backendUrl || !apiKey) {
    return errorResponse(
      { error: "bff_not_configured", detail: "BACKEND_URL ou API_KEY não configurados." },
      503,
    );
  }

  const { analysisId } = await params;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);

  try {
    const backendResponse = await fetch(
      `${backendUrl}/api/analyses/${encodeURIComponent(analysisId)}`,
      {
        headers: { "X-API-Key": apiKey },
        signal: controller.signal,
        cache: "no-store",
      },
    );

    if (backendResponse.status === 404) {
      return errorResponse({ error: "not_found", detail: "Análise não encontrada." }, 404);
    }

    if (!backendResponse.ok) {
      return errorResponse(
        {
          error: "backend_error",
          detail: `Backend respondeu ${backendResponse.status}.`,
        },
        502,
      );
    }

    const data = (await backendResponse.json()) as AnalysisDetail;
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
