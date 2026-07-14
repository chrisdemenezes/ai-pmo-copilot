import { useQuery } from "@tanstack/react-query";

import type { LatestRiskItem } from "@/lib/decision-center/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

async function fetchLatestRisks(projectName?: string): Promise<LatestRiskItem[]> {
  const url =
    projectName === undefined
      ? "/api/bff/risks/latest"
      : `/api/bff/risks/latest?project_name=${encodeURIComponent(projectName)}`;
  const response = await fetch(url);
  return parseWorkspaceResponse<LatestRiskItem[]>(response);
}

/**
 * Read-only, never a mutation. Same template as useActionItems: one hook
 * serves both the portfolio-wide Executive Decision Queue (no
 * projectName) and any future per-project consumer. FS-008 §3.1/§05.
 */
export function useLatestRisks(projectName?: string) {
  return useQuery({
    queryKey: ["latest-risks", projectName ?? "portfolio"],
    queryFn: () => fetchLatestRisks(projectName),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    retry: false,
  });
}
