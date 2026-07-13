import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useSubmitMeetingIntelligence } from "./use-submit-meeting-intelligence";

const SAMPLE = {
  agent: "meeting_intelligence",
  project_name: "Aurora",
  model_output: {
    structured: true,
    summary: "Reunião semanal de acompanhamento.",
    decisions: ["Adiar o go-live em 1 semana"],
    action_items: [{ description: "Atualizar cronograma", owner: "Ana", due_date: "2026-07-15" }],
    issues: [],
    dependencies: ["Aprovação do cliente"],
  },
};

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function wrapperFor(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("useSubmitMeetingIntelligence", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts to the encoded per-project analyze/meeting BFF route", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const queryClient = makeClient();
    const { result } = renderHook(() => useSubmitMeetingIntelligence("Implantacao SAP S/4HANA"), {
      wrapper: wrapperFor(queryClient),
    });

    result.current.mutate("contexto valido com mais de dez caracteres");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/bff/workspace/Implantacao%20SAP%20S%2F4HANA/analyze/meeting",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("invalidates exactly the 4 template query keys on success, using 'meeting' -- never other kinds", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const queryClient = makeClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useSubmitMeetingIntelligence("Aurora"), {
      wrapper: wrapperFor(queryClient),
    });

    result.current.mutate("contexto valido com mais de dez caracteres");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const invalidatedKeys = invalidateSpy.mock.calls.map((call) => call[0]?.queryKey);
    expect(invalidatedKeys).toContainEqual(["workspace-summary", "Aurora"]);
    expect(invalidatedKeys).toContainEqual(["workspace-latest", "Aurora", "meeting"]);
    expect(invalidatedKeys).toContainEqual(["workspace-timeline", "Aurora"]);
    expect(invalidatedKeys).toContainEqual(["portfolio-summary"]);
    expect(invalidatedKeys).not.toContainEqual(["workspace-latest", "Aurora", "status"]);
    expect(invalidatedKeys).not.toContainEqual(["workspace-latest", "Aurora", "risk"]);
    expect(invalidatedKeys).toHaveLength(4);
  });

  it("does not invalidate any query on error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: "backend_error", detail: "Backend respondeu 500." }), {
          status: 502,
        }),
      ),
    );

    const queryClient = makeClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useSubmitMeetingIntelligence("Aurora"), {
      wrapper: wrapperFor(queryClient),
    });

    result.current.mutate("contexto valido com mais de dez caracteres");
    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});
