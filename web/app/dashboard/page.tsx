"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Header } from "@/components/shell/header";
import { usePortfolioSummary } from "@/lib/hooks/use-portfolio-summary";
import { usePortfolios } from "@/lib/hooks/use-portfolios";
import { usePrograms } from "@/lib/hooks/use-programs";
import { useProjects } from "@/lib/hooks/use-projects";
import { useLatestRisks } from "@/lib/hooks/use-latest-risks";
import { consolidatePortfolios } from "@/lib/domain/program";
import { consolidatePrograms } from "@/lib/domain/project";
import { PortfolioSummaryStrip } from "@/components/dashboard/portfolio-summary-strip";
import { ProjectHealthGrid } from "@/components/dashboard/project-health-grid";
import { HealthStatusDistribution } from "@/components/dashboard/health-status-distribution";
import { RiskConcentrationRanking } from "@/components/dashboard/risk-concentration-ranking";
import { buildExecutiveDecisionQueue, groupLatestRisksByProject } from "@/lib/decision-center/decision-queue";
import { CockpitKpiStrip } from "@/components/cockpit/cockpit-kpi-strip";
import { PortfolioSituationGrid } from "@/components/cockpit/portfolio-situation-grid";
import { ProgramSituationGrid } from "@/components/cockpit/program-situation-grid";
import { ProgramExecutionPanel } from "@/components/cockpit/program-execution-panel";
import { ExecutiveFocusPanel } from "@/components/cockpit/executive-focus-panel";
import { computeExecutiveFocus } from "@/lib/dashboard/executive-focus";
import { type CockpitKPI } from "@/lib/mock/cockpit-data";

export default function DashboardPage() {
  const { data, isPending, isError, error, refetch, isFetching } = usePortfolioSummary();
  const portfolios = usePortfolios();
  const programs = usePrograms();
  const deliveryProjects = useProjects();
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
  const executiveFocus = computeExecutiveFocus(projects);
  // Capability 03: a cadeia de consolidação é transitiva -- Program deriva
  // de seus Projects reais primeiro, e só então Portfolio deriva desses
  // Programs já consolidados (Domain Blueprint CB-003 §2), nunca mais dos
  // valores semeados de Program isolado (Capability 02).
  const consolidatedPrograms = consolidatePrograms(programs.data ?? [], deliveryProjects.data ?? []);
  const consolidatedPortfolios = consolidatePortfolios(portfolios.data ?? [], consolidatedPrograms);
  // Single Decision Source (TIP-009 §08): a mesma buildExecutiveDecisionQueue()
  // do /decisions, nunca uma contagem recalculada aqui. null enquanto o
  // sinal de Risco ainda não resolveu -- nunca afirma um número que pode
  // estar incompleto (Executive Trust).
  const criticalDecisionsCount =
    risks.isPending && !risks.isError
      ? null
      : buildExecutiveDecisionQueue(projects, groupLatestRisksByProject(risks.data ?? [])).length;
  // AR-1 finding: a faixa de KPIs lia COCKPIT_KPIS (mock, Sprint 1) mesmo
  // depois de Portfolio/Program/Project virarem domínio real (Capabilities
  // 01-03) -- "Programas em Execução"/"Projetos em Andamento" mostravam
  // 8/24 (mock antigo) contra 4/7 reais, e "Decisões Pendentes" (5) não
  // batia nem com o próprio PENDING_DECISIONS mock (4 itens). Corrigido
  // para contagens reais; "Decisões Pendentes" reaproveita o mesmo
  // criticalDecisionsCount do link para o qual o KPI já apontava (/decisions).
  const kpis: CockpitKPI[] = [
    {
      label: "Portfólios Ativos",
      value: String((portfolios.data ?? []).filter((p) => p.status === "Ativo").length),
    },
    {
      label: "Programas em Execução",
      value: String((programs.data ?? []).filter((p) => p.status === "Ativo").length),
    },
    {
      label: "Projetos em Andamento",
      value: String((deliveryProjects.data ?? []).filter((p) => p.status === "Ativo").length),
    },
    {
      label: "Decisões Pendentes",
      value: criticalDecisionsCount === null ? "…" : String(criticalDecisionsCount),
      href: "/decisions",
    },
  ];

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
          <h2 className="font-display text-lg font-semibold text-ink">Executive Overview</h2>
          <p className="text-sm text-ink-muted">
            Contagens reais de Portfólio/Programa/Projeto (Capabilities 01–03); Decisões Pendentes reflete a Executive Decision Queue real.
          </p>
        </div>
        <CockpitKpiStrip kpis={kpis} />
      </section>

      <section className="flex flex-col gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">Situação do Portfólio</h2>
          <p className="text-sm text-ink-muted">
            Capabilities 01–03 (Release 0.2) — indicadores consolidados transitivamente a partir dos Projects e Programs reais.
          </p>
        </div>
        {portfolios.isPending || programs.isPending ? (
          <Skeleton className="h-48" />
        ) : (
          <PortfolioSituationGrid portfolios={consolidatedPortfolios} />
        )}
      </section>

      <section className="flex flex-col gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">Situação dos Programas</h2>
          <p className="text-sm text-ink-muted">
            Capability 02/03 (Release 0.2) — indicadores consolidados a partir dos Projects reais.
          </p>
        </div>
        {programs.isPending || portfolios.isPending || deliveryProjects.isPending ? (
          <Skeleton className="h-48" />
        ) : (
          <ProgramSituationGrid programs={consolidatedPrograms} portfolios={portfolios.data ?? []} />
        )}
      </section>

      {/* V1 Product & Capability Completion, Pacote D: rebaixado ao estilo
          já usado por "Distribuição de saúde"/"Maior concentração de
          risco" -- é um detalhamento (Top 5) de "Situação dos Programas"
          logo acima, não uma métrica primária própria; toda seção com
          o mesmo peso visual (text-lg font-semibold) tornava a hierarquia
          de leitura plana. Nenhum dado removido, apenas o peso do título. */}
      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-ink-muted">Program Execution — Top 5 que exigem atenção</h2>
        {programs.isPending || deliveryProjects.isPending ? (
          <Skeleton className="h-48" />
        ) : (
          <ProgramExecutionPanel programs={consolidatedPrograms} projects={deliveryProjects.data ?? []} />
        )}
      </section>

      <section className="flex flex-col gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">Executive Focus</h2>
          <p className="text-sm text-ink-muted">Onde devo concentrar minha atenção hoje?</p>
        </div>
        <ExecutiveFocusPanel focus={executiveFocus} />
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

/**
 * Local V1 Pilot Findings Review (D-217, Seção 6A) marcou 5 seções
 * alimentadas por web/lib/mock/cockpit-data.ts como "Dados demonstrativos"
 * (D-219), depois reforçou a marcação com um aviso contextual (H1, D-223)
 * -- ambas as tentativas de comunicação visual falharam no teste real com
 * usuário (a Human User Session #2, D-222, e o micro-teste humano de H1
 * mostraram que o usuário não percebe a distinção mesmo com o selo/aviso
 * visíveis). Removidas do Dashboard do piloto (Local V1 Pilot Final
 * Hardening, H1, decisão explícita do Founder): zero ambiguidade é mais
 * seguro que qualquer selo que dependa do usuário notá-lo. Os componentes e
 * o dado mock permanecem no repositório (WorkItemsOverview,
 * DecisionCenterPanel, ActionsCenterTable, RecentActivityTimeline,
 * AIRecommendationsPanel, web/lib/mock/cockpit-data.ts) para uma futura
 * Capability real, não foram excluídos.
 */
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
