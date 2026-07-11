import type { ProjectSummary } from "./types";

export interface PortfolioTotals {
  projectCount: number;
  totalOpenRisks: number;
  totalPendingActionItems: number;
}

/** W1 -- Portfolio Summary Strip. Client-side reduce over the same payload as W2/W3/W5. */
export function aggregatePortfolio(projects: ProjectSummary[]): PortfolioTotals {
  return projects.reduce<PortfolioTotals>(
    (totals, project) => ({
      projectCount: totals.projectCount + 1,
      totalOpenRisks: totals.totalOpenRisks + project.open_risks,
      totalPendingActionItems: totals.totalPendingActionItems + project.pending_action_items,
    }),
    { projectCount: 0, totalOpenRisks: 0, totalPendingActionItems: 0 },
  );
}

export type HealthStatusKey = "green" | "yellow" | "red" | "none";

/** W3 -- Health Status Distribution. "none" covers latest_health_status: null. */
export function groupByHealthStatus(
  projects: ProjectSummary[],
): Record<HealthStatusKey, number> {
  const counts: Record<HealthStatusKey, number> = { green: 0, yellow: 0, red: 0, none: 0 };
  for (const project of projects) {
    const key: HealthStatusKey = project.latest_health_status ?? "none";
    counts[key] += 1;
  }
  return counts;
}

/** W5 -- Risk Concentration Ranking. Only projects with open_risks > 0, highest first. */
export function rankByRisk(projects: ProjectSummary[], limit = 5): ProjectSummary[] {
  return projects
    .filter((project) => project.open_risks > 0)
    .sort((a, b) => b.open_risks - a.open_risks)
    .slice(0, limit);
}
