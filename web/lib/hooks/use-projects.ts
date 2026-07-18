import { useQuery } from "@tanstack/react-query";

import { listProjects } from "@/lib/domain/project";

/** Same query shape as usePortfolios()/usePrograms() -- see those hooks for the rationale. */
export function useProjects() {
  return useQuery({
    queryKey: ["projects-delivery"],
    queryFn: listProjects,
    staleTime: 30_000,
  });
}
