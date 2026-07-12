/** Mirrors ProjectSummaryResponse in src/api/routes/intelligence.py:64. */
export interface WorkspaceSummary {
  project_name: string;
  total_analyses: number;
  open_risks: number;
  pending_action_items: number;
  latest_health_status: "green" | "yellow" | "red" | null;
}

/** Mirrors AnalysisSummary in src/api/routes/intelligence.py:51 -- no payload. */
export interface AnalysisListItem {
  id: number;
  kind: "meeting" | "risk" | "status";
  project_name: string | null;
  created_at: string;
}

/** model_output shapes -- mirror the 3 prompt schemas exactly, field for field. */
export interface RiskItem {
  description: string;
  probability: "low" | "medium" | "high";
  impact: "low" | "medium" | "high";
  mitigation: string;
}

export interface RiskModelOutput {
  structured: true;
  risks: RiskItem[];
  escalation_recommendation: string | null;
}

export interface ActionItem {
  description: string;
  owner: string | null;
  due_date: string | null;
}

export interface MeetingModelOutput {
  structured: true;
  summary: string;
  decisions: string[];
  action_items: ActionItem[];
  issues: string[];
  dependencies: string[];
}

export interface StatusModelOutput {
  structured: true;
  health_status: "green" | "yellow" | "red";
  key_findings: string[];
  recommendations: string[];
}

/** parse_structured_output falls back to this on any LLM parse failure. */
export interface UnstructuredModelOutput {
  structured: false;
  raw_output: string;
}

export type ModelOutput =
  | RiskModelOutput
  | MeetingModelOutput
  | StatusModelOutput
  | UnstructuredModelOutput;

/** Mirrors AnalysisDetail in src/api/routes/intelligence.py:60 -- includes payload. */
export interface AnalysisDetail<T extends ModelOutput = ModelOutput> extends AnalysisListItem {
  payload: {
    agent: string;
    project_name: string | null;
    model_output: T;
  };
}

/**
 * Narrows AnalysisDetail's model_output by the analysis kind requested --
 * the backend doesn't type this itself (payload is a raw JSON column), but
 * the caller always knows which kind it asked GET /api/analyses?kind=... for.
 */
export type ModelOutputForKind<K extends AnalysisListItem["kind"]> = K extends "risk"
  ? RiskModelOutput | UnstructuredModelOutput
  : K extends "meeting"
    ? MeetingModelOutput | UnstructuredModelOutput
    : StatusModelOutput | UnstructuredModelOutput;

export interface WorkspaceErrorBody {
  error: string;
  detail: string;
}
