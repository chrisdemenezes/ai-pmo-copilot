import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import DecisionsPage from "./page";
import { usePortfolioSummary } from "@/lib/hooks/use-portfolio-summary";
import { useLatestRisks } from "@/lib/hooks/use-latest-risks";
import type { ProjectSummary } from "@/lib/dashboard/types";

vi.mock("@/lib/hooks/use-portfolio-summary", () => ({
  usePortfolioSummary: vi.fn(),
}));
vi.mock("@/lib/hooks/use-latest-risks", () => ({
  useLatestRisks: vi.fn(),
}));

const mockedHook = vi.mocked(usePortfolioSummary);
const mockedRisks = vi.mocked(useLatestRisks);
// Default: risks already resolved with no data -- most tests only care
// about the Status signal; override per-test to exercise Risco/erro/loading.
mockedRisks.mockReturnValue(hookState({ data: [] }) as never);

function hookState(overrides: Partial<Record<string, unknown>>) {
  return {
    isPending: false,
    isError: false,
    data: undefined,
    error: null,
    refetch: vi.fn(),
    isFetching: false,
    ...overrides,
  } as never;
}

const MIXED_PORTFOLIO: ProjectSummary[] = [
  {
    project_name: "Aurora",
    total_analyses: 2,
    open_risks: 0,
    pending_action_items: 1,
    latest_health_status: "green",
  },
  {
    project_name: "Implantacao SAP S/4HANA",
    total_analyses: 3,
    open_risks: 1,
    pending_action_items: 1,
    latest_health_status: "red",
  },
];

describe("DecisionsPage", () => {
  it("renders the skeleton while pending", () => {
    mockedHook.mockReturnValue(hookState({ isPending: true }));
    const { container } = render(<DecisionsPage />);
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
  });

  it("throws to the error boundary when the first load fails", () => {
    const error = new Error("Backend respondeu 500.");
    mockedHook.mockReturnValue(hookState({ isError: true, error }));
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<DecisionsPage />)).toThrow("Backend respondeu 500.");
    spy.mockRestore();
  });

  it("shows the affirmative empty state when no project needs a decision (Princípio de Atenção)", () => {
    mockedHook.mockReturnValue(
      hookState({
        data: [
          {
            project_name: "Aurora",
            total_analyses: 1,
            open_risks: 0,
            pending_action_items: 0,
            latest_health_status: "green",
          },
        ],
      }),
    );
    render(<DecisionsPage />);
    expect(screen.getByText("Nenhuma decisão pendente")).toBeInTheDocument();
    expect(screen.getByText("Todo o portfólio está no curso esperado.")).toBeInTheDocument();
  });

  it("renders a card only for the project that needs a decision", () => {
    mockedHook.mockReturnValue(hookState({ data: MIXED_PORTFOLIO }));
    render(<DecisionsPage />);

    expect(screen.getByRole("heading", { name: "Implantacao SAP S/4HANA" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Aurora" })).toBeNull();
    expect(screen.queryByText("Nenhuma decisão pendente")).toBeNull();
  });

  it("never renders a create/edit/resolve control", () => {
    mockedHook.mockReturnValue(hookState({ data: MIXED_PORTFOLIO }));
    render(<DecisionsPage />);
    for (const forbidden of [/criar/i, /editar/i, /resolver/i, /nova decisão/i]) {
      expect(screen.queryByRole("button", { name: forbidden })).toBeNull();
    }
  });
});

describe("DecisionsPage -- sinal de Risco (Incremento 2)", () => {
  const GREEN_PORTFOLIO: ProjectSummary[] = [
    {
      project_name: "Aurora",
      total_analyses: 1,
      open_risks: 1,
      pending_action_items: 0,
      latest_health_status: "green",
    },
  ];

  it("waits for both Status and Risco to resolve before rendering the empty state (Executive Trust)", () => {
    mockedHook.mockReturnValue(hookState({ data: GREEN_PORTFOLIO }));
    mockedRisks.mockReturnValue(hookState({ isPending: true, data: undefined }) as never);

    const { container } = render(<DecisionsPage />);
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
    expect(screen.queryByText("Nenhuma decisão pendente")).toBeNull();

    mockedRisks.mockReturnValue(hookState({ data: [] }) as never);
  });

  it("adds a risk-sourced card when a project has an attention-zone risk", () => {
    mockedHook.mockReturnValue(hookState({ data: GREEN_PORTFOLIO }));
    mockedRisks.mockReturnValue(
      hookState({
        data: [
          {
            project_name: "Aurora",
            description: "Atraso no fornecedor",
            probability: "high",
            impact: "high",
            mitigation: "Escalar",
            escalation_recommendation: null,
            source_analysis_id: 1,
            source_created_at: "2026-07-01T00:00:00Z",
          },
        ],
      }) as never,
    );

    render(<DecisionsPage />);
    expect(screen.getByRole("heading", { name: "Aurora" })).toBeInTheDocument();
    expect(screen.getByText("1 risco(s) na zona de atenção")).toBeInTheDocument();

    mockedRisks.mockReturnValue(hookState({ data: [] }) as never);
  });

  it("shows a degraded but honest message when Risco fails, without blocking Status decisions", () => {
    mockedHook.mockReturnValue(hookState({ data: MIXED_PORTFOLIO }));
    mockedRisks.mockReturnValue(hookState({ isError: true, data: undefined }) as never);

    render(<DecisionsPage />);
    expect(
      screen.getByText("Não foi possível carregar os riscos -- mostrando decisões de Status."),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Implantacao SAP S/4HANA" })).toBeInTheDocument();

    mockedRisks.mockReturnValue(hookState({ data: [] }) as never);
  });
});
