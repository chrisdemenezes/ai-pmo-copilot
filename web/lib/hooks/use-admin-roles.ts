import { useQuery } from "@tanstack/react-query";

import { listRoles } from "@/lib/domain/user";

/** Global role catalog (Épico 1) -- rarely changes, long staleTime. */
export function useAdminRoles() {
  return useQuery({
    queryKey: ["admin-roles"],
    queryFn: listRoles,
    staleTime: 60_000,
  });
}
