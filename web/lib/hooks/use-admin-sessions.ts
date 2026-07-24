import { useQuery } from "@tanstack/react-query";

import { listSessions } from "@/lib/domain/session";

/** Same query shape as useAdminApiKeys() -- see that hook for the rationale
 * (D-011 accessor pattern). */
export function useAdminSessions() {
  return useQuery({
    queryKey: ["admin-sessions"],
    queryFn: listSessions,
    staleTime: 10_000,
  });
}
