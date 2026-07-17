import { NextResponse } from "next/server";

import type { ActionItemView, WorkspaceErrorBody } from "@/lib/workspace/types";

const BACKEND_TIMEOUT_MS = 8_000;

function errorResponse(body: WorkspaceErrorBody, status: number) {
  return NextResponse.json(body, { status });
}

/**
 * Single BFF route for both views of GET /api/action-items (FS-007 §2.3):
 * project_name present = Workspace view, absent = portfolio view -- the
 * query parameter is forwarded as-is, same mechanism as the summary route.
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

  // project_name travels as a query parameter, never a path segment --
  // same reasoning as the workspace summary BFF route: Starlette's path
  // converter can't capture a literal "/" in a project name, query
  // parameters can. URLSearchParams already hands us the decoded value.
  const projectName = new URL(request.url).searchParams.get("project_name");
  const backendUrlObj = new URL(`${backendUrl}/api/action-items`);
  if (projectName !== null) {
    backendUrlObj.searchParams.set("project_name", projectName);
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

    const data = (await backendResponse.json()) as ActionItemView[];
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
