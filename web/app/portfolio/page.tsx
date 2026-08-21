"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BoardView } from "@/components/ui/board-view";
import { Header } from "@/components/shell/header";
import { ExecutivePortfolioCard } from "@/components/portfolio-intelligence/executive-portfolio-card";
import { usePortfolioSummary } from "@/lib/hooks/use-portfolio-summary";
import { useLatestRisks } from "@/lib/hooks/use-latest-risks";
import {
  buildExecutivePortfolioView,
  type PortfolioIntelligenceItem,
  type PortfolioLayer,
} from "@/lib/portfolio-intelligence/portfolio-view";
import { buildExecutiveDecisionQueue, groupLatestRisksByProject } from "@/lib/decision-center/decision-queue";

/**
 * Executive Portfolio View -- página "Priorização" (TIP-010 Incremento 1:
 * camadas de decisão hoje/esta semana e ausência de sinal; a camada de
 * Risco a Monitorar chega no Incremento 2). Single Decision Source:
 * consome buildExecutiveDecisionQueue() tal como está, nunca recalcula
 * uma decisão (FS-009 §3.3). Progressive Purpose: responde "onde devo
 * concentrar meu tempo?" -- distinta da pergunta do Dashboard
 * (Architecture Review §3). Os 2 sinais (Status via usePortfolioSummary,
 * Risco via useLatestRisks) são independentes, mesmo padrão de /decisions.
 *
 * Local V1 Pilot Findings Review (D-217, Seção 5): a regra de ranking já
 * existente em buildExecutivePortfolioView() era invisível na UI -- sem
 * título "Priorização", sem cabeçalho de camada, sem explicação da regra.
 * O agrupamento abaixo é puramente de apresentação: reusa item.layer, já
 * computado, na ordem já determinística devolvida pela função -- nenhuma
 * lógica de negócio nova, nenhum ranking adicional.
 */
const LAYER_ORDER: PortfolioLayer[] = [
  "decision_today",
  "decision_this_week",
  "risk_to_monitor",
  "no_signal",
];

const LAYER_LABEL: Record<PortfolioLayer, string> = {
  decision_today: "Decisão hoje",
  decision_this_week: "Decisão esta semana",
  risk_to_monitor: "Risco a monitorar",
  no_signal: "Sem sinal de atenção",
};

function groupByLayer(
  items: PortfolioIntelligenceItem[],
): Map<PortfolioLayer, PortfolioIntelligenceItem[]> {
  const grouped = new Map<PortfolioLayer, PortfolioIntelligenceItem[]>();
  for (const item of items) {
    const existing = grouped.get(item.layer);
    if (existing) {
      existing.push(item);
    } else {
      grouped.set(item.layer, [item]);
    }
  }
  return grouped;
}
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
  const grouped = groupByLayer(items);

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
          <h1 className="font-display text-2xl font-semibold">Priorização</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Ordenado por prioridade: decisão pendente hoje, depois esta semana, depois risco a
            monitorar, depois sem sinal de atenção.
          </p>
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
        <Tabs defaultValue="lista">
          <TabsList>
            <TabsTrigger value="lista">Lista</TabsTrigger>
            <TabsTrigger value="board">Board</TabsTrigger>
          </TabsList>
          <TabsContent value="lista">
            <div className="flex flex-col gap-6">
              {LAYER_ORDER.map((layer) => {
                const layerItems = grouped.get(layer);
                if (!layerItems || layerItems.length === 0) return null;
                return (
                  <div key={layer} className="flex flex-col gap-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
                      {LAYER_LABEL[layer]}
                    </p>
                    <div className="flex flex-col gap-3">
                      {layerItems.map((item) => (
                        <ExecutivePortfolioCard key={item.project_name} item={item} />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </TabsContent>
          {/* V1 Product & Capability Completion, Pacote J: visualização
              alternativa dos mesmos 4 layers (item.layer, já computado por
              buildExecutivePortfolioView, intocado) -- somente leitura,
              sem drag-and-drop (as camadas não são um estado que o usuário
              muda manualmente, são derivadas do sinal real de Status/Risco). */}
          <TabsContent value="board">
            <BoardView
              columns={LAYER_ORDER.map((layer) => ({
                key: layer,
                label: LAYER_LABEL[layer],
                items: grouped.get(layer) ?? [],
              }))}
              getItemKey={(item) => item.project_name}
              renderItem={(item) => <ExecutivePortfolioCard item={item} />}
            />
          </TabsContent>
        </Tabs>
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
