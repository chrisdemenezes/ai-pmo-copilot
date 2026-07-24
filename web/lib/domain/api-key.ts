/**
 * API Keys (Enterprise Administration, D-051) -- repository-shaped
 * accessors over the real backend via the BFF (`/api/bff/admin/api-keys`),
 * same pattern as `user.ts` (D-011): one module owns the wire shape,
 * nothing above it touches snake_case.
 */

export interface ApiKey {
  id: string;
  name: string;
  keyPrefix: string;
  createdAt: string;
  lastUsedAt: string | null;
  revokedAt: string | null;
}

export interface CreatedApiKey extends ApiKey {
  /** Only ever populated by `createApiKey()`, exactly once -- never
   * returned by `listApiKeys()`. */
  plaintextKey: string;
}

/** Wire shape of ApiKeyResponse (src/api/routes/administration.py). */
interface ApiKeyApiRow {
  id: number;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

interface CreatedApiKeyApiRow extends ApiKeyApiRow {
  plaintext_key: string;
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

function toApiKey(row: ApiKeyApiRow): ApiKey {
  return {
    id: String(row.id),
    name: row.name,
    keyPrefix: row.key_prefix,
    createdAt: row.created_at,
    lastUsedAt: row.last_used_at,
    revokedAt: row.revoked_at,
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

export async function listApiKeys(): Promise<ApiKey[]> {
  const response = await fetch("/api/bff/admin/api-keys");
  const rows = await parseAdminResponse<ApiKeyApiRow[]>(response);
  return rows.map(toApiKey);
}

export async function createApiKey(name: string): Promise<CreatedApiKey> {
  const response = await fetch("/api/bff/admin/api-keys", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  const row = await parseAdminResponse<CreatedApiKeyApiRow>(response);
  return { ...toApiKey(row), plaintextKey: row.plaintext_key };
}

export async function revokeApiKey(apiKeyId: string): Promise<void> {
  const response = await fetch(`/api/bff/admin/api-keys/${encodeURIComponent(apiKeyId)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail =
      (body && typeof body === "object" && "detail" in body && String(body.detail)) ||
      `Falha na operação (${response.status}).`;
    throw new AdminApiError(response.status, detail);
  }
}
