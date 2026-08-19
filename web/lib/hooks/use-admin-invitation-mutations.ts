import { useMutation, useQueryClient } from "@tanstack/react-query";

import { cancelInvitation, createInvitation } from "@/lib/domain/invitation";

function useInvalidateAdminInvitations() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["admin-invitations"] });
}

export function useCreateAdminInvitation() {
  const invalidate = useInvalidateAdminInvitations();
  return useMutation({
    mutationFn: ({ email, roleName }: { email: string; roleName: string }) =>
      createInvitation(email, roleName),
    onSuccess: invalidate,
  });
}

export function useCancelAdminInvitation() {
  const invalidate = useInvalidateAdminInvitations();
  return useMutation({
    mutationFn: (invitationId: string) => cancelInvitation(invitationId),
    onSuccess: invalidate,
  });
}
