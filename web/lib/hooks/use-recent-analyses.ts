import { useQuery } from "@tanstack/react-query";

import type { AnalysisDetail, AnalysisListItem, ModelOutputForKind } from "@/lib/workspace/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

type AnalysisKind = AnalysisListItem["kind"];

async function fetchRecentByKind<K extends AnalysisKind>(
  projectName: string,
  kind: K,
  limit: number,
  projectId?: number,
): Promise<AnalysisDetail<ModelOutputForKind<K>>[]> {
  const encodedProject = encodeURIComponent(projectName);

  const listUrl = new URL(
    `/api/bff/workspace/${encodedProject}/analyses`,
    window.location.origin,
  );
  listUrl.searchParams.set("kind", kind);
  listUrl.searchParams.set("limit", String(limit));
  // TD-008 Fase 3b, Etapa 2 (dual-key): project_id coexiste com o nome.
  if (projectId !== undefined) {
    listUrl.searchParams.set("project_id", String(projectId));
  }

  const listResponse = await fetch(listUrl.pathname + listUrl.search);
  const list = await parseWorkspaceResponse<AnalysisListItem[]>(listResponse);

  return Promise.all(
    list.map(async (item) => {
      const detailResponse = await fetch(
        `/api/bff/workspace/${encodedProject}/analyses/${item.id}`,
      );
      return parseWorkspaceResponse<AnalysisDetail<ModelOutputForKind<K>>>(detailResponse);
    }),
  );
}

/**
 * Executive Memory (FS-010 §3.1) -- mesma rota já usada por
 * useWorkspaceLatestByKind, só com um limit maior (zero rota nova). Newest-
 * first, herdado da ordenação já existente de GET /api/analyses. Usado
 * exclusivamente para computar Executive Memory Insights
 * (web/lib/executive-memory/memory-insights.ts) -- nunca para exibir uma
 * lista ao executivo (isso continua sendo IntelligenceTimeline/AnalysisHistory).
 */
export function useRecentAnalysesByKind<K extends AnalysisKind>(
  projectName: string,
  kind: K,
  limit: number,
  projectId?: number,
) {
  return useQuery({
    queryKey: ["workspace-recent", projectName, kind, limit, projectId ?? null],
    queryFn: () => fetchRecentByKind(projectName, kind, limit, projectId),
    staleTime: 30_000,
    retry: false,
  });
}
