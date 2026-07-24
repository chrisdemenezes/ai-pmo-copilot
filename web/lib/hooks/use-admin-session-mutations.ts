import { useMutation, useQueryClient } from "@tanstack/react-query";

import { revokeSession } from "@/lib/domain/session";

export function useRevokeAdminSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => revokeSession(sessionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-sessions"] }),
  });
}
