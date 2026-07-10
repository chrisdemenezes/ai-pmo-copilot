import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { usePortfolioSummary } from "./use-portfolio-summary";

const SAMPLE = [
  {
    project_name: "Multilift",
    total_analyses: 3,
    open_risks: 2,
    pending_action_items: 1,
    latest_health_status: "yellow" as const,
  },
];

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("usePortfolioSummary", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches /api/bff/dashboard and returns the parsed body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE), { status: 200 })),
    );

    const { result } = renderHook(() => usePortfolioSummary(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
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

    const { result } = renderHook(() => usePortfolioSummary(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Backend respondeu 500.");
  });
});
