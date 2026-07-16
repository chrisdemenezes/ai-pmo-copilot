import { describe, expect, it } from "vitest";

import {
  buildRecurringActions,
  buildRecurringRisks,
  selectTopLearnings,
  type OrganizationalLearning,
} from "./organizational-learnings";
import type { LatestRiskItem } from "@/lib/decision-center/types";
import type { ActionItemView } from "@/lib/workspace/types";

function risk(description: string, projectName: string | null): LatestRiskItem {
  return {
    project_name: projectName,
    description,
    probability: "high",
    impact: "high",
    mitigation: "Mitigar",
    escalation_recommendation: null,
    source_analysis_id: 1,
    source_created_at: "2026-07-01T00:00:00Z",
  };
}

function action(description: string, projectName: string | null): ActionItemView {
  return {
    project_name: projectName,
    description,
    owner: null,
    due_date: null,
    source_analysis_id: 1,
    source_created_at: "2026-07-01T00:00:00Z",
  };
}

describe("buildRecurringRisks (Evidence First)", () => {
  it("excludes a risk that appears in only 1 or 2 projects -- evento/observação, not aprendizado (Journey §02)", () => {
    const oneProject = [risk("Atraso do fornecedor", "Aurora")];
    expect(buildRecurringRisks(oneProject)).toEqual([]);

    const twoProjects = [
      risk("Atraso do fornecedor", "Aurora"),
      risk("Atraso do fornecedor", "Multilift"),
    ];
    expect(buildRecurringRisks(twoProjects)).toEqual([]);
  });

  it("includes a risk that recurs in 3+ distinct projects, with the real count and project names", () => {
    const risks = [
      risk("Atraso do fornecedor", "Aurora"),
      risk("Atraso do fornecedor", "Multilift"),
      risk("Atraso do fornecedor", "Portal do Cliente 2.0"),
    ];
    expect(buildRecurringRisks(risks)).toEqual([
      {
        category: "risco",
        description: "Atraso do fornecedor",
        occurrences: 3,
        projectNames: ["Aurora", "Multilift", "Portal do Cliente 2.0"],
      },
    ]);
  });

  it("never counts a project with no real name -- auditability requires a citable project (Journey §03)", () => {
    const risks = [
      risk("Atraso do fornecedor", "Aurora"),
      risk("Atraso do fornecedor", "Multilift"),
      risk("Atraso do fornecedor", null),
    ];
    expect(buildRecurringRisks(risks)).toEqual([]);
  });

  it("counts a project only once even if the same risk appears twice for it", () => {
    const risks = [
      risk("Atraso do fornecedor", "Aurora"),
      risk("Atraso do fornecedor", "Aurora"),
      risk("Atraso do fornecedor", "Multilift"),
      risk("Atraso do fornecedor", "Portal do Cliente 2.0"),
    ];
    expect(buildRecurringRisks(risks)[0].occurrences).toBe(3);
  });

  it("matches by exact text only -- never a fabricated similarity heuristic", () => {
    const risks = [
      risk("Atraso do fornecedor", "Aurora"),
      risk("Atraso no fornecedor", "Multilift"),
      risk("atraso do fornecedor", "Portal do Cliente 2.0"),
    ];
    expect(buildRecurringRisks(risks)).toEqual([]);
  });

  it("is deterministic -- same evidence always produces the same result (Evidence First)", () => {
    const risks = [
      risk("Atraso do fornecedor", "Aurora"),
      risk("Atraso do fornecedor", "Multilift"),
      risk("Atraso do fornecedor", "Portal do Cliente 2.0"),
      risk("Falta de treinamento", "Aurora"),
      risk("Falta de treinamento", "Multilift"),
      risk("Falta de treinamento", "Renovacao de Infraestrutura de Rede"),
      risk("Falta de treinamento", "Programa de Governanca de Dados"),
    ];
    const first = buildRecurringRisks(risks);
    const second = buildRecurringRisks(risks);
    expect(first).toEqual(second);
  });

  it("orders by occurrence count descending, tie-broken alphabetically by description", () => {
    const risks = [
      // "Falta de treinamento": 4 projects
      risk("Falta de treinamento", "Aurora"),
      risk("Falta de treinamento", "Multilift"),
      risk("Falta de treinamento", "Renovacao de Infraestrutura de Rede"),
      risk("Falta de treinamento", "Programa de Governanca de Dados"),
      // "Atraso do fornecedor": 3 projects
      risk("Atraso do fornecedor", "Aurora"),
      risk("Atraso do fornecedor", "Multilift"),
      risk("Atraso do fornecedor", "Portal do Cliente 2.0"),
      // "Zebra de escopo": 3 projects (tie with "Atraso" on count, alphabetically after)
      risk("Zebra de escopo", "Aurora"),
      risk("Zebra de escopo", "Multilift"),
      risk("Zebra de escopo", "Portal do Cliente 2.0"),
    ];
    const result = buildRecurringRisks(risks);
    expect(result.map((r) => r.description)).toEqual([
      "Falta de treinamento",
      "Atraso do fornecedor",
      "Zebra de escopo",
    ]);
  });
});

describe("buildRecurringActions", () => {
  it("uses the same 3+ distinct-project rule, applied to ActionItemView.description", () => {
    const actions = [
      action("Confirmar cronograma com o patrocinador", "Aurora"),
      action("Confirmar cronograma com o patrocinador", "Multilift"),
      action("Confirmar cronograma com o patrocinador", "Portal do Cliente 2.0"),
    ];
    expect(buildRecurringActions(actions)).toEqual([
      {
        category: "acao",
        description: "Confirmar cronograma com o patrocinador",
        occurrences: 3,
        projectNames: ["Aurora", "Multilift", "Portal do Cliente 2.0"],
      },
    ]);
  });
});

describe("selectTopLearnings", () => {
  const risco = (description: string, occurrences: number): OrganizationalLearning => ({
    category: "risco",
    description,
    occurrences,
    projectNames: [],
  });
  const acao = (description: string, occurrences: number): OrganizationalLearning => ({
    category: "acao",
    description,
    occurrences,
    projectNames: [],
  });

  it("caps at the given limit without reordering across categories (fixed category order, UX Flow §03)", () => {
    const learnings = [
      risco("R1", 5),
      risco("R2", 4),
      risco("R3", 3),
      // "A1" has more occurrences than R3, but risco still comes first in the input order.
      acao("A1", 9),
    ];
    const result = selectTopLearnings(learnings, 3);
    expect(result.map((l) => l.description)).toEqual(["R1", "R2", "R3"]);
  });

  it("never pads with fewer than the real number of items (UX Flow §05: no artificial filler)", () => {
    const learnings = [risco("Único aprendizado real", 3)];
    expect(selectTopLearnings(learnings, 5)).toEqual(learnings);
  });

  it("returns an empty array when there are zero real learnings", () => {
    expect(selectTopLearnings([], 5)).toEqual([]);
  });
});
