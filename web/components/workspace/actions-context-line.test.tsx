import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { ActionsContextLine } from "./actions-context-line";
import { useActionItems } from "@/lib/hooks/use-action-items";
import type { ActionItemView } from "@/lib/workspace/types";

vi.mock("@/lib/hooks/use-action-items", () => ({ useActionItems: vi.fn() }));

const mockedActionItems = vi.mocked(useActionItems);

function daysFromNow(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString();
}

function item(overrides: Partial<ActionItemView>): ActionItemView {
  return {
    project_name: "Aurora",
    description: "a",
    owner: null,
    due_date: null,
    source_analysis_id: 1,
    source_created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("ActionsContextLine", () => {
  it("renders nothing while data is not yet available", () => {
    mockedActionItems.mockReturnValue({ isPending: true, isError: false, data: undefined } as never);
    const { container } = render(<ActionsContextLine projectName="Aurora" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing on error", () => {
    mockedActionItems.mockReturnValue({ isPending: false, isError: true, data: undefined } as never);
    const { container } = render(<ActionsContextLine projectName="Aurora" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when the attention count is zero -- present only when > 0 (UX Flow §07)", () => {
    mockedActionItems.mockReturnValue({
      isPending: false,
      isError: false,
      data: [item({ due_date: daysFromNow(30) })],
    } as never);
    const { container } = render(<ActionsContextLine projectName="Aurora" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the real attention count when greater than zero", () => {
    mockedActionItems.mockReturnValue({
      isPending: false,
      isError: false,
      data: [item({ due_date: daysFromNow(-1) }), item({ due_date: daysFromNow(2) })],
    } as never);
    render(<ActionsContextLine projectName="Aurora" />);
    expect(screen.getByText("2 ações exigem atenção")).toBeInTheDocument();
  });

  it("scopes the hook to the project it renders", () => {
    mockedActionItems.mockReturnValue({ isPending: true, isError: false, data: undefined } as never);
    render(<ActionsContextLine projectName="Implantacao SAP S/4HANA" />);
    expect(mockedActionItems).toHaveBeenCalledWith("Implantacao SAP S/4HANA");
  });
});
