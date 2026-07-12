import { NextResponse } from "next/server";

import type { AnalysisListItem, WorkspaceErrorBody } from "@/lib/workspace/types";

const BACKEND_TIMEOUT_MS = 8_000;

// Query params this route accepts from the client and forwards as-is to the
// backend's GET /api/analyses -- no new filter invented, only what
// src/api/routes/intelligence.py:134 already supports.
const FORWARDED_PARAMS = ["kind", "limit", "offset", "created_from", "created_to"];

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

  // Next.js hands this route the raw (still URL-encoded) segment -- decode
  // once. URLSearchParams.set() below encodes it correctly for the outbound
  // query string; no manual encodeURIComponent is needed for this one.
  const { projectName: rawProjectName } = await params;
  const projectName = decodeURIComponent(rawProjectName);
  const incoming = new URL(request.url);

  const backendUrlObj = new URL(`${backendUrl}/api/analyses`);
  backendUrlObj.searchParams.set("project_name", projectName);
  for (const key of FORWARDED_PARAMS) {
    const value = incoming.searchParams.get(key);
    if (value !== null) {
      backendUrlObj.searchParams.set(key, value);
    }
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);

  try {
    const backendResponse = await fetch(backendUrlObj, {
      headers: { "X-API-Key": apiKey },
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

    const data = (await backendResponse.json()) as AnalysisListItem[];
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
