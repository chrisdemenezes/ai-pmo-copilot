/**
 * STRATECH V1 Product & Capability Completion — Package K (Financial
 * Management / Executive Financial KPIs).
 *
 * Same "derived, never duplicated" discipline consolidateFromChildren()
 * (shared.ts, AR-1) already uses for progressPercentage/health: Program and
 * Portfolio never carry their own financial column (Technical Design
 * `TECHNICAL-DESIGN-PACKAGE-K-FINANCIAL-MANAGEMENT.md` §2) -- their KPI is
 * always a runtime sum over their own Projects, computed here, once.
 *
 * Nulls are never treated as zero: a Project with no financial data
 * contributes nothing to a rollup, and a rollup with zero contributing
 * Projects reports every field as null rather than fabricating a total.
 */

import type { Project } from "./project";

export interface FinancialSummary {
  approvedBudget: number | null;
  actualCost: number | null;
  forecastCost: number | null;
  /** approvedBudget - actualCost -- positive means under budget. */
  variance: number | null;
  /** variance as a percentage of approvedBudget. */
  variancePercentage: number | null;
}

function sumDefined(values: (number | null)[]): number | null {
  const present = values.filter((value): value is number => value !== null);
  if (present.length === 0) return null;
  return present.reduce((sum, value) => sum + value, 0);
}

function computeVariance(approvedBudget: number | null, actualCost: number | null): {
  variance: number | null;
  variancePercentage: number | null;
} {
  if (approvedBudget === null || actualCost === null) {
    return { variance: null, variancePercentage: null };
  }
  const variance = approvedBudget - actualCost;
  const variancePercentage = approvedBudget === 0 ? null : (variance / approvedBudget) * 100;
  return { variance, variancePercentage };
}

/** A single Project's own financial summary -- variance computed, never stored. */
export function projectFinancialSummary(project: Project): FinancialSummary {
  const { variance, variancePercentage } = computeVariance(
    project.approvedBudget,
    project.actualCost,
  );
  return {
    approvedBudget: project.approvedBudget,
    actualCost: project.actualCost,
    forecastCost: project.forecastCost,
    variance,
    variancePercentage,
  };
}

/**
 * Sums financial data across a set of Projects -- the same function serves
 * a Program's rollup (its own Projects) and a Portfolio's rollup (every
 * Project under its Programs), the caller only decides which Projects to
 * pass in.
 */
export function aggregateFinancials(projects: Project[]): FinancialSummary {
  const approvedBudget = sumDefined(projects.map((project) => project.approvedBudget));
  const actualCost = sumDefined(projects.map((project) => project.actualCost));
  const forecastCost = sumDefined(projects.map((project) => project.forecastCost));
  const { variance, variancePercentage } = computeVariance(approvedBudget, actualCost);
  return { approvedBudget, actualCost, forecastCost, variance, variancePercentage };
}
