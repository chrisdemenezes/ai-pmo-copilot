/**
 * Wave 8 (Executive Analytics), Visual Analytics Section 7.D -- a single
 * reusable Pareto (80/20 concentration) computation, shared by every
 * concentration view (cost variance, schedule variance, risk exposure,
 * overdue actions, ...). Purely descriptive: identifies where a set of
 * real values concentrates, never asserts a causal relationship.
 */

export interface ParetoItem {
  label: string;
  value: number;
}

export interface ParetoBar extends ParetoItem {
  percentageOfTotal: number;
  cumulativePercentage: number;
}

/** Sorts descending by value and computes each item's share of the total
 * plus the running cumulative share -- the two numbers a Pareto chart
 * needs (bars + the 80/20 line). Items with a non-positive value are
 * dropped: a Pareto ranks concentration among real contributors, a zero
 * or negative entry contributes nothing to rank. */
export function computeParetoData(items: ParetoItem[]): ParetoBar[] {
  const positive = items.filter((item) => item.value > 0);
  const total = positive.reduce((sum, item) => sum + item.value, 0);
  if (total === 0) return [];
  const sorted = [...positive].sort((a, b) => b.value - a.value);
  let cumulative = 0;
  return sorted.map((item) => {
    const percentageOfTotal = (item.value / total) * 100;
    cumulative += percentageOfTotal;
    return { ...item, percentageOfTotal, cumulativePercentage: cumulative };
  });
}
