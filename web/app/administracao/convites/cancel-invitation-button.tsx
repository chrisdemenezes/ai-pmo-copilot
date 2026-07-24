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
import { useCancelAdminInvitation } from "@/lib/hooks/use-admin-invitation-mutations";
import { AdminApiError, type Invitation } from "@/lib/domain/invitation";

/** Cancelling is irreversible (a cancelled invitation can never be
 * accepted) -- always passes through explicit confirmation, same
 * discipline as RevokeApiKeyButton. */
export function CancelInvitationButton({ invitation }: { invitation: Invitation }) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const mutation = useCancelAdminInvitation();

  function confirmCancel() {
    mutation.mutate(invitation.id, {
      onSuccess: () => {
        toast("Convite cancelado", { description: invitation.email });
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
        Cancelar
      </Button>
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancelar convite de &ldquo;{invitation.email}&rdquo;?</DialogTitle>
            <DialogDescription>
              O link deste convite deixará de funcionar imediatamente. Esta ação não pode
              ser desfeita.
            </DialogDescription>
          </DialogHeader>
          {mutation.isError && (
            <p className="text-sm text-danger" role="alert">
              {mutation.error instanceof AdminApiError
                ? mutation.error.message
                : "Falha ao cancelar convite."}
            </p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Voltar
            </Button>
            <Button onClick={confirmCancel} disabled={mutation.isPending}>
              {mutation.isPending ? "Cancelando..." : "Cancelar convite"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
