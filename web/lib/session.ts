import crypto from "node:crypto";

/**
 * Individual session (STRATECH V2 Epic 2 -- Identity Foundation): the
 * cookie now carries a real identity (session_id, user_id, organization_id)
 * signed with HMAC, replacing the Nível 1 workspace-wide boolean session
 * (RFC-001). Credential verification itself lives in the backend
 * (POST /api/auth/login, Argon2) -- this module only signs/verifies the
 * cookie payload, exactly as it did before.
 */

export const SESSION_COOKIE_NAME = "stratech_session";

const SESSION_TTL_MS = 12 * 60 * 60 * 1000;

export interface SessionIdentity {
  sessionId: string;
  userId: number;
  organizationId: number;
  expiresAt: number;
}

function getSecret(): string {
  const secret = process.env.SESSION_SECRET;
  if (!secret) {
    throw new Error("SESSION_SECRET must be set to issue or verify sessions");
  }
  return secret;
}

function sign(value: string): string {
  return crypto.createHmac("sha256", getSecret()).update(value).digest("hex");
}

function safeEqual(a: string, b: string): boolean {
  const bufferA = Buffer.from(a);
  const bufferB = Buffer.from(b);
  if (bufferA.length !== bufferB.length) {
    return false;
  }
  return crypto.timingSafeEqual(bufferA, bufferB);
}

export function createSessionToken(
  userId: number,
  organizationId: number,
): { token: string; expiresAt: Date } {
  const sessionId = crypto.randomUUID();
  const expiresAt = new Date(Date.now() + SESSION_TTL_MS);
  const payload = `${sessionId}.${userId}.${organizationId}.${expiresAt.getTime()}`;
  return { token: `${payload}.${sign(payload)}`, expiresAt };
}

/** Boolean gate used by proxy.ts -- unchanged in shape from before Epic 2. */
export function verifySessionToken(token: string | undefined): boolean {
  return resolveSessionIdentity(token) !== null;
}

/** Full identity used by the BFF session route (login/logout/whoami). */
export function resolveSessionIdentity(token: string | undefined): SessionIdentity | null {
  if (!token) {
    return null;
  }
  const parts = token.split(".");
  if (parts.length !== 5) {
    return null;
  }
  const [sessionId, userIdRaw, organizationIdRaw, expiresAtRaw, signature] = parts;
  const payload = `${sessionId}.${userIdRaw}.${organizationIdRaw}.${expiresAtRaw}`;
  if (!safeEqual(signature, sign(payload))) {
    return null;
  }

  const userId = Number(userIdRaw);
  const organizationId = Number(organizationIdRaw);
  const expiresAt = Number(expiresAtRaw);
  if (
    !Number.isFinite(userId) ||
    !Number.isFinite(organizationId) ||
    !Number.isFinite(expiresAt) ||
    expiresAt <= Date.now()
  ) {
    return null;
  }

  return { sessionId, userId, organizationId, expiresAt };
}
