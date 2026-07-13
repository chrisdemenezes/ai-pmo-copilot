import { describe, expect, it } from "vitest";

import { NEXT_STEP_FALLBACK, contextHeading, suggestedDecision } from "./decision-momentum";

describe("decision-momentum (Decision Experience Review, Rev. 2 -- fixed UI rules, never the AI)", () => {
  it.each([
    ["red", "Pontos de atenção"],
    ["yellow", "Pontos de atenção"],
    ["green", "Notas do período"],
  ] as const)("contextHeading(%s) -> %s", (healthStatus, expected) => {
    expect(contextHeading(healthStatus)).toBe(expected);
  });

  it.each([
    ["red", "Escalar ao patrocinador"],
    ["yellow", "Acompanhar de perto"],
    ["green", "Manter o curso atual"],
  ] as const)("suggestedDecision(%s) -> %s", (healthStatus, expected) => {
    expect(suggestedDecision(healthStatus)).toBe(expected);
  });

  it("NEXT_STEP_FALLBACK is an honest continuity statement, not a fabricated recommendation", () => {
    expect(NEXT_STEP_FALLBACK).toBe(
      "Nenhuma recomendação registrada nesta análise — continue acompanhando o projeto.",
    );
  });
});
