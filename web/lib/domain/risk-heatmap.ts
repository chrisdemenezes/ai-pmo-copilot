/**
 * Wave 8 (Executive Analytics), Visual Analytics Section 7.E -- Risk
 * Heatmap (Probability x Impact). Preserves the real domain taxonomy
 * (probability/impact are "low" | "medium" | "high" strings, per
 * `LatestRiskItemResponse` -- never a numeric score invented client-side
 * beyond the ordinal mapping needed to place a risk on a 3x3 grid).
 */

export type RiskLevel = "low" | "medium" | "high";

export interface RiskHeatmapInput {
  id: number | string;
  label: string;
  probability: RiskLevel | null;
  impact: RiskLevel | null;
}

export interface RiskHeatmapCell {
  probability: RiskLevel;
  impact: RiskLevel;
  risks: RiskHeatmapInput[];
}

const LEVELS: RiskLevel[] = ["low", "medium", "high"];

/** Buckets risks onto the 3x3 (probability x impact) grid. A risk missing
 * either dimension is excluded from the grid (never guessed) -- callers
 * should report it separately as "sem classificação completa" rather than
 * placing it on an invented cell. */
export function bucketRisksByProbabilityImpact(
  risks: RiskHeatmapInput[],
): RiskHeatmapCell[] {
  const cells: RiskHeatmapCell[] = [];
  for (const impact of LEVELS) {
    for (const probability of LEVELS) {
      cells.push({
        probability,
        impact,
        risks: risks.filter((risk) => risk.probability === probability && risk.impact === impact),
      });
    }
  }
  return cells;
}

const LEVEL_WEIGHT: Record<RiskLevel, number> = { low: 1, medium: 2, high: 3 };

/** A cell's ordinal exposure score (probability weight x impact weight,
 * 1-9) -- used only to choose a cell's color intensity, never presented
 * as a certified quantitative risk score. */
export function cellExposureScore(cell: { probability: RiskLevel; impact: RiskLevel }): number {
  return LEVEL_WEIGHT[cell.probability] * LEVEL_WEIGHT[cell.impact];
}
