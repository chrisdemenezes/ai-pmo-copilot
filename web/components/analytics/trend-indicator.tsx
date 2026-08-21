import { Minus, TrendingDown, TrendingUp } from "lucide-react";

import { cn } from "@/lib/utils";
import type { MetricSentiment } from "@/lib/domain/executive-metric";

const SENTIMENT_CLASS: Record<MetricSentiment, string> = {
  ok: "text-ok",
  warn: "text-warn",
  danger: "text-danger",
  neutral: "text-ink-muted",
};

/**
 * Wave 8 (Executive Analytics) -- a compact up/down/flat arrow, colored by
 * an already-decided `sentiment` (see `metricSentiment()`), never a bare
 * color with no semantic backing it.
 */
export function TrendIndicator({
  direction,
  sentiment,
  label,
}: {
  direction: "up" | "down" | "flat";
  sentiment: MetricSentiment;
  label?: string;
}) {
  const Icon = direction === "up" ? TrendingUp : direction === "down" ? TrendingDown : Minus;
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs font-medium", SENTIMENT_CLASS[sentiment])}>
      <Icon className="size-3.5" aria-hidden="true" />
      {label}
    </span>
  );
}
