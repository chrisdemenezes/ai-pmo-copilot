import { describe, expect, it } from "vitest";

import {
  deriveCostPerformanceSignal,
  deriveForecastDeviationSignal,
  derivePortfolioConcentrationSignal,
  deriveRiskConcentrationSignal,
  deriveSchedulePerformanceSignal,
} from "./executive-signal";
import { computeParetoData } from "./pareto";
import type { PerformanceHistoryPoint } from "./performance-history";
import { bucketRisksByProbabilityImpact } from "./risk-heatmap";

function point(asOf: string, ev: number | null, ac: number | null, pv: number | null): PerformanceHistoryPoint {
  return {
    asOf,
    ev: { value: ev, reason: ev === null ? "no_snapshot_captured" : null },
    ac: { value: ac, reason: ac === null ? "no_snapshot_captured" : null },
    pv: { value: pv, reason: pv === null ? "no_baseline_defined" : null },
  };
}

describe("deriveCostPerformanceSignal", () => {
  it("returns null with fewer than 2 usable points", () => {
    expect(deriveCostPerformanceSignal([point("2026-01-01", 100, 100, 100)], "Projeto A")).toBeNull();
  });

  it("flags cost_performance_deteriorating when CPI falls", () => {
    const history = [point("2026-01-01", 100, 100, 100), point("2026-02-01", 80, 100, 100)];

    const signal = deriveCostPerformanceSignal(history, "Projeto A");

    expect(signal?.type).toBe("cost_performance_deteriorating");
    expect(signal?.trend).toBe("down");
    expect(signal?.severity).toBe("critical");
  });

  it("flags recovery_trend when CPI improves", () => {
    const history = [point("2026-01-01", 80, 100, 100), point("2026-02-01", 100, 100, 100)];

    const signal = deriveCostPerformanceSignal(history, "Projeto A");

    expect(signal?.type).toBe("recovery_trend");
    expect(signal?.trend).toBe("up");
  });

  it("returns null when CPI does not change", () => {
    const history = [point("2026-01-01", 100, 100, 100), point("2026-02-01", 100, 100, 100)];

    expect(deriveCostPerformanceSignal(history, "Projeto A")).toBeNull();
  });

  it("skips points where AC is missing rather than treating it as zero", () => {
    const history = [
      point("2026-01-01", 100, null, 100),
      point("2026-02-01", 90, 100, 100),
      point("2026-03-01", 80, 100, 100),
    ];

    const signal = deriveCostPerformanceSignal(history, "Projeto A");

    // Only 2 usable points (Feb, Mar) -- Jan is excluded, never treated as AC=0.
    expect(signal?.evidenceReference).toContain("2026-02-01");
    expect(signal?.evidenceReference).toContain("2026-03-01");
  });
});

describe("deriveSchedulePerformanceSignal", () => {
  it("flags schedule_performance_deteriorating when SPI falls", () => {
    const history = [point("2026-01-01", 100, 100, 100), point("2026-02-01", 70, 100, 100)];

    const signal = deriveSchedulePerformanceSignal(history, "Projeto A");

    expect(signal?.type).toBe("schedule_performance_deteriorating");
  });
});

describe("derivePortfolioConcentrationSignal", () => {
  it("returns null when there is nothing to rank", () => {
    expect(derivePortfolioConcentrationSignal([], "custo")).toBeNull();
  });

  it("flags concentration when the top ~20% of contributors account for >=80%", () => {
    const bars = computeParetoData([
      { label: "Projeto A", value: 85 },
      { label: "Projeto B", value: 5 },
      { label: "Projeto C", value: 5 },
      { label: "Projeto D", value: 5 },
      { label: "Projeto E", value: 5 },
    ]);

    const signal = derivePortfolioConcentrationSignal(bars, "custo");

    expect(signal?.type).toBe("portfolio_concentration");
    expect(signal?.evidenceReference).toContain("Projeto A");
  });

  it("returns null when concentration is below threshold (evenly distributed)", () => {
    const bars = computeParetoData([
      { label: "Projeto A", value: 20 },
      { label: "Projeto B", value: 20 },
      { label: "Projeto C", value: 20 },
      { label: "Projeto D", value: 20 },
      { label: "Projeto E", value: 20 },
    ]);

    expect(derivePortfolioConcentrationSignal(bars, "custo")).toBeNull();
  });
});

describe("deriveRiskConcentrationSignal", () => {
  it("returns null when there are no classified risks", () => {
    expect(deriveRiskConcentrationSignal(bucketRisksByProbabilityImpact([]))).toBeNull();
  });

  it("flags risk_concentration when high x high risks dominate", () => {
    const cells = bucketRisksByProbabilityImpact([
      { id: 1, label: "A", probability: "high", impact: "high" },
      { id: 2, label: "B", probability: "high", impact: "high" },
      { id: 3, label: "C", probability: "low", impact: "low" },
    ]);

    const signal = deriveRiskConcentrationSignal(cells);

    expect(signal?.type).toBe("risk_concentration");
    expect(signal?.currentValue).toBeCloseTo((2 / 3) * 100);
  });

  it("returns null when high x high risks are a small minority", () => {
    const cells = bucketRisksByProbabilityImpact([
      { id: 1, label: "A", probability: "high", impact: "high" },
      { id: 2, label: "B", probability: "low", impact: "low" },
      { id: 3, label: "C", probability: "low", impact: "low" },
      { id: 4, label: "D", probability: "low", impact: "low" },
    ]);

    expect(deriveRiskConcentrationSignal(cells)).toBeNull();
  });
});

describe("deriveForecastDeviationSignal", () => {
  it("returns null when bac or vac is not available", () => {
    expect(deriveForecastDeviationSignal(null, -5000, "Projeto A")).toBeNull();
    expect(deriveForecastDeviationSignal(100000, null, "Projeto A")).toBeNull();
  });

  it("returns null when deviation is below threshold", () => {
    expect(deriveForecastDeviationSignal(100000, -5000, "Projeto A")).toBeNull();
  });

  it("flags forecast_deviation when |VAC|/BAC exceeds the threshold", () => {
    const signal = deriveForecastDeviationSignal(100000, -15000, "Projeto A");

    expect(signal?.type).toBe("forecast_deviation");
    expect(signal?.trend).toBe("down");
    expect(signal?.severity).toBe("warning");
  });

  it("is critical when the deviation is severe", () => {
    const signal = deriveForecastDeviationSignal(100000, -30000, "Projeto A");

    expect(signal?.severity).toBe("critical");
  });
});
