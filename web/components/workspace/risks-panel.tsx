"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ActionsContextLine } from "@/components/workspace/actions-context-line";
import { useWorkspaceLatestByKind } from "@/lib/hooks/use-workspace-latest";
import { buildRiskMatrix } from "@/lib/workspace/aggregate";
import { severityLabel } from "@/lib/workspace/labels";
import {
  RISK_NEXT_STEP_FALLBACK,
  isHighAttentionRisk,
  riskContextHeading,
  suggestedRiskDecision,
} from "@/lib/workspace/risk-momentum";
import { hasRiskShape, type RiskItem, type RiskModelOutput } from "@/lib/workspace/types";

/**
 * Seção 4 -- Riscos (padrão Executive Brief + Decision Momentum, TIP-006).
 * Painel C ("risk"), independente das demais seções. Mesmo princípio do
 * Status Executivo (TIP-005A): não lista todos os riscos com o mesmo peso
 * -- destaca só os que exigem atenção (zona vermelha real da matriz
 * probabilidade x impacto, web/lib/workspace/risk-momentum.ts), mantendo os
 * demais visíveis, nunca escondidos, só menos proeminentes.
 */
export function RisksPanel({ projectName }: { projectName: string }) {
  const latestRisk = useWorkspaceLatestByKind(projectName, "risk");

  return (
    <section className="flex flex-col gap-3" aria-labelledby="risks-heading">
      <h2 id="risks-heading" className="text-sm font-semibold text-ink-muted">
        Riscos
      </h2>
      <Card>
        <CardContent className="flex flex-col gap-5 p-5">
          <ActionsContextLine projectName={projectName} />
          {latestRisk.isPending ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : latestRisk.isError ? (
            <p className="text-sm text-danger">Não foi possível carregar os riscos.</p>
          ) : !latestRisk.data ? (
            <p className="text-sm text-ink-muted">Nenhuma análise de risco registrada ainda.</p>
          ) : !hasRiskShape(latestRisk.data.payload.model_output) ? (
            <p className="text-sm text-ink-muted">Resposta da IA não estruturada nesta análise.</p>
          ) : (
            <RisksBriefBody modelOutput={latestRisk.data.payload.model_output} />
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function RiskRow({ risk }: { risk: RiskItem }) {
  return (
    <li>
      <Card>
        <CardContent className="flex flex-col gap-2 p-4">
          <p className="text-sm">{risk.description}</p>
          <div className="flex flex-wrap gap-4 text-xs text-ink-muted">
            <span>Probabilidade: {severityLabel(risk.probability)}</span>
            <span>Impacto: {severityLabel(risk.impact)}</span>
          </div>
          <p className="text-xs text-ink-muted">Mitigação: {risk.mitigation}</p>
        </CardContent>
      </Card>
    </li>
  );
}

function RisksBriefBody({ modelOutput }: { modelOutput: RiskModelOutput }) {
  if (modelOutput.risks.length === 0) {
    return <p className="text-sm text-ink-muted">Nenhum risco identificado nesta análise.</p>;
  }

  const attentionRisks = modelOutput.risks.filter(isHighAttentionRisk);
  const otherRisks = modelOutput.risks.filter((risk) => !isHighAttentionRisk(risk));

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
          {riskContextHeading(attentionRisks.length)}
        </p>
        {attentionRisks.length === 0 ? (
          <p className="text-sm text-ink-muted">
            Nenhum risco na zona de atenção (alta probabilidade x alto impacto) nesta análise.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {attentionRisks.map((risk, index) => (
              <RiskRow key={index} risk={risk} />
            ))}
          </ul>
        )}
      </div>

      {otherRisks.length > 0 ? (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
            Também identificado
          </p>
          <ul className="flex flex-col gap-2">
            {otherRisks.map((risk, index) => (
              <RiskRow key={index} risk={risk} />
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
            {suggestedRiskDecision(attentionRisks.length)}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
            Próximo passo
          </p>
          <p className="text-sm text-ink">
            {modelOutput.escalation_recommendation ?? RISK_NEXT_STEP_FALLBACK}
          </p>
        </div>
      </div>

      <RiskMatrix risks={modelOutput.risks} />
    </div>
  );
}

function RiskMatrix({ risks }: { risks: RiskItem[] }) {
  const cells = buildRiskMatrix(risks);
  return (
    <div className="grid grid-cols-3 gap-1 text-center text-xs">
      {cells.map((cell) => (
        <div
          key={`${cell.probability}-${cell.impact}`}
          className="rounded-md border border-border bg-surface-2 p-2"
          title={`Probabilidade ${severityLabel(cell.probability)} × Impacto ${severityLabel(cell.impact)}`}
        >
          <p className="text-ink-muted">
            {severityLabel(cell.probability)} × {severityLabel(cell.impact)}
          </p>
          <p className="font-mono text-base tabular-nums">{cell.count}</p>
        </div>
      ))}
    </div>
  );
}
