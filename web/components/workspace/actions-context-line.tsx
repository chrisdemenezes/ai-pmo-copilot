"use client";

import { useActionItems } from "@/lib/hooks/use-action-items";
import { useResolvedProjectId } from "@/lib/hooks/use-resolved-project-id";
import { actionsContextLine, attentionCount } from "@/lib/workspace/action-momentum";

/**
 * Linha de contexto "N ações exigem atenção" nos 3 Executive Briefs
 * (FS-007 §2.7) -- reaproveita useActionItems(projectName), mesma entrada
 * de cache já usada pela seção "Ações" do Workspace (§03), nenhuma chamada
 * duplicada. Mesma contagem de urgência de action-momentum.ts (atrasado +
 * vence em breve), nunca o total bruto. Ausente quando a contagem é zero,
 * silenciosa em loading/erro -- é um complemento, não um painel próprio.
 */
export function ActionsContextLine({ projectName }: { projectName: string }) {
  // TD-008 Fase 3b, Etapa 3: chave exata pelo project_id resolvido (summary
  // deduplicado -- compartilhado com a seção de Ações e o Executive Brief).
  const projectId = useResolvedProjectId(projectName);
  const actionItems = useActionItems(projectName, projectId);

  if (!actionItems.data) return null;

  const count = attentionCount(actionItems.data, new Date());
  if (count === 0) return null;

  return <p className="text-sm text-ink-muted">{actionsContextLine(count)}</p>;
}
