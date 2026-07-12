import type { AnalysisListItem } from "./types";

/**
 * Padrão de referência (FS-005 §1/§2, decisão do Founder): o usuário vê
 * objetivos, nunca o nome técnico do agente. Hoje só "status" é real --
 * risk_review e meeting_intelligence entram como novas entradas aqui
 * quando forem especificados, nunca como um seletor redesenhado.
 */
export interface AnalysisCatalogEntry {
  kind: AnalysisListItem["kind"];
  goalLabel: string;
  description: string;
}

export const ANALYSIS_CATALOG: readonly AnalysisCatalogEntry[] = [
  {
    kind: "status",
    goalLabel: "Status Executivo",
    description: "Entenda a saúde geral do projeto a partir do contexto fornecido.",
  },
];
