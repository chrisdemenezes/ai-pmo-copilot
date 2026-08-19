"use client";

import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useReindexAdminDocument } from "@/lib/hooks/use-admin-document-mutations";
import { DocumentApiError, type StratechDocument } from "@/lib/domain/document";

/** Retry path for a document left in "ingested_pending_index"/"failed"
 * (Technical Design §3.2) -- indexing failure is never hidden, always
 * retryable from the same row. */
export function ReindexDocumentButton({ document }: { document: StratechDocument }) {
  const mutation = useReindexAdminDocument();

  function handleReindex() {
    mutation.mutate(document.documentId, {
      onSuccess: () => toast("Documento reindexado", { description: document.sourceName }),
      onError: (error) => {
        toast("Falha ao reindexar", {
          description: error instanceof DocumentApiError ? error.message : document.sourceName,
        });
      },
    });
  }

  return (
    <Button variant="outline" size="sm" onClick={handleReindex} disabled={mutation.isPending}>
      {mutation.isPending ? "Reindexando..." : "Reindexar"}
    </Button>
  );
}
