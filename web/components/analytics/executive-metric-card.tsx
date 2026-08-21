import { Card, CardContent } from "@/components/ui/card";
import { DataQualityBadge } from "@/components/analytics/data-quality-badge";
import { TrendIndicator } from "@/components/analytics/trend-indicator";
import { formatMetricValue, type MetricFormat, type MetricValue } from "@/lib/domain/executive-metric";
import type { MetricSentiment } from "@/lib/domain/executive-metric";

/**
 * Wave 8 (Executive Analytics) -- the single reusable Executive KPI card:
 * a label, a value that is either real or an explicit N/A (never a
 * fabricated zero), and optional trend context. Same visual shell as
 * `CockpitKpiStrip`'s cards (Card/CardContent, `font-mono text-2xl`), so a
 * new KPI in this family looks native next to the existing ones rather
 * than introducing a second visual language.
 */
export function ExecutiveMetricCard({
  label,
  metric,
  format,
  trend,
  helper,
}: {
  label: string;
  metric: MetricValue;
  format: MetricFormat;
  trend?: { direction: "up" | "down" | "flat"; sentiment: MetricSentiment; label: string };
  helper?: string;
}) {
  return (
    <Card data-testid="executive-metric-card">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs text-ink-muted">{label}</p>
          {metric.value === null && metric.reason !== null && (
            <DataQualityBadge reason={metric.reason} />
          )}
        </div>
        <p className="font-mono text-2xl tabular-nums">{formatMetricValue(metric, format)}</p>
        <div className="mt-1 flex items-center gap-2">
          {trend && (
            <TrendIndicator direction={trend.direction} sentiment={trend.sentiment} label={trend.label} />
          )}
          {helper && <p className="text-xs text-ink-faint">{helper}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
