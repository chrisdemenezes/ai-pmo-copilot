"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceLatestByKind } from "@/lib/hooks/use-workspace-latest";
import { buildRiskMatrix } from "@/lib/workspace/aggregate";
import { severityLabel } from "@/lib/workspace/labels";
import type { RiskItem } from "@/lib/workspace/types";

/** Seção 4 -- Riscos. Painel C ("risk"), independente das demais seções. */
export function RisksPanel({ projectName }: { projectName: string }) {
  const latestRisk = useWorkspaceLatestByKind(projectName, "risk");

  return (
    <section className="flex flex-col gap-3" aria-labelledby="risks-heading">
      <h2 id="risks-heading" className="text-sm font-semibold text-ink-muted">
        Riscos
      </h2>
      {latestRisk.isPending ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : latestRisk.isError ? (
        <p className="text-sm text-danger">Não foi possível carregar os riscos.</p>
      ) : !latestRisk.data ? (
        <p className="text-sm text-ink-muted">Nenhuma análise de risco registrada ainda.</p>
      ) : latestRisk.data.payload.model_output.structured === false ? (
        <p className="text-sm text-ink-muted">Resposta da IA não estruturada nesta análise.</p>
      ) : (
        <>
          <ul className="flex flex-col gap-2">
            {latestRisk.data.payload.model_output.risks.map((risk, index) => (
              <li key={index}>
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
            ))}
          </ul>
          {latestRisk.data.payload.model_output.escalation_recommendation && (
            <p className="text-sm text-warn">
              Recomendação de escalonamento:{" "}
              {latestRisk.data.payload.model_output.escalation_recommendation}
            </p>
          )}
          {latestRisk.data.payload.model_output.risks.length > 0 && (
            <RiskMatrix risks={latestRisk.data.payload.model_output.risks} />
          )}
        </>
      )}
    </section>
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
