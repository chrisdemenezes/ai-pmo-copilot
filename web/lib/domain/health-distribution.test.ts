import { describe, expect, it } from "vitest";

import { computeHealthDistribution } from "./health-distribution";

describe("computeHealthDistribution", () => {
  it("counts every real status plus the null (sem dado) bucket", () => {
    const result = computeHealthDistribution(["green", "green", "yellow", "red", null]);

    expect(result).toEqual([
      { status: "green", count: 2 },
      { status: "yellow", count: 1 },
      { status: "red", count: 1 },
      { status: null, count: 1 },
    ]);
  });

  it("returns zero counts for an empty input, never fabricating data", () => {
    expect(computeHealthDistribution([])).toEqual([
      { status: "green", count: 0 },
      { status: "yellow", count: 0 },
      { status: "red", count: 0 },
      { status: null, count: 0 },
    ]);
  });
});
