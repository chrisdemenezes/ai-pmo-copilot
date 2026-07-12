import { describe, expect, it } from "vitest";

import { buildRiskMatrix, groupAnalysesByKind } from "./aggregate";
import type { AnalysisListItem, RiskItem } from "./types";

describe("buildRiskMatrix", () => {
  it("returns all 9 probability x impact cells, even when empty", () => {
    const cells = buildRiskMatrix([]);
    expect(cells).toHaveLength(9);
    expect(cells.every((cell) => cell.count === 0)).toBe(true);
  });

  it("counts each risk into its probability x impact cell", () => {
    const risks: RiskItem[] = [
      { description: "a", probability: "high", impact: "high", mitigation: "" },
      { description: "b", probability: "high", impact: "high", mitigation: "" },
      { description: "c", probability: "low", impact: "medium", mitigation: "" },
    ];
    const cells = buildRiskMatrix(risks);
    const highHigh = cells.find((c) => c.probability === "high" && c.impact === "high");
    const lowMedium = cells.find((c) => c.probability === "low" && c.impact === "medium");
    expect(highHigh?.count).toBe(2);
    expect(lowMedium?.count).toBe(1);
  });
});

describe("groupAnalysesByKind", () => {
  it("splits a mixed list into meeting/risk/status buckets", () => {
    const analyses: AnalysisListItem[] = [
      { id: 1, kind: "meeting", project_name: "Aurora", created_at: "2026-07-01T00:00:00Z" },
      { id: 2, kind: "risk", project_name: "Aurora", created_at: "2026-07-02T00:00:00Z" },
      { id: 3, kind: "status", project_name: "Aurora", created_at: "2026-07-03T00:00:00Z" },
      { id: 4, kind: "risk", project_name: "Aurora", created_at: "2026-07-04T00:00:00Z" },
    ];
    const grouped = groupAnalysesByKind(analyses);
    expect(grouped.meeting).toHaveLength(1);
    expect(grouped.risk).toHaveLength(2);
    expect(grouped.status).toHaveLength(1);
  });
});
