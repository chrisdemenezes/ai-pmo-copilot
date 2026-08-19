import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { AnalyzeProjectStatusResponse } from "@/lib/workspace/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

async function submitProjectStatus(
  projectName: string,
  projectContext: string,
): Promise<AnalyzeProjectStatusResponse> {
  const response = await fetch(
    `/api/bff/workspace/${encodeURIComponent(projectName)}/analyze/status`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_context: projectContext }),
    },
  );
  return parseWorkspaceResponse<AnalyzeProjectStatusResponse>(response);
}

/**
 * FS-005 §3 -- template de referência para risk_review/meeting_intelligence:
 * mesmas 4 invalidações (summary, latest-by-kind, timeline por prefixo,
 * portfolio-summary), nunca os latest-by-kind de outros kinds. Verificado
 * contra web/app/providers.tsx: QueryClient único por sessão, então a
 * invalidação de portfolio-summary já deixa o Dashboard atualizado na
 * próxima navegação client-side, sem WebSocket/polling.
 *
 * Executive Memory (TIP-011): sem invalidar também "workspace-recent", o
 * Insight ficaria até 30s desatualizado após uma nova análise (Decision
 * Context Preservation exige refletir a realidade imediata, não um cache
 * antigo) -- prefixo de 3 partes casa com a queryKey completa (que inclui
 * limit) por padrão do React Query (exact: false).
 *
 * TD-006: mesma corrida de fetch em voo do TD-004/005 -- `cancelQueries`
 * antes de invalidar "workspace-latest"/"workspace-recent" para que o
 * primeiro fetch (ainda em voo no mount) não engula esta invalidação e
 * deixe o Executive Memory Insight "Mudou" desatualizado.
 */
export function useSubmitProjectStatus(projectName: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectContext: string) => submitProjectStatus(projectName, projectContext),
    onSuccess: async () => {
      await queryClient.cancelQueries({ queryKey: ["workspace-latest", projectName, "status"] });
      await queryClient.cancelQueries({ queryKey: ["workspace-recent", projectName, "status"] });
      queryClient.invalidateQueries({ queryKey: ["workspace-summary", projectName] });
      queryClient.invalidateQueries({ queryKey: ["workspace-latest", projectName, "status"] });
      queryClient.invalidateQueries({ queryKey: ["workspace-recent", projectName, "status"] });
      queryClient.invalidateQueries({ queryKey: ["workspace-timeline", projectName] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-summary"] });
    },
  });
}
