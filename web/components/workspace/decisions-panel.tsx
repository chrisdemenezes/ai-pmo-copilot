"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceLatestByKind } from "@/lib/hooks/use-workspace-latest";

/**
 * Seção 6 -- Decisões (+ Dependências). Painel C ("meeting", compartilhado
 * com a Seção 5) -- FS-004 §3 UX Review: os dois arrays vêm do mesmo
 * payload, uma segunda seção duplicaria cabeçalho sem separar dado real.
 */
export function DecisionsPanel({ projectName }: { projectName: string }) {
  const latestMeeting = useWorkspaceLatestByKind(projectName, "meeting");

  return (
    <section className="flex flex-col gap-3" aria-labelledby="decisions-heading">
      <h2 id="decisions-heading" className="text-sm font-semibold text-ink-muted">
        Decisões
      </h2>
      {latestMeeting.isPending ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      ) : latestMeeting.isError ? (
        <p className="text-sm text-danger">Não foi possível carregar as decisões.</p>
      ) : !latestMeeting.data ? (
        <p className="text-sm text-ink-muted">Nenhuma análise de reunião registrada ainda.</p>
      ) : latestMeeting.data.payload.model_output.structured === false ? (
        <p className="text-sm text-ink-muted">Resposta da IA não estruturada nesta análise.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-muted">
              Decisões
            </p>
            {latestMeeting.data.payload.model_output.decisions.length === 0 ? (
              <p className="text-sm text-ink-muted">Nenhuma decisão registrada.</p>
            ) : (
              <ul className="list-disc pl-5 text-sm">
                {latestMeeting.data.payload.model_output.decisions.map((decision, index) => (
                  <li key={index}>{decision}</li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-muted">
              Dependências
            </p>
            {latestMeeting.data.payload.model_output.dependencies.length === 0 ? (
              <p className="text-sm text-ink-muted">Nenhuma dependência registrada.</p>
            ) : (
              <ul className="list-disc pl-5 text-sm">
                {latestMeeting.data.payload.model_output.dependencies.map((dependency, index) => (
                  <li key={index}>{dependency}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
