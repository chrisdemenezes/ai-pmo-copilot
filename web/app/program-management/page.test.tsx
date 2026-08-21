import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import ProgramManagementPage from "./page";
import { usePortfolios } from "@/lib/hooks/use-portfolios";
import { usePrograms } from "@/lib/hooks/use-programs";
import { useProjects } from "@/lib/hooks/use-projects";
import { Program } from "@/lib/domain/program";
import { Project } from "@/lib/domain/project";
import type { Portfolio } from "@/lib/domain/portfolio";

vi.mock("@/lib/hooks/use-portfolios", () => ({
  usePortfolios: vi.fn(),
}));
vi.mock("@/lib/hooks/use-programs", () => ({
  usePrograms: vi.fn(),
}));
vi.mock("@/lib/hooks/use-projects", () => ({
  useProjects: vi.fn(),
}));

const mockedPortfolios = vi.mocked(usePortfolios);
const mockedPrograms = vi.mocked(usePrograms);
const mockedProjects = vi.mocked(useProjects);
// Default: most tests don't care about the financial rollup -- override
// per-test to exercise it.
mockedProjects.mockReturnValue({
  isPending: false,
  isError: false,
  data: [],
  error: null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any);

function fakePortfolio(overrides: Partial<Portfolio> = {}): Portfolio {
  return {
    id: "PF-001",
    name: "Portfólio Teste",
    code: "PF-001",
    description: "",
    category: "",
    executiveOwner: "Owner",
    strategicObjective: "",
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

function fakeProgram(overrides: Partial<Parameters<typeof Program.create>[0]> = {}) {
  return Program.create({
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
  });
}

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

describe("ProgramManagementPage", () => {
  it("renders the skeleton while pending", () => {
    mockedPortfolios.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    mockedPrograms.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(<ProgramManagementPage />);
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
  });

  it("groups Programs under their own Portfolio only", () => {
    mockedPortfolios.mockReturnValue({
      isPending: false,
      isError: false,
      data: [fakePortfolio({ id: "PF-001", name: "Corporativo" }), fakePortfolio({ id: "PF-002", name: "Digital" })],
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    mockedPrograms.mockReturnValue({
      isPending: false,
      isError: false,
      data: [
        fakeProgram({ id: "PG-001", name: "Programa A", portfolioId: "PF-001" }),
        fakeProgram({ id: "PG-002", name: "Programa B", portfolioId: "PF-002" }),
      ],
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<ProgramManagementPage />);
    expect(screen.getByText("Corporativo")).toBeInTheDocument();
    expect(screen.getByText("Digital")).toBeInTheDocument();
    expect(screen.getByText("Programa A")).toBeInTheDocument();
    expect(screen.getByText("Programa B")).toBeInTheDocument();
  });

  // V1 Product & Capability Completion, Package K: KPI financeiro do
  // Portfólio é um rollup em runtime sobre os Projects de seus próprios
  // Programs -- transitivo, nunca uma coluna própria em Portfolio.
  it("shows a Portfolio-level financial rollup over Projects of its own Programs", () => {
    mockedPortfolios.mockReturnValue({
      isPending: false,
      isError: false,
      data: [fakePortfolio({ id: "PF-001", name: "Corporativo" })],
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    mockedPrograms.mockReturnValue({
      isPending: false,
      isError: false,
      data: [fakeProgram({ id: "PG-001", name: "Programa A", portfolioId: "PF-001" })],
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    mockedProjects.mockReturnValue({
      isPending: false,
      isError: false,
      data: [
        fakeProject({ id: "PJ-001", programId: "PG-001", approvedBudget: 1000, actualCost: 800 }),
        fakeProject({ id: "PJ-002", programId: "PG-001", approvedBudget: 500, actualCost: 600 }),
      ],
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<ProgramManagementPage />);

    expect(screen.getByText(/Orçamento aprovado: R\$\s?1\.500/)).toBeInTheDocument();
    expect(screen.getByText(/Custo real: R\$\s?1\.400/)).toBeInTheDocument();
    expect(screen.getByText(/Variação: R\$\s?100/)).toBeInTheDocument();
  });

  it("shows an empty-state message for a Portfolio with no Programs", () => {
    mockedPortfolios.mockReturnValue({
      isPending: false,
      isError: false,
      data: [fakePortfolio({ id: "PF-001", name: "Sem Programas" })],
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    mockedPrograms.mockReturnValue({
      isPending: false,
      isError: false,
      data: [],
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<ProgramManagementPage />);
    expect(screen.getByText("Nenhum Program vinculado a este Portfólio ainda.")).toBeInTheDocument();
  });
});
