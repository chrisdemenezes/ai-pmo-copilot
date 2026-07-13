import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AnalyzeProjectDialog } from "./analyze-project-dialog";
import { useSubmitProjectStatus } from "@/lib/hooks/use-submit-project-status";
import { useSubmitRiskReview } from "@/lib/hooks/use-submit-risk-review";
import { WorkspaceFetchError } from "@/lib/hooks/workspace-fetch-error";

vi.mock("@/lib/hooks/use-submit-project-status", () => ({
  useSubmitProjectStatus: vi.fn(),
}));
vi.mock("@/lib/hooks/use-submit-risk-review", () => ({
  useSubmitRiskReview: vi.fn(),
}));

vi.mock("sonner", () => ({ toast: vi.fn() }));

const mockedSubmitStatus = vi.mocked(useSubmitProjectStatus);
const mockedSubmitRisk = vi.mocked(useSubmitRiskReview);

function baseMutation(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    mutate: vi.fn(),
    reset: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
    ...overrides,
  } as never;
}

const LONG_ENOUGH = "contexto valido com mais de dez caracteres";

describe("AnalyzeProjectDialog", () => {
  beforeEach(() => {
    mockedSubmitStatus.mockReturnValue(baseMutation());
    mockedSubmitRisk.mockReturnValue(baseMutation());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses goal-oriented language, never the technical agent name, as primary UI copy", async () => {
    render(<AnalyzeProjectDialog projectName="Aurora" />);

    const trigger = screen.getByRole("button", { name: "Analisar Projeto" });
    expect(trigger).toBeInTheDocument();
    expect(screen.queryByText("project_status", { exact: false })).not.toBeInTheDocument();
    expect(screen.queryByText("risk_review", { exact: false })).not.toBeInTheDocument();

    await userEvent.click(trigger);
    expect(screen.getByRole("tab", { name: "Status Executivo" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Avaliação de Riscos" })).toBeInTheDocument();
  });

  it("defaults to the first catalog entry (Status Executivo) and switches on tab click", async () => {
    mockedSubmitStatus.mockReturnValue(baseMutation());
    mockedSubmitRisk.mockReturnValue(baseMutation());
    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));

    expect(screen.getByRole("tab", { name: "Status Executivo" })).toHaveAttribute(
      "aria-selected",
      "true",
    );

    await userEvent.click(screen.getByRole("tab", { name: "Avaliação de Riscos" }));
    expect(screen.getByRole("tab", { name: "Avaliação de Riscos" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("keeps the submit button disabled below the 10-character minimum", async () => {
    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));

    const submit = screen.getByRole("button", { name: "Executar Análise" });
    expect(submit).toBeDisabled();

    await userEvent.type(screen.getByLabelText("Contexto do projeto"), "curto");
    expect(submit).toBeDisabled();
  });

  it("enables submission once the context clears the minimum length", async () => {
    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));

    await userEvent.type(screen.getByLabelText("Contexto do projeto"), LONG_ENOUGH);
    expect(screen.getByRole("button", { name: "Executar Análise" })).toBeEnabled();
  });

  it("shows a loading state and disables the field while the active tab's mutation is pending", async () => {
    mockedSubmitStatus.mockReturnValue(baseMutation({ isPending: true }));
    mockedSubmitRisk.mockReturnValue(baseMutation());
    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));

    expect(screen.getByRole("button", { name: "Executando…" })).toBeDisabled();
    expect(screen.getByLabelText("Contexto do projeto")).toBeDisabled();
  });

  it("keeps the modal open and preserves the typed text when submission fails", async () => {
    const mutate = vi.fn();
    mockedSubmitStatus.mockReturnValue(
      baseMutation({
        mutate,
        isError: true,
        error: new WorkspaceFetchError({ error: "backend_error", detail: "Backend respondeu 500." }),
      }),
    );
    mockedSubmitRisk.mockReturnValue(baseMutation());
    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));

    const textarea = screen.getByLabelText("Contexto do projeto");
    await userEvent.type(textarea, LONG_ENOUGH);

    expect(screen.getByText("Backend respondeu 500.")).toBeInTheDocument();
    expect(textarea).toHaveValue(LONG_ENOUGH);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("closes the modal and previews the verdict via toast on success for Status Executivo (Decision Momentum, Rev. 2)", async () => {
    const { toast } = await import("sonner");
    const response = {
      agent: "project_status",
      project_name: "Aurora",
      model_output: { structured: true, health_status: "yellow", key_findings: [], recommendations: [] },
    };
    const mutate = vi.fn(
      (_context: string, options?: { onSuccess?: (data: typeof response) => void }) => {
        options?.onSuccess?.(response);
      },
    );
    mockedSubmitStatus.mockReturnValue(baseMutation({ mutate }));
    mockedSubmitRisk.mockReturnValue(baseMutation());

    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));
    await userEvent.type(screen.getByLabelText("Contexto do projeto"), LONG_ENOUGH);
    await userEvent.click(screen.getByRole("button", { name: "Executar Análise" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(toast).toHaveBeenCalledWith(
      "Análise concluída",
      expect.objectContaining({ description: 'Status Executivo de "Aurora": Atenção.' }),
    );
  });

  it("falls back to a mute confirmation when the Status Executivo response is unstructured", async () => {
    const { toast } = await import("sonner");
    const response = {
      agent: "project_status",
      project_name: "Aurora",
      model_output: { structured: false, raw_output: "not json" },
    };
    const mutate = vi.fn(
      (_context: string, options?: { onSuccess?: (data: typeof response) => void }) => {
        options?.onSuccess?.(response);
      },
    );
    mockedSubmitStatus.mockReturnValue(baseMutation({ mutate }));
    mockedSubmitRisk.mockReturnValue(baseMutation());

    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));
    await userEvent.type(screen.getByLabelText("Contexto do projeto"), LONG_ENOUGH);
    await userEvent.click(screen.getByRole("button", { name: "Executar Análise" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(toast).toHaveBeenCalledWith(
      "Análise concluída",
      expect.objectContaining({ description: 'Status Executivo de "Aurora" atualizado.' }),
    );
  });

  it("falls back to a mute confirmation when structured=true but the shape doesn't match StatusModelOutput (TIP-006)", async () => {
    const { toast } = await import("sonner");
    // Real Demo Mode failure mode: structured JSON, wrong agent's schema.
    const response = {
      agent: "project_status",
      project_name: "Aurora",
      model_output: { structured: true, risks: [], escalation_recommendation: null },
    };
    const mutate = vi.fn(
      (_context: string, options?: { onSuccess?: (data: typeof response) => void }) => {
        options?.onSuccess?.(response);
      },
    );
    mockedSubmitStatus.mockReturnValue(baseMutation({ mutate }));
    mockedSubmitRisk.mockReturnValue(baseMutation());

    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));
    await userEvent.type(screen.getByLabelText("Contexto do projeto"), LONG_ENOUGH);
    await userEvent.click(screen.getByRole("button", { name: "Executar Análise" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(toast).toHaveBeenCalledWith(
      "Análise concluída",
      expect.objectContaining({ description: 'Status Executivo de "Aurora" atualizado.' }),
    );
  });

  it("switching to Avaliação de Riscos submits via useSubmitRiskReview and previews the attention count", async () => {
    const { toast } = await import("sonner");
    const response = {
      agent: "risk_review",
      project_name: "Aurora",
      model_output: {
        structured: true,
        risks: [
          { description: "Atraso", probability: "high", impact: "high", mitigation: "Plano B" },
          { description: "Custo", probability: "low", impact: "low", mitigation: "Monitorar" },
        ],
        escalation_recommendation: "Escalar ao sponsor",
      },
    };
    const statusMutate = vi.fn();
    const riskMutate = vi.fn(
      (_context: string, options?: { onSuccess?: (data: typeof response) => void }) => {
        options?.onSuccess?.(response);
      },
    );
    mockedSubmitStatus.mockReturnValue(baseMutation({ mutate: statusMutate }));
    mockedSubmitRisk.mockReturnValue(baseMutation({ mutate: riskMutate }));

    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));
    await userEvent.click(screen.getByRole("tab", { name: "Avaliação de Riscos" }));
    await userEvent.type(screen.getByLabelText("Contexto do projeto"), LONG_ENOUGH);
    await userEvent.click(screen.getByRole("button", { name: "Executar Análise" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(riskMutate).toHaveBeenCalled();
    expect(statusMutate).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(
      "Análise concluída",
      expect.objectContaining({ description: 'Avaliação de Riscos de "Aurora": 1 risco(s) exigem atenção.' }),
    );
  });

  it("falls back to a mute confirmation on the risk tab when structured=true but the shape doesn't match RiskModelOutput (TIP-006)", async () => {
    const { toast } = await import("sonner");
    // Real Demo Mode failure mode: structured JSON, wrong agent's schema.
    const response = {
      agent: "risk_review",
      project_name: "Aurora",
      model_output: { structured: true, health_status: "green", key_findings: [], recommendations: [] },
    };
    const riskMutate = vi.fn(
      (_context: string, options?: { onSuccess?: (data: typeof response) => void }) => {
        options?.onSuccess?.(response);
      },
    );
    mockedSubmitStatus.mockReturnValue(baseMutation());
    mockedSubmitRisk.mockReturnValue(baseMutation({ mutate: riskMutate }));

    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));
    await userEvent.click(screen.getByRole("tab", { name: "Avaliação de Riscos" }));
    await userEvent.type(screen.getByLabelText("Contexto do projeto"), LONG_ENOUGH);
    await userEvent.click(screen.getByRole("button", { name: "Executar Análise" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(toast).toHaveBeenCalledWith(
      "Análise concluída",
      expect.objectContaining({ description: 'Avaliação de Riscos de "Aurora" atualizada.' }),
    );
  });
});
