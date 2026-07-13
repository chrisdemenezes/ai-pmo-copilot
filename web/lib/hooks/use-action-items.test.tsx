import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useActionItems } from "./use-action-items";

const SAMPLE = [
  {
    project_name: "Aurora",
    description: "Atualizar cronograma",
    owner: "Ana",
    due_date: "2026-07-15",
    source_analysis_id: 202,
    source_created_at: "2026-07-09T10:00:00Z",
  },
];

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

describe("useActionItems", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches the Workspace view with an encoded project_name query param", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useActionItems("Implantacao SAP S/4HANA"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/bff/action-items?project_name=Implantacao%20SAP%20S%2F4HANA",
    );
    expect(result.current.data).toEqual(SAMPLE);
  });

  it("fetches the portfolio view when projectName is omitted", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useActionItems(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledWith("/api/bff/action-items");
  });

  // FS-007 §03: cache key is ["action-items", projectName ?? "portfolio"] --
  // the 3 Briefs' context lines share the per-project entry with the "Ações"
  // section, so one Workspace screen never fetches the same list twice.
  it("caches under ['action-items', projectName] for the Workspace view", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const { queryClient, wrapper } = makeWrapper();
    const { result } = renderHook(() => useActionItems("Aurora"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(queryClient.getQueryData(["action-items", "Aurora"])).toEqual(SAMPLE);
  });

  it("caches under ['action-items', 'portfolio'] for the portfolio view", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const { queryClient, wrapper } = makeWrapper();
    const { result } = renderHook(() => useActionItems(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(queryClient.getQueryData(["action-items", "portfolio"])).toEqual(SAMPLE);
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

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useActionItems("Aurora"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Backend respondeu 500.");
  });
});
