"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Header } from "@/components/shell/header";
import { OrganizationalLearningCard } from "@/components/organizational-intelligence/organizational-learning-card";
import { useLatestRisks } from "@/lib/hooks/use-latest-risks";
import { useActionItems } from "@/lib/hooks/use-action-items";
import {
  CATEGORY_LABELS,
  buildRecurringActions,
  buildRecurringRisks,
  selectTopLearnings,
  type OrganizationalLearning,
  type OrganizationalLearningCategory,
} from "@/lib/organizational-intelligence/organizational-learnings";

const LEARNINGS_LIMIT = 5;
// UX Flow §03 -- ordem fixa desta V1 (Riscos antes de Ações), nunca por
// contagem global entre categorias.
const CATEGORY_ORDER: OrganizationalLearningCategory[] = ["risco", "acao"];

/**
 * Aprendizados (Organizational Intelligence, TIP-012) -- única superfície
 * que responde "o que a organização inteira está aprendendo?" (Discovery
 * §01). Reaproveita 100% as 2 leituras portfolio-wide já existentes
 * (useLatestRisks, useActionItems -- Decision Center/Action Intelligence),
 * zero rota nova (FS-011 §3.1/§3.2). Cada painel falha isoladamente, mesma
 * disciplina do Workspace -- nunca um erro bloqueia o outro sinal.
 */
export default function AprendizadosPage() {
  const risks = useLatestRisks();
  const actions = useActionItems();

  if (risks.isPending || actions.isPending) {
    return <AprendizadosSkeleton />;
  }

  const recurringRisks = buildRecurringRisks(risks.data ?? []);
  const recurringActions = buildRecurringActions(actions.data ?? []);
  const byCategory: Record<OrganizationalLearningCategory, OrganizationalLearning[]> = {
    risco: recurringRisks,
    acao: recurringActions,
  };
  const learnings = selectTopLearnings(
    CATEGORY_ORDER.flatMap((category) => byCategory[category]),
    LEARNINGS_LIMIT,
  );

  const isFetching = risks.isFetching || actions.isFetching;
  const refetchAll = () => {
    risks.refetch();
    actions.refetch();
  };

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Header>
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
            Organizational Intelligence
          </p>
          <h1 className="font-display text-2xl font-semibold">Aprendizados</h1>
        </div>
        <Button variant="ghost" size="sm" onClick={refetchAll} disabled={isFetching}>
          {isFetching ? "Atualizando…" : "Atualizar"}
        </Button>
      </Header>

      {risks.isError ? (
        <p className="text-sm text-danger">
          Não foi possível carregar os riscos -- mostrando apenas ações recorrentes.
        </p>
      ) : null}
      {actions.isError ? (
        <p className="text-sm text-danger">
          Não foi possível carregar as ações -- mostrando apenas riscos recorrentes.
        </p>
      ) : null}

      {learnings.length === 0 ? (
        <EmptyState />
      ) : (
        CATEGORY_ORDER.map((category) => {
          const group = learnings.filter((learning) => learning.category === category);
          if (group.length === 0) return null;
          return (
            <section key={category} className="flex flex-col gap-3">
              <h2 className="font-display text-lg font-semibold text-ink">
                {CATEGORY_LABELS[category]}
              </h2>
              {group.map((learning) => (
                <OrganizationalLearningCard
                  key={`${learning.category}-${learning.description}`}
                  learning={learning}
                />
              ))}
            </section>
          );
        })
      )}
    </main>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-2 p-12 text-center">
        <p className="font-medium">Nenhum aprendizado organizacional identificado no momento</p>
        <p className="text-sm text-ink-muted">
          Assim que o mesmo risco ou a mesma ação aparecer em 3 ou mais projetos, ele aparece aqui
          automaticamente.
        </p>
      </CardContent>
    </Card>
  );
}

function AprendizadosSkeleton() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </main>
  );
}
