import { describe, expect, it } from "vitest";

import { bucketRisksByProbabilityImpact, cellExposureScore } from "./risk-heatmap";

describe("bucketRisksByProbabilityImpact", () => {
  it("produces exactly the 9 cells of a 3x3 grid", () => {
    const cells = bucketRisksByProbabilityImpact([]);
    expect(cells).toHaveLength(9);
  });

  it("places a risk on the cell matching its exact probability and impact", () => {
    const cells = bucketRisksByProbabilityImpact([
      { id: 1, label: "Atraso de fornecedor", probability: "high", impact: "high" },
    ]);

    const cell = cells.find((c) => c.probability === "high" && c.impact === "high");
    expect(cell?.risks).toHaveLength(1);
    expect(cell?.risks[0].label).toBe("Atraso de fornecedor");
  });

  it("excludes a risk missing either dimension rather than guessing a cell", () => {
    const cells = bucketRisksByProbabilityImpact([
      { id: 1, label: "Sem classificação", probability: null, impact: "high" },
    ]);

    const totalPlaced = cells.reduce((sum, cell) => sum + cell.risks.length, 0);
    expect(totalPlaced).toBe(0);
  });
});

describe("cellExposureScore", () => {
  it("is 9 for the highest probability x highest impact cell", () => {
    expect(cellExposureScore({ probability: "high", impact: "high" })).toBe(9);
  });

  it("is 1 for the lowest probability x lowest impact cell", () => {
    expect(cellExposureScore({ probability: "low", impact: "low" })).toBe(1);
  });
});
