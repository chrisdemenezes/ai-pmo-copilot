/**
 * Wave 8 (Executive Analytics & Experience Completion) -- shared shape for
 * every deterministic metric the backend computes (EVM family today,
 * Section 2 of `TECHNICAL-DESIGN-WAVE-8-EXECUTIVE-ANALYTICS.md`).
 *
 * Mirrors `MetricValueResponse` exactly: a metric is either a real
 * `value`, or `null` with an explicit machine-readable `reason` -- never a
 * fabricated zero. This module is the single place that turns a `reason`
 * code into PT-BR copy and a `value` into a formatted string, so every
 * screen that renders a metric agrees on the same words (same discipline
 * `healthStatusLabel` already established for health_status).
 */

export interface MetricValue {
  value: number | null;
  reason: string | null;
}

const REASON_LABELS: Record<string, string> = {
  no_baseline_defined: "Nenhum baseline definido para este projeto",
  before_baseline_start: "Data anterior ao início do baseline",
  after_baseline_end: "Data posterior ao fim do baseline",
  no_snapshot_captured: "Nenhum snapshot de performance capturado ainda",
  zero_actual_cost: "Custo real registrado é zero",
  zero_planned_value: "Valor planejado é zero nesta data",
  zero_cost_performance_index: "Índice de desempenho de custo é zero",
};

/** PT-BR explanation for a metric's absence -- falls back to the raw code
 * (never silently blank) if a new backend reason isn't mapped yet. */
export function metricReasonLabel(reason: string | null): string {
  if (reason === null) return "";
  return REASON_LABELS[reason] ?? reason;
}

export type MetricFormat = "currency" | "percentage" | "ratio" | "decimal";

const currencyFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});
const decimalFormatter = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const ratioFormatter = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });

/** "—" (never "0", never "R$ 0") when the metric has no value -- an
 * absent metric must never look identical to a real zero. */
export function formatMetricValue(metric: MetricValue, format: MetricFormat): string {
  if (metric.value === null) return "—";
  switch (format) {
    case "currency":
      return currencyFormatter.format(metric.value);
    case "percentage":
      return `${decimalFormatter.format(metric.value * 100)}%`;
    case "ratio":
      return ratioFormatter.format(metric.value);
    case "decimal":
      return decimalFormatter.format(metric.value);
  }
}

export type Polarity = "higher-is-better" | "lower-is-better";

export type MetricSentiment = "ok" | "warn" | "danger" | "neutral";

/** Maps a signed value to a sentiment given which direction is "good" for
 * this particular metric (e.g. positive cost variance is good; positive
 * schedule slip is bad) -- never a bare color, always tied to a real
 * polarity decision the caller makes explicitly. */
export function metricSentiment(
  metric: MetricValue,
  polarity: Polarity,
  neutralThreshold = 0,
): MetricSentiment {
  if (metric.value === null) return "neutral";
  const isPositive = metric.value > neutralThreshold;
  const isNegative = metric.value < -neutralThreshold;
  if (!isPositive && !isNegative) return "neutral";
  const isGood = polarity === "higher-is-better" ? isPositive : isNegative;
  return isGood ? "ok" : "danger";
}
