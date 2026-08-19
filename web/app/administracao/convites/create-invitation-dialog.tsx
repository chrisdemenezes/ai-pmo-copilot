"use client";

import { useMemo, useState, type FormEvent } from "react";
import { Copy, Plus } from "lucide-react";
import { toast } from "sonner";

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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAdminRoles } from "@/lib/hooks/use-admin-roles";
import { useCreateAdminInvitation } from "@/lib/hooks/use-admin-invitation-mutations";
import { AdminApiError, type CreatedInvitation } from "@/lib/domain/invitation";

/**
 * Convites (D-054) -- creation is two steps, like API Keys: the invite
 * token only ever exists in this one response, so the dialog stays open
 * after success to reveal the invite link for delivery (manual today; via
 * a NotificationProvider once one exists), instead of closing immediately.
 */
export function CreateInvitationDialog() {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [roleName, setRoleName] = useState("");
  const [created, setCreated] = useState<CreatedInvitation | null>(null);

  const roles = useAdminRoles();
  const mutation = useCreateAdminInvitation();

  const inviteLink = useMemo(() => {
    if (!created) return "";
    if (typeof window === "undefined") return `/convite/${created.plaintextToken}`;
    return `${window.location.origin}/convite/${created.plaintextToken}`;
  }, [created]);

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      setEmail("");
      setRoleName("");
      setCreated(null);
      mutation.reset();
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (email.trim().length === 0 || roleName.length === 0 || mutation.isPending) return;

    mutation.mutate(
      { email: email.trim(), roleName },
      { onSuccess: (invitation) => setCreated(invitation) },
    );
  }

  async function copyLink() {
    if (!created) return;
    await navigator.clipboard.writeText(inviteLink);
    toast("Link do convite copiado");
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> Novo convite
        </Button>
      </DialogTrigger>
      <DialogContent>
        {created ? (
          <>
            <DialogHeader>
              <DialogTitle>Convite criado</DialogTitle>
              <DialogDescription>
                Copie e entregue este link agora -- ele não será mostrado novamente.
              </DialogDescription>
            </DialogHeader>
            <div className="flex items-center gap-2 rounded-md border border-border bg-surface-2 p-3">
              <code className="flex-1 overflow-x-auto whitespace-nowrap font-mono text-sm">
                {inviteLink}
              </code>
              <Button type="button" variant="outline" size="sm" onClick={copyLink}>
                <Copy /> Copiar
              </Button>
            </div>
            <DialogFooter>
              <Button onClick={() => handleOpenChange(false)}>Concluir</Button>
            </DialogFooter>
          </>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <DialogHeader>
              <DialogTitle>Novo convite</DialogTitle>
              <DialogDescription>
                A pessoa convidada define a própria senha ao aceitar -- você nunca a vê.
              </DialogDescription>
            </DialogHeader>

            <div className="flex flex-col gap-2">
              <Label htmlFor="create-invitation-email">E-mail</Label>
              <Input
                id="create-invitation-email"
                type="email"
                required
                placeholder="pessoa@empresa.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="create-invitation-role">Papel</Label>
              <Select value={roleName} onValueChange={setRoleName}>
                <SelectTrigger id="create-invitation-role" className="w-full">
                  <SelectValue placeholder="Selecione um papel" />
                </SelectTrigger>
                <SelectContent>
                  {(roles.data ?? []).map((role) => (
                    <SelectItem key={role.id} value={role.name}>
                      {role.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {mutation.isError && (
              <p className="text-sm text-danger" role="alert">
                {mutation.error instanceof AdminApiError
                  ? mutation.error.message
                  : "Falha ao criar convite."}
              </p>
            )}

            <DialogFooter>
              <Button
                type="submit"
                disabled={
                  email.trim().length === 0 || roleName.length === 0 || mutation.isPending
                }
              >
                {mutation.isPending ? "Criando..." : "Criar"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
