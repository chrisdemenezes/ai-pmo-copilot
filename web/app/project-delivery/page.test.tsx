import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import ProjectDeliveryPage from "./page";
import { usePrograms } from "@/lib/hooks/use-programs";
import { useProjects } from "@/lib/hooks/use-projects";
import { Program } from "@/lib/domain/program";
import { Project } from "@/lib/domain/project";

vi.mock("@/lib/hooks/use-programs", () => ({
  usePrograms: vi.fn(),
}));
vi.mock("@/lib/hooks/use-projects", () => ({
  useProjects: vi.fn(),
}));

const mockedPrograms = vi.mocked(usePrograms);
const mockedProjects = vi.mocked(useProjects);

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
    ...overrides,
  });
}

describe("ProjectDeliveryPage", () => {
  it("renders the skeleton while pending", () => {
    mockedPrograms.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    mockedProjects.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(<ProjectDeliveryPage />);
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
  });

  it("groups Projects under their own Program only", () => {
    mockedPrograms.mockReturnValue({
      isPending: false,
      isError: false,
      data: [fakeProgram({ id: "PG-001", name: "Programa A" }), fakeProgram({ id: "PG-002", name: "Programa B" })],
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    mockedProjects.mockReturnValue({
      isPending: false,
      isError: false,
      data: [
        fakeProject({ id: "PJ-001", name: "Projeto Um", programId: "PG-001" }),
        fakeProject({ id: "PJ-002", name: "Projeto Dois", programId: "PG-002" }),
      ],
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<ProjectDeliveryPage />);
    expect(screen.getByText("Programa A")).toBeInTheDocument();
    expect(screen.getByText("Programa B")).toBeInTheDocument();
    expect(screen.getByText("Projeto Um")).toBeInTheDocument();
    expect(screen.getByText("Projeto Dois")).toBeInTheDocument();
  });

  it("shows an empty-state message for a Program with no Projects", () => {
    mockedPrograms.mockReturnValue({
      isPending: false,
      isError: false,
      data: [fakeProgram({ id: "PG-001", name: "Sem Projects" })],
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    mockedProjects.mockReturnValue({
      isPending: false,
      isError: false,
      data: [],
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<ProjectDeliveryPage />);
    expect(screen.getByText("Nenhum Project vinculado a este Program ainda.")).toBeInTheDocument();
  });
});
