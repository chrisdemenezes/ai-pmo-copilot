import { useQuery } from "@tanstack/react-query";

import type { AnalysisDetail } from "@/lib/workspace/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

async function fetchAnalysisDetail(
  projectName: string,
  analysisId: number,
): Promise<AnalysisDetail> {
  const response = await fetch(
    `/api/bff/workspace/${encodeURIComponent(projectName)}/analyses/${analysisId}`,
  );
  return parseWorkspaceResponse<AnalysisDetail>(response);
}

/**
 * Drill-down sob demanda para a Seção 8 (Histórico completo) -- só busca
 * quando o item é aberto (enabled), não antecipa nada para toda a lista.
 */
export function useWorkspaceAnalysisDetail(
  projectName: string,
  analysisId: number | null,
) {
  return useQuery({
    queryKey: ["workspace-analysis-detail", projectName, analysisId],
    queryFn: () => fetchAnalysisDetail(projectName, analysisId as number),
    enabled: analysisId !== null,
    staleTime: 30_000,
    retry: false,
  });
}
