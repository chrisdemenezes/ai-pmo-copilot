import type { AnalysisListItem } from "./types";

/**
 * Padrão de referência (FS-005 §1/§2, formalizado na FS-006 §2.1): o
 * usuário nunca escolhe um agente ou uma tecnologia -- ele informa o que
 * quer entender sobre o projeto. Hierarquia Pergunta -> Capability ->
 * Executor: "goalLabel" é a única coisa que aparece na interface;
 * "capability" é metadado puramente arquitetural (nunca renderizado),
 * preparando a futura fusão das 3 Capabilities sem forçar nenhuma decisão
 * de UI ainda não aprovada; "kind" resolve o Executor real (hook/BFF/agente).
 */
export type Capability = "project-intelligence" | "risk-intelligence" | "communication-intelligence";

export interface AnalysisCatalogEntry {
  kind: AnalysisListItem["kind"];
  capability: Capability;
  goalLabel: string;
  description: string;
}

export const ANALYSIS_CATALOG: readonly AnalysisCatalogEntry[] = [
  {
    kind: "status",
    capability: "project-intelligence",
    goalLabel: "Como está o projeto?",
    description: "Entenda a saúde geral do projeto a partir do contexto fornecido.",
  },
  {
    kind: "risk",
    capability: "risk-intelligence",
    goalLabel: "Quais riscos exigem atenção?",
    description: "Descubra quais riscos exigem atenção da liderança a partir do contexto fornecido.",
  },
  {
    kind: "meeting",
    capability: "communication-intelligence",
    goalLabel: "O que mudou na última reunião?",
    description: "Entenda o que uma reunião muda no projeto e quais decisões ela exige.",
  },
];
