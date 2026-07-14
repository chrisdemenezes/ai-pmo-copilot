"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Header } from "@/components/shell/header";
import { ExecutiveDecisionCard } from "@/components/decision-center/executive-decision-card";
import { usePortfolioSummary } from "@/lib/hooks/use-portfolio-summary";
import { buildExecutiveDecisionQueue } from "@/lib/decision-center/decision-queue";

/**
 * Executive Decision Queue -- página de portfólio "Decisões" (TIP-009
 * Incremento 1: só o sinal de Status, já portfolio-wide via
 * usePortfolioSummary(), zero leitura nova). Single Decision Source: esta
 * página é a única origem de organização/priorização de decisões -- nunca
 * recalculada em outro lugar da plataforma. Princípio de Atenção: só
 * projetos que realmente exigem uma decisão aparecem aqui.
 */
export default function DecisionsPage() {
  const { data, isPending, isError, error, refetch, isFetching } = usePortfolioSummary();

  if (isPending) {
    return <DecisionsSkeleton />;
  }

  // Mesma disciplina de stale-while-revalidate do Dashboard/Projetos/Ações.
  if (isError && !data) {
    throw error;
  }

  const decisions = buildExecutiveDecisionQueue(data ?? []);

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Header>
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
            Executive Decision Queue
          </p>
          <h1 className="font-display text-2xl font-semibold">Decisões</h1>
        </div>
        <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? "Atualizando…" : "Atualizar"}
        </Button>
      </Header>

      {decisions.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="flex flex-col gap-3">
          {decisions.map((decision) => (
            <ExecutiveDecisionCard key={`${decision.project_name}-${decision.source}`} decision={decision} />
          ))}
        </div>
      )}
    </main>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-2 p-12 text-center">
        <p className="font-medium">Nenhuma decisão pendente</p>
        <p className="text-sm text-ink-muted">Todo o portfólio está no curso esperado.</p>
      </CardContent>
    </Card>
  );
}

function DecisionsSkeleton() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-40 w-full" />
    </main>
  );
}
