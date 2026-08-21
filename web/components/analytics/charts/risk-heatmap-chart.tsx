import { Fragment } from "react";

import { ChartCard } from "@/components/analytics/chart-card";
import { cn } from "@/lib/utils";
import {
  bucketRisksByProbabilityImpact,
  cellExposureScore,
  type RiskHeatmapInput,
  type RiskLevel,
} from "@/lib/domain/risk-heatmap";

const LEVEL_LABEL: Record<RiskLevel, string> = { low: "Baixa", medium: "Média", high: "Alta" };
const ROWS: RiskLevel[] = ["high", "medium", "low"];
const COLS: RiskLevel[] = ["low", "medium", "high"];

/** Exposure score (1-9) -> a background intensity class, using only the
 * existing ok/warn/danger tokens -- never a new color scale invented for
 * this one chart. */
function cellClass(score: number): string {
  if (score >= 6) return "bg-danger-soft text-danger";
  if (score >= 3) return "bg-warn-soft text-warn";
  return "bg-ok-soft text-ok";
}

/**
 * Wave 8 (Executive Analytics), Visual Analytics Section 7.E -- Risk
 * Heatmap (Probability x Impact), preserving the real 3-level domain
 * taxonomy. A risk missing either dimension is reported separately below
 * the grid, never placed on a guessed cell.
 */
export function RiskHeatmapChart({ risks }: { risks: RiskHeatmapInput[] }) {
  const cells = bucketRisksByProbabilityImpact(risks);
  const unclassified = risks.filter((risk) => risk.probability === null || risk.impact === null);
  const isEmpty = risks.length === 0;

  return (
    <ChartCard
      title="Mapa de Calor de Riscos"
      description="Probabilidade x Impacto"
      isEmpty={isEmpty}
      emptyMessage="Nenhum risco registrado para esta visualização."
    >
      <div className="grid grid-cols-[auto_repeat(3,1fr)] gap-1 text-xs">
        <div />
        {COLS.map((impact) => (
          <div key={impact} className="text-center font-medium text-ink-muted">
            {LEVEL_LABEL[impact]}
          </div>
        ))}
        {ROWS.map((probability) => (
          <Fragment key={probability}>
            <div className="flex items-center font-medium text-ink-muted">
              {LEVEL_LABEL[probability]}
            </div>
            {COLS.map((impact) => {
              const cell = cells.find((c) => c.probability === probability && c.impact === impact);
              const score = cellExposureScore({ probability, impact });
              return (
                <div
                  key={`${probability}-${impact}`}
                  className={cn(
                    "flex aspect-square items-center justify-center rounded-md font-mono font-semibold",
                    cellClass(score),
                  )}
                  title={`${cell?.risks.length ?? 0} risco(s)`}
                >
                  {cell?.risks.length ?? 0}
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>
      <div className="mt-2 flex justify-between text-[10px] text-ink-faint">
        <span>Impacto →</span>
        <span>↑ Probabilidade</span>
      </div>
      {unclassified.length > 0 && (
        <p className="mt-2 text-xs text-ink-faint">
          {unclassified.length} risco(s) sem classificação completa de probabilidade/impacto,
          não exibido(s) no mapa.
        </p>
      )}
    </ChartCard>
  );
}
