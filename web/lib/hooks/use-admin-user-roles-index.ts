import { useQuery } from "@tanstack/react-query";

import { listUserRolesIndex } from "@/lib/domain/user";

/** Bulk role-name index for the whole org -- backs the role column and
 * role filter in the user list. */
export function useAdminUserRolesIndex() {
  return useQuery({
    queryKey: ["admin-user-roles-index"],
    queryFn: listUserRolesIndex,
    staleTime: 10_000,
  });
}
