import { describe, expect, it } from "vitest";

import { computeParetoData } from "./pareto";

describe("computeParetoData", () => {
  it("returns an empty array when there is nothing to rank", () => {
    expect(computeParetoData([])).toEqual([]);
  });

  it("sorts descending by value", () => {
    const result = computeParetoData([
      { label: "A", value: 10 },
      { label: "B", value: 50 },
      { label: "C", value: 30 },
    ]);

    expect(result.map((bar) => bar.label)).toEqual(["B", "C", "A"]);
  });

  it("computes percentage of total and cumulative percentage", () => {
    const result = computeParetoData([
      { label: "A", value: 25 },
      { label: "B", value: 75 },
    ]);

    expect(result[0]).toMatchObject({ label: "B", percentageOfTotal: 75 });
    expect(result[0].cumulativePercentage).toBeCloseTo(75);
    expect(result[1]).toMatchObject({ label: "A", percentageOfTotal: 25 });
    expect(result[1].cumulativePercentage).toBeCloseTo(100);
  });

  it("drops zero and negative values -- they never contribute to rank", () => {
    const result = computeParetoData([
      { label: "A", value: 10 },
      { label: "B", value: 0 },
      { label: "C", value: -5 },
    ]);

    expect(result.map((bar) => bar.label)).toEqual(["A"]);
    expect(result[0].percentageOfTotal).toBe(100);
  });

  it("never divides by zero when every value is non-positive", () => {
    expect(computeParetoData([{ label: "A", value: 0 }])).toEqual([]);
  });
});
