import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import DecisionsPage from "./page";
import { usePortfolioSummary } from "@/lib/hooks/use-portfolio-summary";
import type { ProjectSummary } from "@/lib/dashboard/types";

vi.mock("@/lib/hooks/use-portfolio-summary", () => ({
  usePortfolioSummary: vi.fn(),
}));

const mockedHook = vi.mocked(usePortfolioSummary);

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
