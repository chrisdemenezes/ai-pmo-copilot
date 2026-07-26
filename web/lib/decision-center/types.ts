/**
 * Mirrors LatestRiskItemResponse in src/api/routes/intelligence.py -- one
 * row of GET /api/risks/latest (FS-008 §3.1/§3.2). Only the risks of the
 * most recent risk analysis per project, never the whole history.
 */
export interface LatestRiskItem {
  // project_id is the identity key used to join risks to their project
  // (TD-008 Fase 3b, Etapa 4a); project_name is display only.
  project_id: number | null;
  project_name: string | null;
  description: string;
  probability: "low" | "medium" | "high" | null;
  impact: "low" | "medium" | "high" | null;
  mitigation: string | null;
  escalation_recommendation: string | null;
  source_analysis_id: number;
  source_created_at: string;
}
