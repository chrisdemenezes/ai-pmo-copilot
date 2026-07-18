"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Header } from "@/components/shell/header";
import { usePortfolioSummary } from "@/lib/hooks/use-portfolio-summary";
import { useLatestRisks } from "@/lib/hooks/use-latest-risks";
import { PortfolioSummaryStrip } from "@/components/dashboard/portfolio-summary-strip";
import { ProjectHealthGrid } from "@/components/dashboard/project-health-grid";
import { HealthStatusDistribution } from "@/components/dashboard/health-status-distribution";
import { RiskConcentrationRanking } from "@/components/dashboard/risk-concentration-ranking";
import { buildExecutiveDecisionQueue, groupLatestRisksByProject } from "@/lib/decision-center/decision-queue";
import { CockpitKpiStrip } from "@/components/cockpit/cockpit-kpi-strip";
import { PortfolioSituationGrid } from "@/components/cockpit/portfolio-situation-grid";
import { ProgramSituationGrid } from "@/components/cockpit/program-situation-grid";
import { COCKPIT_KPIS, PORTFOLIO_SITUATIONS, PROGRAM_SITUATIONS } from "@/lib/mock/cockpit-data";

export default function DashboardPage() {
  const { data, isPending, isError, error, refetch, isFetching } = usePortfolioSummary();
  const risks = useLatestRisks();

  if (isPending) {
    return <DashboardSkeleton />;
  }

  // Only escalate to app/dashboard/error.tsx (FS-001 §12) when there is
  // nothing cached to show. A failed background poll must not discard a
  // dashboard that already loaded successfully -- FS-001 §6/§10
  // (stale-while-revalidate): "revalidação em background... UI atualiza
  // sem piscar", never "some dados válidos por causa de uma falha
  // transitória".
  if (isError && !data) {
    throw error;
  }

  const projects = data ?? [];
  // Single Decision Source (TIP-009 §08): a mesma buildExecutiveDecisionQueue()
  // do /decisions, nunca uma contagem recalculada aqui. null enquanto o
  // sinal de Risco ainda não resolveu -- nunca afirma um número que pode
  // estar incompleto (Executive Trust).
  const criticalDecisionsCount =
    risks.isPending && !risks.isError
      ? null
      : buildExecutiveDecisionQueue(projects, groupLatestRisksByProject(risks.data ?? [])).length;

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
      <Header>
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
            STRATECH · Executive Cockpit
          </p>
          <h1 className="font-display text-2xl font-semibold">Dashboard Executivo</h1>
        </div>
        <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? "Atualizando…" : "Atualizar"}
        </Button>
      </Header>

      <section className="flex flex-col gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">Visão Executiva</h2>
          <p className="text-sm text-ink-muted">
            Indicadores de Portfólio/Programa/Projeto — demonstração (Sprint 1, dados simulados).
          </p>
        </div>
        <CockpitKpiStrip kpis={COCKPIT_KPIS} />
      </section>

      <section className="flex flex-col gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">Situação do Portfólio</h2>
          <p className="text-sm text-ink-muted">Demonstração — Portfólio ainda não é uma entidade real (Release 0.2).</p>
        </div>
        <PortfolioSituationGrid portfolios={PORTFOLIO_SITUATIONS} />
      </section>

      <section className="flex flex-col gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">Situação dos Programas</h2>
          <p className="text-sm text-ink-muted">Demonstração — Programa ainda não é uma entidade real (Release 0.2).</p>
        </div>
        <ProgramSituationGrid programs={PROGRAM_SITUATIONS} />
      </section>

      {projects.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <PortfolioSummaryStrip projects={projects} criticalDecisionsCount={criticalDecisionsCount} />
          <section className="flex flex-col gap-3">
            <div>
              <h2 className="font-display text-lg font-semibold text-ink">Projetos</h2>
              <p className="text-sm text-ink-muted">
                {projects.length} {projects.length === 1 ? "projeto" : "projetos"}
              </p>
            </div>
            <ProjectHealthGrid projects={projects} />
          </section>
          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold text-ink-muted">Distribuição de saúde</h2>
            <HealthStatusDistribution projects={projects} />
          </section>
          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold text-ink-muted">Maior concentração de risco</h2>
            <RiskConcentrationRanking projects={projects} />
          </section>
        </>
      )}
    </main>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-2 p-12 text-center">
        <p className="font-medium">Nenhum projeto com análise registrada ainda</p>
        <p className="text-sm text-ink-muted">
          Assim que uma reunião, risco ou status de projeto for analisado, ele aparece aqui
          automaticamente.
        </p>
      </CardContent>
    </Card>
  );
}

function DashboardSkeleton() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
      <Skeleton className="h-64" />
    </main>
  );
}
