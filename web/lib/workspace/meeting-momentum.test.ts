import { describe, expect, it } from "vitest";

import { NEXT_STEP_FALLBACK_MEETING, impactHeadline, suggestedNextStep } from "./meeting-momentum";

describe("meeting-momentum (FS-006 §2.4 -- fixed UI rules, never the AI)", () => {
  it("impactHeadline reports real counts, never a severity classification", () => {
    expect(impactHeadline(3, 2, 4)).toBe("3 decisão(ões) · 2 ponto(s) de atenção · 4 responsabilidade(s)");
    expect(impactHeadline(0, 0, 0)).toBe("0 decisão(ões) · 0 ponto(s) de atenção · 0 responsabilidade(s)");
  });

  it("suggestedNextStep prioritizes issues over decisions -- only real, existing next steps", () => {
    expect(suggestedNextStep(1, 5)).toEqual({ label: "Executar Avaliação de Riscos" });
    expect(suggestedNextStep(0, 3)).toEqual({ label: "Atualizar Status Executivo" });
  });

  it("suggestedNextStep returns null rather than fabricating a suggestion", () => {
    expect(suggestedNextStep(0, 0)).toBeNull();
  });

  it("NEXT_STEP_FALLBACK_MEETING is an honest continuity statement", () => {
    expect(NEXT_STEP_FALLBACK_MEETING).toContain("Nenhum próximo passo");
  });
});
