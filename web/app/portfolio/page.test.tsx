import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import PortfolioPage from "./page";
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
    project_name: "Portal do Cliente 2.0",
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

describe("PortfolioPage", () => {
  it("renders the skeleton while pending", () => {
    mockedHook.mockReturnValue(hookState({ isPending: true }));
    const { container } = render(<PortfolioPage />);
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
  });

  it("throws to the error boundary when the first load fails", () => {
    const error = new Error("Backend respondeu 500.");
    mockedHook.mockReturnValue(hookState({ isError: true, error }));
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<PortfolioPage />)).toThrow("Backend respondeu 500.");
    spy.mockRestore();
  });

  it("renders the empty state when the portfolio has no projects", () => {
    mockedHook.mockReturnValue(hookState({ data: [] }));
    render(<PortfolioPage />);
    expect(screen.getByText("Nenhum projeto com análise registrada ainda")).toBeInTheDocument();
  });

  it("covers the whole portfolio -- every project appears, not only the ones with a pending decision", () => {
    mockedHook.mockReturnValue(hookState({ data: MIXED_PORTFOLIO }));
    render(<PortfolioPage />);

    expect(screen.getByRole("heading", { name: "Implantacao SAP S/4HANA" })).toBeInTheDocument();
    // "Portal do Cliente 2.0" has no pending decision -- discreet form (no heading role), but still present.
    expect(screen.getByText("Portal do Cliente 2.0")).toBeInTheDocument();
  });

  // Incremento 2 -- camada de Risco a Monitorar: um projeto saudável com
  // risco identificado, mas sem decisão pendente, aparece nesta camada.
  it("shows a project with open_risks but no pending decision in the risk_to_monitor layer", () => {
    mockedHook.mockReturnValue(
      hookState({
        data: [
          {
            project_name: "Migracao de Data Center",
            total_analyses: 2,
            open_risks: 2,
            pending_action_items: 0,
            latest_health_status: "green",
          },
        ],
      }),
    );

    render(<PortfolioPage />);
    expect(screen.getByText("Por que este projeto merece acompanhamento?")).toBeInTheDocument();
    expect(screen.getByText("2 risco(s) identificado(s)")).toBeInTheDocument();
  });

  it("never renders a create/edit/resolve control", () => {
    mockedHook.mockReturnValue(hookState({ data: MIXED_PORTFOLIO }));
    render(<PortfolioPage />);
    for (const forbidden of [/criar/i, /editar/i, /resolver/i, /nova prioridade/i]) {
      expect(screen.queryByRole("button", { name: forbidden })).toBeNull();
    }
  });

  it("waits for both Status and Risco to resolve before rendering (Executive Trust)", () => {
    mockedHook.mockReturnValue(hookState({ data: MIXED_PORTFOLIO }));
    mockedRisks.mockReturnValue(hookState({ isPending: true, data: undefined }) as never);

    const { container } = render(<PortfolioPage />);
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);

    mockedRisks.mockReturnValue(hookState({ data: [] }) as never);
  });

  it("shows a degraded but honest message when Risco fails, without blocking Status-derived layers", () => {
    mockedHook.mockReturnValue(hookState({ data: MIXED_PORTFOLIO }));
    mockedRisks.mockReturnValue(hookState({ isError: true, data: undefined }) as never);

    render(<PortfolioPage />);
    expect(
      screen.getByText("Não foi possível carregar os riscos -- mostrando apenas o sinal de Status."),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Implantacao SAP S/4HANA" })).toBeInTheDocument();

    mockedRisks.mockReturnValue(hookState({ data: [] }) as never);
  });
});
