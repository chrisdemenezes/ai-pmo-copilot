import type { ExecutiveMemoryInsight } from "@/lib/executive-memory/memory-insights";

/**
 * Executive Memory Insight (Executive UI Pattern, FS-010 §6) -- discreto,
 * contextual, nunca competitivo (UX Flow §3): tom neutro, nunca a cor de
 * alerta do campo principal ao lado do qual aparece. Nunca interativo
 * (Silent Intelligence, UX Flow §5-6) -- puro texto, sem onClick/href.
 */
export function ExecutiveMemoryInsightChip({ insight }: { insight: ExecutiveMemoryInsight }) {
  return (
    <span
      data-signal={insight.kind}
      className="inline-flex items-center rounded-full border border-border bg-surface-2 px-2.5 py-0.5 font-mono text-[11px] text-ink-muted"
    >
      {insight.text}
    </span>
  );
}
