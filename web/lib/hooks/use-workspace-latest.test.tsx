import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useWorkspaceLatestByKind } from "./use-workspace-latest";

const LIST_SAMPLE = [
  { id: 42, kind: "risk" as const, project_name: "Aurora", created_at: "2026-07-01T10:00:00Z" },
];

const DETAIL_SAMPLE = {
  id: 42,
  kind: "risk" as const,
  project_name: "Aurora",
  created_at: "2026-07-01T10:00:00Z",
  payload: {
    agent: "risk_review",
    project_name: "Aurora",
    model_output: { structured: true, risks: [], escalation_recommendation: null },
  },
};

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("useWorkspaceLatestByKind", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches the latest analysis of a kind (list with limit=1, then its detail)", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(LIST_SAMPLE), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(DETAIL_SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useWorkspaceLatestByKind("Aurora", "risk"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(DETAIL_SAMPLE);

    const [listCall] = fetchMock.mock.calls[0];
    expect(listCall).toContain("kind=risk");
    expect(listCall).toContain("limit=1");
    const [detailCall] = fetchMock.mock.calls[1];
    expect(detailCall).toBe("/api/bff/workspace/Aurora/analyses/42");
  });

  it("returns null when there is no analysis of that kind yet -- not an error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 })),
    );

    const { result } = renderHook(() => useWorkspaceLatestByKind("Aurora", "meeting"), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });

  it("surfaces an error if the list call fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: "backend_error", detail: "Backend respondeu 500." }), {
          status: 502,
        }),
      ),
    );

    const { result } = renderHook(() => useWorkspaceLatestByKind("Aurora", "status"), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Backend respondeu 500.");
  });
});
