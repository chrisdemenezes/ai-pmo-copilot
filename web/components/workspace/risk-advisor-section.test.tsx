import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { RiskAdvisorSection } from "./risk-advisor-section";
import { useAskRiskAdvisor } from "@/lib/hooks/use-ask-risk-advisor";

vi.mock("@/lib/hooks/use-ask-risk-advisor", () => ({ useAskRiskAdvisor: vi.fn() }));

const mockedUseAskRiskAdvisor = vi.mocked(useAskRiskAdvisor);

function baseMutation(overrides: Record<string, unknown> = {}) {
  return {
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    data: undefined,
    error: undefined,
    ...overrides,
  };
}

describe("RiskAdvisorSection", () => {
  it("disables the Perguntar button until at least 3 characters are typed", async () => {
    mockedUseAskRiskAdvisor.mockReturnValue(baseMutation() as never);
    render(<RiskAdvisorSection projectName="Aurora" />);

    const button = screen.getByRole("button", { name: "Perguntar" });
    expect(button).toBeDisabled();

    await userEvent.type(screen.getByLabelText("Pergunta para o Risk Advisor"), "Oi");
    expect(button).toBeDisabled();

    await userEvent.type(screen.getByLabelText("Pergunta para o Risk Advisor"), " tudo bem?");
    expect(button).toBeEnabled();
  });

  it("calls mutate with the typed question when Perguntar is clicked", async () => {
    const mutate = vi.fn();
    mockedUseAskRiskAdvisor.mockReturnValue(baseMutation({ mutate }) as never);
    render(<RiskAdvisorSection projectName="Aurora" />);

    await userEvent.type(
      screen.getByLabelText("Pergunta para o Risk Advisor"),
      "Qual o risco mais crítico?",
    );
    await userEvent.click(screen.getByRole("button", { name: "Perguntar" }));

    expect(mutate).toHaveBeenCalledWith(
      "Qual o risco mais crítico?",
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });

  it("shows the answer and its citations on success", () => {
    mockedUseAskRiskAdvisor.mockReturnValue(
      baseMutation({
        isSuccess: true,
        data: {
          answer: "O risco mais crítico é o atraso no fornecedor de middleware.",
          cited_analyses: [{ source_analysis_id: 7, source_created_at: "2026-07-10T14:00:00Z" }],
        },
      }) as never,
    );
    render(<RiskAdvisorSection projectName="Aurora" />);

    expect(
      screen.getByText("O risco mais crítico é o atraso no fornecedor de middleware."),
    ).toBeInTheDocument();
    expect(screen.getByText("Baseado em")).toBeInTheDocument();
  });

  it("shows an error message when the question fails", () => {
    mockedUseAskRiskAdvisor.mockReturnValue(
      baseMutation({ isError: true, error: new Error("Backend respondeu 500.") }) as never,
    );
    render(<RiskAdvisorSection projectName="Aurora" />);

    expect(screen.getByText("Backend respondeu 500.")).toBeInTheDocument();
  });

  it("disables the textarea and button while pending", () => {
    mockedUseAskRiskAdvisor.mockReturnValue(baseMutation({ isPending: true }) as never);
    render(<RiskAdvisorSection projectName="Aurora" />);

    expect(screen.getByLabelText("Pergunta para o Risk Advisor")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Perguntando..." })).toBeDisabled();
  });
});
