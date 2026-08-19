// TD-008 Fase 3b, Etapa 5: o read-model `ProjectSummary` foi consolidado em
// `ProjectIntelligenceSummary` (`lib/project/intelligence-summary.ts`) --
// uma única projeção de inteligência sobre a entidade Project, ancorada no
// `project_id`. Este módulo mantém apenas o corpo de erro do BFF do Dashboard.

export interface DashboardErrorBody {
  error: string;
  detail: string;
}

/**
 * Executive Intelligence Explicit Scope (Vision, Princípio 13): every
 * Decision Support request declares its scope explicitly -- `organization`
 * is a valid, intentional choice, never a default the UI pre-selects.
 */
export type DecisionSupportScopeType = "project" | "portfolio" | "organization";

export type DecisionSupportScope =
  | { type: "project"; project_id: number }
  | { type: "portfolio"; portfolio_id: number }
  | { type: "organization" };

/**
 * Mirrors DecisionSupportResponse (src/api/routes/intelligence.py, Wave 6).
 * One entry per real, distinct primary source (Founder Decision -- Wave 6
 * Final Consolidation Actions, D-165): `advisor_names` lists every Advisor
 * that cited it -- never one entry per Advisor for the same source.
 */
export interface DecisionSupportCitation {
  advisor_names: string[];
  source_type: string;
  source_id: number;
  source_label: string;
}

export interface DecisionSupportAdvisorExecution {
  advisor_name: string;
  had_evidence: boolean;
}

export interface DecisionSupportCorrelation {
  advisor_names: [string, string];
  is_structural_pair: boolean;
}

export interface DecisionSupportCompositionTrace {
  selection_signals: string[];
  selected_advisor_names: string[];
  advisors_used: DecisionSupportAdvisorExecution[];
  correlations: DecisionSupportCorrelation[];
  synthesis_source_advisor_names: string[] | null;
}

export interface DecisionSupportResponse {
  capability: string;
  insufficient_basis: boolean;
  insufficient_basis_reason: string | null;
  answer: string | null;
  advisors_used: string[];
  citations: DecisionSupportCitation[];
  composition_trace: DecisionSupportCompositionTrace;
}

/**
 * Mirrors ExecutiveNarrativeResponse (src/api/routes/intelligence.py, Wave
 * 6). Never accepts a free-text question -- only `scope` -- and echoes it
 * back (Technical Design -- Executive Narrative, §5.3), unlike Decision
 * Support. Reuses `DecisionSupportScope`/`DecisionSupportCitation`/
 * `DecisionSupportCompositionTrace` -- identical shapes, never duplicated.
 */
export interface ExecutiveNarrativeResponse {
  capability: string;
  scope: DecisionSupportScope;
  insufficient_basis: boolean;
  insufficient_basis_reason: string | null;
  narrative: string | null;
  advisors_used: string[];
  citations: DecisionSupportCitation[];
  composition_trace: DecisionSupportCompositionTrace;
}
