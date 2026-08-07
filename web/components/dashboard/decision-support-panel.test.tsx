import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { DecisionSupportPanel } from "./decision-support-panel";
import { usePortfolios } from "@/lib/hooks/use-portfolios";
import { useProjects } from "@/lib/hooks/use-projects";
import { useAskDecisionSupport } from "@/lib/hooks/use-ask-decision-support";

vi.mock("@/lib/hooks/use-portfolios", () => ({ usePortfolios: vi.fn() }));
vi.mock("@/lib/hooks/use-projects", () => ({ useProjects: vi.fn() }));
vi.mock("@/lib/hooks/use-ask-decision-support", async () => {
  const actual = await vi.importActual<typeof import("@/lib/hooks/use-ask-decision-support")>(
    "@/lib/hooks/use-ask-decision-support",
  );
  return { ...actual, useAskDecisionSupport: vi.fn() };
});

const mockedPortfolios = vi.mocked(usePortfolios);
const mockedProjects = vi.mocked(useProjects);
const mockedMutation = vi.mocked(useAskDecisionSupport);

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

describe("DecisionSupportPanel", () => {
  beforeEach(() => {
    mockedPortfolios.mockReturnValue(emptyQueryState());
    mockedProjects.mockReturnValue(emptyQueryState());
  });

  it("disables the submit button until both a question and an explicit scope are provided", () => {
    mockedMutation.mockReturnValue(mutationState());
    render(<DecisionSupportPanel />);

    expect(screen.getByRole("button", { name: "Perguntar" })).toBeDisabled();
  });

  it("never pre-selects a scope -- the selector starts with a placeholder, not 'Organização'", () => {
    mockedMutation.mockReturnValue(mutationState());
    render(<DecisionSupportPanel />);

    expect(screen.getByRole("combobox", { name: "Escopo" })).toHaveTextContent("Escopo");
  });

  it("shows an explicit insufficient-basis message, never a blank answer", () => {
    mockedMutation.mockReturnValue(
      mutationState({
        data: {
          capability: "decision_support",
          insufficient_basis: true,
          insufficient_basis_reason: "selection_empty",
          answer: null,
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
    render(<DecisionSupportPanel />);

    expect(screen.getByRole("status")).toHaveTextContent("Base insuficiente");
  });

  it("renders the synthesis, advisors used, and citations for a complete result", () => {
    mockedMutation.mockReturnValue(
      mutationState({
        data: {
          capability: "decision_support",
          insufficient_basis: false,
          insufficient_basis_reason: null,
          answer: "Existe risco de escalação e a entrega está em andamento.",
          advisors_used: ["risk_advisor", "delivery_advisor"],
          citations: [
            { advisor_name: "risk_advisor", source_type: "analysis_record", source_id: 7, source_label: "Risk 7" },
          ],
          composition_trace: {
            selection_signals: ["risco"],
            selected_advisor_names: ["risk_advisor", "delivery_advisor"],
            advisors_used: [],
            correlations: [],
            synthesis_source_advisor_names: ["risk_advisor", "delivery_advisor"],
          },
        },
      }),
    );
    render(<DecisionSupportPanel />);

    expect(screen.getByText("Existe risco de escalação e a entrega está em andamento.")).toBeInTheDocument();
    expect(screen.getByText("risk_advisor")).toBeInTheDocument();
    expect(screen.getByText("delivery_advisor")).toBeInTheDocument();
    expect(screen.getByText(/Risk 7/)).toBeInTheDocument();
  });

  it("surfaces the error detail on failure", () => {
    mockedMutation.mockReturnValue(
      mutationState({ isError: true, error: new Error("Projeto ou portfólio não encontrado.") }),
    );
    render(<DecisionSupportPanel />);

    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível obter uma resposta agora.");
  });
});
