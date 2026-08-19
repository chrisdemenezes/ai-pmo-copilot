import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useAskRiskAdvisor } from "./use-ask-risk-advisor";

const SAMPLE = {
  answer: "O risco mais crítico é o atraso no fornecedor de middleware.",
  cited_analyses: [{ source_analysis_id: 7, source_created_at: "2026-07-10T14:00:00Z" }],
};

function wrapperFor(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("useAskRiskAdvisor", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts the question to the encoded per-project risk-advisor BFF route", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useAskRiskAdvisor("Implantacao SAP S/4HANA"), {
      wrapper: wrapperFor(queryClient),
    });

    result.current.mutate("Qual o risco mais crítico?");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/bff/workspace/Implantacao%20SAP%20S%2F4HANA/risk-advisor",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ question: "Qual o risco mais crítico?" }),
      }),
    );
    expect(result.current.data).toEqual(SAMPLE);
  });

  it("surfaces the backend error message on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: "backend_error", detail: "Backend respondeu 500." }), {
          status: 502,
        }),
      ),
    );

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useAskRiskAdvisor("Aurora"), {
      wrapper: wrapperFor(queryClient),
    });

    result.current.mutate("Qual o risco mais crítico?");
    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error?.message).toBe("Backend respondeu 500.");
  });
});
