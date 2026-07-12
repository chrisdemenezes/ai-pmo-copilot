import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useWorkspaceSummary } from "./use-workspace-summary";

const SAMPLE = {
  project_name: "Aurora",
  total_analyses: 3,
  open_risks: 2,
  pending_action_items: 1,
  latest_health_status: "yellow" as const,
};

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("useWorkspaceSummary", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches the encoded workspace summary URL and returns the parsed body", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useWorkspaceSummary("Implantacao SAP S/4HANA"), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/bff/workspace/Implantacao%20SAP%20S%2F4HANA/summary",
    );
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

    const { result } = renderHook(() => useWorkspaceSummary("Aurora"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Backend respondeu 500.");
  });
});
