import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import DashboardPage from "./page";
import { usePortfolioSummary } from "@/lib/hooks/use-portfolio-summary";

vi.mock("@/lib/hooks/use-portfolio-summary", () => ({
  usePortfolioSummary: vi.fn(),
}));

const mockedHook = vi.mocked(usePortfolioSummary);

describe("DashboardPage", () => {
  it("renders the skeleton while pending", () => {
    mockedHook.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(<DashboardPage />);
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
  });

  it("renders the empty state when the portfolio has no projects", () => {
    mockedHook.mockReturnValue({
      isPending: false,
      isError: false,
      data: [],
      error: null,
      refetch: vi.fn(),
      isFetching: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<DashboardPage />);
    expect(
      screen.getByText("Nenhum projeto com análise registrada ainda"),
    ).toBeInTheDocument();
  });

  it("renders the widgets when the portfolio has projects", () => {
    mockedHook.mockReturnValue({
      isPending: false,
      isError: false,
      data: [
        {
          project_name: "Multilift",
          total_analyses: 5,
          open_risks: 3,
          pending_action_items: 2,
          latest_health_status: "red",
        },
      ],
      error: null,
      refetch: vi.fn(),
      isFetching: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<DashboardPage />);
    // Appears in both the Project Health Grid and the Risk Concentration Ranking.
    expect(screen.getAllByText("Multilift").length).toBeGreaterThan(0);
    // "Projetos" appears both as the strip label and the grid section heading.
    expect(screen.getAllByText("Projetos").length).toBeGreaterThan(0);
  });

  it("throws the query error when there is no cached data to fall back to", () => {
    mockedHook.mockReturnValue({
      isPending: false,
      isError: true,
      data: undefined,
      error: new Error("Backend respondeu 500."),
      refetch: vi.fn(),
      isFetching: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    expect(() => render(<DashboardPage />)).toThrow("Backend respondeu 500.");
  });

  it("keeps rendering cached data when a background refetch fails (Achado #1 fix)", () => {
    mockedHook.mockReturnValue({
      isPending: false,
      isError: true,
      data: [
        {
          project_name: "Multilift",
          total_analyses: 5,
          open_risks: 3,
          pending_action_items: 2,
          latest_health_status: "red",
        },
      ],
      error: new Error("Backend respondeu 500."),
      refetch: vi.fn(),
      isFetching: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    expect(() => render(<DashboardPage />)).not.toThrow();
    expect(screen.getAllByText("Multilift").length).toBeGreaterThan(0);
  });
});
