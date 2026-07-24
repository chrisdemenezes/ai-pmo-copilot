import { useQuery } from "@tanstack/react-query";

import { listApiKeys } from "@/lib/domain/api-key";

/** Same query shape as useAdminUsers() -- see that hook for the rationale
 * (D-011 accessor pattern). */
export function useAdminApiKeys() {
  return useQuery({
    queryKey: ["admin-api-keys"],
    queryFn: listApiKeys,
    staleTime: 10_000,
  });
}
