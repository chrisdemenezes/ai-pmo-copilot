import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { WorkspaceHeader } from "./workspace-header";
import { ExecutiveSummary } from "./executive-summary";
import { IntelligenceTimeline } from "./intelligence-timeline";
import { RisksPanel } from "./risks-panel";
import { ActionsPanel } from "./actions-panel";
import { DecisionsPanel } from "./decisions-panel";
import { RecommendationsPanel } from "./recommendations-panel";
import { useWorkspaceSummary } from "@/lib/hooks/use-workspace-summary";
import { useWorkspaceTimeline } from "@/lib/hooks/use-workspace-timeline";
import { useWorkspaceLatestByKind } from "@/lib/hooks/use-workspace-latest";

vi.mock("@/lib/hooks/use-workspace-summary", () => ({ useWorkspaceSummary: vi.fn() }));
vi.mock("@/lib/hooks/use-workspace-timeline", () => ({ useWorkspaceTimeline: vi.fn() }));
vi.mock("@/lib/hooks/use-workspace-latest", () => ({ useWorkspaceLatestByKind: vi.fn() }));

const mockedSummary = vi.mocked(useWorkspaceSummary);
const mockedTimeline = vi.mocked(useWorkspaceTimeline);
const mockedLatest = vi.mocked(useWorkspaceLatestByKind);

const PENDING = { isPending: true, isError: false, data: undefined, refetch: vi.fn(), isFetching: false } as never;
const ERROR = { isPending: false, isError: true, data: undefined, refetch: vi.fn(), isFetching: false } as never;

function summaryState(overrides: Partial<Record<string, unknown>>) {
  return { isPending: false, isError: false, isFetching: false, refetch: vi.fn(), ...overrides } as never;
}

describe("WorkspaceHeader (Painel A, independente)", () => {
  it("shows a skeleton while pending", () => {
    mockedSummary.mockReturnValue(PENDING);
    const { container } = render(<WorkspaceHeader projectName="Aurora" />);
    expect(container.querySelector('[data-slot="skeleton"]')).not.toBeNull();
  });

  it("falls back to the raw project name on error, without crashing", () => {
    mockedSummary.mockReturnValue(ERROR);
    render(<WorkspaceHeader projectName="Aurora" />);
    expect(screen.getByRole("heading", { name: "Aurora" })).toBeInTheDocument();
  });

  it("renders the project name and health badge on success", () => {
    mockedSummary.mockReturnValue(
      summaryState({
        data: {
          project_name: "Aurora",
          total_analyses: 3,
          open_risks: 2,
          pending_action_items: 1,
          latest_health_status: "red",
        },
      }),
    );
    render(<WorkspaceHeader projectName="Aurora" />);
    expect(screen.getByRole("heading", { name: "Aurora" })).toBeInTheDocument();
    expect(screen.getByText("Crítico")).toBeInTheDocument();
  });
});

describe("ExecutiveSummary (Painéis A + C, cada um com estado próprio)", () => {
  it("renders the counts card even while the findings card is still loading", () => {
    mockedSummary.mockReturnValue(
      summaryState({
        data: {
          project_name: "Aurora",
          total_analyses: 4,
          open_risks: 1,
          pending_action_items: 0,
          latest_health_status: "green",
        },
      }),
    );
    mockedLatest.mockReturnValue(PENDING);

    render(<ExecutiveSummary projectName="Aurora" />);
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getAllByText("Achados-chave").length).toBeGreaterThan(0);
  });

  it("renders findings even while the counts card errored -- neither blocks the other", () => {
    mockedSummary.mockReturnValue(ERROR);
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 9,
          kind: "status",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          payload: {
            agent: "project_status",
            project_name: "Aurora",
            model_output: { structured: true, health_status: "green", key_findings: ["Achado real"], recommendations: [] },
          },
        },
      }),
    );

    render(<ExecutiveSummary projectName="Aurora" />);
    expect(screen.getByText("Achado real")).toBeInTheDocument();
    expect(screen.getByText("Não foi possível carregar as contagens.")).toBeInTheDocument();
  });

  it("never invents a finding -- shows a plain empty state when there is no status analysis yet", () => {
    mockedSummary.mockReturnValue(summaryState({ data: { project_name: "Aurora", total_analyses: 0, open_risks: 0, pending_action_items: 0, latest_health_status: null } }));
    mockedLatest.mockReturnValue(summaryState({ data: null }));

    render(<ExecutiveSummary projectName="Aurora" />);
    expect(screen.getByText("Nenhuma análise de status registrada ainda.")).toBeInTheDocument();
  });
});

describe("IntelligenceTimeline (Painel B, independente)", () => {
  it("shows an empty message, not an error, when there is simply no history yet", () => {
    mockedTimeline.mockReturnValue(summaryState({ data: [] }));
    render(<IntelligenceTimeline projectName="Aurora" />);
    expect(screen.getByText("Nenhuma análise registrada ainda.")).toBeInTheDocument();
  });

  it("lists analyses with a kind badge, most recent first as returned by the backend", () => {
    mockedTimeline.mockReturnValue(
      summaryState({
        data: [
          { id: 2, kind: "risk", project_name: "Aurora", created_at: "2026-07-02T10:00:00Z" },
          { id: 1, kind: "meeting", project_name: "Aurora", created_at: "2026-07-01T10:00:00Z" },
        ],
      }),
    );
    render(<IntelligenceTimeline projectName="Aurora" />);
    expect(screen.getByText("Risco")).toBeInTheDocument();
    expect(screen.getByText("Reunião")).toBeInTheDocument();
  });
});

describe("RisksPanel (Painel C, 'risk')", () => {
  it("renders risks, escalation recommendation, and the matrix on success", () => {
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 1,
          kind: "risk",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          payload: {
            agent: "risk_review",
            project_name: "Aurora",
            model_output: {
              structured: true,
              risks: [{ description: "Atraso", probability: "high", impact: "high", mitigation: "Plano B" }],
              escalation_recommendation: "Escalar ao sponsor",
            },
          },
        },
      }),
    );
    render(<RisksPanel projectName="Aurora" />);
    expect(screen.getByText("Atraso")).toBeInTheDocument();
    expect(screen.getByText(/Escalar ao sponsor/)).toBeInTheDocument();
  });

  it("handles an unstructured payload without crashing", () => {
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 1,
          kind: "risk",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          payload: { agent: "risk_review", project_name: "Aurora", model_output: { structured: false, raw_output: "not json" } },
        },
      }),
    );
    render(<RisksPanel projectName="Aurora" />);
    expect(screen.getByText("Resposta da IA não estruturada nesta análise.")).toBeInTheDocument();
  });
});

describe("ActionsPanel and DecisionsPanel (share the 'meeting' query, independent states)", () => {
  const meetingData = {
    id: 5,
    kind: "meeting" as const,
    project_name: "Aurora",
    created_at: "2026-07-01T00:00:00Z",
    payload: {
      agent: "meeting_intelligence",
      project_name: "Aurora",
      model_output: {
        structured: true as const,
        summary: "resumo",
        decisions: ["Decisão A"],
        action_items: [{ description: "Enviar proposta", owner: "Ana", due_date: "2026-08-01" }],
        issues: [],
        dependencies: ["Aprovação jurídica"],
      },
    },
  };

  it("ActionsPanel renders action items", () => {
    mockedLatest.mockReturnValue(summaryState({ data: meetingData }));
    render(<ActionsPanel projectName="Aurora" />);
    expect(screen.getByText("Enviar proposta")).toBeInTheDocument();
    expect(screen.getByText(/Ana/)).toBeInTheDocument();
  });

  it("DecisionsPanel renders decisions and dependencies from the same payload", () => {
    mockedLatest.mockReturnValue(summaryState({ data: meetingData }));
    render(<DecisionsPanel projectName="Aurora" />);
    expect(screen.getByText("Decisão A")).toBeInTheDocument();
    expect(screen.getByText("Aprovação jurídica")).toBeInTheDocument();
  });
});

describe("RecommendationsPanel (Painel C, 'status')", () => {
  it("renders recommendations verbatim", () => {
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 3,
          kind: "status",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          payload: {
            agent: "project_status",
            project_name: "Aurora",
            model_output: { structured: true, health_status: "yellow", key_findings: [], recommendations: ["Revisar cronograma"] },
          },
        },
      }),
    );
    render(<RecommendationsPanel projectName="Aurora" />);
    expect(screen.getByText("Revisar cronograma")).toBeInTheDocument();
  });
});
