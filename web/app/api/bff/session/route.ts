import { NextResponse } from "next/server";

import {
  SESSION_COOKIE_NAME,
  createSessionToken,
  resolveSessionIdentity,
} from "@/lib/session";

const BACKEND_TIMEOUT_MS = 8_000;

function withTimeout(): { controller: AbortController; timeout: ReturnType<typeof setTimeout> } {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);
  return { controller, timeout };
}

function readSessionIdentityFromRequest(request: Request) {
  const token = request.headers
    .get("cookie")
    ?.split("; ")
    .find((entry) => entry.startsWith(`${SESSION_COOKIE_NAME}=`))
    ?.slice(SESSION_COOKIE_NAME.length + 1);
  return resolveSessionIdentity(token);
}

export async function POST(request: Request) {
  const backendUrl = process.env.BACKEND_URL;
  const apiKey = process.env.API_KEY;

  if (!backendUrl || !apiKey) {
    return NextResponse.json(
      { error: "session_not_configured", detail: "BACKEND_URL ou API_KEY não configurados." },
      { status: 503 },
    );
  }

  let organization: unknown;
  let email: unknown;
  let password: unknown;
  try {
    ({ organization, email, password } = await request.json());
  } catch {
    return NextResponse.json(
      {
        error: "invalid_request",
        detail: "Corpo deve ser JSON com organization, email e password.",
      },
      { status: 400 },
    );
  }

  if (
    typeof organization !== "string" ||
    typeof email !== "string" ||
    typeof password !== "string"
  ) {
    return NextResponse.json(
      { error: "invalid_credentials", detail: "Organização, e-mail ou senha inválidos." },
      { status: 401 },
    );
  }

  const { controller, timeout } = withTimeout();
  try {
    const backendResponse = await fetch(`${backendUrl}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify({ organization, email, password }),
      signal: controller.signal,
      cache: "no-store",
    });

    if (!backendResponse.ok) {
      return NextResponse.json(
        { error: "invalid_credentials", detail: "Organização, e-mail ou senha incorretos." },
        { status: 401 },
      );
    }

    const { user_id: userId, organization_id: organizationId } = (await backendResponse.json()) as {
      user_id: number;
      organization_id: number;
    };

    const { token, expiresAt } = createSessionToken(userId, organizationId);
    const response = NextResponse.json({ authenticated: true });
    response.cookies.set(SESSION_COOKIE_NAME, token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      expires: expiresAt,
      path: "/",
    });
    return response;
  } catch {
    return NextResponse.json(
      { error: "backend_unavailable", detail: "Não foi possível contatar o backend." },
      { status: 502 },
    );
  } finally {
    clearTimeout(timeout);
  }
}

export async function DELETE(request: Request) {
  const backendUrl = process.env.BACKEND_URL;
  const apiKey = process.env.API_KEY;
  const identity = readSessionIdentityFromRequest(request);

  // Best-effort (TDS Section 15.2/15.4): a failed or skipped call to the
  // backend never blocks the user's logout -- the cookie is always expired.
  if (identity && backendUrl && apiKey) {
    const { controller, timeout } = withTimeout();
    try {
      await fetch(`${backendUrl}/api/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({ session_id: identity.sessionId, user_id: identity.userId }),
        signal: controller.signal,
        cache: "no-store",
      });
    } catch {
      // Logged server-side by the backend when reachable; nothing else to
      // do here -- the cookie still expires below.
    } finally {
      clearTimeout(timeout);
    }
  }

  const response = NextResponse.json({ authenticated: false });
  response.cookies.set(SESSION_COOKIE_NAME, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    expires: new Date(0),
    path: "/",
  });
  return response;
}

export async function GET(request: Request) {
  const identity = readSessionIdentityFromRequest(request);

  if (!identity) {
    return NextResponse.json({ authenticated: false });
  }

  return NextResponse.json({
    authenticated: true,
    user_id: identity.userId,
    organization_id: identity.organizationId,
  });
}
