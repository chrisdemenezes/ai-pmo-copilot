"use client";

import { useState } from "react";
import { ShieldCheck, X } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminRoles } from "@/lib/hooks/use-admin-roles";
import { useAdminUserRoles } from "@/lib/hooks/use-admin-user-roles";
import { useAssignAdminUserRole, useRemoveAdminUserRole } from "@/lib/hooks/use-admin-user-mutations";
import { AdminApiError, type AdminUser } from "@/lib/domain/user";

export function UserRolesDialog({ user }: { user: AdminUser }) {
  const [open, setOpen] = useState(false);
  const [roleToAssign, setRoleToAssign] = useState("");
  const [roleToRemove, setRoleToRemove] = useState<string | null>(null);

  const allRoles = useAdminRoles();
  const currentRoles = useAdminUserRoles(open ? user.id : null);
  const assignMutation = useAssignAdminUserRole();
  const removeMutation = useRemoveAdminUserRole();

  const currentRoleNames = new Set((currentRoles.data ?? []).map((role) => role.name));
  const assignableRoles = (allRoles.data ?? []).filter((role) => !currentRoleNames.has(role.name));

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      setRoleToAssign("");
      setRoleToRemove(null);
      assignMutation.reset();
      removeMutation.reset();
    }
  }

  function handleAssign() {
    if (!roleToAssign || assignMutation.isPending) return;
    assignMutation.mutate(
      { userId: user.id, roleName: roleToAssign },
      {
        onSuccess: () => {
          toast("Papel atribuído", { description: `${user.displayName} -> ${roleToAssign}` });
          setRoleToAssign("");
        },
      },
    );
  }

  function confirmRemove() {
    if (!roleToRemove || removeMutation.isPending) return;
    const name = roleToRemove;
    removeMutation.mutate(
      { userId: user.id, roleName: name },
      {
        onSuccess: () => {
          toast("Papel removido", { description: `${user.displayName} -> ${name}` });
          setRoleToRemove(null);
        },
        // Stays open on error -- the last-active-admin guard becomes
        // visible in the confirmation dialog itself, below.
      },
    );
  }

  return (
    <>
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm" aria-label={`Papéis de ${user.displayName}`}>
            <ShieldCheck /> Papéis
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Papéis de {user.displayName}</DialogTitle>
            <DialogDescription>Associação de Roles (RBAC).</DialogDescription>
          </DialogHeader>

          {currentRoles.isPending ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-6 w-32" />
              <Skeleton className="h-6 w-24" />
            </div>
          ) : currentRoles.isError ? (
            <p className="text-sm text-danger" role="alert">
              Falha ao carregar papéis atuais.
            </p>
          ) : (currentRoles.data ?? []).length === 0 ? (
            <p className="text-sm text-ink-muted">Nenhum papel atribuído.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {(currentRoles.data ?? []).map((role) => (
                <Badge key={role.id} variant="neutral" className="gap-1">
                  {role.name}
                  <button
                    type="button"
                    aria-label={`Remover papel ${role.name}`}
                    onClick={() => setRoleToRemove(role.name)}
                    className="ml-1 rounded-full hover:opacity-70"
                  >
                    <X className="size-3" />
                  </button>
                </Badge>
              ))}
            </div>
          )}

          <div className="flex items-end gap-2">
            <div className="flex flex-1 flex-col gap-2">
              <Select value={roleToAssign} onValueChange={setRoleToAssign}>
                <SelectTrigger className="w-full" aria-label="Atribuir novo papel">
                  <SelectValue placeholder="Atribuir novo papel" />
                </SelectTrigger>
                <SelectContent>
                  {assignableRoles.map((role) => (
                    <SelectItem key={role.id} value={role.name}>
                      {role.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleAssign} disabled={!roleToAssign || assignMutation.isPending}>
              {assignMutation.isPending ? "Atribuindo..." : "Atribuir"}
            </Button>
          </div>

          {assignMutation.isError && (
            <p className="text-sm text-danger" role="alert">
              {assignMutation.error instanceof AdminApiError
                ? assignMutation.error.message
                : "Falha ao atribuir papel."}
            </p>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={roleToRemove !== null} onOpenChange={(next) => !next && setRoleToRemove(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remover papel &quot;{roleToRemove}&quot;?</DialogTitle>
            <DialogDescription>
              {user.displayName} perderá as permissões associadas a este papel.
            </DialogDescription>
          </DialogHeader>
          {removeMutation.isError && (
            <p className="text-sm text-danger" role="alert">
              {removeMutation.error instanceof AdminApiError
                ? removeMutation.error.message
                : "Falha ao remover papel."}
            </p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setRoleToRemove(null)}>
              Cancelar
            </Button>
            <Button onClick={confirmRemove} disabled={removeMutation.isPending}>
              {removeMutation.isPending ? "Removendo..." : "Remover"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
