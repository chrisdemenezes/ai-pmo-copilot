/**
 * User Management (Enterprise Administration, Wave 2) -- repository-shaped
 * accessors over the real backend via the BFF (`/api/bff/admin/users`),
 * same pattern as `portfolio.ts`/`program.ts`/`project.ts` (D-011): one
 * module owns the wire shape, nothing above it touches snake_case.
 */

export interface AdminUser {
  id: string;
  email: string;
  displayName: string;
  identityType: string;
  isActive: boolean;
}

export interface AdminRole {
  id: string;
  name: string;
  description: string | null;
}

/** Wire shape of UserResponse (src/api/routes/administration.py). */
interface UserApiRow {
  id: number;
  email: string;
  display_name: string;
  identity_type: string;
  is_active: boolean;
}

interface RoleApiRow {
  id: number;
  name: string;
  description: string | null;
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

function toAdminUser(row: UserApiRow): AdminUser {
  return {
    id: String(row.id),
    email: row.email,
    displayName: row.display_name,
    identityType: row.identity_type,
    isActive: row.is_active,
  };
}

function toAdminRole(row: RoleApiRow): AdminRole {
  return { id: String(row.id), name: row.name, description: row.description };
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

export async function listUsers(): Promise<AdminUser[]> {
  const response = await fetch("/api/bff/admin/users");
  const rows = await parseAdminResponse<UserApiRow[]>(response);
  return rows.map(toAdminUser);
}

export async function listRoles(): Promise<AdminRole[]> {
  const response = await fetch("/api/bff/admin/roles");
  const rows = await parseAdminResponse<RoleApiRow[]>(response);
  return rows.map(toAdminRole);
}

export async function listRolesForUser(userId: string): Promise<AdminRole[]> {
  const response = await fetch(
    `/api/bff/admin/users/${encodeURIComponent(userId)}/roles-current`,
  );
  const rows = await parseAdminResponse<RoleApiRow[]>(response);
  return rows.map(toAdminRole);
}

/** { user_id: [role names] } for the whole organization -- see
 * GET /admin/user-roles-index. Keys arrive as strings over JSON even
 * though the backend's dict is keyed by int; normalized to string here to
 * match `AdminUser.id`. */
export async function listUserRolesIndex(): Promise<Record<string, string[]>> {
  const response = await fetch("/api/bff/admin/user-roles-index");
  return parseAdminResponse<Record<string, string[]>>(response);
}

export interface CreateUserInput {
  email: string;
  displayName: string;
  password: string;
  roleName: string;
}

export async function createUser(input: CreateUserInput): Promise<AdminUser> {
  const response = await fetch("/api/bff/admin/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: input.email,
      display_name: input.displayName,
      password: input.password,
      role_name: input.roleName,
    }),
  });
  const row = await parseAdminResponse<UserApiRow>(response);
  return toAdminUser(row);
}

export interface UpdateUserInput {
  email?: string;
  displayName?: string;
}

export async function updateUser(userId: string, input: UpdateUserInput): Promise<AdminUser> {
  const response = await fetch(`/api/bff/admin/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...(input.email !== undefined ? { email: input.email } : {}),
      ...(input.displayName !== undefined ? { display_name: input.displayName } : {}),
    }),
  });
  const row = await parseAdminResponse<UserApiRow>(response);
  return toAdminUser(row);
}

export async function setUserActive(userId: string, isActive: boolean): Promise<AdminUser> {
  const response = await fetch(`/api/bff/admin/users/${encodeURIComponent(userId)}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: isActive }),
  });
  const row = await parseAdminResponse<UserApiRow>(response);
  return toAdminUser(row);
}

export async function assignRole(userId: string, roleName: string): Promise<AdminUser> {
  const response = await fetch(`/api/bff/admin/users/${encodeURIComponent(userId)}/roles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role_name: roleName }),
  });
  const row = await parseAdminResponse<UserApiRow>(response);
  return toAdminUser(row);
}

export async function removeRole(userId: string, roleName: string): Promise<AdminUser> {
  const response = await fetch(
    `/api/bff/admin/users/${encodeURIComponent(userId)}/roles/${encodeURIComponent(roleName)}`,
    { method: "DELETE" },
  );
  const row = await parseAdminResponse<UserApiRow>(response);
  return toAdminUser(row);
}
