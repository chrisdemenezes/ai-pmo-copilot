/**
 * Sessions (Enterprise Administration, item 5 -- resolves TD-010) --
 * repository-shaped accessors over the real backend via the BFF
 * (`/api/bff/admin/sessions`), same pattern as `api-key.ts`: one module
 * owns the wire shape, nothing above it touches snake_case.
 */

import { AdminApiError } from "./api-key";

export interface AdminSession {
  id: string;
  userId: number;
  createdAt: string;
  lastSeenAt: string | null;
  revokedAt: string | null;
}

/** Wire shape of SessionResponse (src/api/routes/administration.py). */
interface SessionApiRow {
  id: string;
  user_id: number;
  created_at: string;
  last_seen_at: string | null;
  revoked_at: string | null;
}

function toSession(row: SessionApiRow): AdminSession {
  return {
    id: row.id,
    userId: row.user_id,
    createdAt: row.created_at,
    lastSeenAt: row.last_seen_at,
    revokedAt: row.revoked_at,
  };
}

async function throwFromResponse(response: Response): Promise<never> {
  const body = await response.json().catch(() => null);
  const detail =
    (body && typeof body === "object" && "detail" in body && String(body.detail)) ||
    `Falha na operação (${response.status}).`;
  throw new AdminApiError(response.status, detail);
}

export async function listSessions(): Promise<AdminSession[]> {
  const response = await fetch("/api/bff/admin/sessions");
  if (!response.ok) {
    await throwFromResponse(response);
  }
  const rows = (await response.json()) as SessionApiRow[];
  return rows.map(toSession);
}

export async function revokeSession(sessionId: string): Promise<void> {
  const response = await fetch(`/api/bff/admin/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    await throwFromResponse(response);
  }
}
