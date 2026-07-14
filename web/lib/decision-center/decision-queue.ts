import { healthStatusLabel } from "@/components/ui/badge";
import type { ProjectSummary } from "@/lib/dashboard/types";
import { suggestedDecision } from "@/lib/workspace/decision-momentum";

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

/** Ordenação fixa: "hoje" antes de "esta_semana", depois project_name -- determinística, nunca uma prioridade inventada. */
function byWindowThenProject(a: ExecutiveDecision, b: ExecutiveDecision): number {
  if (a.window !== b.window) return a.window === "hoje" ? -1 : 1;
  return a.project_name.localeCompare(b.project_name);
}

/**
 * Incremento 1 (TIP-009 §04): só o sinal de Status, já 100% portfolio-wide
 * hoje via ProjectSummaryService.summarize_portfolio() -- zero leitura
 * nova. O Incremento 2 estende esta função para também consumir o sinal
 * de Risco.
 */
export function buildExecutiveDecisionQueue(portfolio: ProjectSummary[]): ExecutiveDecision[] {
  const decisions: ExecutiveDecision[] = [];

  for (const project of portfolio) {
    const status = statusDecision(project);
    if (status) decisions.push(status);
  }

  return decisions.sort(byWindowThenProject);
}
