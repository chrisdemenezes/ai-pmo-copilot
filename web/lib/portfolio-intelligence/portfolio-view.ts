import { rankByRisk } from "@/lib/dashboard/aggregate";
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
export type PortfolioLayer =
  | "decision_today"
  | "decision_this_week"
  | "risk_to_monitor"
  | "no_signal";

export interface PortfolioIntelligenceItem {
  project_name: string;
  layer: PortfolioLayer;
  /** Rótulo institucional fixo da camada -- nunca gerado pela IA (UX Flow §3). */
  whyAttention: string;
  /** Dado real verbatim -- nunca uma consequência inferida (Founder, aprovação da User Journey). */
  realSignal: string;
  /** Navegação real -- null só na camada "sem sinal de atenção" (UX Flow §3). */
  nextMove: { label: string; href: string } | null;
}

const WHY_ATTENTION: Record<PortfolioLayer, string> = {
  decision_today: "Decisão pendente hoje",
  decision_this_week: "Decisão pendente esta semana",
  // Reformulação exata do Founder (aprovação da User Journey): nunca "o
  // que acontece se eu não agir" -- essa pergunta pressupõe uma
  // consequência que a plataforma não possui para este caso.
  risk_to_monitor: "Por que este projeto merece acompanhamento?",
  no_signal: "Sem sinal de atenção",
};

const NO_SIGNAL_REAL_SIGNAL = "Nenhuma decisão pendente, nenhum risco identificado";

function byProjectName(a: PortfolioIntelligenceItem, b: PortfolioIntelligenceItem): number {
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

function groupDecisionsByProject(decisions: ExecutiveDecision[]): Map<string, ExecutiveDecision[]> {
  const grouped = new Map<string, ExecutiveDecision[]>();
  for (const decision of decisions) {
    const existing = grouped.get(decision.project_name);
    if (existing) {
      existing.push(decision);
    } else {
      grouped.set(decision.project_name, [decision]);
    }
  }
  return grouped;
}

/**
 * buildExecutivePortfolioView (TIP-010) -- as 4 camadas completas
 * (Incremento 2 adiciona "risco a monitorar", reaproveitando rankByRisk()
 * do Dashboard, primeira vez que essa função é usada por outra
 * superfície). Ordenação fixa: camada (1-2-3-4), depois project_name
 * dentro das camadas 1/2/4 -- camada 3 mantém a ordem de concentração de
 * risco de rankByRisk(), nunca reordenada aqui.
 */
export function buildExecutivePortfolioView(
  portfolio: ProjectSummary[],
  decisions: ExecutiveDecision[],
): PortfolioIntelligenceItem[] {
  const decisionsByProject = groupDecisionsByProject(decisions);

  const decisionToday: PortfolioIntelligenceItem[] = [];
  const decisionThisWeek: PortfolioIntelligenceItem[] = [];
  const withoutDecision: ProjectSummary[] = [];

  for (const project of portfolio) {
    const projectDecisions = decisionsByProject.get(project.project_name);
    if (!projectDecisions || projectDecisions.length === 0) {
      withoutDecision.push(project);
      continue;
    }

    const top = highestPriorityDecision(projectDecisions)!;
    const layer: PortfolioLayer = top.window === "hoje" ? "decision_today" : "decision_this_week";
    const item: PortfolioIntelligenceItem = {
      project_name: project.project_name,
      layer,
      whyAttention: WHY_ATTENTION[layer],
      realSignal: top.context,
      nextMove: { label: "Ver decisão completa", href: "/decisions" },
    };
    (layer === "decision_today" ? decisionToday : decisionThisWeek).push(item);
  }

  // rankByRisk() já filtra open_risks > 0 e ordena por concentração
  // descendente -- reaproveitado tal como está (web/lib/dashboard/aggregate.ts),
  // sem limite de top 5 aqui: a Executive Portfolio View cobre o
  // portfólio inteiro, diferente do widget do Dashboard (Architecture
  // Review §3.2).
  const riskRanked = rankByRisk(withoutDecision, withoutDecision.length);
  const riskProjectNames = new Set(riskRanked.map((project) => project.project_name));

  const riskToMonitor: PortfolioIntelligenceItem[] = riskRanked.map((project) => ({
    project_name: project.project_name,
    layer: "risk_to_monitor",
    whyAttention: WHY_ATTENTION.risk_to_monitor,
    realSignal: `${project.open_risks} risco(s) identificado(s)`,
    nextMove: {
      label: "Ver riscos no Workspace",
      href: `/workspace/${encodeURIComponent(project.project_name)}`,
    },
  }));

  const noSignal: PortfolioIntelligenceItem[] = withoutDecision
    .filter((project) => !riskProjectNames.has(project.project_name))
    .map((project) => ({
      project_name: project.project_name,
      layer: "no_signal",
      whyAttention: WHY_ATTENTION.no_signal,
      realSignal: NO_SIGNAL_REAL_SIGNAL,
      nextMove: null,
    }))
    .sort(byProjectName);

  return [
    ...decisionToday.sort(byProjectName),
    ...decisionThisWeek.sort(byProjectName),
    ...riskToMonitor,
    ...noSignal,
  ];
}
