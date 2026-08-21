import { useMutation, useQueryClient } from "@tanstack/react-query";

import { reindexDocument, uploadDocument, uploadDocumentFromUrl } from "@/lib/domain/document";

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

export function useUploadAdminDocumentFromUrl() {
  const invalidate = useInvalidateAdminDocuments();
  return useMutation({
    mutationFn: ({ url, sourceName }: { url: string; sourceName?: string }) =>
      uploadDocumentFromUrl(url, sourceName),
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
