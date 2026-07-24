"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useRevokeAdminApiKey } from "@/lib/hooks/use-admin-api-key-mutations";
import { AdminApiError, type ApiKey } from "@/lib/domain/api-key";

/** Revocation is irreversible (Founder, critério 4: operação sensível) --
 * always passes through explicit confirmation, same discipline as
 * ToggleStatusButton's inativação path. */
export function RevokeApiKeyButton({ apiKey }: { apiKey: ApiKey }) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const mutation = useRevokeAdminApiKey();

  function confirmRevoke() {
    mutation.mutate(apiKey.id, {
      onSuccess: () => {
        toast("Chave revogada", { description: apiKey.name });
        setConfirmOpen(false);
      },
    });
  }

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setConfirmOpen(true)}
        disabled={mutation.isPending}
      >
        Revogar
      </Button>
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revogar &ldquo;{apiKey.name}&rdquo;?</DialogTitle>
            <DialogDescription>
              Qualquer sistema usando esta chave deixará de conseguir se autenticar
              imediatamente. Esta ação não pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          {mutation.isError && (
            <p className="text-sm text-danger" role="alert">
              {mutation.error instanceof AdminApiError
                ? mutation.error.message
                : "Falha ao revogar chave."}
            </p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={confirmRevoke} disabled={mutation.isPending}>
              {mutation.isPending ? "Revogando..." : "Revogar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
