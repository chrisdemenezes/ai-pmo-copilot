import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import AprendizadosPage from "./page";
import { useLatestRisks } from "@/lib/hooks/use-latest-risks";
import { useActionItems } from "@/lib/hooks/use-action-items";
import type { LatestRiskItem } from "@/lib/decision-center/types";
import type { ActionItemView } from "@/lib/workspace/types";

vi.mock("@/lib/hooks/use-latest-risks", () => ({ useLatestRisks: vi.fn() }));
vi.mock("@/lib/hooks/use-action-items", () => ({ useActionItems: vi.fn() }));

const mockedRisks = vi.mocked(useLatestRisks);
const mockedActions = vi.mocked(useActionItems);

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

function risk(description: string, projectName: string): LatestRiskItem {
  return {
    project_name: projectName,
    description,
    probability: "high",
    impact: "high",
    mitigation: "Mitigar",
    escalation_recommendation: null,
    source_analysis_id: 1,
    source_created_at: "2026-07-01T00:00:00Z",
  };
}

function action(description: string, projectName: string): ActionItemView {
  return {
    project_name: projectName,
    description,
    owner: null,
    due_date: null,
    source_analysis_id: 1,
    source_created_at: "2026-07-01T00:00:00Z",
  };
}

const RECURRING_RISK = [
  risk("Atraso do fornecedor de middleware", "Aurora"),
  risk("Atraso do fornecedor de middleware", "Multilift"),
  risk("Atraso do fornecedor de middleware", "Portal do Cliente 2.0"),
];

describe("AprendizadosPage (Organizational Intelligence)", () => {
  it("renders the skeleton while either source is pending", () => {
    mockedRisks.mockReturnValue(hookState({ isPending: true }));
    mockedActions.mockReturnValue(hookState({ isPending: true }));
    const { container } = render(<AprendizadosPage />);
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
  });

  it("shows the honest empty state when no pattern reaches 3+ occurrences", () => {
    mockedRisks.mockReturnValue(hookState({ data: [] }));
    mockedActions.mockReturnValue(hookState({ data: [] }));
    render(<AprendizadosPage />);
    expect(
      screen.getByText("Nenhum aprendizado organizacional identificado no momento"),
    ).toBeInTheDocument();
  });

  it("shows exactly 1 real learning normally -- never an artificial filler state (UX Flow §05)", () => {
    mockedRisks.mockReturnValue(hookState({ data: RECURRING_RISK }));
    mockedActions.mockReturnValue(hookState({ data: [] }));
    render(<AprendizadosPage />);
    expect(screen.getByText("Riscos recorrentes")).toBeInTheDocument();
    expect(screen.getByText("Este risco apareceu em 3 projetos diferentes.")).toBeInTheDocument();
    expect(screen.queryByText("Ações recorrentes")).toBeNull();
  });

  it("renders Riscos recorrentes before Ações recorrentes -- fixed category order (UX Flow §03)", () => {
    mockedRisks.mockReturnValue(hookState({ data: RECURRING_RISK }));
    mockedActions.mockReturnValue(
      hookState({
        data: [
          action("Confirmar cronograma com o patrocinador", "Aurora"),
          action("Confirmar cronograma com o patrocinador", "Multilift"),
          action("Confirmar cronograma com o patrocinador", "Renovacao de Infraestrutura de Rede"),
        ],
      }),
    );
    render(<AprendizadosPage />);
    const headings = screen.getAllByRole("heading", { level: 2 });
    const labels = headings.map((heading) => heading.textContent);
    expect(labels.indexOf("Riscos recorrentes")).toBeLessThan(labels.indexOf("Ações recorrentes"));
  });

  it("degrades gracefully when risks fail but actions succeed", () => {
    mockedRisks.mockReturnValue(hookState({ isError: true, error: new Error("boom") }));
    mockedActions.mockReturnValue(
      hookState({
        data: [
          action("Confirmar cronograma com o patrocinador", "Aurora"),
          action("Confirmar cronograma com o patrocinador", "Multilift"),
          action("Confirmar cronograma com o patrocinador", "Renovacao de Infraestrutura de Rede"),
        ],
      }),
    );
    render(<AprendizadosPage />);
    expect(
      screen.getByText("Não foi possível carregar os riscos -- mostrando apenas ações recorrentes."),
    ).toBeInTheDocument();
    expect(screen.getByText("Ações recorrentes")).toBeInTheDocument();
  });

  it("never renders a concept label/chip on category headings -- Zero Labels Rule", () => {
    mockedRisks.mockReturnValue(hookState({ data: RECURRING_RISK }));
    mockedActions.mockReturnValue(hookState({ data: [] }));
    render(<AprendizadosPage />);
    for (const forbiddenLabel of ["Aprendizado Organizacional", "Organizational Finding", "Executive Finding"]) {
      expect(screen.queryByText(forbiddenLabel)).toBeNull();
    }
  });
});
