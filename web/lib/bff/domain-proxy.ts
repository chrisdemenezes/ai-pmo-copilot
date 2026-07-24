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

/**
 * Exported for BFF routes that need custom behavior `forwardDomainRequest`
 * doesn't support (per-route timeout, field renaming, status-code mapping
 * -- the 3 analyze routes and the 4 Intelligence read routes, Security
 * Hardening Gate) but still need the same session-cookie -> institutional
 * headers resolution, never duplicated.
 */
export function readSessionIdentity(request: Request) {
  const token = request.headers
    .get("cookie")
    ?.split("; ")
    .find((entry) => entry.startsWith(`${SESSION_COOKIE_NAME}=`))
    ?.slice(SESSION_COOKIE_NAME.length + 1);
  return resolveSessionIdentity(token);
}

export function institutionalHeaders(identity: {
  userId: number;
  organizationId: number;
  sessionId: string;
}): Record<string, string> {
  return {
    "X-Stratech-User-Id": String(identity.userId),
    "X-Stratech-Organization-Id": String(identity.organizationId),
    "X-Stratech-Session-Id": identity.sessionId,
  };
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
    // Forward the method + body verbatim (User Management, Wave 2 --
    // POST/PATCH/DELETE joined the previously GET-only Domain BFF), so one
    // helper still serves every HTTP verb instead of a second one.
    const method = request.method;
    const hasBody = method !== "GET" && method !== "HEAD" && method !== "DELETE";
    // Forward the caller's query string too (Security Hardening Gate --
    // intelligence.py's read routes are all query-parameter driven:
    // project_name/kind/created_from/created_to) -- a no-op for routes the
    // frontend never calls with a query string.
    const incomingSearch = new URL(request.url).search;
    const backendResponse = await fetch(`${backendUrl}${backendPath}${incomingSearch}`, {
      method,
      headers: {
        "X-API-Key": apiKey,
        "X-Stratech-User-Id": String(identity.userId),
        "X-Stratech-Organization-Id": String(identity.organizationId),
        "X-Stratech-Session-Id": identity.sessionId,
        ...(hasBody ? { "Content-Type": "application/json" } : {}),
      },
      body: hasBody ? await request.text() : undefined,
      signal: controller.signal,
      cache: "no-store",
    });

    const responseBody = await backendResponse.json().catch(() => null);

    if (!backendResponse.ok) {
      // The backend's own status (401/403/404/400/409/...) and detail
      // message are real signal for a write -- collapsing every failure
      // to a generic 502 (as the read-only routes always did, since a
      // failed read only ever meant "something's wrong") would hide the
      // difference between "email já existe" (409) and "not found" (404)
      // from the Frontend.
      return errorResponse(
        responseBody ?? { error: "backend_error", detail: `Backend respondeu ${backendResponse.status}.` },
        backendResponse.status,
      );
    }

    return NextResponse.json(responseBody, { status: backendResponse.status });
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

/**
 * Session-LESS forwarding for the public invitation flow (item 6, Convites
 * -- D-054): the invitee has no account yet, so there are no institutional
 * headers to resolve -- authorization is the token in the URL/body itself,
 * exactly like `/api/bff/session`'s login POST. Same timeout/error contract
 * as `forwardDomainRequest`, minus the session gate. Only mount this on
 * routes the `proxy.ts` matcher exempts from the session gate.
 */
export async function forwardPublicRequest(
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

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);

  try {
    const method = request.method;
    const hasBody = method !== "GET" && method !== "HEAD" && method !== "DELETE";
    const backendResponse = await fetch(`${backendUrl}${backendPath}`, {
      method,
      headers: {
        "X-API-Key": apiKey,
        ...(hasBody ? { "Content-Type": "application/json" } : {}),
      },
      body: hasBody ? await request.text() : undefined,
      signal: controller.signal,
      cache: "no-store",
    });

    const responseBody = await backendResponse.json().catch(() => null);
    if (!backendResponse.ok) {
      return errorResponse(
        responseBody ?? {
          error: "backend_error",
          detail: `Backend respondeu ${backendResponse.status}.`,
        },
        backendResponse.status,
      );
    }
    return NextResponse.json(responseBody, { status: backendResponse.status });
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
