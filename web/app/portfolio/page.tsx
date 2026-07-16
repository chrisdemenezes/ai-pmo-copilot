"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Header } from "@/components/shell/header";
import { ExecutivePortfolioCard } from "@/components/portfolio-intelligence/executive-portfolio-card";
import { usePortfolioSummary } from "@/lib/hooks/use-portfolio-summary";
import { useLatestRisks } from "@/lib/hooks/use-latest-risks";
import { buildExecutiveDecisionQueue, groupLatestRisksByProject } from "@/lib/decision-center/decision-queue";
import { buildExecutivePortfolioView } from "@/lib/portfolio-intelligence/portfolio-view";

/**
 * Executive Portfolio View -- página "Portfólio" (TIP-010 Incremento 1:
 * camadas de decisão hoje/esta semana e ausência de sinal; a camada de
 * Risco a Monitorar chega no Incremento 2). Single Decision Source:
 * consome buildExecutiveDecisionQueue() tal como está, nunca recalcula
 * uma decisão (FS-009 §3.3). Progressive Purpose: responde "onde devo
 * concentrar meu tempo?" -- distinta da pergunta do Dashboard
 * (Architecture Review §3). Os 2 sinais (Status via usePortfolioSummary,
 * Risco via useLatestRisks) são independentes, mesmo padrão de /decisions.
 */
export default function PortfolioPage() {
  const summary = usePortfolioSummary();
  const risks = useLatestRisks();

  // Mesma disciplina de /decisions: nunca afirma uma camada final
  // (Executive Trust) enquanto o sinal de Risco ainda pode mudar o
  // veredito. Uma falha de Risco (não um loading) já é resolvida -- a
  // visão segue com o que sabe, honestamente.
  if (summary.isPending || (risks.isPending && !risks.isError)) {
    return <PortfolioSkeleton />;
  }

  if (summary.isError && !summary.data) {
    throw summary.error;
  }

  const risksByProject = groupLatestRisksByProject(risks.data ?? []);
  const decisions = buildExecutiveDecisionQueue(summary.data ?? [], risksByProject);
  const items = buildExecutivePortfolioView(summary.data ?? [], decisions);

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
            Executive Portfolio View
          </p>
          <h1 className="font-display text-2xl font-semibold">Portfólio</h1>
        </div>
        <Button variant="ghost" size="sm" onClick={refetchAll} disabled={isFetching}>
          {isFetching ? "Atualizando…" : "Atualizar"}
        </Button>
      </Header>
      {risks.isError ? (
        <p className="text-sm text-danger">
          Não foi possível carregar os riscos -- mostrando apenas o sinal de Status.
        </p>
      ) : null}

      {items.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="flex flex-col gap-3">
          {items.map((item) => (
            <ExecutivePortfolioCard key={item.project_name} item={item} />
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
        <p className="font-medium">Nenhum projeto com análise registrada ainda</p>
      </CardContent>
    </Card>
  );
}

function PortfolioSkeleton() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </main>
  );
}
