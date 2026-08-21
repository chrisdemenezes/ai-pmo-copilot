/**
 * Wave 8 (Executive Analytics), Visual Analytics Section 7.C -- Portfolio
 * Health distribution. Reuses the real domain taxonomy exactly
 * (health_status: "green" | "yellow" | "red" | null), the same one
 * `healthStatusVariant`/`healthStatusLabel` already normalize -- never a
 * new health vocabulary invented for the chart.
 */

export type HealthStatus = "green" | "yellow" | "red" | null;

export interface HealthDistributionBucket {
  status: HealthStatus;
  count: number;
}

const ORDER: HealthStatus[] = ["green", "yellow", "red", null];

/** Counts how many items fall into each real health status -- `null`
 * ("sem dado") is its own bucket, never folded silently into another. */
export function computeHealthDistribution(
  statuses: HealthStatus[],
): HealthDistributionBucket[] {
  return ORDER.map((status) => ({
    status,
    count: statuses.filter((value) => value === status).length,
  }));
}
