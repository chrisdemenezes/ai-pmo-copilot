import { useWorkspaceSummary } from "./use-workspace-summary";

/**
 * TD-008 Fase 3b, Etapa 3 -- resolução compartilhada nome->id do Workspace.
 *
 * Lê `useWorkspaceSummary(projectName)`, que é a única resolução nome->id no
 * frontend (o backend a devolve em `/api/projects/summary` desde a Etapa 1).
 * O React Query deduplica essa query por chave, então cada consumidor que
 * chama este hook reaproveita o mesmo `project_id` já resolvido -- sem
 * resolução redundante e sem request adicional (WorkspaceHeader e
 * ExecutiveBrief já buscam o mesmo summary).
 *
 * Retorna o `project_id` técnico quando resolvido, ou `undefined` enquanto o
 * summary está pending, falhou, ou o projeto ainda não tem análises (id
 * null). Nesse intervalo os consumidores seguem operando por nome
 * (additividade estrita) -- nenhum painel bloqueia o outro.
 */
export function useResolvedProjectId(projectName: string): number | undefined {
  const summary = useWorkspaceSummary(projectName);
  return summary.data?.project_id ?? undefined;
}
