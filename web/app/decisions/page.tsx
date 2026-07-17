"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Header } from "@/components/shell/header";
import { ExecutiveDecisionCard } from "@/components/decision-center/executive-decision-card";
import { usePortfolioSummary } from "@/lib/hooks/use-portfolio-summary";
import { useLatestRisks } from "@/lib/hooks/use-latest-risks";
import { buildExecutiveDecisionQueue, groupLatestRisksByProject } from "@/lib/decision-center/decision-queue";

/**
 * Executive Decision Queue -- página de portfólio "Decisões" (TIP-009
 * Incremento 2: Status + Risco combinados). Single Decision Source: esta
 * página é a única origem de organização/priorização de decisões -- nunca
 * recalculada em outro lugar da plataforma. Princípio de Atenção: só
 * projetos que realmente exigem uma decisão aparecem aqui. Os 2 painéis
 * (Status via usePortfolioSummary, Risco via useLatestRisks) são
 * independentes -- um falhando não bloqueia o outro; buildExecutiveDecisionQueue
 * é uma função pura, sem chamada de rede própria.
 */
export default function DecisionsPage() {
  const summary = usePortfolioSummary();
  const risks = useLatestRisks();

  // Espera os 2 sinais resolverem antes de computar a fila -- nunca
  // afirma "nenhuma decisão pendente" (Executive Trust) enquanto o sinal
  // de Risco ainda pode mudar esse veredito. Uma falha de Risco (não um
  // loading) já é resolvida -- a fila segue com o que sabe, honestamente.
  if (summary.isPending || (risks.isPending && !risks.isError)) {
    return <DecisionsSkeleton />;
  }

  // Mesma disciplina de stale-while-revalidate do Dashboard/Projetos/Ações.
  if (summary.isError && !summary.data) {
    throw summary.error;
  }

  // O painel de Risco é independente -- se falhar, a fila continua
  // mostrando as decisões de Status (mesmo princípio de "cada painel
  // falha isoladamente" já usado no Workspace); nunca bloqueia a tela
  // inteira nem finge um dado que não chegou.
  const risksByProject = groupLatestRisksByProject(risks.data ?? []);
  const decisions = buildExecutiveDecisionQueue(summary.data ?? [], risksByProject);

  const isFetching = summary.isFetching || risks.isFetching;
  const refetchAll = () => {
    summary.refetch();
    risks.refetch();
  };

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Header>
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
            Executive Decision Queue
          </p>
          <h1 className="font-display text-2xl font-semibold">Decisões</h1>
        </div>
        <Button variant="ghost" size="sm" onClick={refetchAll} disabled={isFetching}>
          {isFetching ? "Atualizando…" : "Atualizar"}
        </Button>
      </Header>
      {risks.isError ? (
        <p className="text-sm text-danger">
          Não foi possível carregar os riscos -- mostrando decisões de Status.
        </p>
      ) : null}

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
