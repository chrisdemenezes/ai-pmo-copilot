import { describe, expect, it } from "vitest";

import { buildExecutivePortfolioView } from "./portfolio-view";
import type { ExecutiveDecision } from "@/lib/decision-center/decision-queue";
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

function decision(overrides: Partial<ExecutiveDecision>): ExecutiveDecision {
  return {
    project_name: "Aurora",
    source: "status",
    window: "hoje",
    context: "Status: Crítico",
    decision: "Escalar ao patrocinador",
    whyItDependsOnMe: "Só um julgamento executivo decide se e como agir sobre este status.",
    consequenceOfInaction: "Nada muda sozinho.",
    nextStep: "Escalar ao patrocinador",
    ...overrides,
  };
}

describe("buildExecutivePortfolioView", () => {
  it("puts a project with a 'hoje' decision in the decision_today layer", () => {
    const portfolio = [project({ project_name: "SAP", latest_health_status: "red" })];
    const decisions = [decision({ project_name: "SAP", window: "hoje", context: "Status: Crítico" })];

    const [item] = buildExecutivePortfolioView(portfolio, decisions);

    expect(item.layer).toBe("decision_today");
    expect(item.whyAttention).toBe("Decisão pendente hoje");
    expect(item.realSignal).toBe("Status: Crítico");
    expect(item.nextMove).toEqual({ label: "Ver decisão completa", href: "/decisions" });
  });

  it("puts a project with only an 'esta_semana' decision in the decision_this_week layer", () => {
    const portfolio = [project({ project_name: "CRM", latest_health_status: "yellow" })];
    const decisions = [decision({ project_name: "CRM", window: "esta_semana", context: "Status: Atenção" })];

    const [item] = buildExecutivePortfolioView(portfolio, decisions);

    expect(item.layer).toBe("decision_this_week");
    expect(item.whyAttention).toBe("Decisão pendente esta semana");
  });

  it("prefers a 'hoje' decision over an 'esta_semana' decision from the same project", () => {
    const portfolio = [project({ project_name: "SAP" })];
    const decisions = [
      decision({ project_name: "SAP", source: "risk", window: "hoje", context: "2 risco(s) na zona de atenção" }),
      decision({ project_name: "SAP", source: "status", window: "esta_semana", context: "Status: Atenção" }),
    ];

    const [item] = buildExecutivePortfolioView(portfolio, decisions);

    expect(item.layer).toBe("decision_today");
    expect(item.realSignal).toBe("2 risco(s) na zona de atenção");
  });

  it("generates exactly one line for a project with 2 decisions (Status + Risco)", () => {
    const portfolio = [project({ project_name: "SAP" })];
    const decisions = [
      decision({ project_name: "SAP", source: "status", window: "hoje" }),
      decision({ project_name: "SAP", source: "risk", window: "hoje" }),
    ];

    const items = buildExecutivePortfolioView(portfolio, decisions);

    expect(items).toHaveLength(1);
  });

  it("puts a project with no decision in the no_signal layer, with no navigable next move", () => {
    const portfolio = [project({ project_name: "Portal", latest_health_status: "green" })];

    const [item] = buildExecutivePortfolioView(portfolio, []);

    expect(item.layer).toBe("no_signal");
    expect(item.whyAttention).toBe("Sem sinal de atenção");
    expect(item.realSignal).toBe("Nenhuma decisão pendente, nenhum risco identificado");
    expect(item.nextMove).toBeNull();
  });

  it("orders decision_today before decision_this_week before no_signal, alphabetically within a layer", () => {
    const portfolio = [
      project({ project_name: "Zeta" }),
      project({ project_name: "Multilift" }),
      project({ project_name: "Aurora" }),
      project({ project_name: "Beta" }),
    ];
    const decisions = [
      decision({ project_name: "Zeta", window: "esta_semana" }),
      decision({ project_name: "Multilift", window: "hoje" }),
      decision({ project_name: "Aurora", window: "hoje" }),
      // "Beta" has no decision -> no_signal
    ];

    const items = buildExecutivePortfolioView(portfolio, decisions);

    expect(items.map((i) => i.project_name)).toEqual(["Aurora", "Multilift", "Zeta", "Beta"]);
  });

  it("returns every project exactly once, covering the whole portfolio", () => {
    const portfolio = [
      project({ project_name: "A", latest_health_status: "red" }),
      project({ project_name: "B", latest_health_status: "yellow" }),
      project({ project_name: "C", latest_health_status: "green" }),
    ];
    const decisions = [
      decision({ project_name: "A", window: "hoje" }),
      decision({ project_name: "B", window: "esta_semana" }),
    ];

    const items = buildExecutivePortfolioView(portfolio, decisions);

    expect(items).toHaveLength(3);
    expect(new Set(items.map((i) => i.project_name))).toEqual(new Set(["A", "B", "C"]));
  });
});
