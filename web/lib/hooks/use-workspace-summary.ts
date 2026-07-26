import { useQuery } from "@tanstack/react-query";

import type { ProjectIntelligenceSummary } from "@/lib/workspace/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

async function fetchWorkspaceSummary(
  projectName: string,
  projectId?: number,
): Promise<ProjectIntelligenceSummary> {
  const url = new URL(
    `/api/bff/workspace/${encodeURIComponent(projectName)}/summary`,
    window.location.origin,
  );
  // TD-008 Fase 3b, Etapa 2 (dual-key): quando o project_id resolvido já é
  // conhecido, envia-o junto com o nome; coexistem. Aditivo -- ausente, a
  // chamada é idêntica à anterior.
  if (projectId !== undefined) {
    url.searchParams.set("project_id", String(projectId));
  }
  const response = await fetch(url.pathname + url.search);
  return parseWorkspaceResponse<ProjectIntelligenceSummary>(response);
}

/**
 * Painel A (TIP-004 §1) -- independente dos painéis B e C: nunca depende do
 * resultado deles, nunca bloqueia a renderização deles. Alimenta a Seção 1
 * (Cabeçalho) e a parte numérica da Seção 2 (Executive Summary).
 *
 * projectId (opcional, TD-008 Fase 3b Etapa 2): quando informado, é
 * encaminhado como chave exata junto com o nome (dual-key coexistente).
 */
export function useWorkspaceSummary(projectName: string, projectId?: number) {
  return useQuery({
    queryKey: ["workspace-summary", projectName, projectId ?? null],
    queryFn: () => fetchWorkspaceSummary(projectName, projectId),
    staleTime: 30_000,
    retry: false,
  });
}
