import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { ExecutiveNarrativePanel } from "./executive-narrative-panel";
import { usePortfolios } from "@/lib/hooks/use-portfolios";
import { useProjects } from "@/lib/hooks/use-projects";
import { useGenerateExecutiveNarrative } from "@/lib/hooks/use-generate-executive-narrative";

vi.mock("@/lib/hooks/use-portfolios", () => ({ usePortfolios: vi.fn() }));
vi.mock("@/lib/hooks/use-projects", () => ({ useProjects: vi.fn() }));
vi.mock("@/lib/hooks/use-generate-executive-narrative", async () => {
  const actual = await vi.importActual<typeof import("@/lib/hooks/use-generate-executive-narrative")>(
    "@/lib/hooks/use-generate-executive-narrative",
  );
  return { ...actual, useGenerateExecutiveNarrative: vi.fn() };
});

const mockedPortfolios = vi.mocked(usePortfolios);
const mockedProjects = vi.mocked(useProjects);
const mockedMutation = vi.mocked(useGenerateExecutiveNarrative);

function emptyQueryState() {
  return {
    isPending: false,
    isError: false,
    data: [],
    error: null,
    refetch: vi.fn(),
    isFetching: false,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any;
}

function mutationState(overrides: Record<string, unknown> = {}) {
  return {
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    data: undefined,
    error: null,
    ...overrides,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any;
}

describe("ExecutiveNarrativePanel", () => {
  beforeEach(() => {
    mockedPortfolios.mockReturnValue(emptyQueryState());
    mockedProjects.mockReturnValue(emptyQueryState());
  });

  it("never renders a free-text question field -- only the scope selector (Technical Design §2)", () => {
    mockedMutation.mockReturnValue(mutationState());
    render(<ExecutiveNarrativePanel />);

    expect(screen.queryByLabelText("Pergunta executiva")).not.toBeInTheDocument();
  });

  it("disables the submit button until an explicit scope is provided", () => {
    mockedMutation.mockReturnValue(mutationState());
    render(<ExecutiveNarrativePanel />);

    expect(screen.getByRole("button", { name: "Gerar Narrativa" })).toBeDisabled();
  });

  it("never pre-selects a scope -- the selector starts with a placeholder, not 'Organização'", () => {
    mockedMutation.mockReturnValue(mutationState());
    render(<ExecutiveNarrativePanel />);

    expect(screen.getByRole("combobox", { name: "Escopo" })).toHaveTextContent("Escopo");
  });

  it("shows an explicit insufficient-basis message, never a blank narrative", () => {
    mockedMutation.mockReturnValue(
      mutationState({
        data: {
          capability: "executive_narrative",
          scope: { type: "organization", project_id: null, portfolio_id: null },
          insufficient_basis: true,
          insufficient_basis_reason: "collection_empty",
          narrative: null,
          advisors_used: [],
          citations: [],
          composition_trace: {
            selection_signals: [],
            selected_advisor_names: [],
            advisors_used: [],
            correlations: [],
            synthesis_source_advisor_names: null,
          },
        },
      }),
    );
    render(<ExecutiveNarrativePanel />);

    expect(screen.getByRole("status")).toHaveTextContent("Base insuficiente");
  });

  it("renders the narrative, advisors used, and citations for a complete result", () => {
    mockedMutation.mockReturnValue(
      mutationState({
        data: {
          capability: "executive_narrative",
          scope: { type: "project", project_id: 42, portfolio_id: null },
          insufficient_basis: false,
          insufficient_basis_reason: null,
          narrative: "Risco de escalação identificado; entrega em andamento.",
          advisors_used: ["risk_advisor", "delivery_advisor"],
          citations: [
            { advisor_name: "risk_advisor", source_type: "analysis_record", source_id: 7, source_label: "Risk 7" },
          ],
          composition_trace: {
            selection_signals: ["risk_advisor", "delivery_advisor"],
            selected_advisor_names: ["risk_advisor", "delivery_advisor"],
            advisors_used: [],
            correlations: [],
            synthesis_source_advisor_names: ["risk_advisor", "delivery_advisor"],
          },
        },
      }),
    );
    render(<ExecutiveNarrativePanel />);

    expect(screen.getByText("Risco de escalação identificado; entrega em andamento.")).toBeInTheDocument();
    expect(screen.getByText("risk_advisor")).toBeInTheDocument();
    expect(screen.getByText("delivery_advisor")).toBeInTheDocument();
    expect(screen.getByText(/Risk 7/)).toBeInTheDocument();
  });

  it("surfaces the error detail on failure", () => {
    mockedMutation.mockReturnValue(
      mutationState({ isError: true, error: new Error("Projeto ou portfólio não encontrado.") }),
    );
    render(<ExecutiveNarrativePanel />);

    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível gerar a narrativa agora.");
  });
});
