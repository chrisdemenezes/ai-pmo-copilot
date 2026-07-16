import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useSubmitProjectStatus } from "./use-submit-project-status";

const SAMPLE = {
  agent: "project_status",
  project_name: "Aurora",
  model_output: {
    structured: true,
    health_status: "green",
    key_findings: ["Projeto dentro do prazo"],
    recommendations: ["Manter cadência atual"],
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

describe("useSubmitProjectStatus", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts to the encoded per-project analyze/status BFF route", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const queryClient = makeClient();
    const { result } = renderHook(() => useSubmitProjectStatus("Implantacao SAP S/4HANA"), {
      wrapper: wrapperFor(queryClient),
    });

    result.current.mutate("contexto valido com mais de dez caracteres");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/bff/workspace/Implantacao%20SAP%20S%2F4HANA/analyze/status",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("invalidates exactly the 5 query keys on success (FS-005 §3 + Executive Memory's workspace-recent), never other kinds", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const queryClient = makeClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useSubmitProjectStatus("Aurora"), {
      wrapper: wrapperFor(queryClient),
    });

    result.current.mutate("contexto valido com mais de dez caracteres");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const invalidatedKeys = invalidateSpy.mock.calls.map((call) => call[0]?.queryKey);
    expect(invalidatedKeys).toContainEqual(["workspace-summary", "Aurora"]);
    expect(invalidatedKeys).toContainEqual(["workspace-latest", "Aurora", "status"]);
    expect(invalidatedKeys).toContainEqual(["workspace-recent", "Aurora", "status"]);
    expect(invalidatedKeys).toContainEqual(["workspace-timeline", "Aurora"]);
    expect(invalidatedKeys).toContainEqual(["portfolio-summary"]);
    expect(invalidatedKeys).not.toContainEqual(["workspace-latest", "Aurora", "risk"]);
    expect(invalidatedKeys).not.toContainEqual(["workspace-latest", "Aurora", "meeting"]);
    expect(invalidatedKeys).toHaveLength(5);
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

    const { result } = renderHook(() => useSubmitProjectStatus("Aurora"), {
      wrapper: wrapperFor(queryClient),
    });

    result.current.mutate("contexto valido com mais de dez caracteres");
    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});
