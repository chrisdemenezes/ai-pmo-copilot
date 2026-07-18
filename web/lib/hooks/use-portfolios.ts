import { useQuery } from "@tanstack/react-query";

import { listPortfolios } from "@/lib/domain/portfolio";

/**
 * Same query shape as usePortfolioSummary() (real Project data) -- the
 * seam is deliberate: when Release 0.2 wires a real backend endpoint for
 * Portfolio, only listPortfolios() changes, not this hook or its callers.
 */
export function usePortfolios() {
  return useQuery({
    queryKey: ["portfolios"],
    queryFn: listPortfolios,
    staleTime: 30_000,
  });
}
