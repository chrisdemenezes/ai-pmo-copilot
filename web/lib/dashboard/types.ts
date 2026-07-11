/** Mirrors ProjectSummaryResponse in src/api/routes/intelligence.py:64 -- no field invented. */
export interface ProjectSummary {
  project_name: string;
  total_analyses: number;
  open_risks: number;
  pending_action_items: number;
  latest_health_status: "green" | "yellow" | "red" | null;
}

export interface DashboardErrorBody {
  error: string;
  detail: string;
}
