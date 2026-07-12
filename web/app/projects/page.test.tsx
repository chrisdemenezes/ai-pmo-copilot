import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ProjectsPage from "./page";
import { usePortfolioSummary } from "@/lib/hooks/use-portfolio-summary";

vi.mock("@/lib/hooks/use-portfolio-summary", () => ({
  usePortfolioSummary: vi.fn(),
}));

const mockedHook = vi.mocked(usePortfolioSummary);

const TWO_PROJECTS = [
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
    pending_action_items: 1,
    latest_health_status: "green",
  },
];

describe("ProjectsPage", () => {
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

    const { container } = render(<ProjectsPage />);
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

    render(<ProjectsPage />);
    expect(
      screen.getByText("Nenhum projeto com análise registrada ainda"),
    ).toBeInTheDocument();
  });

  it("renders the full list when the portfolio has projects", () => {
    mockedHook.mockReturnValue({
      isPending: false,
      isError: false,
      data: TWO_PROJECTS,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<ProjectsPage />);
    expect(screen.getAllByText("Multilift").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Aurora").length).toBeGreaterThan(0);
    expect(screen.getByText("2 de 2 projetos")).toBeInTheDocument();
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

    expect(() => render(<ProjectsPage />)).toThrow("Backend respondeu 500.");
  });

  it("keeps rendering cached data when a background refetch fails", () => {
    mockedHook.mockReturnValue({
      isPending: false,
      isError: true,
      data: TWO_PROJECTS,
      error: new Error("Backend respondeu 500."),
      refetch: vi.fn(),
      isFetching: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    expect(() => render(<ProjectsPage />)).not.toThrow();
    expect(screen.getAllByText("Multilift").length).toBeGreaterThan(0);
  });

  describe("busca client-side", () => {
    beforeEach(() => {
      mockedHook.mockReturnValue({
        isPending: false,
        isError: false,
        data: TWO_PROJECTS,
        error: null,
        refetch: vi.fn(),
        isFetching: false,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } as any);
    });

    it("filters the list by project name as the user types, case-insensitive", async () => {
      const user = userEvent.setup();
      render(<ProjectsPage />);

      await user.type(screen.getByLabelText("Buscar projeto"), "aurora");

      expect(screen.getAllByText("Aurora").length).toBeGreaterThan(0);
      expect(screen.queryByText("Multilift")).not.toBeInTheDocument();
      expect(screen.getByText("1 de 2 projetos")).toBeInTheDocument();
    });

    it("shows a distinct message (not the empty-portfolio message) when the search matches nothing", async () => {
      const user = userEvent.setup();
      render(<ProjectsPage />);

      await user.type(screen.getByLabelText("Buscar projeto"), "não existe");

      expect(
        screen.getByText('Nenhum projeto encontrado para "não existe"'),
      ).toBeInTheDocument();
      expect(
        screen.queryByText("Nenhum projeto com análise registrada ainda"),
      ).not.toBeInTheDocument();
    });
  });
});
