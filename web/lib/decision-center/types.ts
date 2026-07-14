/**
 * Mirrors LatestRiskItemResponse in src/api/routes/intelligence.py -- one
 * row of GET /api/risks/latest (FS-008 §3.1/§3.2). Only the risks of the
 * most recent risk analysis per project, never the whole history.
 */
export interface LatestRiskItem {
  project_name: string | null;
  description: string;
  probability: "low" | "medium" | "high" | null;
  impact: "low" | "medium" | "high" | null;
  mitigation: string | null;
  escalation_recommendation: string | null;
  source_analysis_id: number;
  source_created_at: string;
}
