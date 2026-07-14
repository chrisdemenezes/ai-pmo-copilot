import { healthStatusLabel } from "@/components/ui/badge";
import type { ProjectSummary } from "@/lib/dashboard/types";
import { suggestedDecision } from "@/lib/workspace/decision-momentum";
import { RISK_NEXT_STEP_FALLBACK, isHighAttentionRisk, suggestedRiskDecision } from "@/lib/workspace/risk-momentum";
import type { LatestRiskItem } from "./types";

/**
 * Single Decision Source (TIP-009 §08): toda lógica de organização,
 * priorização e consolidação de decisões executivas vive exclusivamente
 * aqui. Nunca produz um sinal novo -- só consome os que decision-momentum.ts
 * (e, no Incremento 2, risk-momentum.ts) já calculam. Dashboard, Workspace e
 * futuras Capabilities devem ler o resultado desta função, nunca
 * recalcular a mesma regra em outro lugar (Architecture Review §3.2).
 */

export type DecisionSource = "status" | "risk";

/**
 * "sem_urgência" nunca é um valor atribuído -- é a ausência de entrada na
 * fila (User Journey §2, UX Flow §4). window deriva só da mesma
 * Prioridade já aprovada -- nenhum cálculo novo, nenhuma IA nova.
 */
export type DecisionWindow = "hoje" | "esta_semana";

export interface ExecutiveDecision {
  project_name: string;
  source: DecisionSource;
  window: DecisionWindow;
  context: string;
  decision: string;
  whyItDependsOnMe: string;
  consequenceOfInaction: string;
  nextStep: string;
}

const WINDOW_LABEL: Record<DecisionWindow, string> = {
  hoje: "Hoje",
  esta_semana: "Esta semana",
};

export function windowLabel(window: DecisionWindow): string {
  return WINDOW_LABEL[window];
}

/**
 * Texto institucional fixo por fonte de decisão -- nunca gerado pela IA,
 * nunca concatenado com texto verbatim de uma análise (FS-008 §3.5).
 */
const WHY_TEXT: Record<DecisionSource, string> = {
  status: "Só um julgamento executivo decide se e como agir sobre este status.",
  risk: "Só um julgamento executivo decide como mitigar ou aceitar este risco.",
};

/**
 * "O que acontece se eu não decidir?" -- descreve só o mecanismo real da
 * própria plataforma (nada se auto-resolve), nunca uma previsão de
 * consequência de negócio que o dado não sustenta.
 */
const CONSEQUENCE_TEXT: Record<DecisionSource, string> = {
  status: "Nada muda sozinho: este status permanece assim até uma nova Análise de Status ser executada.",
  risk: "Nada muda sozinho: estes riscos permanecem na zona de atenção até uma nova Avaliação de Riscos ser executada.",
};

function statusDecision(project: ProjectSummary): ExecutiveDecision | null {
  const status = project.latest_health_status;
  if (status !== "red" && status !== "yellow") return null;

  const decision = suggestedDecision(status);
  return {
    project_name: project.project_name,
    source: "status",
    window: status === "red" ? "hoje" : "esta_semana",
    context: `Status: ${healthStatusLabel(status)}`,
    decision,
    whyItDependsOnMe: WHY_TEXT.status,
    consequenceOfInaction: CONSEQUENCE_TEXT.status,
    // Nota de escopo (FS-008 §3.5): reaproveita o mesmo texto de "Decisão
    // sugerida" -- o recommendations[] real do Brief exigiria estender
    // ProjectSummaryResponse, fora de escopo desta Feature.
    nextStep: decision,
  };
}

/**
 * isHighAttentionRisk espera probability/impact não-nulos (RiskItem) --
 * um risco sem os dois campos reais nunca conta como zona de atenção,
 * nunca quebra a checagem.
 */
function isAttentionRisk(risk: LatestRiskItem): boolean {
  if (!risk.probability || !risk.impact) return false;
  return isHighAttentionRisk({
    description: risk.description,
    probability: risk.probability,
    impact: risk.impact,
    mitigation: risk.mitigation ?? "",
  });
}

function riskDecision(projectName: string, risks: LatestRiskItem[]): ExecutiveDecision | null {
  const attentionCount = risks.filter(isAttentionRisk).length;
  if (attentionCount === 0) return null;

  const nextStep = risks.find((risk) => risk.escalation_recommendation)?.escalation_recommendation;

  return {
    project_name: projectName,
    source: "risk",
    window: "hoje",
    context: `${attentionCount} risco(s) na zona de atenção`,
    decision: suggestedRiskDecision(attentionCount),
    whyItDependsOnMe: WHY_TEXT.risk,
    consequenceOfInaction: CONSEQUENCE_TEXT.risk,
    nextStep: nextStep ?? RISK_NEXT_STEP_FALLBACK,
  };
}

/** Ordenação fixa: "hoje" antes de "esta_semana", depois project_name -- determinística, nunca uma prioridade inventada. */
function byWindowThenProject(a: ExecutiveDecision, b: ExecutiveDecision): number {
  if (a.window !== b.window) return a.window === "hoje" ? -1 : 1;
  return a.project_name.localeCompare(b.project_name);
}

/**
 * Incremento 2 (TIP-009 §04): incorpora o sinal de Risco --
 * latestRisksByProject vem de useLatestRisks() (FS-008 §3.1). Um mesmo
 * projeto pode gerar 2 entradas (Status + Risco), nunca fundidas (User
 * Journey §2). Default vazio preserva o comportamento do Incremento 1
 * quando nenhum dado de risco ainda foi carregado.
 */
export function buildExecutiveDecisionQueue(
  portfolio: ProjectSummary[],
  latestRisksByProject: Map<string, LatestRiskItem[]> = new Map(),
): ExecutiveDecision[] {
  const decisions: ExecutiveDecision[] = [];

  for (const project of portfolio) {
    const status = statusDecision(project);
    if (status) decisions.push(status);

    const risks = latestRisksByProject.get(project.project_name);
    if (risks) {
      const risk = riskDecision(project.project_name, risks);
      if (risk) decisions.push(risk);
    }
  }

  return decisions.sort(byWindowThenProject);
}

/**
 * Agrupa a lista plana de GET /api/risks/latest por projeto -- mesma
 * forma exigida por buildExecutiveDecisionQueue. Itens sem project_name
 * (nunca esperados na visão de portfólio) são ignorados.
 */
export function groupLatestRisksByProject(risks: LatestRiskItem[]): Map<string, LatestRiskItem[]> {
  const grouped = new Map<string, LatestRiskItem[]>();
  for (const risk of risks) {
    if (!risk.project_name) continue;
    const existing = grouped.get(risk.project_name);
    if (existing) {
      existing.push(risk);
    } else {
      grouped.set(risk.project_name, [risk]);
    }
  }
  return grouped;
}
