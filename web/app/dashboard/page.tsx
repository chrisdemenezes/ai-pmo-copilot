"use client";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { usePortfolioSummary } from "@/lib/hooks/use-portfolio-summary";
import { PortfolioSummaryStrip } from "@/components/dashboard/portfolio-summary-strip";
import { ProjectHealthGrid } from "@/components/dashboard/project-health-grid";
import { HealthStatusDistribution } from "@/components/dashboard/health-status-distribution";
import { RiskConcentrationRanking } from "@/components/dashboard/risk-concentration-ranking";

export default function DashboardPage() {
  const { data, isPending, isError, error, refetch, isFetching } = usePortfolioSummary();

  if (isPending) {
    return <DashboardSkeleton />;
  }

  // Caught by app/dashboard/error.tsx -- FS-001 §12.
  if (isError) {
    throw error;
  }

  const projects = data;

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-display text-2xl font-semibold">Dashboard Executivo</h1>
        <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? "Atualizando…" : "Atualizar"}
        </Button>
      </div>

      {projects.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <PortfolioSummaryStrip projects={projects} />
          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-medium text-ink-muted">Distribuição de saúde</h2>
            <HealthStatusDistribution projects={projects} />
          </section>
          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-medium text-ink-muted">Maior concentração de risco</h2>
            <RiskConcentrationRanking projects={projects} />
          </section>
          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-medium text-ink-muted">Projetos</h2>
            <ProjectHealthGrid projects={projects} />
          </section>
        </>
      )}
    </main>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong p-12 text-center">
      <p className="font-medium">Nenhum projeto com análise registrada ainda</p>
      <p className="text-sm text-ink-muted">
        Assim que uma reunião, risco ou status de projeto for analisado, ele aparece aqui
        automaticamente.
      </p>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
      <div
        className="grid gap-4"
        style={{ gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))" }}
      >
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    </main>
  );
}
