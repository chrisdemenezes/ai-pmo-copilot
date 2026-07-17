import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ActionItemsList, ActionsSection } from "./actions-section";
import { useActionItems } from "@/lib/hooks/use-action-items";
import { useWorkspaceAnalysisDetail } from "@/lib/hooks/use-workspace-analysis-detail";
import type { ActionItemView } from "@/lib/workspace/types";

vi.mock("@/lib/hooks/use-action-items", () => ({ useActionItems: vi.fn() }));
// AnalysisDetailDialog (drill-down para a análise de origem) chama este hook.
vi.mock("@/lib/hooks/use-workspace-analysis-detail", () => ({
  useWorkspaceAnalysisDetail: vi.fn(),
}));

const mockedActionItems = vi.mocked(useActionItems);
const mockedDetail = vi.mocked(useWorkspaceAnalysisDetail);
mockedDetail.mockReturnValue({ isPending: true, isError: false, data: undefined } as never);

const PENDING = { isPending: true, isError: false, data: undefined } as never;
const ERROR = { isPending: false, isError: true, data: undefined } as never;

function daysFromNow(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString();
}

function item(overrides: Partial<ActionItemView>): ActionItemView {
  return {
    project_name: "Aurora",
    description: "Atualizar cronograma",
    owner: "Ana",
    due_date: null,
    source_analysis_id: 202,
    source_created_at: "2026-07-09T10:00:00Z",
    ...overrides,
  };
}

const GROUPED_SAMPLE: ActionItemView[] = [
  item({ description: "Ação atrasada", due_date: daysFromNow(-3), source_analysis_id: 1 }),
  item({ description: "Ação da semana", due_date: daysFromNow(2), source_analysis_id: 2 }),
  item({ description: "Ação futura", due_date: daysFromNow(30), source_analysis_id: 3 }),
  item({ description: "Ação sem prazo", due_date: null, source_analysis_id: 4, owner: null }),
];

describe("ActionsSection (Workspace)", () => {
  it("shows a skeleton while pending", () => {
    mockedActionItems.mockReturnValue(PENDING);
    const { container } = render(<ActionsSection projectName="Aurora" />);
    expect(screen.getByRole("heading", { name: "Ações" })).toBeInTheDocument();
    expect(container.querySelector('[data-slot="skeleton"]')).not.toBeNull();
  });

  it("shows an honest error message on failure", () => {
    mockedActionItems.mockReturnValue(ERROR);
    render(<ActionsSection projectName="Aurora" />);
    expect(screen.getByText("Não foi possível carregar as ações.")).toBeInTheDocument();
  });

  it("shows the empty state when the project has no action items", () => {
    mockedActionItems.mockReturnValue({ isPending: false, isError: false, data: [] } as never);
    render(<ActionsSection projectName="Aurora" />);
    expect(
      screen.getByText("Nenhuma ação registrada em reuniões deste projeto ainda."),
    ).toBeInTheDocument();
  });

  it("scopes the hook to the project it renders", () => {
    mockedActionItems.mockReturnValue(PENDING);
    render(<ActionsSection projectName="Implantacao SAP S/4HANA" />);
    expect(mockedActionItems).toHaveBeenCalledWith("Implantacao SAP S/4HANA");
  });

  it("renders items grouped by urgency with a real attention headline", () => {
    mockedActionItems.mockReturnValue({
      isPending: false,
      isError: false,
      data: GROUPED_SAMPLE,
    } as never);
    render(<ActionsSection projectName="Aurora" />);

    expect(screen.getByText("1 atrasada(s) · 1 vence(m) em breve")).toBeInTheDocument();
    // A ação atrasada aparece duas vezes por desenho: no bloco "Próxima ação
    // sugerida" e no grupo "Atrasado".
    expect(screen.getAllByText("Ação atrasada")).toHaveLength(2);
    expect(screen.getByText("Ação da semana")).toBeInTheDocument();
    expect(screen.getByText("Ação futura")).toBeInTheDocument();
    expect(screen.getByText("Ação sem prazo")).toBeInTheDocument();
  });
});

describe("ActionItemsList (corpo compartilhado Workspace/portfólio)", () => {
  it("keeps 'Atrasado' always the first group heading", () => {
    render(<ActionItemsList items={GROUPED_SAMPLE} />);

    const headings = ["Atrasado", "Vence em breve", "No prazo", "Sem prazo"].map((label) =>
      screen.getByText(label),
    );
    // DOM order proves visual hierarchy: overdue first, no user reordering.
    for (let i = 1; i < headings.length; i += 1) {
      const position = headings[i - 1].compareDocumentPosition(headings[i]);
      expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });

  it("suggests the most urgent item as text, never a button", () => {
    render(<ActionItemsList items={GROUPED_SAMPLE} />);

    const suggestion = screen.getByText("Próxima ação sugerida");
    const block = suggestion.parentElement as HTMLElement;
    expect(within(block).getByText("Ação atrasada")).toBeInTheDocument();
    expect(within(block).queryByRole("button")).toBeNull();
  });

  it("omits the suggestion block when no item has a parseable deadline", () => {
    render(<ActionItemsList items={[item({ due_date: null })]} />);
    expect(screen.queryByText("Próxima ação sugerida")).toBeNull();
  });

  it("never renders a create/edit/assign control (não é um gerenciador de tarefas)", () => {
    render(<ActionItemsList items={GROUPED_SAMPLE} />);
    for (const forbidden of [/criar/i, /editar/i, /atribuir/i, /concluir/i]) {
      expect(screen.queryByRole("button", { name: forbidden })).toBeNull();
    }
  });

  it("shows the project name on each card only in the portfolio view", () => {
    const items = [item({ description: "Ação multi", project_name: "Medlog" })];

    const { rerender } = render(<ActionItemsList items={items} />);
    expect(screen.queryByText("Medlog")).toBeNull();

    rerender(<ActionItemsList items={items} showProject />);
    expect(screen.getByText("Medlog")).toBeInTheDocument();
  });

  it("opens the origin meeting analysis when an item is clicked", async () => {
    const user = userEvent.setup();
    render(<ActionItemsList items={[item({ description: "Ação clicável", source_analysis_id: 77 })]} />);

    await user.click(screen.getByRole("button", { name: /Ação clicável/ }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(mockedDetail).toHaveBeenLastCalledWith("Aurora", 77);
  });

  it("degrades an item without a project to plain text instead of a broken drill-down", () => {
    render(<ActionItemsList items={[item({ description: "Órfã", project_name: null })]} />);
    expect(screen.getByText("Órfã")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Órfã/ })).toBeNull();
  });
});
