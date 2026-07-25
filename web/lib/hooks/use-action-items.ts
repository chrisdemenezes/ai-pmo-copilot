import { useQuery } from "@tanstack/react-query";

import type { ActionItemView } from "@/lib/workspace/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

async function fetchActionItems(
  projectName?: string,
  projectId?: number,
): Promise<ActionItemView[]> {
  // Encoding preservado exatamente (encodeURIComponent -> %20, não "+"), para
  // manter o formato de fio idêntico ao anterior. project_id coexiste com o
  // nome (TD-008 Fase 3b, Etapa 2, dual-key) -- ambos aditivos.
  const params: string[] = [];
  if (projectName !== undefined) params.push(`project_name=${encodeURIComponent(projectName)}`);
  if (projectId !== undefined) params.push(`project_id=${projectId}`);
  const url =
    params.length === 0 ? "/api/bff/action-items" : `/api/bff/action-items?${params.join("&")}`;
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
 *
 * projectId (opcional, TD-008 Fase 3b Etapa 2): chave exata encaminhada
 * junto com o nome quando conhecida (dual-key coexistente).
 */
export function useActionItems(projectName?: string, projectId?: number) {
  return useQuery({
    queryKey: ["action-items", projectName ?? "portfolio", projectId ?? null],
    queryFn: () => fetchActionItems(projectName, projectId),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    retry: false,
  });
}
