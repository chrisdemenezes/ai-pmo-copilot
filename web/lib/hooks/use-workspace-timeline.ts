import { useQuery } from "@tanstack/react-query";

import type { AnalysisListItem } from "@/lib/workspace/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

interface TimelineOptions {
  limit?: number;
  offset?: number;
  // TD-008 Fase 3b, Etapa 2 (dual-key): project_id opcional, coexiste com o
  // nome da rota; encaminhado ao BFF quando conhecido.
  projectId?: number;
}

async function fetchWorkspaceTimeline(
  projectName: string,
  { limit, offset, projectId }: TimelineOptions,
): Promise<AnalysisListItem[]> {
  const url = new URL(
    `/api/bff/workspace/${encodeURIComponent(projectName)}/analyses`,
    window.location.origin,
  );
  if (limit !== undefined) url.searchParams.set("limit", String(limit));
  if (offset !== undefined) url.searchParams.set("offset", String(offset));
  if (projectId !== undefined) url.searchParams.set("project_id", String(projectId));

  const response = await fetch(url.pathname + url.search);
  return parseWorkspaceResponse<AnalysisListItem[]>(response);
}

/**
 * Painel B (TIP-004 §1) -- independente dos painéis A e C. Lista pura
 * (id/kind/created_at), sem buscar o payload de cada item -- evita N+1 e
 * mantém o painel autocontido. Alimenta a Seção 3 (Intelligence Timeline) e
 * a Seção 8 (Histórico completo), que reaproveita a mesma lista paginada.
 */
export function useWorkspaceTimeline(projectName: string, options: TimelineOptions = {}) {
  return useQuery({
    queryKey: [
      "workspace-timeline",
      projectName,
      options.limit,
      options.offset,
      options.projectId ?? null,
    ],
    queryFn: () => fetchWorkspaceTimeline(projectName, options),
    staleTime: 30_000,
    retry: false,
  });
}
