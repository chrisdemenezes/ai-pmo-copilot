"use client";

import { Badge, healthStatusLabel, healthStatusVariant } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceSummary } from "@/lib/hooks/use-workspace-summary";
import { useWorkspaceLatestByKind } from "@/lib/hooks/use-workspace-latest";

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/**
 * Seção 2 -- Executive Summary. Agregador puro: contagens, datas e estados
 * já existentes. Nunca gera interpretação, previsão, tendência ou síntese
 * (Product Owner directive, TIP-004 §2) -- "achados-chave" abaixo é o
 * array key_findings exibido verbatim, exatamente como a análise de status
 * mais recente já o escreveu, não um resumo novo montado por este
 * componente.
 *
 * Combina o Painel A (contagens/estado) e o Painel C/"status" (achados),
 * cada um com seu próprio estado de loading/erro -- nenhum bloqueia o outro.
 */
export function ExecutiveSummary({ projectName }: { projectName: string }) {
  const summary = useWorkspaceSummary(projectName);
  const latestStatus = useWorkspaceLatestByKind(projectName, "status");

  return (
    <section className="flex flex-col gap-3" aria-labelledby="executive-summary-heading">
      <h2 id="executive-summary-heading" className="font-display text-lg font-semibold text-ink">
        Executive Summary
      </h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardContent className="flex flex-col gap-3 p-5">
            {summary.isPending ? (
              <>
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-4 w-24" />
              </>
            ) : summary.isError ? (
              <p className="text-sm text-danger">Não foi possível carregar as contagens.</p>
            ) : (
              <dl className="grid grid-cols-3 gap-3 text-sm">
                <div>
                  <dt className="text-xs text-ink-muted">Análises</dt>
                  <dd className="font-mono text-lg tabular-nums">{summary.data.total_analyses}</dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-muted">Riscos identificados</dt>
                  <dd className="font-mono text-lg tabular-nums">{summary.data.open_risks}</dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-muted">Ações pendentes</dt>
                  <dd className="font-mono text-lg tabular-nums">
                    {summary.data.pending_action_items}
                  </dd>
                </div>
                <div className="col-span-3">
                  <dt className="text-xs text-ink-muted">Saúde atual</dt>
                  <dd className="mt-1">
                    <Badge variant={healthStatusVariant(summary.data.latest_health_status)}>
                      {healthStatusLabel(summary.data.latest_health_status)}
                    </Badge>
                  </dd>
                </div>
              </dl>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex flex-col gap-3 p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
              Achados-chave
            </p>
            {latestStatus.isPending ? (
              <>
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
              </>
            ) : latestStatus.isError ? (
              <p className="text-sm text-danger">Não foi possível carregar os achados.</p>
            ) : !latestStatus.data ? (
              <p className="text-sm text-ink-muted">Nenhuma análise de status registrada ainda.</p>
            ) : latestStatus.data.payload.model_output.structured === false ? (
              <p className="text-sm text-ink-muted">Resposta da IA não estruturada nesta análise.</p>
            ) : (
              <>
                <ul className="list-disc pl-5 text-sm">
                  {latestStatus.data.payload.model_output.key_findings.map((finding, index) => (
                    <li key={index}>{finding}</li>
                  ))}
                </ul>
                <p className="text-xs text-ink-faint">
                  Da análise de {formatDate(latestStatus.data.created_at)}
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
