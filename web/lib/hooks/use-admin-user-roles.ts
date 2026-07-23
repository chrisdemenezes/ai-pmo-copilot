import { useQuery } from "@tanstack/react-query";

import { listRolesForUser } from "@/lib/domain/user";

/** Roles a specific user already has -- lets the UI offer "assign" vs.
 * "remove" per role instead of a single ambiguous action. */
export function useAdminUserRoles(userId: string | null) {
  return useQuery({
    queryKey: ["admin-user-roles", userId],
    queryFn: () => listRolesForUser(userId as string),
    enabled: userId !== null,
    staleTime: 10_000,
  });
}
