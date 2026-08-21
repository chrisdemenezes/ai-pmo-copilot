import { ChartCard } from "@/components/analytics/chart-card";
import type { PerformanceHistoryPoint } from "@/lib/domain/performance-history";

const CHART_HEIGHT = 120;

interface SeriesDef {
  key: "pv" | "ev" | "ac";
  label: string;
  className: string;
}

const SERIES: SeriesDef[] = [
  { key: "pv", label: "Planejado (PV)", className: "stroke-ink-muted" },
  { key: "ev", label: "Agregado (EV, estimado)", className: "stroke-accent" },
  { key: "ac", label: "Real (AC)", className: "stroke-danger" },
];

function buildPolyline(
  points: PerformanceHistoryPoint[],
  key: SeriesDef["key"],
  maxValue: number,
): string | null {
  const defined = points
    .map((point, index) => ({ index, value: point[key].value }))
    .filter((entry): entry is { index: number; value: number } => entry.value !== null);
  if (defined.length < 2) return null;
  const stepX = points.length > 1 ? 100 / (points.length - 1) : 0;
  return defined
    .map(({ index, value }) => {
      const x = index * stepX;
      const y = maxValue > 0 ? CHART_HEIGHT - (value / maxValue) * CHART_HEIGHT : CHART_HEIGHT;
      return `${x},${y}`;
    })
    .join(" ");
}

/**
 * Wave 8 (Executive Analytics), Visual Analytics Section 7.A -- S-Curve.
 * Plots only real captured points (`GET performance-history`); a series
 * with fewer than 2 real values renders no line at all rather than a
 * single fabricated segment. Empty state ("Dados históricos insuficientes")
 * shown whenever there is no history yet -- never a placeholder curve.
 */
export function SCurveChart({ points }: { points: PerformanceHistoryPoint[] }) {
  const isEmpty = points.length === 0;
  const maxValue = Math.max(
    0,
    ...points.flatMap((point) => [point.pv.value, point.ev.value, point.ac.value]).filter(
      (value): value is number => value !== null,
    ),
  );

  return (
    <ChartCard
      title="Curva S (Planejado x Agregado x Real)"
      description="PV/EV/AC ao longo do tempo, apenas pontos reais capturados"
      isEmpty={isEmpty}
      emptyMessage="Dados históricos insuficientes -- nenhum snapshot de performance capturado ainda."
    >
      <svg
        role="img"
        aria-label="Curva S de desempenho do projeto"
        viewBox={`0 0 100 ${CHART_HEIGHT}`}
        preserveAspectRatio="none"
        className="h-32 w-full"
      >
        {SERIES.map((series) => {
          const polyline = buildPolyline(points, series.key, maxValue);
          if (!polyline) return null;
          return (
            <polyline
              key={series.key}
              points={polyline}
              fill="none"
              className={series.className}
              strokeWidth={1.5}
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </svg>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-muted">
        {SERIES.map((series) => (
          <li key={series.key} className="flex items-center gap-1.5">
            <span className={`h-0.5 w-3 ${series.className.replace("stroke-", "bg-")}`} />
            {series.label}
          </li>
        ))}
      </ul>
    </ChartCard>
  );
}
