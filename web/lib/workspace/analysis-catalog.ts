import type { AnalysisListItem } from "./types";

/**
 * Padrão de referência (FS-005 §1/§2, decisão do Founder): o usuário vê
 * objetivos, nunca o nome técnico do agente. meeting_intelligence entra como
 * nova entrada aqui quando for especificado, nunca como um seletor
 * redesenhado. Com 2+ entradas, AnalyzeProjectDialog usa Tabs (Design
 * System já existente) para a escolha -- não um componente novo.
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
  {
    kind: "risk",
    goalLabel: "Avaliação de Riscos",
    description: "Descubra quais riscos exigem atenção da liderança a partir do contexto fornecido.",
  },
];
