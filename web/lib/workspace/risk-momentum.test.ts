import { describe, expect, it } from "vitest";

import {
  RISK_NEXT_STEP_FALLBACK,
  isHighAttentionRisk,
  riskContextHeading,
  suggestedRiskDecision,
} from "./risk-momentum";
import type { RiskItem } from "./types";

function risk(probability: RiskItem["probability"], impact: RiskItem["impact"]): RiskItem {
  return { description: "d", probability, impact, mitigation: "m" };
}

describe("risk-momentum (fixed UI rules over real probability/impact, never the AI)", () => {
  it.each([
    ["high", "high", true],
    ["high", "medium", true],
    ["medium", "high", true],
    ["medium", "medium", false],
    ["low", "high", false],
    ["high", "low", false],
    ["low", "low", false],
  ] as const)("isHighAttentionRisk(%s, %s) -> %s", (probability, impact, expected) => {
    expect(isHighAttentionRisk(risk(probability, impact))).toBe(expected);
  });

  it("riskContextHeading reacts to whether any attention risk exists", () => {
    expect(riskContextHeading(0)).toBe("Sem riscos críticos no momento");
    expect(riskContextHeading(2)).toBe("Riscos que exigem atenção");
  });

  it("suggestedRiskDecision reacts to whether any attention risk exists", () => {
    expect(suggestedRiskDecision(0)).toBe("Manter monitoramento de rotina");
    expect(suggestedRiskDecision(1)).toBe("Priorizar mitigação imediata");
  });

  it("RISK_NEXT_STEP_FALLBACK is an honest continuity statement, not a fabricated recommendation", () => {
    expect(RISK_NEXT_STEP_FALLBACK).toContain("continue monitorando");
  });
});
