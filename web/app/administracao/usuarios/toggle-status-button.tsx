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
import { useSetAdminUserActive } from "@/lib/hooks/use-admin-user-mutations";
import { AdminApiError, type AdminUser } from "@/lib/domain/user";

/**
 * Ativação é reversível e de baixo risco -- aplicada direto. Inativação
 * bloqueia o acesso do usuário, então é uma operação sensível (Founder,
 * critério 4): sempre passa por confirmação explícita.
 */
export function ToggleStatusButton({ user }: { user: AdminUser }) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const mutation = useSetAdminUserActive();

  function activate() {
    mutation.mutate(
      { userId: user.id, isActive: true },
      {
        onSuccess: () => toast("Usuário ativado", { description: user.displayName }),
      },
    );
  }

  function confirmDeactivate() {
    mutation.mutate(
      { userId: user.id, isActive: false },
      {
        onSuccess: () => {
          toast("Usuário inativado", { description: user.displayName });
          setConfirmOpen(false);
        },
        // Stays open on error -- the message below is the only place the
        // Founder's guards (auto-inativação, último administrador) become
        // visible to the admin who triggered them.
      },
    );
  }

  if (user.isActive) {
    return (
      <>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setConfirmOpen(true)}
          disabled={mutation.isPending}
        >
          Inativar
        </Button>
        <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Inativar {user.displayName}?</DialogTitle>
              <DialogDescription>
                O usuário deixará de conseguir entrar ou acessar a API até ser reativado.
              </DialogDescription>
            </DialogHeader>
            {mutation.isError && (
              <p className="text-sm text-danger" role="alert">
                {mutation.error instanceof AdminApiError
                  ? mutation.error.message
                  : "Falha ao inativar usuário."}
              </p>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setConfirmOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={confirmDeactivate} disabled={mutation.isPending}>
                {mutation.isPending ? "Inativando..." : "Inativar"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </>
    );
  }

  return (
    <Button variant="outline" size="sm" onClick={activate} disabled={mutation.isPending}>
      {mutation.isPending ? "Ativando..." : "Ativar"}
    </Button>
  );
}
