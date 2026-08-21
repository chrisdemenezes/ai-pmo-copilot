"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BoardView } from "@/components/ui/board-view";
import { Header } from "@/components/shell/header";
import { ActionItemsList } from "@/components/workspace/actions-section";
import { useActionItems } from "@/lib/hooks/use-action-items";
import { URGENCY_ORDER, bucketByUrgency, urgencyLabel } from "@/lib/workspace/action-momentum";
import type { ActionItemView } from "@/lib/workspace/types";

/**
 * Página de portfólio "Ações" (TIP-008, Incremento 2) -- primeira decisão
 * executiva da plataforma que não exige escolher um projeto antes: o item
 * mais urgente do portfólio inteiro já chega destacado no topo. Reaproveita
 * 100% do Incremento 1 (useActionItems sem projectName, action-momentum.ts,
 * ActionItemsList) -- zero lógica de dado nova. Nunca um gerenciador de
 * tarefas: nenhum botão de criar/editar/atribuir, nenhum filtro ou view
 * configurável (FS-007, Diretrizes 1-3).
 */
export default function ActionsPage() {
  const { data, isPending, isError, error, refetch, isFetching } = useActionItems();

  if (isPending) {
    return <ActionsSkeleton />;
  }

  // Same stale-while-revalidate discipline as Dashboard/Projetos: a failed
  // background poll must not discard a list that already loaded.
  if (isError && !data) {
    throw error;
  }

  const items = data ?? [];

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Header>
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
            Apoio à Decisão Executiva
          </p>
          <h1 className="font-display text-2xl font-semibold">Ações</h1>
        </div>
        <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? "Atualizando…" : "Atualizar"}
        </Button>
      </Header>

      {items.length === 0 ? (
        <EmptyState />
      ) : (
        <Tabs defaultValue="lista">
          <TabsList>
            <TabsTrigger value="lista">Lista</TabsTrigger>
            <TabsTrigger value="board">Board</TabsTrigger>
          </TabsList>
          <TabsContent value="lista">
            <Card>
              <CardContent className="flex flex-col gap-5 p-5">
                <ActionItemsList items={items} showProject />
              </CardContent>
            </Card>
          </TabsContent>
          {/* V1 Product & Capability Completion, Pacote J: mesmas 4
              categorias de urgência já reais (bucketByUrgency, intocado),
              somente leitura -- sem clique para o detalhe da análise de
              origem (isso continua exclusivo da Lista), sem
              criar/editar/atribuir/arrastar. */}
          <TabsContent value="board">
            <BoardView
              columns={URGENCY_ORDER.map((bucket) => ({
                key: bucket,
                label: urgencyLabel(bucket),
                items: items.filter((item) => bucketByUrgency(item.due_date, new Date()) === bucket),
              }))}
              getItemKey={(item) => `${item.source_analysis_id}-${item.description}`}
              renderItem={(item) => <ActionBoardCard item={item} />}
            />
          </TabsContent>
        </Tabs>
      )}
    </main>
  );
}

function ActionBoardCard({ item }: { item: ActionItemView }) {
  return (
    <div className="flex flex-col gap-2 rounded-md border border-border bg-surface px-3 py-2">
      <span className="text-sm text-ink">{item.description}</span>
      <div className="flex flex-wrap gap-3 text-xs text-ink-muted">
        {item.project_name ? <span>{item.project_name}</span> : null}
        <span>Responsável: {item.owner ?? "não definido"}</span>
        <span>Prazo: {item.due_date ?? "sem prazo"}</span>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-2 p-12 text-center">
        <p className="font-medium">Nenhuma ação registrada em reuniões ainda</p>
        <p className="text-sm text-ink-muted">
          Assim que uma análise de reunião identificar responsabilidades, elas aparecem aqui
          automaticamente, agrupadas por urgência.
        </p>
      </CardContent>
    </Card>
  );
}

function ActionsSkeleton() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-64" />
    </main>
  );
}
