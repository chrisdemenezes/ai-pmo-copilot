/**
 * Wave 8 (Executive Analytics), Section 8 -- Executive Signals.
 *
 * A Signal is "a fact/condition derived deterministically from real data
 * that deserves executive attention" -- never a Decision, never a
 * Recommendation, never an action. Every function here is pure arithmetic
 * over already-computed metrics; none of them call an LLM or infer
 * anything not directly observable in the inputs.
 *
 * RESOURCE_BOTTLENECK is deliberately not implemented: `Project.team_json`
 * only carries `{size, leadName}` -- no hours/FTE/allocation-by-period
 * exists anywhere in the domain (Phase A reconciliation), so a resource
 * signal would have nothing real to derive from. Building it would mean
 * fabricating data to satisfy a dashboard, which this mission's governing
 * decision explicitly forbids.
 */
import type { ParetoBar } from "./pareto";
import type { PerformanceHistoryPoint } from "./performance-history";
import type { RiskHeatmapCell } from "./risk-heatmap";

export type SignalType =
  | "cost_performance_deteriorating"
  | "schedule_performance_deteriorating"
  | "recovery_trend"
  | "portfolio_concentration"
  | "risk_concentration"
  | "forecast_deviation";

export type SignalSeverity = "info" | "warning" | "critical";

export interface ExecutiveSignal {
  type: SignalType;
  severity: SignalSeverity;
  scope: string;
  metric: string;
  currentValue: number;
  baselineOrThreshold: number;
  trend: "up" | "down" | "flat";
  evidenceReference: string;
  asOf: string;
}

function ratioSeries(
  history: PerformanceHistoryPoint[],
  numerator: "ev",
  denominator: "ac" | "pv",
): { asOf: string; ratio: number }[] {
  return history
    .map((point) => {
      const num = point[numerator].value;
      const den = point[denominator].value;
      if (num === null || den === null || den === 0) return null;
      return { asOf: point.asOf, ratio: num / den };
    })
    .filter((entry): entry is { asOf: string; ratio: number } => entry !== null);
}

function trendSignal(
  series: { asOf: string; ratio: number }[],
  scope: string,
  metric: string,
  deterioratingType: SignalType,
): ExecutiveSignal | null {
  if (series.length < 2) return null;
  const previous = series[series.length - 2];
  const latest = series[series.length - 1];
  if (latest.ratio === previous.ratio) return null;
  const isDeteriorating = latest.ratio < previous.ratio;
  const severity: SignalSeverity = latest.ratio < 1 ? "critical" : "warning";
  return {
    type: isDeteriorating ? deterioratingType : "recovery_trend",
    severity: isDeteriorating ? severity : "info",
    scope,
    metric,
    currentValue: latest.ratio,
    baselineOrThreshold: previous.ratio,
    trend: isDeteriorating ? "down" : "up",
    evidenceReference: `${metric} em ${previous.asOf} (${previous.ratio.toFixed(2)}) -> ${latest.asOf} (${latest.ratio.toFixed(2)})`,
    asOf: latest.asOf,
  };
}

/** CPI (EV/AC) trend across the real captured history -- needs at least 2
 * points with both EV and AC present. */
export function deriveCostPerformanceSignal(
  history: PerformanceHistoryPoint[],
  scope: string,
): ExecutiveSignal | null {
  return trendSignal(
    ratioSeries(history, "ev", "ac"),
    scope,
    "CPI",
    "cost_performance_deteriorating",
  );
}

/** SPI (EV/PV) trend across the real captured history. */
export function deriveSchedulePerformanceSignal(
  history: PerformanceHistoryPoint[],
  scope: string,
): ExecutiveSignal | null {
  return trendSignal(
    ratioSeries(history, "ev", "pv"),
    scope,
    "SPI",
    "schedule_performance_deteriorating",
  );
}

const CONCENTRATION_THRESHOLD = 80;
const TOP_SHARE = 0.2;

/** Flags when a small share of contributors accounts for a
 * disproportionate share of the total -- descriptive concentration only,
 * never asserts why. */
export function derivePortfolioConcentrationSignal(
  bars: ParetoBar[],
  metric: string,
): ExecutiveSignal | null {
  if (bars.length === 0) return null;
  const topCount = Math.max(1, Math.round(bars.length * TOP_SHARE));
  const topBars = bars.slice(0, topCount);
  const topShare = topBars[topBars.length - 1].cumulativePercentage;
  if (topShare < CONCENTRATION_THRESHOLD) return null;
  return {
    type: "portfolio_concentration",
    severity: "warning",
    scope: "portfolio",
    metric,
    currentValue: topShare,
    baselineOrThreshold: CONCENTRATION_THRESHOLD,
    trend: "flat",
    evidenceReference: `${topBars.map((bar) => bar.label).join(", ")} concentram ${topShare.toFixed(0)}% de ${metric}`,
    asOf: new Date().toISOString().slice(0, 10),
  };
}

const RISK_CONCENTRATION_THRESHOLD = 0.3;

/** Flags when high-probability x high-impact risks are a disproportionate
 * share of the total classified risk count. */
export function deriveRiskConcentrationSignal(cells: RiskHeatmapCell[]): ExecutiveSignal | null {
  const total = cells.reduce((sum, cell) => sum + cell.risks.length, 0);
  if (total === 0) return null;
  const highHigh = cells.find((cell) => cell.probability === "high" && cell.impact === "high");
  const highHighCount = highHigh?.risks.length ?? 0;
  const share = highHighCount / total;
  if (share < RISK_CONCENTRATION_THRESHOLD) return null;
  return {
    type: "risk_concentration",
    severity: share >= 0.5 ? "critical" : "warning",
    scope: "portfolio",
    metric: "Concentração de risco (Prob. Alta x Impacto Alto)",
    currentValue: share * 100,
    baselineOrThreshold: RISK_CONCENTRATION_THRESHOLD * 100,
    trend: "flat",
    evidenceReference: `${highHighCount} de ${total} riscos classificados estão em Probabilidade Alta x Impacto Alto`,
    asOf: new Date().toISOString().slice(0, 10),
  };
}

const FORECAST_DEVIATION_THRESHOLD = 0.1;

/** Flags when the estimated cost at completion deviates materially from
 * the approved budget -- requires both a real BAC and a real VAC (i.e. a
 * baseline and at least one snapshot); returns null otherwise, never a
 * fabricated deviation. */
export function deriveForecastDeviationSignal(
  bac: number | null,
  vac: number | null,
  scope: string,
): ExecutiveSignal | null {
  if (bac === null || vac === null || bac === 0) return null;
  const deviationRatio = Math.abs(vac) / bac;
  if (deviationRatio < FORECAST_DEVIATION_THRESHOLD) return null;
  return {
    type: "forecast_deviation",
    severity: deviationRatio >= 0.25 ? "critical" : "warning",
    scope,
    metric: "VAC / BAC",
    currentValue: deviationRatio * 100,
    baselineOrThreshold: FORECAST_DEVIATION_THRESHOLD * 100,
    trend: vac < 0 ? "down" : "up",
    evidenceReference: `VAC de ${vac.toFixed(2)} sobre BAC de ${bac.toFixed(2)}`,
    asOf: new Date().toISOString().slice(0, 10),
  };
}
