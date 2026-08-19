import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useGenerateExecutiveNarrative } from "./use-generate-executive-narrative";

const SAMPLE = {
  capability: "executive_narrative",
  scope: { type: "project", project_id: 42, portfolio_id: null },
  insufficient_basis: false,
  insufficient_basis_reason: null,
  narrative: "Síntese executiva: risco de escalação identificado, entrega em andamento.",
  advisors_used: ["risk_advisor", "delivery_advisor"],
  citations: [],
  composition_trace: {
    selection_signals: ["risk_advisor", "delivery_advisor"],
    selected_advisor_names: ["risk_advisor", "delivery_advisor"],
    advisors_used: [],
    correlations: [],
    synthesis_source_advisor_names: null,
  },
};

function wrapperFor(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("useGenerateExecutiveNarrative", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts only the scope (never a question) to the Executive Narrative BFF route", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useGenerateExecutiveNarrative(), {
      wrapper: wrapperFor(queryClient),
    });

    result.current.mutate({ type: "project", project_id: 42 });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/bff/executive-narrative",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ scope: { type: "project", project_id: 42 } }),
      }),
    );
    expect(result.current.data).toEqual(SAMPLE);
  });

  it("surfaces the backend error message on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: "scope_not_found", detail: "Projeto ou portfólio não encontrado." }), {
          status: 404,
        }),
      ),
    );

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useGenerateExecutiveNarrative(), {
      wrapper: wrapperFor(queryClient),
    });

    result.current.mutate({ type: "portfolio", portfolio_id: 999 });
    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error?.message).toBe("Projeto ou portfólio não encontrado.");
  });
});
