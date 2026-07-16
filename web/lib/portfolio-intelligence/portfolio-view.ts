import type { ProjectSummary } from "@/lib/dashboard/types";
import type { ExecutiveDecision } from "@/lib/decision-center/decision-queue";

/**
 * Executive Responsibility Separation (TIP-010 §08): esta função nunca
 * recalcula uma decisão -- recebe a saída já computada de
 * buildExecutiveDecisionQueue() (Decision Center) como parâmetro (Single
 * Decision Source, FS-009 §3.3). Um projeto com múltiplas decisões
 * (Status + Risco) ocupa uma única linha aqui, na camada mais alta que se
 * aplica -- é uma visão de priorização por projeto, não uma lista de
 * decisões.
 */
export type PortfolioLayer = "decision_today" | "decision_this_week" | "no_signal";

export interface PortfolioIntelligenceItem {
  project_name: string;
  layer: PortfolioLayer;
  /** Rótulo institucional fixo da camada -- nunca gerado pela IA (UX Flow §3). */
  whyAttention: string;
  /** Dado real verbatim -- ExecutiveDecision.context da entrada de maior prioridade do projeto. */
  realSignal: string;
  /** Navegação real -- null só na camada "sem sinal de atenção" (UX Flow §3). */
  nextMove: { label: string; href: string } | null;
}

const WHY_ATTENTION: Record<PortfolioLayer, string> = {
  decision_today: "Decisão pendente hoje",
  decision_this_week: "Decisão pendente esta semana",
  no_signal: "Sem sinal de atenção",
};

const NO_SIGNAL_REAL_SIGNAL = "Nenhuma decisão pendente, nenhum risco identificado";

/** Ordenação fixa: camada (1-2-4 -- 3 chega no Incremento 2), depois project_name -- determinística, nunca inferida pela IA. */
const LAYER_ORDER: Record<PortfolioLayer, number> = {
  decision_today: 0,
  decision_this_week: 1,
  no_signal: 3,
};

function byLayerThenProject(a: PortfolioIntelligenceItem, b: PortfolioIntelligenceItem): number {
  if (a.layer !== b.layer) return LAYER_ORDER[a.layer] - LAYER_ORDER[b.layer];
  return a.project_name.localeCompare(b.project_name);
}

/**
 * A entrada de maior prioridade de um projeto na Executive Decision Queue
 * -- "hoje" vence "esta_semana"; entre entradas da mesma janela, a
 * primeira encontrada (ordem já determinística de buildExecutiveDecisionQueue).
 */
function highestPriorityDecision(decisions: ExecutiveDecision[]): ExecutiveDecision | undefined {
  return decisions.find((d) => d.window === "hoje") ?? decisions[0];
}

/**
 * buildExecutivePortfolioView (TIP-010 Incremento 1) -- camadas de decisão
 * (hoje/esta semana) e ausência de sinal. A camada de Risco a Monitorar
 * chega no Incremento 2 (TIP-010 §04).
 */
export function buildExecutivePortfolioView(
  portfolio: ProjectSummary[],
  decisions: ExecutiveDecision[],
): PortfolioIntelligenceItem[] {
  const decisionsByProject = new Map<string, ExecutiveDecision[]>();
  for (const decision of decisions) {
    const existing = decisionsByProject.get(decision.project_name);
    if (existing) {
      existing.push(decision);
    } else {
      decisionsByProject.set(decision.project_name, [decision]);
    }
  }

  const items = portfolio.map((project): PortfolioIntelligenceItem => {
    const projectDecisions = decisionsByProject.get(project.project_name);

    if (projectDecisions && projectDecisions.length > 0) {
      const top = highestPriorityDecision(projectDecisions)!;
      const layer: PortfolioLayer = top.window === "hoje" ? "decision_today" : "decision_this_week";
      return {
        project_name: project.project_name,
        layer,
        whyAttention: WHY_ATTENTION[layer],
        realSignal: top.context,
        nextMove: { label: "Ver decisão completa", href: "/decisions" },
      };
    }

    return {
      project_name: project.project_name,
      layer: "no_signal",
      whyAttention: WHY_ATTENTION.no_signal,
      realSignal: NO_SIGNAL_REAL_SIGNAL,
      nextMove: null,
    };
  });

  return items.sort(byLayerThenProject);
}
