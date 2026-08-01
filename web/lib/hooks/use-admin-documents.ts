import { useQuery } from "@tanstack/react-query";

import { listDocuments } from "@/lib/domain/document";

/** Same query shape as useAdminApiKeys() -- see that hook for the
 * rationale (D-011 accessor pattern). */
export function useAdminDocuments() {
  return useQuery({
    queryKey: ["admin-documents"],
    queryFn: listDocuments,
    staleTime: 10_000,
  });
}
