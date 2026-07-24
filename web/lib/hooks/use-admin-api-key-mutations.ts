import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createApiKey, revokeApiKey } from "@/lib/domain/api-key";

function useInvalidateAdminApiKeys() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["admin-api-keys"] });
}

export function useCreateAdminApiKey() {
  const invalidate = useInvalidateAdminApiKeys();
  return useMutation({
    mutationFn: (name: string) => createApiKey(name),
    onSuccess: invalidate,
  });
}

export function useRevokeAdminApiKey() {
  const invalidate = useInvalidateAdminApiKeys();
  return useMutation({
    mutationFn: (apiKeyId: string) => revokeApiKey(apiKeyId),
    onSuccess: invalidate,
  });
}
