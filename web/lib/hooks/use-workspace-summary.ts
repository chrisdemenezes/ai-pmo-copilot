import { useQuery } from "@tanstack/react-query";

import type { WorkspaceSummary } from "@/lib/workspace/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

async function fetchWorkspaceSummary(projectName: string): Promise<WorkspaceSummary> {
  const response = await fetch(`/api/bff/workspace/${encodeURIComponent(projectName)}/summary`);
  return parseWorkspaceResponse<WorkspaceSummary>(response);
}

/**
 * Painel A (TIP-004 §1) -- independente dos painéis B e C: nunca depende do
 * resultado deles, nunca bloqueia a renderização deles. Alimenta a Seção 1
 * (Cabeçalho) e a parte numérica da Seção 2 (Executive Summary).
 */
export function useWorkspaceSummary(projectName: string) {
  return useQuery({
    queryKey: ["workspace-summary", projectName],
    queryFn: () => fetchWorkspaceSummary(projectName),
    staleTime: 30_000,
    retry: false,
  });
}
