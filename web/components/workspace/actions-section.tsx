"use client";

import { useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AnalysisDetailDialog } from "@/components/workspace/analysis-history";
import { useActionItems } from "@/lib/hooks/use-action-items";
import {
  URGENCY_ORDER,
  attentionHeadline,
  bucketByUrgency,
  suggestedNextAction,
  urgencyLabel,
  type UrgencyBucket,
} from "@/lib/workspace/action-momentum";
import type { ActionItemView } from "@/lib/workspace/types";

/**
 * Seção "Ações" do Workspace (FS-007 §2.7) -- módulo de apoio à decisão,
 * não um gerenciador de tarefas: nenhum botão de criar/editar/atribuir,
 * nenhum filtro ou view configurável. A tela responde as 3 perguntas fixas
 * por hierarquia visual: "O que está atrasado?" → "O que vence em seguida?"
 * → "O que exige minha atenção hoje?". Mesma composição Card + estados
 * independentes dos demais painéis (padrão Executive Brief).
 */
export function ActionsSection({ projectName }: { projectName: string }) {
  const actionItems = useActionItems(projectName);

  return (
    <section className="flex flex-col gap-3" aria-labelledby="actions-heading">
      <h2 id="actions-heading" className="text-sm font-semibold text-ink-muted">
        Ações
      </h2>
      <Card>
        <CardContent className="flex flex-col gap-5 p-5">
          {actionItems.isPending ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : actionItems.isError ? (
            <p className="text-sm text-danger">Não foi possível carregar as ações.</p>
          ) : actionItems.data.length === 0 ? (
            <p className="text-sm text-ink-muted">
              Nenhuma ação registrada em reuniões deste projeto ainda.
            </p>
          ) : (
            <ActionItemsList items={actionItems.data} />
          )}
        </CardContent>
      </Card>
    </section>
  );
}

/**
 * Corpo compartilhado entre a seção do Workspace e a página de portfólio
 * "Ações" (TIP-008, Incrementos 1-2): agrupamento fixo por urgência,
 * atrasado sempre primeiro, nunca reordenável pelo usuário. showProject
 * distingue a visão de portfólio (multi-projeto) da de Workspace.
 */
export function ActionItemsList({
  items,
  showProject = false,
}: {
  items: ActionItemView[];
  showProject?: boolean;
}) {
  const [openItem, setOpenItem] = useState<ActionItemView | null>(null);

  const today = new Date();
  const grouped = new Map<UrgencyBucket, ActionItemView[]>();
  for (const item of items) {
    const bucket = bucketByUrgency(item.due_date, today);
    grouped.set(bucket, [...(grouped.get(bucket) ?? []), item]);
  }

  const atrasadoCount = grouped.get("atrasado")?.length ?? 0;
  const venceEmBreveCount = grouped.get("vence_em_breve")?.length ?? 0;
  const suggestion = suggestedNextAction(items);

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
          O que exige minha atenção hoje?
        </p>
        <p className="text-sm font-semibold text-ink">
          {attentionHeadline(atrasadoCount, venceEmBreveCount)}
        </p>
      </div>

      {suggestion ? (
        <div className="flex flex-col gap-1 rounded-md bg-surface-2 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
            Próxima ação sugerida
          </p>
          {/* Texto, nunca um CTA clicável -- mesmo princípio dos 3 Briefs. */}
          <p className="text-sm text-ink">
            {suggestion.description}
            {showProject && suggestion.project_name ? ` — ${suggestion.project_name}` : null}
          </p>
        </div>
      ) : null}

      {URGENCY_ORDER.map((bucket) => {
        const bucketItems = grouped.get(bucket);
        if (!bucketItems || bucketItems.length === 0) return null;
        return (
          <div key={bucket} className="flex flex-col gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
              {urgencyLabel(bucket)}
            </p>
            <ul className="flex flex-col gap-2">
              {bucketItems.map((item) => (
                <ActionItemRow
                  key={`${item.source_analysis_id}-${item.description}`}
                  item={item}
                  showProject={showProject}
                  onOpen={() => setOpenItem(item)}
                />
              ))}
            </ul>
          </div>
        );
      })}

      {/* Drill-down para a análise de reunião de origem (source_analysis_id),
          reaproveitando o mesmo diálogo do Histórico completo. */}
      <AnalysisDetailDialog
        projectName={openItem?.project_name ?? ""}
        analysisId={openItem?.source_analysis_id ?? null}
        onClose={() => setOpenItem(null)}
      />
    </div>
  );
}

function ActionItemRow({
  item,
  showProject,
  onOpen,
}: {
  item: ActionItemView;
  showProject: boolean;
  onOpen: () => void;
}) {
  const canOpenOrigin = item.project_name !== null;
  const meta = (
    <div className="flex flex-wrap gap-4 text-xs text-ink-muted">
      {showProject && item.project_name ? <span>{item.project_name}</span> : null}
      <span>Responsável: {item.owner ?? "não definido"}</span>
      <span>Prazo: {item.due_date ?? "sem prazo"}</span>
    </div>
  );

  return (
    <li>
      {canOpenOrigin ? (
        <button
          type="button"
          onClick={onOpen}
          className="flex w-full flex-col gap-2 rounded-md border border-border bg-surface px-3 py-2 text-left hover:bg-surface-2"
        >
          <span className="text-sm text-ink">{item.description}</span>
          {meta}
        </button>
      ) : (
        <div className="flex w-full flex-col gap-2 rounded-md border border-border bg-surface px-3 py-2">
          <span className="text-sm text-ink">{item.description}</span>
          {meta}
        </div>
      )}
    </li>
  );
}
