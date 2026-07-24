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
import { useRevokeAdminSession } from "@/lib/hooks/use-admin-session-mutations";
import { AdminApiError } from "@/lib/domain/api-key";
import type { AdminSession } from "@/lib/domain/session";

/** Revocation takes effect on the session's next request -- always passes
 * through explicit confirmation, same discipline as RevokeApiKeyButton. */
export function RevokeSessionButton({ session }: { session: AdminSession }) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const mutation = useRevokeAdminSession();

  function confirmRevoke() {
    mutation.mutate(session.id, {
      onSuccess: () => {
        toast("Sessão revogada", { description: `Usuário #${session.userId}` });
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
            <DialogTitle>Revogar esta sessão?</DialogTitle>
            <DialogDescription>
              O usuário desta sessão perderá o acesso na próxima requisição e precisará
              entrar novamente. Esta ação não pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          {mutation.isError && (
            <p className="text-sm text-danger" role="alert">
              {mutation.error instanceof AdminApiError
                ? mutation.error.message
                : "Falha ao revogar sessão."}
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
