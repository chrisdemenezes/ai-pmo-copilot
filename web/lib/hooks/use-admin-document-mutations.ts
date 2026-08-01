import { useMutation, useQueryClient } from "@tanstack/react-query";

import { reindexDocument, uploadDocument } from "@/lib/domain/document";

function useInvalidateAdminDocuments() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["admin-documents"] });
}

export function useUploadAdminDocument() {
  const invalidate = useInvalidateAdminDocuments();
  return useMutation({
    mutationFn: ({ file, sourceName }: { file: File; sourceName?: string }) =>
      uploadDocument(file, sourceName),
    onSuccess: invalidate,
  });
}

export function useReindexAdminDocument() {
  const invalidate = useInvalidateAdminDocuments();
  return useMutation({
    mutationFn: (documentId: string) => reindexDocument(documentId),
    onSuccess: invalidate,
  });
}
