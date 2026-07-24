import { createSessionToken, SESSION_COOKIE_NAME } from "@/lib/session";

/**
 * Shared by every BFF route test that now needs a signed session cookie
 * (Security Hardening Gate C-1: intelligence.py's routes require RBAC +
 * organization scope, so the BFF must resolve institutional headers from a
 * real session before proxying). Requires SESSION_SECRET to be stubbed by
 * the caller first (createSessionToken throws otherwise).
 */
export function authenticatedRequest(
  url: string,
  init: RequestInit = {},
  identity: { userId: number; organizationId: number; sessionId?: string } = {
    userId: 1,
    organizationId: 1,
  },
): Request {
  const { token } = createSessionToken(
    identity.userId,
    identity.organizationId,
    identity.sessionId ?? "test-session",
  );
  const headers = new Headers(init.headers);
  headers.set("cookie", `${SESSION_COOKIE_NAME}=${token}`);
  return new Request(url, { ...init, headers });
}
