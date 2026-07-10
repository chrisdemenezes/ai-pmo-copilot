import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE_NAME, verifySessionToken } from "@/lib/session";

// FS-001 dependency: gates /dashboard and every BFF route behind the
// Nível 1 workspace session (RFC-001). /api/bff/session issues that
// session, so it must stay reachable while unauthenticated.
const LOGIN_ROUTE = "/api/bff/session";

export const config = {
  matcher: ["/dashboard", "/dashboard/:path*", "/api/bff/:path*"],
};

export function proxy(request: NextRequest) {
  // Emergency kill switch (TIP-001 §7 rollback strategy): if the session
  // gate misbehaves in production, disable it without reverting the whole
  // feature. Isolated to this one check -- the rest of /dashboard is unaffected.
  if (process.env.DISABLE_WORKSPACE_SESSION_GATE === "true") {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;

  if (pathname === LOGIN_ROUTE) {
    return NextResponse.next();
  }

  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (verifySessionToken(token)) {
    return NextResponse.next();
  }

  if (pathname.startsWith("/api/bff/")) {
    return NextResponse.json(
      { error: "unauthenticated", detail: "Sessão de workspace requerida." },
      { status: 401 },
    );
  }

  const loginUrl = new URL("/entrar", request.url);
  loginUrl.searchParams.set("redirect", pathname);
  return NextResponse.redirect(loginUrl);
}
