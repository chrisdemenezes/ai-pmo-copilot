import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";
import type { PortfolioIntelligenceItem } from "@/lib/portfolio-intelligence/portfolio-view";

/**
 * Executive Portfolio Card (FS-009 §3.5) -- responde as 3 perguntas do
 * Founder: por que este projeto merece minha atenção, quais sinais reais
 * justificam essa posição, qual o próximo movimento recomendado. A camada
 * "sem sinal de atenção" nunca tem um link de ação (Princípio da Atenção,
 * UX Flow §4) -- renderiza com densidade reduzida e tom neutro, nunca
 * competindo com as demais camadas.
 */
export function ExecutivePortfolioCard({ item }: { item: PortfolioIntelligenceItem }) {
  if (!item.nextMove) {
    return (
      <div
        className="flex items-center justify-between gap-3 rounded-md border border-border px-4 py-2.5 text-sm"
        data-layer={item.layer}
      >
        <span className="font-medium text-ink-muted">{item.project_name}</span>
        <span className="text-xs text-ink-faint">{item.whyAttention}</span>
      </div>
    );
  }

  return (
    <Link href={item.nextMove.href} className="block" data-layer={item.layer}>
      <Card className="transition-colors hover:bg-surface-2">
        <CardContent className="flex flex-col gap-3 p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-display text-base font-semibold text-ink">{item.project_name}</h3>
            <span className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
              {item.whyAttention}
            </span>
          </div>

          <p className="text-sm text-ink-muted">{item.realSignal}</p>

          <p className="text-sm font-medium text-ink">{item.nextMove.label} →</p>
        </CardContent>
      </Card>
    </Link>
  );
}
