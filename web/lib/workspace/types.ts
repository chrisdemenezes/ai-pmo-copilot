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

/**
 * parse_structured_output (src/agents/shared/output_parser.py) only checks
 * that the LLM's raw text is valid JSON -- "structured: true" never
 * guarantees the parsed object actually has the fields this schema expects.
 * Confirmed against the real backend: Demo Mode's MockLLMProvider replays
 * whatever response_file was last written, independent of which agent is
 * called, so a live call can return "structured: true" JSON shaped like a
 * different agent's schema entirely. Never trust risks/escalation_recommendation
 * without this check first.
 */
export function hasRiskShape(
  modelOutput: RiskModelOutput | UnstructuredModelOutput,
): modelOutput is RiskModelOutput {
  return modelOutput.structured === true && Array.isArray((modelOutput as RiskModelOutput).risks);
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

/** Same reasoning as hasRiskShape above -- "structured: true" alone is not enough. */
export function hasStatusShape(
  modelOutput: StatusModelOutput | UnstructuredModelOutput,
): modelOutput is StatusModelOutput {
  const candidate = modelOutput as StatusModelOutput;
  return (
    modelOutput.structured === true &&
    ["green", "yellow", "red"].includes(candidate.health_status) &&
    Array.isArray(candidate.key_findings) &&
    Array.isArray(candidate.recommendations)
  );
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

/** Mirrors ProjectStatusAgent.analyze's return shape (src/agents/project_status/agent.py). */
export interface AnalyzeProjectStatusResponse {
  agent: string;
  project_name: string | null;
  model_output: StatusModelOutput | UnstructuredModelOutput;
}

/** Mirrors RiskReviewAgent.analyze's return shape (src/agents/risk_review/agent.py). */
export interface AnalyzeRiskReviewResponse {
  agent: string;
  project_name: string | null;
  model_output: RiskModelOutput | UnstructuredModelOutput;
}
