import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AnalyzeProjectDialog } from "./analyze-project-dialog";
import { useSubmitProjectStatus } from "@/lib/hooks/use-submit-project-status";
import { useSubmitRiskReview } from "@/lib/hooks/use-submit-risk-review";
import { useSubmitMeetingIntelligence } from "@/lib/hooks/use-submit-meeting-intelligence";
import { WorkspaceFetchError } from "@/lib/hooks/workspace-fetch-error";

vi.mock("@/lib/hooks/use-submit-project-status", () => ({
  useSubmitProjectStatus: vi.fn(),
}));
vi.mock("@/lib/hooks/use-submit-risk-review", () => ({
  useSubmitRiskReview: vi.fn(),
}));
vi.mock("@/lib/hooks/use-submit-meeting-intelligence", () => ({
  useSubmitMeetingIntelligence: vi.fn(),
}));

vi.mock("sonner", () => ({ toast: vi.fn() }));

const mockedSubmitStatus = vi.mocked(useSubmitProjectStatus);
const mockedSubmitRisk = vi.mocked(useSubmitRiskReview);
const mockedSubmitMeeting = vi.mocked(useSubmitMeetingIntelligence);

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

const TAB_STATUS = "Como está o projeto?";
const TAB_RISK = "Quais riscos exigem atenção?";
const TAB_MEETING = "O que mudou na última reunião?";

describe("AnalyzeProjectDialog", () => {
  beforeEach(() => {
    mockedSubmitStatus.mockReturnValue(baseMutation());
    mockedSubmitRisk.mockReturnValue(baseMutation());
    mockedSubmitMeeting.mockReturnValue(baseMutation());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses goal-oriented questions, never a technical or agent name, as primary UI copy", async () => {
    render(<AnalyzeProjectDialog projectName="Aurora" />);

    const trigger = screen.getByRole("button", { name: "Analisar Projeto" });
    expect(trigger).toBeInTheDocument();
    expect(screen.queryByText("project_status", { exact: false })).not.toBeInTheDocument();
    expect(screen.queryByText("risk_review", { exact: false })).not.toBeInTheDocument();
    expect(screen.queryByText("meeting_intelligence", { exact: false })).not.toBeInTheDocument();
    expect(screen.queryByText("transcript", { exact: false })).not.toBeInTheDocument();

    await userEvent.click(trigger);
    expect(screen.getByText("O que você quer entender sobre este projeto?")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: TAB_STATUS })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: TAB_RISK })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: TAB_MEETING })).toBeInTheDocument();
  });

  it("defaults to the first catalog entry and switches on tab click", async () => {
    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));

    expect(screen.getByRole("tab", { name: TAB_STATUS })).toHaveAttribute("aria-selected", "true");

    await userEvent.click(screen.getByRole("tab", { name: TAB_RISK }));
    expect(screen.getByRole("tab", { name: TAB_RISK })).toHaveAttribute("aria-selected", "true");
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
    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));

    const textarea = screen.getByLabelText("Contexto do projeto");
    await userEvent.type(textarea, LONG_ENOUGH);

    expect(screen.getByText("Backend respondeu 500.")).toBeInTheDocument();
    expect(textarea).toHaveValue(LONG_ENOUGH);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("closes the modal and previews the verdict via toast on success for 'Como está o projeto?' (Decision Momentum)", async () => {
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

  it("falls back to a mute confirmation when the status response is unstructured", async () => {
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

  it("switching to 'Quais riscos exigem atenção?' submits via useSubmitRiskReview and previews the attention count", async () => {
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
    await userEvent.click(screen.getByRole("tab", { name: TAB_RISK }));
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
    mockedSubmitRisk.mockReturnValue(baseMutation({ mutate: riskMutate }));

    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));
    await userEvent.click(screen.getByRole("tab", { name: TAB_RISK }));
    await userEvent.type(screen.getByLabelText("Contexto do projeto"), LONG_ENOUGH);
    await userEvent.click(screen.getByRole("button", { name: "Executar Análise" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(toast).toHaveBeenCalledWith(
      "Análise concluída",
      expect.objectContaining({ description: 'Avaliação de Riscos de "Aurora" atualizada.' }),
    );
  });

  it("switching to 'O que mudou na última reunião?' shows the meeting-specific context label and placeholder", async () => {
    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));
    await userEvent.click(screen.getByRole("tab", { name: TAB_MEETING }));

    expect(screen.getByLabelText("Contexto da reunião")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Cole a ata, notas ou transcrição da reunião..."),
    ).toBeInTheDocument();
  });

  it("submits the meeting tab via useSubmitMeetingIntelligence and previews the real impact headline", async () => {
    const { toast } = await import("sonner");
    const response = {
      agent: "meeting_intelligence",
      project_name: "Aurora",
      model_output: {
        structured: true,
        summary: "resumo",
        decisions: ["Decisão A"],
        action_items: [{ description: "Enviar proposta", owner: "Ana", due_date: null }],
        issues: ["Atraso no fornecedor"],
        dependencies: [],
      },
    };
    const statusMutate = vi.fn();
    const meetingMutate = vi.fn(
      (_context: string, options?: { onSuccess?: (data: typeof response) => void }) => {
        options?.onSuccess?.(response);
      },
    );
    mockedSubmitStatus.mockReturnValue(baseMutation({ mutate: statusMutate }));
    mockedSubmitMeeting.mockReturnValue(baseMutation({ mutate: meetingMutate }));

    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));
    await userEvent.click(screen.getByRole("tab", { name: TAB_MEETING }));
    await userEvent.type(screen.getByLabelText("Contexto da reunião"), LONG_ENOUGH);
    await userEvent.click(screen.getByRole("button", { name: "Executar Análise" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(meetingMutate).toHaveBeenCalled();
    expect(statusMutate).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(
      "Análise concluída",
      expect.objectContaining({
        description: 'Comunicação de "Aurora": 1 decisão(ões) · 1 ponto(s) de atenção · 1 responsabilidade(s).',
      }),
    );
  });

  it("falls back to a mute confirmation on the meeting tab when structured=true but the shape doesn't match MeetingModelOutput", async () => {
    const { toast } = await import("sonner");
    const response = {
      agent: "meeting_intelligence",
      project_name: "Aurora",
      model_output: { structured: true, health_status: "green", key_findings: [], recommendations: [] },
    };
    const meetingMutate = vi.fn(
      (_context: string, options?: { onSuccess?: (data: typeof response) => void }) => {
        options?.onSuccess?.(response);
      },
    );
    mockedSubmitMeeting.mockReturnValue(baseMutation({ mutate: meetingMutate }));

    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));
    await userEvent.click(screen.getByRole("tab", { name: TAB_MEETING }));
    await userEvent.type(screen.getByLabelText("Contexto da reunião"), LONG_ENOUGH);
    await userEvent.click(screen.getByRole("button", { name: "Executar Análise" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(toast).toHaveBeenCalledWith(
      "Análise concluída",
      expect.objectContaining({ description: 'Comunicação de "Aurora" atualizada.' }),
    );
  });
});
