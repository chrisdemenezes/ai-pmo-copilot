import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { PortfolioSituationGrid } from "./portfolio-situation-grid";
import type { Portfolio } from "@/lib/domain/portfolio";

function portfolio(overrides: Partial<Portfolio>): Portfolio {
  return {
    id: "1",
    name: "Portfólio de Teste",
    code: "PT-1",
    description: "",
    category: "",
    executiveOwner: "Diretoria",
    strategicObjective: "",
    status: "Ativo",
    health: "green",
    priority: "Alta",
    startDate: "2026-01-01",
    plannedEndDate: "2026-12-01",
    actualEndDate: null,
    progressPercentage: 50,
    programCount: 1,
    projectCount: 1,
    linkedDemands: 0,
    linkedRisks: 0,
    linkedIssues: 0,
    pendingDecisions: 0,
    ...overrides,
  } as Portfolio;
}

describe("PortfolioSituationGrid", () => {
  it("shows an Atrasado schedule badge for a portfolio past its planned end date", () => {
    render(
      <PortfolioSituationGrid
        portfolios={[portfolio({ plannedEndDate: "2020-01-01", actualEndDate: null })]}
      />,
    );

    expect(screen.getAllByText("Atrasado").length).toBeGreaterThan(0);
  });

  it("shows a No prazo schedule badge for a portfolio with a distant planned end date", () => {
    render(
      <PortfolioSituationGrid
        portfolios={[portfolio({ plannedEndDate: "2099-01-01", actualEndDate: null })]}
      />,
    );

    expect(screen.getAllByText("No prazo").length).toBeGreaterThan(0);
  });

  it("never marks a closed portfolio as Atrasado even with a past planned end date", () => {
    render(
      <PortfolioSituationGrid
        portfolios={[
          portfolio({ plannedEndDate: "2020-01-01", actualEndDate: "2019-12-01", status: "Encerrado" }),
        ]}
      />,
    );

    expect(screen.queryByText("Atrasado")).toBeNull();
  });

  // V1 Product & Capability Completion, Pacote G: explica a relação
  // Saúde x Prazo (Human User Session #2, D-222) sem alterar nenhum
  // algoritmo -- só a comunicação.
  it("offers an explanation of Saúde and Prazo as independent dimensions", () => {
    render(<PortfolioSituationGrid portfolios={[portfolio({})]} />);
    expect(screen.getByLabelText("O que significa Saúde?")).toBeInTheDocument();
    expect(screen.getByLabelText("O que significa Prazo?")).toBeInTheDocument();
  });
});
