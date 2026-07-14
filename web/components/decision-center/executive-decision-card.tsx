import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";
import { windowLabel, type ExecutiveDecision } from "@/lib/decision-center/decision-queue";

/**
 * Executive Decision Card (FS-008 §3.5) -- responde as 5 perguntas do
 * Founder: qual projeto, qual contexto, por que depende de mim, o que
 * acontece se eu não decidir, qual o próximo passo. Também mostra a
 * "Decisão sugerida" (suggestedDecision()/suggestedRiskDecision(),
 * verbatim) como campo próprio -- mesma convenção já usada nos 3
 * Executive Briefs (Decisão sugerida + Próximo passo lado a lado); para
 * Risco os dois textos divergem de verdade (Executive Trust: nenhuma
 * informação real fica de fora do card). Reaproveita a mesma composição
 * Card já usada pelos Briefs -- nenhuma linguagem visual nova (FS-008
 * §3.6). Clicar leva ao Workspace do projeto, fechando o Executive Loop.
 */
export function ExecutiveDecisionCard({ decision }: { decision: ExecutiveDecision }) {
  return (
    <Link
      href={`/workspace/${encodeURIComponent(decision.project_name)}`}
      className="block"
      data-source={decision.source}
    >
      <Card className="transition-colors hover:bg-surface-2">
        <CardContent className="flex flex-col gap-4 p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-display text-base font-semibold text-ink">{decision.project_name}</h3>
            <span className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
              {windowLabel(decision.window)}
            </span>
          </div>

          <p className="text-sm text-ink">{decision.context}</p>

          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
              Por que depende de mim
            </p>
            <p className="text-sm text-ink-muted">{decision.whyItDependsOnMe}</p>
          </div>

          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
              Se eu não decidir
            </p>
            <p className="text-sm text-ink-muted">{decision.consequenceOfInaction}</p>
          </div>

          <div className="flex flex-col gap-3 rounded-md bg-surface-2 p-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
                Decisão sugerida
              </p>
              <p className="text-sm font-semibold text-ink">{decision.decision}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Próximo passo</p>
              <p className="text-sm text-ink">{decision.nextStep}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
