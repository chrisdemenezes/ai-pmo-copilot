/**
 * Convites (Invitations, item 6 -- D-054) -- repository-shaped accessors
 * over the real backend via the BFF, same pattern as `api-key.ts` /
 * `session.ts`: one module owns the wire shape, nothing above it touches
 * snake_case. Admin management goes through `/api/bff/admin/invitations`
 * (session-gated); the public preview/accept flow goes through
 * `/api/bff/invitations/*` (token-authenticated, no session).
 */

export type InvitationStatus = "pending" | "accepted" | "expired" | "cancelled";

export interface Invitation {
  id: string;
  email: string;
  roleName: string;
  status: InvitationStatus;
  createdAt: string;
  expiresAt: string;
  acceptedAt: string | null;
  cancelledAt: string | null;
}

export interface CreatedInvitation extends Invitation {
  /** Only ever populated by `createInvitation()`, exactly once -- never
   * returned by `listInvitations()`. The invite link is built from it. */
  plaintextToken: string;
}

export interface InvitationPreview {
  organizationName: string;
  roleName: string;
  status: InvitationStatus;
  email: string;
}

interface InvitationApiRow {
  id: number;
  email: string;
  role_name: string;
  status: InvitationStatus;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
  cancelled_at: string | null;
}

interface CreatedInvitationApiRow extends InvitationApiRow {
  plaintext_token: string;
}

interface InvitationPreviewApiRow {
  organization_name: string;
  role_name: string;
  status: InvitationStatus;
  email: string;
}

export class AdminApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "AdminApiError";
  }
}

function toInvitation(row: InvitationApiRow): Invitation {
  return {
    id: String(row.id),
    email: row.email,
    roleName: row.role_name,
    status: row.status,
    createdAt: row.created_at,
    expiresAt: row.expires_at,
    acceptedAt: row.accepted_at,
    cancelledAt: row.cancelled_at,
  };
}

async function parseAdminResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail =
      (body && typeof body === "object" && "detail" in body && String(body.detail)) ||
      `Falha na operação (${response.status}).`;
    throw new AdminApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export async function listInvitations(): Promise<Invitation[]> {
  const response = await fetch("/api/bff/admin/invitations");
  const rows = await parseAdminResponse<InvitationApiRow[]>(response);
  return rows.map(toInvitation);
}

export async function createInvitation(
  email: string,
  roleName: string,
): Promise<CreatedInvitation> {
  const response = await fetch("/api/bff/admin/invitations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, role_name: roleName }),
  });
  const row = await parseAdminResponse<CreatedInvitationApiRow>(response);
  return { ...toInvitation(row), plaintextToken: row.plaintext_token };
}

export async function cancelInvitation(invitationId: string): Promise<void> {
  const response = await fetch(
    `/api/bff/admin/invitations/${encodeURIComponent(invitationId)}`,
    { method: "DELETE" },
  );
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail =
      (body && typeof body === "object" && "detail" in body && String(body.detail)) ||
      `Falha na operação (${response.status}).`;
    throw new AdminApiError(response.status, detail);
  }
}

// -- Public flow (no session; the token is the authorization) ----------

export async function previewInvitation(token: string): Promise<InvitationPreview> {
  const response = await fetch(`/api/bff/invitations/${encodeURIComponent(token)}`);
  const row = await parseAdminResponse<InvitationPreviewApiRow>(response);
  return {
    organizationName: row.organization_name,
    roleName: row.role_name,
    status: row.status,
    email: row.email,
  };
}

export async function acceptInvitation(
  token: string,
  displayName: string,
  password: string,
): Promise<void> {
  const response = await fetch("/api/bff/invitations/accept", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, display_name: displayName, password }),
  });
  await parseAdminResponse<{ user_id: number; organization_id: number }>(response);
}
