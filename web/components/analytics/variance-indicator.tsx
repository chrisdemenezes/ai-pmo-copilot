import { DataQualityBadge } from "@/components/analytics/data-quality-badge";
import { cn } from "@/lib/utils";
import {
  formatMetricValue,
  metricSentiment,
  type MetricFormat,
  type MetricValue,
  type Polarity,
} from "@/lib/domain/executive-metric";

const SENTIMENT_CLASS = {
  ok: "text-ok",
  warn: "text-warn",
  danger: "text-danger",
  neutral: "text-ink-muted",
} as const;

/**
 * Wave 8 (Executive Analytics) -- a signed metric (CV, SV, budget
 * variance, ...) colored by whether the sign is good or bad for this
 * specific metric (`polarity`), with an explicit reason shown instead of
 * a fabricated value when the metric is N/A.
 */
export function VarianceIndicator({
  metric,
  polarity,
  format = "currency",
}: {
  metric: MetricValue;
  polarity: Polarity;
  format?: MetricFormat;
}) {
  const sentiment = metricSentiment(metric, polarity);
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn("font-mono text-sm font-semibold", SENTIMENT_CLASS[sentiment])}>
        {formatMetricValue(metric, format)}
      </span>
      {metric.value === null && metric.reason !== null && (
        <DataQualityBadge reason={metric.reason} />
      )}
    </span>
  );
}
