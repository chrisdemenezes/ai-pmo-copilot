import { useQuery } from "@tanstack/react-query";

import { listUsers } from "@/lib/domain/user";

/** Same query shape as usePortfolios()/usePrograms() -- see those hooks
 * for the rationale (D-011 accessor pattern). */
export function useAdminUsers() {
  return useQuery({
    queryKey: ["admin-users"],
    queryFn: listUsers,
    staleTime: 10_000,
  });
}
