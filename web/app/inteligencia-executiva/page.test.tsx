import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import InteligenciaExecutivaPage from "./page";
import { useAskDecisionSupport } from "@/lib/hooks/use-ask-decision-support";
import { useGenerateExecutiveNarrative } from "@/lib/hooks/use-generate-executive-narrative";
import { useProjects } from "@/lib/hooks/use-projects";
import { usePortfolios } from "@/lib/hooks/use-portfolios";

// Same reason as web/app/dashboard/page.test.tsx: DecisionSupportPanel and
// ExecutiveNarrativePanel each own a real useMutation() that would
// otherwise require a real QueryClientProvider this test never sets up.
vi.mock("@/lib/hooks/use-ask-decision-support", async () => {
  const actual = await vi.importActual<typeof import("@/lib/hooks/use-ask-decision-support")>(
    "@/lib/hooks/use-ask-decision-support",
  );
  return { ...actual, useAskDecisionSupport: vi.fn() };
});
vi.mock("@/lib/hooks/use-generate-executive-narrative", async () => {
  const actual = await vi.importActual<typeof import("@/lib/hooks/use-generate-executive-narrative")>(
    "@/lib/hooks/use-generate-executive-narrative",
  );
  return { ...actual, useGenerateExecutiveNarrative: vi.fn() };
});
// ScopeSelector (used by both panels) calls useProjects()/usePortfolios()
// directly -- real useQuery() calls, same reason as above.
vi.mock("@/lib/hooks/use-projects", () => ({ useProjects: vi.fn() }));
vi.mock("@/lib/hooks/use-portfolios", () => ({ usePortfolios: vi.fn() }));

const mockedDecisionSupportMutation = vi.mocked(useAskDecisionSupport);
mockedDecisionSupportMutation.mockReturnValue({
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  data: undefined,
  error: null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any);
const mockedExecutiveNarrativeMutation = vi.mocked(useGenerateExecutiveNarrative);
mockedExecutiveNarrativeMutation.mockReturnValue({
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  data: undefined,
  error: null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any);
vi.mocked(useProjects).mockReturnValue({
  data: [],
  isPending: false,
  isError: false,
  error: null,
  refetch: vi.fn(),
  isFetching: false,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any);
vi.mocked(usePortfolios).mockReturnValue({
  data: [],
  isPending: false,
  isError: false,
  error: null,
  refetch: vi.fn(),
  isFetching: false,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any);

describe("InteligenciaExecutivaPage", () => {
  it("renders both Decision Support and Narrativa Executiva sections", () => {
    render(<InteligenciaExecutivaPage />);
    expect(screen.getByRole("heading", { name: "Inteligência Executiva" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Decision Support" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Narrativa Executiva" })).toBeInTheDocument();
  });
});
