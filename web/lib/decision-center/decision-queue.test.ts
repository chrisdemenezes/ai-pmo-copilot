import { describe, expect, it } from "vitest";

import { buildExecutiveDecisionQueue, groupLatestRisksByProject, windowLabel } from "./decision-queue";
import type { ProjectIntelligenceSummary } from "@/lib/project/intelligence-summary";
import type { LatestRiskItem } from "./types";

// Stable project_name -> project_id registry so distinct display names get
// distinct identity keys automatically (TD-008 Fase 3b, Etapa 4a: joins are
// by project_id). A project and its risks sharing a name therefore share an
// id, which is exactly what the id-join exercises.
const PROJECT_IDS = new Map<string, number>();
let nextProjectId = 1;
function pidFor(name: string): number {
  const existing = PROJECT_IDS.get(name);
  if (existing !== undefined) return existing;
  const id = nextProjectId++;
  PROJECT_IDS.set(name, id);
  return id;
}

function project(overrides: Partial<ProjectIntelligenceSummary>): ProjectIntelligenceSummary {
  const project_name = overrides.project_name ?? "Aurora";
  return {
    project_id: pidFor(project_name),
    project_name,
    total_analyses: 1,
    open_risks: 0,
    pending_action_items: 0,
    latest_health_status: null,
    ...overrides,
  };
}

function risk(overrides: Partial<LatestRiskItem>): LatestRiskItem {
  const project_name = overrides.project_name === undefined ? "Aurora" : overrides.project_name;
  return {
    project_id: project_name === null ? null : pidFor(project_name),
    project_name,
    description: "Atraso no fornecedor",
    probability: "high",
    impact: "high",
    mitigation: "Escalar",
    escalation_recommendation: null,
    source_analysis_id: 1,
    source_created_at: "2026-07-01T00:00:00Z",
    ...overrides,
  };
}

describe("buildExecutiveDecisionQueue", () => {
  it("returns an empty queue when no project needs a decision", () => {
    const portfolio = [
      project({ project_name: "Aurora", latest_health_status: "green" }),
      project({ project_name: "Medlog", latest_health_status: null }),
    ];
    expect(buildExecutiveDecisionQueue(portfolio)).toEqual([]);
  });

  it("puts a red status project in the 'hoje' window with the real decision text", () => {
    const portfolio = [project({ project_name: "SAP", latest_health_status: "red" })];
    const [entry] = buildExecutiveDecisionQueue(portfolio);

    expect(entry.source).toBe("status");
    expect(entry.window).toBe("hoje");
    expect(entry.context).toBe("Status: Crítico");
    expect(entry.decision).toBe("Escalar ao patrocinador");
    expect(entry.nextStep).toBe("Escalar ao patrocinador");
  });

  it("puts a yellow status project in the 'esta_semana' window", () => {
    const portfolio = [project({ project_name: "SAP", latest_health_status: "yellow" })];
    const [entry] = buildExecutiveDecisionQueue(portfolio);

    expect(entry.window).toBe("esta_semana");
    expect(entry.context).toBe("Status: Atenção");
    expect(entry.decision).toBe("Acompanhar de perto");
  });

  it("never lists a project with green status -- absence is the message (Princípio de Atenção)", () => {
    const portfolio = [project({ project_name: "SAP", latest_health_status: "green" })];
    expect(buildExecutiveDecisionQueue(portfolio)).toEqual([]);
  });

  it("orders 'hoje' entries before 'esta_semana' entries", () => {
    const portfolio = [
      project({ project_name: "Zeta", latest_health_status: "yellow" }),
      project({ project_name: "Alpha", latest_health_status: "red" }),
    ];
    const queue = buildExecutiveDecisionQueue(portfolio);
    expect(queue.map((d) => d.project_name)).toEqual(["Alpha", "Zeta"]);
  });

  it("breaks ties within the same window alphabetically by project name", () => {
    const portfolio = [
      project({ project_name: "Zeta", latest_health_status: "red" }),
      project({ project_name: "Alpha", latest_health_status: "red" }),
    ];
    const queue = buildExecutiveDecisionQueue(portfolio);
    expect(queue.map((d) => d.project_name)).toEqual(["Alpha", "Zeta"]);
  });

  it("includes the fixed 'why' and 'consequence' text, never fabricated per project", () => {
    const portfolio = [project({ project_name: "SAP", latest_health_status: "red" })];
    const [entry] = buildExecutiveDecisionQueue(portfolio);

    expect(entry.whyItDependsOnMe).toBe(
      "Só um julgamento executivo decide se e como agir sobre este status.",
    );
    expect(entry.consequenceOfInaction).toBe(
      "Nada muda sozinho: este status permanece assim até uma nova Análise de Status ser executada.",
    );
  });
});

describe("windowLabel", () => {
  it("labels every window in Portuguese", () => {
    expect(windowLabel("hoje")).toBe("Hoje");
    expect(windowLabel("esta_semana")).toBe("Esta semana");
  });
});

describe("buildExecutiveDecisionQueue -- sinal de Risco (Incremento 2)", () => {
  it("generates a 'hoje' entry when a project has an attention-zone risk", () => {
    const portfolio = [project({ project_name: "Aurora", latest_health_status: "green" })];
    const risksByProject = groupLatestRisksByProject([
      risk({ project_name: "Aurora", probability: "high", impact: "high" }),
    ]);

    const [entry] = buildExecutiveDecisionQueue(portfolio, risksByProject);

    expect(entry.source).toBe("risk");
    expect(entry.window).toBe("hoje");
    expect(entry.context).toBe("1 risco(s) na zona de atenção");
    expect(entry.decision).toBe("Priorizar mitigação imediata");
  });

  it("never generates an entry when no risk is in the attention zone", () => {
    const portfolio = [project({ project_name: "Aurora", latest_health_status: "green" })];
    const risksByProject = groupLatestRisksByProject([
      risk({ project_name: "Aurora", probability: "low", impact: "low" }),
    ]);

    expect(buildExecutiveDecisionQueue(portfolio, risksByProject)).toEqual([]);
  });

  it("uses the real escalation_recommendation as next step when present", () => {
    const portfolio = [project({ project_name: "Aurora", latest_health_status: "green" })];
    const risksByProject = groupLatestRisksByProject([
      risk({
        project_name: "Aurora",
        probability: "high",
        impact: "high",
        escalation_recommendation: "Escalar ao comitê executivo",
      }),
    ]);

    const [entry] = buildExecutiveDecisionQueue(portfolio, risksByProject);
    expect(entry.nextStep).toBe("Escalar ao comitê executivo");
  });

  it("falls back to the honest continuity statement when there is no escalation_recommendation", () => {
    const portfolio = [project({ project_name: "Aurora", latest_health_status: "green" })];
    const risksByProject = groupLatestRisksByProject([
      risk({ project_name: "Aurora", probability: "high", impact: "high", escalation_recommendation: null }),
    ]);

    const [entry] = buildExecutiveDecisionQueue(portfolio, risksByProject);
    expect(entry.nextStep).toBe(
      "Nenhuma recomendação de escalonamento registrada nesta análise — continue monitorando os riscos identificados.",
    );
  });

  it("generates 2 separate entries (Status + Risco) for the same project, never merged", () => {
    const portfolio = [project({ project_name: "Aurora", latest_health_status: "red" })];
    const risksByProject = groupLatestRisksByProject([
      risk({ project_name: "Aurora", probability: "high", impact: "high" }),
    ]);

    const queue = buildExecutiveDecisionQueue(portfolio, risksByProject);
    expect(queue).toHaveLength(2);
    expect(queue.map((d) => d.source).sort()).toEqual(["risk", "status"]);
  });

  it("treats a risk with a null probability/impact as never in the attention zone", () => {
    const portfolio = [project({ project_name: "Aurora", latest_health_status: "green" })];
    const risksByProject = groupLatestRisksByProject([
      risk({ project_name: "Aurora", probability: null, impact: null }),
    ]);

    expect(buildExecutiveDecisionQueue(portfolio, risksByProject)).toEqual([]);
  });

  it("defaults to no risk data when latestRisksByProject is omitted (Incremento 1 behavior preserved)", () => {
    const portfolio = [project({ project_name: "Aurora", latest_health_status: "green" })];
    expect(buildExecutiveDecisionQueue(portfolio)).toEqual([]);
  });
});

describe("groupLatestRisksByProject", () => {
  it("groups risks by project_id (identity), not by name", () => {
    const grouped = groupLatestRisksByProject([
      risk({ project_name: "Aurora", description: "a" }),
      risk({ project_name: "Aurora", description: "b" }),
      risk({ project_name: "Medlog", description: "c" }),
    ]);

    expect(grouped.get(pidFor("Aurora"))).toHaveLength(2);
    expect(grouped.get(pidFor("Medlog"))).toHaveLength(1);
  });

  it("groups two identically-named projects with different ids separately (id is the key)", () => {
    const grouped = groupLatestRisksByProject([
      risk({ project_id: 91, project_name: "Migração", description: "a" }),
      risk({ project_id: 92, project_name: "Migração", description: "b" }),
    ]);

    expect(grouped.get(91)).toHaveLength(1);
    expect(grouped.get(92)).toHaveLength(1);
  });

  it("ignores risks without a project_id", () => {
    const grouped = groupLatestRisksByProject([risk({ project_id: null, project_name: null })]);
    expect(grouped.size).toBe(0);
  });
});

describe("buildExecutiveDecisionQueue -- join por identidade (project_id)", () => {
  it("joins risks to a project whose display name differs from the risk's, when the id matches", () => {
    // Same identity (id 7), different display strings -> still joins. This is
    // the whole point of keying on project_id, not on the name.
    const portfolio = [project({ project_id: 7, project_name: "Projeto Aurora", latest_health_status: "green" })];
    const risksByProject = groupLatestRisksByProject([
      risk({ project_id: 7, project_name: "Aurora", probability: "high", impact: "high" }),
    ]);

    const [entry] = buildExecutiveDecisionQueue(portfolio, risksByProject);
    expect(entry.source).toBe("risk");
    expect(entry.project_id).toBe(7);
  });

  it("does not join a risk whose id differs, even if the display name is identical", () => {
    const portfolio = [project({ project_id: 7, project_name: "Aurora", latest_health_status: "green" })];
    const risksByProject = groupLatestRisksByProject([
      risk({ project_id: 8, project_name: "Aurora", probability: "high", impact: "high" }),
    ]);

    expect(buildExecutiveDecisionQueue(portfolio, risksByProject)).toEqual([]);
  });
});
