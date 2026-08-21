/**
 * Wave 8 (Executive Analytics) -- frontend shape for
 * `GET /projects-delivery/{id}/performance-history` (S-Curve data). Each
 * point is one real captured snapshot date; `pv`/`ev`/`ac` are the same
 * `MetricValue` shape as every other Wave 8 metric -- a real number or an
 * explicit N/A, computed once server-side (`build_history_series`) so the
 * frontend never re-derives the EVM formulas itself.
 */
import type { MetricValue } from "./executive-metric";

export interface PerformanceHistoryPoint {
  asOf: string;
  pv: MetricValue;
  ev: MetricValue;
  ac: MetricValue;
}

export interface PerformanceHistoryApiRow {
  as_of: string;
  pv: MetricValue;
  ev: MetricValue;
  ac: MetricValue;
}

export function toPerformanceHistoryPoint(row: PerformanceHistoryApiRow): PerformanceHistoryPoint {
  return { asOf: row.as_of, pv: row.pv, ev: row.ev, ac: row.ac };
}
