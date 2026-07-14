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
    const { container } = render(
      <PortfolioSummaryStrip projects={projects} criticalDecisionsCount={1} />,
    );
    expect(screen.getByText("Projetos")).toBeInTheDocument();
    expect(screen.getByText("Riscos identificados")).toBeInTheDocument();
    expect(screen.getByText("Ações pendentes")).toBeInTheDocument();
    expect(screen.getByText("Decisões críticas")).toBeInTheDocument();
    const values = Array.from(container.querySelectorAll(".tabular-nums")).map(
      (el) => el.textContent,
    );
    expect(values).toEqual(["2", "3", "2", "1"]);
  });

  // TIP-008 Incremento 3 -- KPI "Ações pendentes" vira link para a página
  // de portfólio "Ações" (Incremento 2); TIP-009 Incremento 3 acrescenta
  // "Decisões críticas" -> /decisions. Os outros 2 KPIs continuam sem link.
  it("links only Ações pendentes and Decisões críticas to their own pages", () => {
    render(<PortfolioSummaryStrip projects={projects} criticalDecisionsCount={1} />);
    expect(screen.getByRole("link", { name: /Ações pendentes/ })).toHaveAttribute(
      "href",
      "/actions",
    );
    expect(screen.getByRole("link", { name: /Decisões críticas/ })).toHaveAttribute(
      "href",
      "/decisions",
    );
    expect(screen.queryByRole("link", { name: /^Projetos/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Riscos identificados/ })).not.toBeInTheDocument();
  });

  it("shows a skeleton placeholder for Decisões críticas when the count is null", () => {
    const { container } = render(
      <PortfolioSummaryStrip projects={projects} criticalDecisionsCount={null} />,
    );
    expect(screen.getByText("Decisões críticas")).toBeInTheDocument();
    expect(container.querySelector('[data-slot="skeleton"]')).not.toBeNull();
  });
});

describe("ProjectHealthGrid", () => {
  it("renders each project's name and health badge (table + mobile card views)", () => {
    render(<ProjectHealthGrid projects={projects} />);
    // Both the md/lg table and the mobile card list render in the DOM
    // simultaneously -- CSS (hidden/md:block) decides which is visible per
    // breakpoint, so each project appears twice.
    expect(screen.getAllByText("Multilift")).toHaveLength(2);
    expect(screen.getAllByText("Aurora")).toHaveLength(2);
    expect(screen.getAllByText("Crítico")).toHaveLength(2);
    expect(screen.getAllByText("Sem dado")).toHaveLength(2);
  });

  it("renders nothing when the portfolio is empty", () => {
    render(<ProjectHealthGrid projects={[]} />);
    expect(screen.queryByText("Multilift")).not.toBeInTheDocument();
  });

  it("links each project name to its Workspace, URL-encoded (TIP-004)", () => {
    render(
      <ProjectHealthGrid
        projects={[
          {
            project_name: "Implantacao SAP S/4HANA",
            total_analyses: 2,
            open_risks: 4,
            pending_action_items: 0,
            latest_health_status: "red",
          },
        ]}
      />,
    );
    const links = screen.getAllByRole("link", { name: "Implantacao SAP S/4HANA" });
    expect(links.length).toBeGreaterThan(0);
    for (const link of links) {
      expect(link).toHaveAttribute(
        "href",
        "/workspace/Implantacao%20SAP%20S%2F4HANA",
      );
    }
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
