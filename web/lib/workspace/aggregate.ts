import type { AnalysisListItem, RiskItem } from "./types";

/**
 * Ephemeral derivation only -- recomputed on every load from data already
 * fetched, never persisted (Product Owner directive, TIP-004).
 */

/** 3x3 grid: rows = probability, columns = impact, low -> high. */
const SEVERITY_LEVELS = ["low", "medium", "high"] as const;
type SeverityLevel = (typeof SEVERITY_LEVELS)[number];

export interface RiskMatrixCell {
  probability: SeverityLevel;
  impact: SeverityLevel;
  count: number;
}

export function buildRiskMatrix(risks: RiskItem[]): RiskMatrixCell[] {
  const cells: RiskMatrixCell[] = [];
  for (const probability of SEVERITY_LEVELS) {
    for (const impact of SEVERITY_LEVELS) {
      const count = risks.filter(
        (risk) => risk.probability === probability && risk.impact === impact,
      ).length;
      cells.push({ probability, impact, count });
    }
  }
  return cells;
}

/** Groups the analyses list by kind, each sub-list already ordered by the backend (created_at desc). */
export function groupAnalysesByKind(
  analyses: AnalysisListItem[],
): Record<AnalysisListItem["kind"], AnalysisListItem[]> {
  return {
    meeting: analyses.filter((item) => item.kind === "meeting"),
    risk: analyses.filter((item) => item.kind === "risk"),
    status: analyses.filter((item) => item.kind === "status"),
  };
}
