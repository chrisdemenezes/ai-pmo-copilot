import type { WorkspaceErrorBody } from "@/lib/workspace/types";

/** Shared across the 3 independent workspace queries -- same shape as DashboardFetchError. */
export class WorkspaceFetchError extends Error {
  constructor(public readonly body: WorkspaceErrorBody) {
    super(body.detail);
  }
}

export async function parseWorkspaceResponse<T>(response: Response): Promise<T> {
  const body = await response.json();
  if (!response.ok) {
    throw new WorkspaceFetchError(body as WorkspaceErrorBody);
  }
  return body as T;
}
