"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceLatestByKind } from "@/lib/hooks/use-workspace-latest";

/** Seção 7 -- Recomendações. Painel C ("status", compartilhado com a Seção 2). */
export function RecommendationsPanel({ projectName }: { projectName: string }) {
  const latestStatus = useWorkspaceLatestByKind(projectName, "status");

  return (
    <section className="flex flex-col gap-3" aria-labelledby="recommendations-heading">
      <h2 id="recommendations-heading" className="text-sm font-semibold text-ink-muted">
        Recomendações
      </h2>
      {latestStatus.isPending ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      ) : latestStatus.isError ? (
        <p className="text-sm text-danger">Não foi possível carregar as recomendações.</p>
      ) : !latestStatus.data ? (
        <p className="text-sm text-ink-muted">Nenhuma análise de status registrada ainda.</p>
      ) : latestStatus.data.payload.model_output.structured === false ? (
        <p className="text-sm text-ink-muted">Resposta da IA não estruturada nesta análise.</p>
      ) : latestStatus.data.payload.model_output.recommendations.length === 0 ? (
        <p className="text-sm text-ink-muted">Nenhuma recomendação na última análise de status.</p>
      ) : (
        <ul className="list-disc pl-5 text-sm">
          {latestStatus.data.payload.model_output.recommendations.map((recommendation, index) => (
            <li key={index}>{recommendation}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
