"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceLatestByKind } from "@/lib/hooks/use-workspace-latest";

/** Seção 5 -- Ações. Painel C ("meeting", compartilhado com a Seção 6). */
export function ActionsPanel({ projectName }: { projectName: string }) {
  const latestMeeting = useWorkspaceLatestByKind(projectName, "meeting");

  return (
    <section className="flex flex-col gap-3" aria-labelledby="actions-heading">
      <h2 id="actions-heading" className="text-sm font-semibold text-ink-muted">
        Ações
      </h2>
      {latestMeeting.isPending ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      ) : latestMeeting.isError ? (
        <p className="text-sm text-danger">Não foi possível carregar as ações.</p>
      ) : !latestMeeting.data ? (
        <p className="text-sm text-ink-muted">Nenhuma análise de reunião registrada ainda.</p>
      ) : latestMeeting.data.payload.model_output.structured === false ? (
        <p className="text-sm text-ink-muted">Resposta da IA não estruturada nesta análise.</p>
      ) : latestMeeting.data.payload.model_output.action_items.length === 0 ? (
        <p className="text-sm text-ink-muted">Nenhuma ação pendente na última reunião analisada.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {latestMeeting.data.payload.model_output.action_items.map((item, index) => (
            <li key={index}>
              <Card>
                <CardContent className="flex flex-col gap-1 p-4">
                  <p className="text-sm">{item.description}</p>
                  <div className="flex flex-wrap gap-4 text-xs text-ink-muted">
                    <span>Responsável: {item.owner ?? "Não definido"}</span>
                    <span>Prazo: {item.due_date ?? "Não definido"}</span>
                  </div>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
