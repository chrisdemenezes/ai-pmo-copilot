import { describe, expect, it } from "vitest";

import { Project, consolidatePrograms, rankProjectsNeedingAttention, countCriticalProjects } from "./project";
import { Program } from "./program";
import type { ProgramProps } from "./program";

function programProps(overrides: Partial<ProgramProps> = {}): ProgramProps {
  return {
    id: "PG-001",
    name: "Programa Teste",
    code: "PG-001",
    description: "",
    portfolioId: "PF-001",
    sponsor: "Sponsor",
    programManager: "Gerente",
    status: "Ativo",
    health: "green",
    priority: "Alta",
    objective: "",
    startDate: "2026-01-01",
    plannedEndDate: "2026-12-31",
    actualEndDate: null,
    progressPercentage: 0,
    projectCount: 0,
    linkedDemands: 0,
    linkedRisks: 0,
    linkedIssues: 0,
    pendingDecisions: 0,
    pendingActions: 0,
    pmoOwner: "PMO",
    lastUpdated: "2026-07-15",
    nextReview: "2026-08-01",
    ...overrides,
  };
}

function projectProps(overrides: Partial<Parameters<typeof Project.create>[0]> = {}) {
  return {
    id: "PJ-TEST",
    name: "Projeto Teste",
    code: "PJ-TEST",
    description: "",
    programId: "PG-001",
    sponsor: "Sponsor",
    projectManager: "Gerente",
    objective: "",
    startDate: "2026-01-01",
    plannedEndDate: "2026-12-31",
    actualEndDate: null,
    progressPercentage: 50,
    health: "green" as const,
    status: "Ativo" as const,
    priority: "Alta" as const,
    lastUpdated: "2026-07-15",
    nextReview: "2026-08-01",
    owner: { name: "Owner", role: "Product Owner" },
    milestones: [],
    team: { size: 3, leadName: "Owner" },
    ...overrides,
  };
}

describe("Project", () => {
  it("refuses to be created without a programId (every Project belongs to a Program)", () => {
    expect(() => Project.create(projectProps({ programId: "" }))).toThrow(/programId/);
  });

  it("belongsToProgram checks the exact programId", () => {
    const project = Project.create(projectProps({ programId: "PG-002" }));
    expect(project.belongsToProgram("PG-002")).toBe(true);
    expect(project.belongsToProgram("PG-001")).toBe(false);
  });

  it("belongsToPortfolio derives through the parent Program", () => {
    const program = Program.create(programProps({ id: "PG-001", portfolioId: "PF-001" }));
    const project = Project.create(projectProps({ programId: "PG-001" }));

    expect(project.belongsToPortfolio("PF-001", [program])).toBe(true);
    expect(project.belongsToPortfolio("PF-999", [program])).toBe(false);
  });

  it("belongsToPortfolio is false when the parent Program is not in the given list", () => {
    const project = Project.create(projectProps({ programId: "PG-999" }));
    expect(project.belongsToPortfolio("PF-001", [])).toBe(false);
  });

  it("isAtRisk and health() reflect the red/yellow/green severity", () => {
    expect(Project.create(projectProps({ health: "red" })).isAtRisk()).toBe(true);
    expect(Project.create(projectProps({ health: "yellow" })).health()).toBe("yellow");
  });

  it("completionPercentage() returns the stored progress", () => {
    expect(Project.create(projectProps({ progressPercentage: 42 })).completionPercentage()).toBe(42);
  });

  it("isOverdue is true when past the planned end date without an actual end date", () => {
    const project = Project.create(projectProps({ plannedEndDate: "2020-01-01" }));
    expect(project.isOverdue(new Date("2026-01-01"))).toBe(true);
  });

  it("isOverdue is false once Encerrado, even past the planned date", () => {
    const project = Project.create(projectProps({ plannedEndDate: "2020-01-01", status: "Encerrado" }));
    expect(project.isOverdue(new Date("2026-01-01"))).toBe(false);
  });
});

describe("consolidatePrograms", () => {
  it("derives projectCount, average progress and worst-case health from real Projects", () => {
    const program = Program.create(programProps({ id: "PG-001" }));
    const projects = [
      Project.create(projectProps({ programId: "PG-001", progressPercentage: 40, health: "yellow" })),
      Project.create(projectProps({ programId: "PG-001", progressPercentage: 60, health: "red" })),
    ];

    const [consolidated] = consolidatePrograms([program], projects);

    expect(consolidated.projectCount).toBe(2);
    expect(consolidated.progressPercentage).toBe(50);
    expect(consolidated.health).toBe("red");
  });

  it("leaves a Program with no Projects at its own values", () => {
    const program = Program.create(programProps({ id: "PG-999", projectCount: 3, progressPercentage: 77 }));

    const [consolidated] = consolidatePrograms([program], []);

    expect(consolidated).toEqual(program);
  });

  it("only aggregates Projects that belong to the given Program", () => {
    const program = Program.create(programProps({ id: "PG-001" }));
    const projects = [
      Project.create(projectProps({ programId: "PG-001", progressPercentage: 100, health: "green" })),
      Project.create(projectProps({ programId: "PG-002", progressPercentage: 0, health: "red" })),
    ];

    const [consolidated] = consolidatePrograms([program], projects);

    expect(consolidated.projectCount).toBe(1);
    expect(consolidated.progressPercentage).toBe(100);
  });
});

describe("rankProjectsNeedingAttention", () => {
  it("ranks red before yellow before green, then by ascending progress", () => {
    const projects = [
      Project.create(projectProps({ id: "PJ-A", name: "A", health: "green", progressPercentage: 10 })),
      Project.create(projectProps({ id: "PJ-B", name: "B", health: "red", progressPercentage: 90 })),
      Project.create(projectProps({ id: "PJ-C", name: "C", health: "red", progressPercentage: 30 })),
      Project.create(projectProps({ id: "PJ-D", name: "D", health: "yellow", progressPercentage: 50 })),
    ];

    const ranked = rankProjectsNeedingAttention(projects, 3);

    expect(ranked.map((project) => project.name)).toEqual(["C", "B", "D"]);
  });

  it("respects the limit parameter", () => {
    const projects = [
      Project.create(projectProps({ id: "PJ-A" })),
      Project.create(projectProps({ id: "PJ-B" })),
      Project.create(projectProps({ id: "PJ-C" })),
    ];

    expect(rankProjectsNeedingAttention(projects, 2)).toHaveLength(2);
  });
});

describe("countCriticalProjects", () => {
  it("counts only red Projects belonging to the given Program", () => {
    const projects = [
      Project.create(projectProps({ programId: "PG-001", health: "red" })),
      Project.create(projectProps({ programId: "PG-001", health: "green" })),
      Project.create(projectProps({ programId: "PG-002", health: "red" })),
    ];

    expect(countCriticalProjects("PG-001", projects)).toBe(1);
  });
});
