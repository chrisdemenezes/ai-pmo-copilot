import type { LatestRiskItem } from "@/lib/decision-center/types";
import type { ActionItemView } from "@/lib/workspace/types";

export type OrganizationalLearningCategory = "risco" | "acao";
// "decisao" e "status" reservados para a extensão futura (Architecture
// Review §04) -- Decisões recorrentes/Tendências de status exigem uma
// leitura agregada nova que não existe hoje (FS-011 §3.3).

export interface OrganizationalLearning {
  category: OrganizationalLearningCategory;
  /** Texto verbatim que se repete entre projetos -- nunca reescrito. */
  description: string;
  /** Sempre >= 3 (Journey §02: 1=evento, 2=observação, 3+=aprendizado organizacional). */
  occurrences: number;
  /** Nomes reais, ordem alfabética -- auditabilidade (Journey §03/§06). */
  projectNames: string[];
}

export const CATEGORY_LABELS: Record<OrganizationalLearningCategory, string> = {
  risco: "Riscos recorrentes",
  acao: "Ações recorrentes",
};

const MIN_OCCURRENCES = 3;

function groupByDescription(
  entries: Array<{ description: string; project_name: string | null }>,
): Map<string, Set<string>> {
  const byDescription = new Map<string, Set<string>>();
  for (const entry of entries) {
    // Evidence First: um projeto sem nome real nunca pode ser citado
    // (auditabilidade, Journey §03) -- não conta para a recorrência.
    if (entry.project_name === null) continue;
    const projects = byDescription.get(entry.description) ?? new Set<string>();
    projects.add(entry.project_name);
    byDescription.set(entry.description, projects);
  }
  return byDescription;
}

function toSortedLearnings(
  byDescription: Map<string, Set<string>>,
  category: OrganizationalLearningCategory,
): OrganizationalLearning[] {
  const learnings: OrganizationalLearning[] = [];
  for (const [description, projects] of byDescription) {
    if (projects.size < MIN_OCCURRENCES) continue;
    learnings.push({
      category,
      description,
      occurrences: projects.size,
      projectNames: Array.from(projects).sort((a, b) => a.localeCompare(b)),
    });
  }
  return learnings.sort(
    (a, b) => b.occurrences - a.occurrences || a.description.localeCompare(b.description),
  );
}

/**
 * Evidence First (TIP-012 §04): recebe exclusivamente evidência real já
 * buscada (GET .../risks/latest, já portfolio-wide, FS-011 §3.1) -- nunca
 * um texto ou uma sugestão. A regra determinística (igualdade textual
 * exata + corte de 3+ projetos distintos) produz a estrutura de dados;
 * nenhuma frase é gerada aqui (ver language-contract.ts).
 */
export function buildRecurringRisks(risks: LatestRiskItem[]): OrganizationalLearning[] {
  return toSortedLearnings(groupByDescription(risks), "risco");
}

/** Mesma técnica de buildRecurringRisks, aplicada a ActionItemView.description (FS-011 §3.2). */
export function buildRecurringActions(actions: ActionItemView[]): OrganizationalLearning[] {
  return toSortedLearnings(groupByDescription(actions), "acao");
}

/**
 * Aplica o limite de 5 (Journey §05, mesmo teto de rankByRisk) sobre uma
 * lista já concatenada na ordem fixa de categorias (UX Flow §03: Riscos
 * antes de Ações nesta V1) -- nunca reordena por contagem global entre
 * categorias, preserva o padrão cognitivo de leitura que a ordem fixa
 * pretende criar (cada categoria já vem ordenada por contagem
 * internamente). Nunca preenche artificialmente com menos de `limit`
 * itens reais (UX Flow §05).
 */
export function selectTopLearnings(
  learningsInFixedCategoryOrder: OrganizationalLearning[],
  limit = 5,
): OrganizationalLearning[] {
  return learningsInFixedCategoryOrder.slice(0, limit);
}
