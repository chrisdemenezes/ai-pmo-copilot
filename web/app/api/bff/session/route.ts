import { NextResponse } from "next/server";

import { SESSION_COOKIE_NAME, createSessionToken, verifyWorkspacePassword } from "@/lib/session";

export async function POST(request: Request) {
  if (!process.env.WORKSPACE_PASSWORD) {
    return NextResponse.json(
      { error: "session_not_configured", detail: "WORKSPACE_PASSWORD não está definido." },
      { status: 503 },
    );
  }

  let password: unknown;
  try {
    ({ password } = await request.json());
  } catch {
    return NextResponse.json(
      { error: "invalid_request", detail: "Corpo deve ser JSON com um campo password." },
      { status: 400 },
    );
  }

  if (typeof password !== "string" || !verifyWorkspacePassword(password)) {
    return NextResponse.json(
      { error: "invalid_credentials", detail: "Senha do workspace incorreta." },
      { status: 401 },
    );
  }

  const { token, expiresAt } = createSessionToken();
  const response = NextResponse.json({ authenticated: true });
  response.cookies.set(SESSION_COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    expires: expiresAt,
    path: "/",
  });
  return response;
}
