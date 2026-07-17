import { describe, expect, it } from "vitest";

import { buildExecutiveDecisionQueue, groupLatestRisksByProject, windowLabel } from "./decision-queue";
import type { ProjectSummary } from "@/lib/dashboard/types";
import type { LatestRiskItem } from "./types";

function project(overrides: Partial<ProjectSummary>): ProjectSummary {
  return {
    project_name: "Aurora",
    total_analyses: 1,
    open_risks: 0,
    pending_action_items: 0,
    latest_health_status: null,
    ...overrides,
  };
}

function risk(overrides: Partial<LatestRiskItem>): LatestRiskItem {
  return {
    project_name: "Aurora",
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
  it("groups risks by project_name", () => {
    const grouped = groupLatestRisksByProject([
      risk({ project_name: "Aurora", description: "a" }),
      risk({ project_name: "Aurora", description: "b" }),
      risk({ project_name: "Medlog", description: "c" }),
    ]);

    expect(grouped.get("Aurora")).toHaveLength(2);
    expect(grouped.get("Medlog")).toHaveLength(1);
  });

  it("ignores risks without a project_name", () => {
    const grouped = groupLatestRisksByProject([risk({ project_name: null })]);
    expect(grouped.size).toBe(0);
  });
});
