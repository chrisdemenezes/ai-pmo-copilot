import { describe, expect, it } from "vitest";

import { FORBIDDEN_VOCABULARY, describeLearning } from "./language-contract";
import type { OrganizationalLearning } from "./organizational-learnings";

const RISK_LEARNING: OrganizationalLearning = {
  category: "risco",
  description: "Atraso do fornecedor de middleware",
  occurrences: 3,
  projectNames: ["Aurora", "Multilift", "Portal do Cliente 2.0"],
};

const ACTION_LEARNING: OrganizationalLearning = {
  category: "acao",
  description: "Confirmar cronograma com o patrocinador",
  occurrences: 4,
  projectNames: ["Aurora", "Multilift", "Portal do Cliente 2.0", "Programa de Governanca de Dados"],
};

describe("describeLearning (Language Contract)", () => {
  it("uses only permitted vocabulary for a recurring risk", () => {
    expect(describeLearning(RISK_LEARNING)).toBe(
      "Este risco apareceu em 3 projetos diferentes.",
    );
  });

  it("uses only permitted vocabulary for a recurring action", () => {
    expect(describeLearning(ACTION_LEARNING)).toBe(
      "Esta ação foi registrada em 4 projetos diferentes.",
    );
  });

  it("never contains any word from the forbidden vocabulary, for any category", () => {
    for (const learning of [RISK_LEARNING, ACTION_LEARNING]) {
      const text = describeLearning(learning).toLowerCase();
      for (const forbidden of FORBIDDEN_VOCABULARY) {
        expect(text).not.toContain(forbidden.toLowerCase());
      }
    }
  });

  it("never includes a percentage, ratio, or relative comparison", () => {
    const text = describeLearning(RISK_LEARNING);
    expect(text).not.toMatch(/%|mais que o normal|acima do esperado|fora do padrão/i);
  });
});
