import { useQuery } from "@tanstack/react-query";

import type { DashboardErrorBody, ProjectSummary } from "@/lib/dashboard/types";

export class DashboardFetchError extends Error {
  constructor(public readonly body: DashboardErrorBody) {
    super(body.detail);
  }
}

async function fetchPortfolioSummary(): Promise<ProjectSummary[]> {
  const response = await fetch("/api/bff/dashboard");
  const body = await response.json();
  if (!response.ok) {
    throw new DashboardFetchError(body as DashboardErrorBody);
  }
  return body as ProjectSummary[];
}

/**
 * staleTime/refetchInterval per FS-001 Data Freshness Matrix (RFC-001 D3):
 * 30s stale window, 60s background poll while the tab is visible.
 *
 * retry: false is a Product Behavior Decision (T9), not the TanStack Query
 * default: the BFF already tolerates transient network slowness via its own
 * 8s timeout, so a query-level retry only delays the honest error signal an
 * executive user is owed -- measured at ~8s (backend down) to ~40s (backend
 * hanging) with the default retry=3 backoff. Scoped to this query only, not
 * the QueryClient global.
 */
export function usePortfolioSummary() {
  return useQuery({
    queryKey: ["portfolio-summary"],
    queryFn: fetchPortfolioSummary,
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    retry: false,
  });
}
