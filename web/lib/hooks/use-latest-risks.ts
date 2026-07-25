import { keepPreviousData, useQuery } from "@tanstack/react-query";

import type { LatestRiskItem } from "@/lib/decision-center/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

async function fetchLatestRisks(
  projectName?: string,
  projectId?: number,
): Promise<LatestRiskItem[]> {
  // Encoding preservado exatamente (encodeURIComponent -> %20, não "+"), para
  // manter o formato de fio idêntico ao anterior. project_id coexiste com o
  // nome (TD-008 Fase 3b, Etapa 2, dual-key) -- ambos aditivos.
  const params: string[] = [];
  if (projectName !== undefined) params.push(`project_name=${encodeURIComponent(projectName)}`);
  if (projectId !== undefined) params.push(`project_id=${projectId}`);
  const url =
    params.length === 0 ? "/api/bff/risks/latest" : `/api/bff/risks/latest?${params.join("&")}`;
  const response = await fetch(url);
  return parseWorkspaceResponse<LatestRiskItem[]>(response);
}

/**
 * Read-only, never a mutation. Same template as useActionItems: one hook
 * serves both the portfolio-wide Executive Decision Queue (no
 * projectName) and any future per-project consumer. FS-008 §3.1/§05.
 *
 * projectId (opcional, TD-008 Fase 3b Etapa 2): chave exata encaminhada
 * junto com o nome quando conhecida (dual-key coexistente).
 */
export function useLatestRisks(projectName?: string, projectId?: number) {
  return useQuery({
    queryKey: ["latest-risks", projectName ?? "portfolio", projectId ?? null],
    queryFn: () => fetchLatestRisks(projectName, projectId),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    retry: false,
    // TD-008 Fase 3b, Etapa 3: troca de chave nome->id sem flash (dado igual).
    placeholderData: keepPreviousData,
  });
}
