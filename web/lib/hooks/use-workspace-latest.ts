import { useQuery } from "@tanstack/react-query";

import type {
  AnalysisDetail,
  AnalysisListItem,
  ModelOutputForKind,
} from "@/lib/workspace/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

type AnalysisKind = AnalysisListItem["kind"];

async function fetchLatestByKind<K extends AnalysisKind>(
  projectName: string,
  kind: K,
): Promise<AnalysisDetail<ModelOutputForKind<K>> | null> {
  const encodedProject = encodeURIComponent(projectName);

  const listUrl = new URL(
    `/api/bff/workspace/${encodedProject}/analyses`,
    window.location.origin,
  );
  listUrl.searchParams.set("kind", kind);
  listUrl.searchParams.set("limit", "1");

  const listResponse = await fetch(listUrl.pathname + listUrl.search);
  const list = await parseWorkspaceResponse<AnalysisListItem[]>(listResponse);

  const latest = list[0];
  if (!latest) {
    return null;
  }

  const detailResponse = await fetch(
    `/api/bff/workspace/${encodedProject}/analyses/${latest.id}`,
  );
  return parseWorkspaceResponse<AnalysisDetail<ModelOutputForKind<K>>>(detailResponse);
}

/**
 * Painel C (TIP-004 §1) -- uma instância independente por kind (risk /
 * meeting / status), nunca lida com o resultado dos Painéis A ou B. Cada
 * instância resolve sua própria lista (kind + limit=1) e o detalhe da
 * análise mais recente daquele tipo, em 2 chamadas internas ao BFF -- o
 * chamador vê um único estado loading/error/success por kind.
 *
 * Alimenta: Seção 4 (Riscos) <- "risk", Seção 5 (Ações) e Seção 6
 * (Decisões + Dependências) <- "meeting", Seção 7 (Recomendações) e a parte
 * qualitativa da Seção 2 (achados-chave, exibidos verbatim) <- "status".
 */
export function useWorkspaceLatestByKind<K extends AnalysisKind>(projectName: string, kind: K) {
  return useQuery({
    queryKey: ["workspace-latest", projectName, kind],
    queryFn: () => fetchLatestByKind(projectName, kind),
    staleTime: 30_000,
    retry: false,
  });
}
