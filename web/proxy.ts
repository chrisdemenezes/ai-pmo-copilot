import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE_NAME, verifySessionToken } from "@/lib/session";

// FS-001 dependency: gates /dashboard and every BFF route behind the
// Nível 1 workspace session (RFC-001). /api/bff/session issues that
// session, so it must stay reachable while unauthenticated.
const LOGIN_ROUTE = "/api/bff/session";

export const config = {
  matcher: [
    "/dashboard",
    "/dashboard/:path*",
    "/workspace",
    "/workspace/:path*",
    "/projects",
    "/projects/:path*",
    "/program-management",
    "/program-management/:path*",
    "/project-delivery",
    "/project-delivery/:path*",
    "/actions",
    "/actions/:path*",
    "/decisions",
    "/decisions/:path*",
    "/portfolio",
    "/portfolio/:path*",
    "/aprendizados",
    "/aprendizados/:path*",
    "/mission-control",
    "/mission-control/:path*",
    // D-051 -- Administração (Usuários, Chaves de API) was never in this
    // matcher: an unauthenticated visitor could load the page shell (data
    // fetches would still 401 via the BFF gate below, but the page itself
    // rendered). API Keys makes this gap more consequential -- closing it
    // for the whole section, not just the new page.
    "/administracao",
    "/administracao/:path*",
    "/api/bff/:path*",
  ],
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
