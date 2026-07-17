import { useQuery } from "@tanstack/react-query";

import type { ActionItemView } from "@/lib/workspace/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

async function fetchActionItems(projectName?: string): Promise<ActionItemView[]> {
  const url =
    projectName === undefined
      ? "/api/bff/action-items"
      : `/api/bff/action-items?project_name=${encodeURIComponent(projectName)}`;
  const response = await fetch(url);
  return parseWorkspaceResponse<ActionItemView[]>(response);
}

/**
 * Read-only, never a mutation -- Action Intelligence has zero writes
 * (FS-007 §03). One hook serves both surfaces: with projectName it feeds a
 * Workspace's "Ações" section; without it, the portfolio "Ações" page.
 * The 3 Briefs' context lines share the same per-project cache entry, so a
 * Workspace never fetches the list twice for the same screen.
 * staleTime/refetchInterval mirror usePortfolioSummary; retry: false for
 * the same Product Behavior Decision (honest error signal over silence).
 */
export function useActionItems(projectName?: string) {
  return useQuery({
    queryKey: ["action-items", projectName ?? "portfolio"],
    queryFn: () => fetchActionItems(projectName),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    retry: false,
  });
}
