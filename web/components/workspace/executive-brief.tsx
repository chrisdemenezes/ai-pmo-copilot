"use client";

import { Badge, healthStatusLabel, healthStatusVariant } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceSummary } from "@/lib/hooks/use-workspace-summary";
import { useWorkspaceLatestByKind } from "@/lib/hooks/use-workspace-latest";
import { useRecentAnalysesByKind } from "@/lib/hooks/use-recent-analyses";
import { ActionsContextLine } from "@/components/workspace/actions-context-line";
import {
  NEXT_STEP_FALLBACK,
  contextHeading,
  suggestedDecision,
} from "@/lib/workspace/decision-momentum";
import { buildStatusInsight } from "@/lib/executive-memory/memory-insights";
import { ExecutiveMemoryInsightChip } from "@/components/executive-memory/executive-memory-insight-chip";
import { hasStatusShape, type StatusModelOutput } from "@/lib/workspace/types";

/** Executive Memory (FS-010 §3.1): mesma rota de useWorkspaceLatestByKind, só com limit maior. */
const RECENT_STATUS_LIMIT = 5;

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/**
 * Seção 2 -- Executive Brief (Decision Experience Review, Rev. 2). Substitui
 * o antigo par Executive Summary + Recomendações: um único momento de
 * decisão, não dois relatórios reorganizados. Mesmos 2 hooks de sempre --
 * zero chamada nova -- mas Painel A (summary/KPIs/impacto) e Painel C
 * (achados/recomendações/decisão/próximo passo) continuam com estados
 * independentes: nenhum bloqueia o outro.
 *
 * Todo texto derivado (título de "Contexto", "Decisão sugerida", fallback de
 * "Próximo passo") vem de web/lib/workspace/decision-momentum.ts -- nunca
 * concatenado com o texto verbatim da IA (key_findings/recommendations).
 */
export function ExecutiveBrief({ projectName }: { projectName: string }) {
  const summary = useWorkspaceSummary(projectName);
  const latestStatus = useWorkspaceLatestByKind(projectName, "status");
  // Executive Memory (FS-010): silencioso enquanto pending/error -- nunca um
  // estado de carregamento próprio (Silent Intelligence). Se a leitura
  // falhar, o Brief continua exatamente como hoje, sem o Insight.
  const recentStatus = useRecentAnalysesByKind(projectName, "status", RECENT_STATUS_LIMIT);
  const statusInsight = recentStatus.data ? buildStatusInsight(recentStatus.data) : null;

  return (
    <section className="flex flex-col gap-3" aria-labelledby="executive-brief-heading">
      <h2 id="executive-brief-heading" className="font-display text-lg font-semibold text-ink">
        Executive Brief
      </h2>
      <Card>
        <CardContent className="flex flex-col gap-6 p-5">
          {summary.isPending ? (
            <div className="flex flex-col gap-3">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-4 w-24" />
            </div>
          ) : summary.isError ? (
            <p className="text-sm text-danger">Não foi possível carregar as contagens.</p>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center gap-3">
                <Badge variant={healthStatusVariant(summary.data.latest_health_status)}>
                  {healthStatusLabel(summary.data.latest_health_status)}
                </Badge>
                <span className="text-sm text-ink-muted">{summary.data.project_name}</span>
                {statusInsight ? <ExecutiveMemoryInsightChip insight={statusInsight} /> : null}
              </div>
              <ActionsContextLine projectName={projectName} />
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
              </dl>
            </div>
          )}

          {latestStatus.isPending ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
            </div>
          ) : latestStatus.isError ? (
            <p className="text-sm text-danger">Não foi possível carregar a análise.</p>
          ) : !latestStatus.data ? (
            <p className="text-sm text-ink-muted">Nenhuma análise de status registrada ainda.</p>
          ) : !hasStatusShape(latestStatus.data.payload.model_output) ? (
            <p className="text-sm text-ink-muted">Resposta da IA não estruturada nesta análise.</p>
          ) : (
            <ExecutiveBriefBody
              modelOutput={latestStatus.data.payload.model_output}
              analyzedAt={latestStatus.data.created_at}
            />
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function ExecutiveBriefBody({
  modelOutput,
  analyzedAt,
}: {
  modelOutput: StatusModelOutput;
  analyzedAt: string;
}) {
  const [nextStep, ...otherRecommendations] = modelOutput.recommendations;

  return (
    <div className="flex flex-col gap-5 border-t border-border pt-5">
      <div className="flex flex-col gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
          {contextHeading(modelOutput.health_status)}
        </p>
        {modelOutput.key_findings.length === 0 ? (
          <p className="text-sm text-ink-muted">Nenhum achado registrado nesta análise.</p>
        ) : (
          <ul className="list-disc pl-5 text-sm">
            {modelOutput.key_findings.map((finding, index) => (
              <li key={index}>{finding}</li>
            ))}
          </ul>
        )}
        <p className="text-xs text-ink-faint">Da análise de {formatDate(analyzedAt)}</p>
      </div>

      {otherRecommendations.length > 0 ? (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
            Também recomendado
          </p>
          <ul className="list-disc pl-5 text-sm">
            {otherRecommendations.map((recommendation, index) => (
              <li key={index}>{recommendation}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="flex flex-col gap-3 rounded-md bg-surface-2 p-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
            Decisão sugerida
          </p>
          <p className="text-sm font-semibold text-ink">
            {suggestedDecision(modelOutput.health_status)}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
            Próximo passo
          </p>
          <p className="text-sm text-ink">{nextStep ?? NEXT_STEP_FALLBACK}</p>
        </div>
      </div>
    </div>
  );
}
