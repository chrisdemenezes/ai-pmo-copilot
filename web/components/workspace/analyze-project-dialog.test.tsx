import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AnalyzeProjectDialog } from "./analyze-project-dialog";
import { useSubmitProjectStatus } from "@/lib/hooks/use-submit-project-status";
import { WorkspaceFetchError } from "@/lib/hooks/workspace-fetch-error";

vi.mock("@/lib/hooks/use-submit-project-status", () => ({
  useSubmitProjectStatus: vi.fn(),
}));

vi.mock("sonner", () => ({ toast: vi.fn() }));

const mockedSubmit = vi.mocked(useSubmitProjectStatus);

function baseMutation(overrides: Partial<ReturnType<typeof useSubmitProjectStatus>> = {}) {
  return {
    mutate: vi.fn(),
    reset: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
    ...overrides,
  } as unknown as ReturnType<typeof useSubmitProjectStatus>;
}

const LONG_ENOUGH = "contexto valido com mais de dez caracteres";

describe("AnalyzeProjectDialog", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses goal-oriented language, never the technical agent name, as primary UI copy", async () => {
    mockedSubmit.mockReturnValue(baseMutation());
    render(<AnalyzeProjectDialog projectName="Aurora" />);

    const trigger = screen.getByRole("button", { name: "Analisar Projeto" });
    expect(trigger).toBeInTheDocument();
    expect(screen.queryByText("project_status", { exact: false })).not.toBeInTheDocument();

    await userEvent.click(trigger);
    expect(screen.getByText("Status Executivo")).toBeInTheDocument();
  });

  it("keeps the submit button disabled below the 10-character minimum", async () => {
    mockedSubmit.mockReturnValue(baseMutation());
    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));

    const submit = screen.getByRole("button", { name: "Executar Análise" });
    expect(submit).toBeDisabled();

    await userEvent.type(screen.getByLabelText("Contexto do projeto"), "curto");
    expect(submit).toBeDisabled();
  });

  it("enables submission once the context clears the minimum length", async () => {
    mockedSubmit.mockReturnValue(baseMutation());
    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));

    await userEvent.type(screen.getByLabelText("Contexto do projeto"), LONG_ENOUGH);
    expect(screen.getByRole("button", { name: "Executar Análise" })).toBeEnabled();
  });

  it("shows a loading state and disables the field while pending", async () => {
    mockedSubmit.mockReturnValue(baseMutation({ isPending: true }));
    render(<AnalyzeProjectDialog projectName="Aurora" />);
    await userEvent.click(screen.getByRole("button", { name: "Analisar Projeto" }));

    expect(screen.getByRole("button", { name: "Executando…" })).toBeDisabled();
    expect(screen.getByLabelText("Contexto do projeto")).toBeDisabled();
  });

  it("keeps the modal open and preserves the typed text when submission fails", async () => {
    const mutate = vi.fn();
    mockedSubmit.mockReturnValue(
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

  it("closes the modal and previews the verdict via toast on success (Decision Momentum, Rev. 2)", async () => {
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
    mockedSubmit.mockReturnValue(baseMutation({ mutate: mutate as never }));

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

  it("falls back to a mute confirmation when the response is unstructured", async () => {
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
    mockedSubmit.mockReturnValue(baseMutation({ mutate: mutate as never }));

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
});
