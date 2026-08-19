import { describe, expect, it, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";

import { ExecutiveBrief } from "./executive-brief";
import { useWorkspaceSummary } from "@/lib/hooks/use-workspace-summary";
import { useWorkspaceLatestByKind } from "@/lib/hooks/use-workspace-latest";
import { useRecentAnalysesByKind } from "@/lib/hooks/use-recent-analyses";
import { useActionItems } from "@/lib/hooks/use-action-items";

// TD-008 Fase 3b, Etapa 2 (dual-key): o Executive Brief resolve nome->id via
// o summary e reaproveita o project_id nas leituras irmãs deste mesmo painel.
vi.mock("@/lib/hooks/use-workspace-summary", () => ({ useWorkspaceSummary: vi.fn() }));
vi.mock("@/lib/hooks/use-workspace-latest", () => ({ useWorkspaceLatestByKind: vi.fn() }));
vi.mock("@/lib/hooks/use-recent-analyses", () => ({ useRecentAnalysesByKind: vi.fn() }));
vi.mock("@/lib/hooks/use-action-items", () => ({ useActionItems: vi.fn() }));

const mockedSummary = vi.mocked(useWorkspaceSummary);
const mockedLatest = vi.mocked(useWorkspaceLatestByKind);
const mockedRecent = vi.mocked(useRecentAnalysesByKind);
const mockedActionItems = vi.mocked(useActionItems);

const idle = { isPending: false, isError: false, data: null } as never;

beforeEach(() => {
  vi.clearAllMocks();
  mockedLatest.mockReturnValue(idle);
  mockedRecent.mockReturnValue({ isPending: false, isError: false, data: undefined } as never);
  mockedActionItems.mockReturnValue({ isPending: true, isError: false, data: undefined } as never);
});

describe("ExecutiveBrief dual-key wiring (Etapa 2)", () => {
  it("threads the resolved project_id from the summary into the sibling reads", () => {
    mockedSummary.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        project_name: "Aurora",
        project_id: 7,
        total_analyses: 2,
        open_risks: 0,
        pending_action_items: 1,
        latest_health_status: "green",
      },
    } as never);

    render(<ExecutiveBrief projectName="Aurora" />);

    // Painel A resolveu o id -> os reads irmãos recebem a chave exata.
    expect(mockedLatest).toHaveBeenCalledWith("Aurora", "status", 7);
    expect(mockedRecent).toHaveBeenCalledWith("Aurora", "status", 5, 7);
    expect(mockedRecent).toHaveBeenCalledWith("Aurora", "risk", 5, 7);
  });

  it("falls back to name-only while the summary is still pending (no id yet)", () => {
    mockedSummary.mockReturnValue({ isPending: true, isError: false, data: undefined } as never);

    render(<ExecutiveBrief projectName="Aurora" />);

    // Sem summary resolvido, projectId é undefined -- comportamento idêntico
    // ao anterior; nenhum painel bloqueia o outro (additividade estrita).
    expect(mockedLatest).toHaveBeenCalledWith("Aurora", "status", undefined);
    expect(mockedRecent).toHaveBeenCalledWith("Aurora", "status", 5, undefined);
    expect(mockedRecent).toHaveBeenCalledWith("Aurora", "risk", 5, undefined);
  });
});
