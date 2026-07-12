"use client";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceTimeline } from "@/lib/hooks/use-workspace-timeline";
import { analysisKindLabel } from "@/lib/workspace/labels";

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Seção 3 -- Intelligence Timeline. Painel B, independente. Lista as
 * execuções mais recentes em ordem cronológica (id/kind/created_at, já
 * ordenado pelo backend) -- sem buscar o payload de cada item.
 */
export function IntelligenceTimeline({ projectName }: { projectName: string }) {
  const timeline = useWorkspaceTimeline(projectName, { limit: 10 });

  return (
    <section className="flex flex-col gap-3" aria-labelledby="timeline-heading">
      <h2 id="timeline-heading" className="text-sm font-semibold text-ink-muted">
        Intelligence Timeline
      </h2>
      {timeline.isPending ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : timeline.isError ? (
        <p className="text-sm text-danger">Não foi possível carregar o histórico recente.</p>
      ) : timeline.data.length === 0 ? (
        <p className="text-sm text-ink-muted">Nenhuma análise registrada ainda.</p>
      ) : (
        <ol className="flex flex-col gap-2">
          {timeline.data.map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between gap-3 rounded-md border border-border bg-surface px-3 py-2"
            >
              <span className="text-sm text-ink-muted">{formatDateTime(item.created_at)}</span>
              <Badge variant="outline">{analysisKindLabel(item.kind)}</Badge>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
