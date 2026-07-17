import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import ActionsPage from "./page";
import { useActionItems } from "@/lib/hooks/use-action-items";
import type { ActionItemView } from "@/lib/workspace/types";

vi.mock("@/lib/hooks/use-action-items", () => ({ useActionItems: vi.fn() }));
// ActionItemsList monta o AnalysisDetailDialog (drill-down de origem).
vi.mock("@/lib/hooks/use-workspace-analysis-detail", () => ({
  useWorkspaceAnalysisDetail: vi.fn().mockReturnValue({
    isPending: true,
    isError: false,
    data: undefined,
  }),
}));

const mockedHook = vi.mocked(useActionItems);

function daysFromNow(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString();
}

const MULTI_PROJECT_ITEMS: ActionItemView[] = [
  {
    project_name: "Aurora",
    description: "Cobrar plano de contingência do fornecedor",
    owner: "Bruno",
    due_date: daysFromNow(-3),
    source_analysis_id: 204,
    source_created_at: "2026-07-05T10:00:00Z",
  },
  {
    project_name: "Implantacao SAP S/4HANA",
    description: "Validar plano de cutover com o cliente",
    owner: "Carla",
    due_date: daysFromNow(1),
    source_analysis_id: 302,
    source_created_at: "2026-07-06T09:00:00Z",
  },
];

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

describe("ActionsPage (portfólio)", () => {
  it("asks the hook for the portfolio view -- no projectName", () => {
    mockedHook.mockReturnValue(hookState({ isPending: true }));
    render(<ActionsPage />);
    expect(mockedHook).toHaveBeenCalledWith();
  });

  it("renders the skeleton while pending", () => {
    mockedHook.mockReturnValue(hookState({ isPending: true }));
    const { container } = render(<ActionsPage />);
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
  });

  it("renders the empty state when no meeting produced action items yet", () => {
    mockedHook.mockReturnValue(hookState({ data: [] }));
    render(<ActionsPage />);
    expect(screen.getByText("Nenhuma ação registrada em reuniões ainda")).toBeInTheDocument();
  });

  it("throws to the error boundary when the first load fails", () => {
    const error = new Error("Backend respondeu 500.");
    mockedHook.mockReturnValue(hookState({ isError: true, error }));
    // Suprime o log do React para o throw esperado.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<ActionsPage />)).toThrow("Backend respondeu 500.");
    spy.mockRestore();
  });

  it("groups items from multiple projects by urgency, project visible on each card", () => {
    mockedHook.mockReturnValue(hookState({ data: MULTI_PROJECT_ITEMS }));
    render(<ActionsPage />);

    expect(screen.getByText("1 atrasada(s) · 1 vence(m) em breve")).toBeInTheDocument();
    expect(screen.getByText("Atrasado")).toBeInTheDocument();
    expect(screen.getByText("Vence em breve")).toBeInTheDocument();
    // O item mais urgente do portfólio inteiro destacado no topo, como texto.
    expect(screen.getByText("Próxima ação sugerida")).toBeInTheDocument();
    expect(screen.getAllByText(/Cobrar plano de contingência/).length).toBeGreaterThan(0);
    expect(screen.getByText("Validar plano de cutover com o cliente")).toBeInTheDocument();
    expect(screen.getByText("Aurora")).toBeInTheDocument();
    expect(screen.getByText("Implantacao SAP S/4HANA")).toBeInTheDocument();
  });

  it("never renders a create/edit/assign control", () => {
    mockedHook.mockReturnValue(hookState({ data: MULTI_PROJECT_ITEMS }));
    render(<ActionsPage />);
    for (const forbidden of [/criar/i, /editar/i, /atribuir/i, /concluir/i, /nova ação/i]) {
      expect(screen.queryByRole("button", { name: forbidden })).toBeNull();
    }
  });
});
