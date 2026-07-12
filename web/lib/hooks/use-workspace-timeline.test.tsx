import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useWorkspaceTimeline } from "./use-workspace-timeline";

const SAMPLE = [{ id: 1, kind: "status" as const, project_name: "Aurora", created_at: "2026-07-01T10:00:00Z" }];

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("useWorkspaceTimeline", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches the analyses list with limit/offset as query params", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(
      () => useWorkspaceTimeline("Aurora", { limit: 10, offset: 20 }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const [calledPath] = fetchMock.mock.calls[0];
    expect(calledPath).toContain("/api/bff/workspace/Aurora/analyses");
    expect(calledPath).toContain("limit=10");
    expect(calledPath).toContain("offset=20");
    expect(result.current.data).toEqual(SAMPLE);
  });

  it("surfaces the BFF error body when the request fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: "backend_error", detail: "Backend respondeu 500." }), {
          status: 502,
        }),
      ),
    );

    const { result } = renderHook(() => useWorkspaceTimeline("Aurora"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Backend respondeu 500.");
  });
});
