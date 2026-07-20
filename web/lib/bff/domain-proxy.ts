import { NextResponse } from "next/server";

import type { DashboardErrorBody } from "@/lib/dashboard/types";
import { SESSION_COOKIE_NAME, resolveSessionIdentity } from "@/lib/session";

/**
 * Shared BFF forwarding for the Enterprise Domain API (Wave 2, Sprint 5).
 *
 * One helper instead of three copy-pasted route bodies (CLAUDE.md: nunca
 * duplicar código) -- same timeout/error contract as the dashboard BFF
 * (`DashboardErrorBody`), plus the piece unique to the Domain API: the
 * X-Stratech-* institutional headers, resolved server-side from the
 * session cookie (never trusted from the browser). No session -> 401
 * before any backend call is made.
 */

const BACKEND_TIMEOUT_MS = 8_000;

function errorResponse(body: DashboardErrorBody, status: number) {
  return NextResponse.json(body, { status });
}

function readSessionIdentity(request: Request) {
  const token = request.headers
    .get("cookie")
    ?.split("; ")
    .find((entry) => entry.startsWith(`${SESSION_COOKIE_NAME}=`))
    ?.slice(SESSION_COOKIE_NAME.length + 1);
  return resolveSessionIdentity(token);
}

export async function forwardDomainRequest(
  request: Request,
  backendPath: string,
): Promise<NextResponse> {
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

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);

  try {
    const backendResponse = await fetch(`${backendUrl}${backendPath}`, {
      headers: {
        "X-API-Key": apiKey,
        "X-Stratech-User-Id": String(identity.userId),
        "X-Stratech-Organization-Id": String(identity.organizationId),
        "X-Stratech-Session-Id": identity.sessionId,
      },
      signal: controller.signal,
      cache: "no-store",
    });

    if (!backendResponse.ok) {
      return errorResponse(
        { error: "backend_error", detail: `Backend respondeu ${backendResponse.status}.` },
        502,
      );
    }

    return NextResponse.json(await backendResponse.json());
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
