import { describe, expect, it } from "vitest";

import { hasMeetingShape, hasRiskShape, hasStatusShape } from "./types";

describe("hasRiskShape / hasStatusShape (TIP-006)", () => {
  it("accepts a well-formed RiskModelOutput", () => {
    expect(
      hasRiskShape({ structured: true, risks: [], escalation_recommendation: null }),
    ).toBe(true);
  });

  it("rejects structured=true whose risks field is missing or the wrong type -- real Demo Mode failure mode", () => {
    expect(hasRiskShape({ structured: true } as never)).toBe(false);
    expect(hasRiskShape({ structured: true, risks: "not-an-array" } as never)).toBe(false);
  });

  it("rejects structured=false", () => {
    expect(hasRiskShape({ structured: false, raw_output: "x" })).toBe(false);
  });

  it("accepts a well-formed StatusModelOutput", () => {
    expect(
      hasStatusShape({ structured: true, health_status: "green", key_findings: [], recommendations: [] }),
    ).toBe(true);
  });

  it("rejects structured=true whose fields belong to a different agent's schema", () => {
    // e.g. a risk_review-shaped body returned for a project_status call
    expect(hasStatusShape({ structured: true, risks: [] } as never)).toBe(false);
    expect(hasStatusShape({ structured: true, health_status: "purple" } as never)).toBe(false);
  });

  it("rejects structured=false", () => {
    expect(hasStatusShape({ structured: false, raw_output: "x" })).toBe(false);
  });
});

describe("hasMeetingShape (TIP-007)", () => {
  it("accepts a well-formed MeetingModelOutput", () => {
    expect(
      hasMeetingShape({
        structured: true,
        summary: "resumo",
        decisions: [],
        action_items: [],
        issues: [],
        dependencies: [],
      }),
    ).toBe(true);
  });

  it("rejects structured=true whose fields belong to a different agent's schema", () => {
    expect(hasMeetingShape({ structured: true, health_status: "green" } as never)).toBe(false);
    expect(hasMeetingShape({ structured: true, risks: [] } as never)).toBe(false);
    expect(hasMeetingShape({ structured: true, summary: "x", decisions: "not-an-array" } as never)).toBe(
      false,
    );
  });

  it("rejects structured=false", () => {
    expect(hasMeetingShape({ structured: false, raw_output: "x" })).toBe(false);
  });
});
