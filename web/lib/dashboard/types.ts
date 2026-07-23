/** Mirrors ProjectSummaryResponse in src/api/routes/intelligence.py:64 -- no field invented. */
export interface ProjectSummary {
  project_name: string;
  /** Additive (TD-008 Fase 3, Epic W3-1) -- optional so existing fixtures/consumers are unaffected. */
  project_id?: number;
  total_analyses: number;
  open_risks: number;
  pending_action_items: number;
  latest_health_status: "green" | "yellow" | "red" | null;
}

export interface DashboardErrorBody {
  error: string;
  detail: string;
}
