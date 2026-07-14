import { describe, expect, it } from "vitest";

import { buildExecutiveDecisionQueue, windowLabel } from "./decision-queue";
import type { ProjectSummary } from "@/lib/dashboard/types";

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
