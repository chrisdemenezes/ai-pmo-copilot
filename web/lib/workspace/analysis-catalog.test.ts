import { describe, expect, it } from "vitest";

import { ANALYSIS_CATALOG } from "./analysis-catalog";

const TECHNICAL_NAMES = ["project_status", "risk_review", "meeting_intelligence", "transcript"];

describe("ANALYSIS_CATALOG (FS-006 §2.1 -- Pergunta -> Capability -> Executor)", () => {
  it("has exactly 3 real entries, one per Capability", () => {
    expect(ANALYSIS_CATALOG).toHaveLength(3);
    expect(ANALYSIS_CATALOG.map((entry) => entry.capability)).toEqual([
      "project-intelligence",
      "risk-intelligence",
      "communication-intelligence",
    ]);
  });

  it("every goalLabel is a question, never a technical or agent name", () => {
    for (const entry of ANALYSIS_CATALOG) {
      expect(entry.goalLabel).toMatch(/\?$/);
      for (const technicalName of TECHNICAL_NAMES) {
        expect(entry.goalLabel.toLowerCase()).not.toContain(technicalName);
        expect(entry.description.toLowerCase()).not.toContain(technicalName);
      }
    }
  });

  it("maps kind to capability 1:1, matching the Executor each kind resolves to", () => {
    const byKind = Object.fromEntries(ANALYSIS_CATALOG.map((entry) => [entry.kind, entry.capability]));
    expect(byKind).toEqual({
      status: "project-intelligence",
      risk: "risk-intelligence",
      meeting: "communication-intelligence",
    });
  });
});
