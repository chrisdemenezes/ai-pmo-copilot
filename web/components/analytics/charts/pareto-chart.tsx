import { ChartCard } from "@/components/analytics/chart-card";
import { computeParetoData, type ParetoItem } from "@/lib/domain/pareto";

const CHART_HEIGHT = 160;
const BAR_AREA_HEIGHT = 110;
const MAX_BARS = 8;

/**
 * Wave 8 (Executive Analytics), Visual Analytics Section 7.D -- bars
 * (individual concentration) + a cumulative line (the running 80/20
 * share), identifying concentration without asserting causality. Plain
 * inline SVG with a `viewBox` (no chart library, no ResizeObserver) so it
 * scales naturally with its container -- `min-w-0` is handled by
 * `ChartCard` already, per the project's established recharts-avoidance
 * discipline for exactly this kind of layout collapse bug.
 */
export function ParetoChart({
  title,
  description,
  items,
}: {
  title: string;
  description?: string;
  items: ParetoItem[];
}) {
  const bars = computeParetoData(items).slice(0, MAX_BARS);
  const isEmpty = bars.length === 0;
  const maxValue = Math.max(...bars.map((bar) => bar.value), 0);
  const barWidth = bars.length > 0 ? 100 / bars.length : 0;

  return (
    <ChartCard title={title} description={description} isEmpty={isEmpty}>
      <svg
        role="img"
        aria-label={`Gráfico de Pareto: ${title}`}
        viewBox={`0 0 100 ${CHART_HEIGHT}`}
        preserveAspectRatio="none"
        className="h-40 w-full"
      >
        {bars.map((bar, index) => {
          const barHeight = maxValue > 0 ? (bar.value / maxValue) * BAR_AREA_HEIGHT : 0;
          const x = index * barWidth;
          return (
            <rect
              key={bar.label}
              x={x + barWidth * 0.15}
              y={BAR_AREA_HEIGHT - barHeight}
              width={barWidth * 0.7}
              height={barHeight}
              className="fill-accent"
            >
              <title>
                {bar.label}: {bar.value.toLocaleString("pt-BR")} (
                {bar.percentageOfTotal.toFixed(1)}%, acumulado{" "}
                {bar.cumulativePercentage.toFixed(1)}%)
              </title>
            </rect>
          );
        })}
        {bars.length > 1 && (
          <polyline
            points={bars
              .map((bar, index) => {
                const x = index * barWidth + barWidth / 2;
                const y = BAR_AREA_HEIGHT - (bar.cumulativePercentage / 100) * BAR_AREA_HEIGHT;
                return `${x},${y}`;
              })
              .join(" ")}
            fill="none"
            className="stroke-warn"
            strokeWidth={1.5}
            vectorEffect="non-scaling-stroke"
          />
        )}
      </svg>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-muted">
        {bars.map((bar) => (
          <li key={bar.label}>
            {bar.label}: {bar.percentageOfTotal.toFixed(0)}%
          </li>
        ))}
      </ul>
    </ChartCard>
  );
}
