import crypto from "node:crypto";

/**
 * Minimal workspace-wide session (RFC-001 "Nível 1"): a single shared
 * password gates the whole BFF, no per-user identity. Signed with an
 * HMAC so the cookie can't be forged without SESSION_SECRET.
 */

export const SESSION_COOKIE_NAME = "workspace_session";

const SESSION_TTL_MS = 12 * 60 * 60 * 1000;

function getSecret(): string {
  const secret = process.env.SESSION_SECRET;
  if (!secret) {
    throw new Error("SESSION_SECRET must be set to issue or verify workspace sessions");
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

export function createSessionToken(): { token: string; expiresAt: Date } {
  const expiresAt = new Date(Date.now() + SESSION_TTL_MS);
  const payload = String(expiresAt.getTime());
  return { token: `${payload}.${sign(payload)}`, expiresAt };
}

export function verifySessionToken(token: string | undefined): boolean {
  if (!token) {
    return false;
  }
  const [payload, signature] = token.split(".");
  if (!payload || !signature || !safeEqual(signature, sign(payload))) {
    return false;
  }
  const expiresAt = Number(payload);
  return Number.isFinite(expiresAt) && expiresAt > Date.now();
}

export function verifyWorkspacePassword(candidate: string): boolean {
  const workspacePassword = process.env.WORKSPACE_PASSWORD;
  if (!workspacePassword) {
    return false;
  }
  return safeEqual(candidate, workspacePassword);
}
