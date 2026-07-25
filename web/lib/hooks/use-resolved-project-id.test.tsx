import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";

import { useResolvedProjectId } from "./use-resolved-project-id";
import { useWorkspaceSummary } from "./use-workspace-summary";

// A resolução nome->id é a saída do summary (deduplicado pelo React Query);
// este hook apenas a projeta (TD-008 Fase 3b, Etapa 3).
vi.mock("./use-workspace-summary", () => ({ useWorkspaceSummary: vi.fn() }));

const mockedSummary = vi.mocked(useWorkspaceSummary);

beforeEach(() => vi.clearAllMocks());

describe("useResolvedProjectId", () => {
  it("returns the resolved project_id once the summary succeeds", () => {
    mockedSummary.mockReturnValue({ data: { project_id: 7 } } as never);
    const { result } = renderHook(() => useResolvedProjectId("Aurora"));
    expect(result.current).toBe(7);
    // reaproveita o summary já buscado -- nenhuma resolução própria.
    expect(mockedSummary).toHaveBeenCalledWith("Aurora");
  });

  it("returns undefined while the summary is pending (falls back to name)", () => {
    mockedSummary.mockReturnValue({ data: undefined } as never);
    const { result } = renderHook(() => useResolvedProjectId("Aurora"));
    expect(result.current).toBeUndefined();
  });

  it("returns undefined when the project has no analyses (project_id null)", () => {
    mockedSummary.mockReturnValue({ data: { project_id: null } } as never);
    const { result } = renderHook(() => useResolvedProjectId("Ghost"));
    expect(result.current).toBeUndefined();
  });
});
