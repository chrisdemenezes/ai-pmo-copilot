import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useLatestRisks } from "./use-latest-risks";

const SAMPLE = [
  {
    project_name: "Multilift",
    description: "Atraso no fornecedor de middleware",
    probability: "high",
    impact: "high",
    mitigation: "Escalar ao patrocinador",
    escalation_recommendation: "Escalar ao comitê executivo",
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

describe("useLatestRisks", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches the Workspace view with an encoded project_name query param", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useLatestRisks("Implantacao SAP S/4HANA"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/bff/risks/latest?project_name=Implantacao%20SAP%20S%2F4HANA",
    );
    expect(result.current.data).toEqual(SAMPLE);
  });

  it("fetches the portfolio view when projectName is omitted", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useLatestRisks(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledWith("/api/bff/risks/latest");
  });

  it("caches under ['latest-risks', projectName] for the Workspace view", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const { queryClient, wrapper } = makeWrapper();
    const { result } = renderHook(() => useLatestRisks("Multilift"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(queryClient.getQueryData(["latest-risks", "Multilift"])).toEqual(SAMPLE);
  });

  it("caches under ['latest-risks', 'portfolio'] for the portfolio view", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const { queryClient, wrapper } = makeWrapper();
    const { result } = renderHook(() => useLatestRisks(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(queryClient.getQueryData(["latest-risks", "portfolio"])).toEqual(SAMPLE);
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
    const { result } = renderHook(() => useLatestRisks("Multilift"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Backend respondeu 500.");
  });
});
