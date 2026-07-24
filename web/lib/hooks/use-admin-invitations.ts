import { useQuery } from "@tanstack/react-query";

import { listInvitations } from "@/lib/domain/invitation";

/** Same query shape as useAdminApiKeys() -- see that hook for the rationale
 * (D-011 accessor pattern). */
export function useAdminInvitations() {
  return useQuery({
    queryKey: ["admin-invitations"],
    queryFn: listInvitations,
    staleTime: 10_000,
  });
}
