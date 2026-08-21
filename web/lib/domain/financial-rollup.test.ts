import { describe, expect, it } from "vitest";

import { Project } from "./project";
import { aggregateFinancials, projectFinancialSummary } from "./financial-rollup";

function fakeProject(overrides: Partial<Parameters<typeof Project.create>[0]> = {}) {
  return Project.create({
    id: "PJ-001",
    name: "Projeto Teste",
    code: "PJ-001",
    description: "",
    programId: "PG-001",
    sponsor: "Sponsor",
    projectManager: "Gerente",
    objective: "",
    startDate: "2026-01-01",
    plannedEndDate: "2026-12-31",
    actualEndDate: null,
    progressPercentage: 50,
    health: "green",
    status: "Ativo",
    priority: "Alta",
    lastUpdated: "2026-07-15",
    nextReview: "2026-08-01",
    owner: { name: "Owner", role: "Product Owner" },
    milestones: [],
    team: { size: 3, leadName: "Owner" },
    approvedBudget: null,
    actualCost: null,
    forecastCost: null,
    ...overrides,
  });
}

describe("projectFinancialSummary", () => {
  it("computes variance and variancePercentage when both budget and actual cost are present", () => {
    const project = fakeProject({ approvedBudget: 1000, actualCost: 800, forecastCost: 1100 });
    const summary = projectFinancialSummary(project);
    expect(summary).toEqual({
      approvedBudget: 1000,
      actualCost: 800,
      forecastCost: 1100,
      variance: 200,
      variancePercentage: 20,
    });
  });

  it("never fabricates a variance when the Project has no financial data", () => {
    const project = fakeProject();
    const summary = projectFinancialSummary(project);
    expect(summary.variance).toBeNull();
    expect(summary.variancePercentage).toBeNull();
  });

  it("reports a negative variance when actual cost exceeds the approved budget", () => {
    const project = fakeProject({ approvedBudget: 1000, actualCost: 1300 });
    expect(projectFinancialSummary(project).variance).toBe(-300);
  });
});

describe("aggregateFinancials", () => {
  it("sums only the Projects that have financial data, ignoring the rest", () => {
    const projects = [
      fakeProject({ approvedBudget: 1000, actualCost: 800 }),
      fakeProject({ approvedBudget: 500, actualCost: 600 }),
      fakeProject(), // no financial data at all
    ];
    const summary = aggregateFinancials(projects);
    expect(summary.approvedBudget).toBe(1500);
    expect(summary.actualCost).toBe(1400);
    expect(summary.variance).toBe(100);
  });

  it("returns every field as null -- never zero -- when no Project in the group has financial data", () => {
    const summary = aggregateFinancials([fakeProject(), fakeProject()]);
    expect(summary).toEqual({
      approvedBudget: null,
      actualCost: null,
      forecastCost: null,
      variance: null,
      variancePercentage: null,
    });
  });

  it("returns the same null-safe shape for an empty group", () => {
    expect(aggregateFinancials([]).approvedBudget).toBeNull();
  });
});
