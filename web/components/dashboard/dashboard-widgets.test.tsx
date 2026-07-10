import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { PortfolioSummaryStrip } from "./portfolio-summary-strip";
import { ProjectHealthGrid } from "./project-health-grid";
import { HealthStatusDistribution } from "./health-status-distribution";
import { RiskConcentrationRanking } from "./risk-concentration-ranking";
import type { ProjectSummary } from "@/lib/dashboard/types";

const projects: ProjectSummary[] = [
  {
    project_name: "Multilift",
    total_analyses: 5,
    open_risks: 3,
    pending_action_items: 2,
    latest_health_status: "red",
  },
  {
    project_name: "Aurora",
    total_analyses: 2,
    open_risks: 0,
    pending_action_items: 0,
    latest_health_status: null,
  },
];

describe("PortfolioSummaryStrip", () => {
  it("renders aggregated totals in label order", () => {
    const { container } = render(<PortfolioSummaryStrip projects={projects} />);
    expect(screen.getByText("Projetos")).toBeInTheDocument();
    expect(screen.getByText("Riscos identificados")).toBeInTheDocument();
    expect(screen.getByText("Ações pendentes")).toBeInTheDocument();
    const values = Array.from(container.querySelectorAll(".tabular-nums")).map(
      (el) => el.textContent,
    );
    expect(values).toEqual(["2", "3", "2"]);
  });
});

describe("ProjectHealthGrid", () => {
  it("renders one card per project with its name and health badge", () => {
    render(<ProjectHealthGrid projects={projects} />);
    expect(screen.getByText("Multilift")).toBeInTheDocument();
    expect(screen.getByText("Aurora")).toBeInTheDocument();
    expect(screen.getByText("red")).toBeInTheDocument();
    expect(screen.getByText("sem dado")).toBeInTheDocument();
  });

  it("renders nothing when the portfolio is empty", () => {
    render(<ProjectHealthGrid projects={[]} />);
    expect(screen.queryByText("Multilift")).not.toBeInTheDocument();
  });
});

describe("HealthStatusDistribution", () => {
  it("counts one red and one none", () => {
    render(<HealthStatusDistribution projects={projects} />);
    expect(screen.getByText("Crítico")).toBeInTheDocument();
    expect(screen.getByText("Sem dado")).toBeInTheDocument();
  });
});

describe("RiskConcentrationRanking", () => {
  it("lists only projects with open risks", () => {
    render(<RiskConcentrationRanking projects={projects} />);
    expect(screen.getByText("Multilift")).toBeInTheDocument();
    expect(screen.queryByText("Aurora")).not.toBeInTheDocument();
  });

  it("shows an empty message when no project has open risks", () => {
    const noRisk = projects.map((p) => ({ ...p, open_risks: 0 }));
    render(<RiskConcentrationRanking projects={noRisk} />);
    expect(screen.getByText("Nenhum projeto com riscos identificados.")).toBeInTheDocument();
  });
});
