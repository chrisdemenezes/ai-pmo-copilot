import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AnalysisHistory } from "./analysis-history";
import { useWorkspaceTimeline } from "@/lib/hooks/use-workspace-timeline";
import { useWorkspaceAnalysisDetail } from "@/lib/hooks/use-workspace-analysis-detail";

vi.mock("@/lib/hooks/use-workspace-timeline", () => ({ useWorkspaceTimeline: vi.fn() }));
vi.mock("@/lib/hooks/use-workspace-analysis-detail", () => ({
  useWorkspaceAnalysisDetail: vi.fn(),
}));

const mockedTimeline = vi.mocked(useWorkspaceTimeline);
const mockedDetail = vi.mocked(useWorkspaceAnalysisDetail);

function state(overrides: Partial<Record<string, unknown>>) {
  return { isPending: false, isError: false, data: undefined, ...overrides } as never;
}

describe("AnalysisHistory (Painel B, paginado)", () => {
  it("shows an empty message on the first page with no analyses", () => {
    mockedTimeline.mockReturnValue(state({ data: [] }));
    mockedDetail.mockReturnValue(state({ data: undefined }));

    render(<AnalysisHistory projectName="Aurora" />);
    expect(screen.getByText("Nenhuma análise registrada ainda.")).toBeInTheDocument();
  });

  it("lists items and disables 'Próxima' when fewer than a full page is returned", () => {
    mockedTimeline.mockReturnValue(
      state({
        data: [{ id: 1, kind: "risk", project_name: "Aurora", created_at: "2026-07-01T10:00:00Z" }],
      }),
    );
    mockedDetail.mockReturnValue(state({ data: undefined }));

    render(<AnalysisHistory projectName="Aurora" />);
    expect(screen.getByRole("button", { name: "Próxima" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
  });

  it("opens the detail dialog with its own loading state when an item is clicked", async () => {
    mockedTimeline.mockReturnValue(
      state({
        data: [{ id: 1, kind: "risk", project_name: "Aurora", created_at: "2026-07-01T10:00:00Z" }],
      }),
    );
    mockedDetail.mockReturnValue(state({ isPending: true }));

    const user = userEvent.setup();
    render(<AnalysisHistory projectName="Aurora" />);

    await user.click(screen.getByRole("button", { name: /01\/07\/2026/ }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("renders the fetched detail body once resolved", async () => {
    mockedTimeline.mockReturnValue(
      state({
        data: [{ id: 1, kind: "status", project_name: "Aurora", created_at: "2026-07-01T10:00:00Z" }],
      }),
    );
    mockedDetail.mockReturnValue(
      state({
        data: {
          id: 1,
          kind: "status",
          project_name: "Aurora",
          created_at: "2026-07-01T10:00:00Z",
          payload: {
            agent: "project_status",
            project_name: "Aurora",
            model_output: { structured: true, health_status: "green", key_findings: ["Achado histórico"], recommendations: [] },
          },
        },
      }),
    );

    const user = userEvent.setup();
    render(<AnalysisHistory projectName="Aurora" />);
    await user.click(screen.getByRole("button", { name: /01\/07\/2026/ }));
    expect(screen.getByText("Achado histórico")).toBeInTheDocument();
  });

  it("falls back to raw JSON, never crashes, when structured=true but the shape matches no known schema (TIP-006)", async () => {
    mockedTimeline.mockReturnValue(
      state({
        data: [{ id: 1, kind: "status", project_name: "Aurora", created_at: "2026-07-01T10:00:00Z" }],
      }),
    );
    mockedDetail.mockReturnValue(
      state({
        data: {
          id: 1,
          kind: "status",
          project_name: "Aurora",
          created_at: "2026-07-01T10:00:00Z",
          payload: {
            agent: "project_status",
            project_name: "Aurora",
            // structured: true, but none of risks/action_items/key_findings
            // present -- the real Demo Mode failure mode this guards.
            model_output: { structured: true, unexpected_field: "x" },
          },
        },
      }),
    );

    const user = userEvent.setup();
    render(<AnalysisHistory projectName="Aurora" />);
    await user.click(screen.getByRole("button", { name: /01\/07\/2026/ }));
    expect(screen.getByText(/unexpected_field/)).toBeInTheDocument();
  });
});
