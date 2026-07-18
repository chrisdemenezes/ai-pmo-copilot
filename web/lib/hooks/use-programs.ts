import { useQuery } from "@tanstack/react-query";

import { listPrograms } from "@/lib/domain/program";

/** Same query shape as usePortfolios() -- see that hook for the rationale. */
export function usePrograms() {
  return useQuery({
    queryKey: ["programs"],
    queryFn: listPrograms,
    staleTime: 30_000,
  });
}
