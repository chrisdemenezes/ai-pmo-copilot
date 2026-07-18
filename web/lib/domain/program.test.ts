import { describe, expect, it } from "vitest";

import { Program, consolidatePortfolios } from "./program";
import type { Portfolio } from "./portfolio";

function baseProps(overrides: Partial<Parameters<typeof Program.create>[0]> = {}) {
  return {
    id: "PG-TEST",
    name: "Programa Teste",
    code: "PG-TEST",
    description: "Descrição",
    portfolioId: "PF-001",
    sponsor: "Sponsor",
    programManager: "Gerente",
    status: "Ativo" as const,
    health: "green" as const,
    priority: "Alta" as const,
    objective: "Objetivo",
    startDate: "2026-01-01",
    plannedEndDate: "2026-12-31",
    actualEndDate: null,
    progressPercentage: 50,
    projectCount: 2,
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

function basePortfolio(overrides: Partial<Portfolio> = {}): Portfolio {
  return {
    id: "PF-001",
    name: "Portfólio Teste",
    code: "PF-001",
    description: "Descrição",
    category: "Categoria",
    executiveOwner: "Owner",
    strategicObjective: "Objetivo",
    status: "Ativo",
    health: "green",
    priority: "Alta",
    startDate: "2025-01-01",
    plannedEndDate: "2027-01-01",
    actualEndDate: null,
    progressPercentage: 10,
    programCount: 0,
    projectCount: 0,
    linkedDemands: 0,
    linkedRisks: 0,
    linkedIssues: 0,
    pendingDecisions: 0,
    sponsor: "Owner",
    pmoOwner: "PMO",
    lastUpdated: "2026-07-01",
    nextReview: "2026-08-01",
    ...overrides,
  };
}

describe("Program", () => {
  it("refuses to be created without a portfolioId (every Program belongs to a Portfolio)", () => {
    expect(() => Program.create(baseProps({ portfolioId: "" }))).toThrow(/portfolioId/);
  });

  it("belongsToPortfolio checks the exact portfolioId", () => {
    const program = Program.create(baseProps({ portfolioId: "PF-002" }));
    expect(program.belongsToPortfolio("PF-002")).toBe(true);
    expect(program.belongsToPortfolio("PF-001")).toBe(false);
  });

  it("isAtRisk is true only for red health", () => {
    expect(Program.create(baseProps({ health: "red" })).isAtRisk()).toBe(true);
    expect(Program.create(baseProps({ health: "yellow" })).isAtRisk()).toBe(false);
  });

  it("isOverdue is true when past the planned end date without an actual end date", () => {
    const program = Program.create(baseProps({ plannedEndDate: "2020-01-01" }));
    expect(program.isOverdue(new Date("2026-01-01"))).toBe(true);
  });

  it("isOverdue is false once the Program is Encerrado, even past the planned date", () => {
    const program = Program.create(
      baseProps({ plannedEndDate: "2020-01-01", status: "Encerrado" }),
    );
    expect(program.isOverdue(new Date("2026-01-01"))).toBe(false);
  });

  it("isOverdue is false with an actual end date recorded", () => {
    const program = Program.create(
      baseProps({ plannedEndDate: "2020-01-01", actualEndDate: "2020-06-01" }),
    );
    expect(program.isOverdue(new Date("2026-01-01"))).toBe(false);
  });
});

describe("consolidatePortfolios", () => {
  it("derives programCount, average progress and worst-case health from real Programs", () => {
    const portfolio = basePortfolio({ id: "PF-001", programCount: 0, progressPercentage: 0, health: "green" });
    const programs = [
      Program.create(baseProps({ portfolioId: "PF-001", progressPercentage: 40, health: "yellow" })),
      Program.create(baseProps({ portfolioId: "PF-001", progressPercentage: 60, health: "red" })),
    ];

    const [consolidated] = consolidatePortfolios([portfolio], programs);

    expect(consolidated.programCount).toBe(2);
    expect(consolidated.progressPercentage).toBe(50);
    expect(consolidated.health).toBe("red");
  });

  it("leaves a Portfolio with no Programs at its seed values", () => {
    const portfolio = basePortfolio({ id: "PF-999", programCount: 3, progressPercentage: 77, health: "yellow" });

    const [consolidated] = consolidatePortfolios([portfolio], []);

    expect(consolidated).toEqual(portfolio);
  });

  it("only aggregates Programs that belong to the given Portfolio", () => {
    const portfolio = basePortfolio({ id: "PF-001" });
    const programs = [
      Program.create(baseProps({ portfolioId: "PF-001", progressPercentage: 100, health: "green" })),
      Program.create(baseProps({ portfolioId: "PF-002", progressPercentage: 0, health: "red" })),
    ];

    const [consolidated] = consolidatePortfolios([portfolio], programs);

    expect(consolidated.programCount).toBe(1);
    expect(consolidated.progressPercentage).toBe(100);
    expect(consolidated.health).toBe("green");
  });
});
