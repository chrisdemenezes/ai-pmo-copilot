import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useAskDecisionSupport } from "./use-ask-decision-support";

const SAMPLE = {
  capability: "decision_support",
  insufficient_basis: false,
  insufficient_basis_reason: null,
  answer: "Existe risco de escalação e a entrega está em andamento.",
  advisors_used: ["risk_advisor", "delivery_advisor"],
  citations: [],
  composition_trace: {
    selection_signals: ["risco"],
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

describe("useAskDecisionSupport", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts the question and scope to the Decision Support BFF route", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useAskDecisionSupport(), {
      wrapper: wrapperFor(queryClient),
    });

    result.current.mutate({
      question: "Existe risco e qual o status de entrega?",
      scope: { type: "project", project_id: 42 },
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/bff/decision-support",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          question: "Existe risco e qual o status de entrega?",
          scope: { type: "project", project_id: 42 },
        }),
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
    const { result } = renderHook(() => useAskDecisionSupport(), {
      wrapper: wrapperFor(queryClient),
    });

    result.current.mutate({
      question: "Como está o portfólio?",
      scope: { type: "portfolio", portfolio_id: 999 },
    });
    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error?.message).toBe("Projeto ou portfólio não encontrado.");
  });
});
