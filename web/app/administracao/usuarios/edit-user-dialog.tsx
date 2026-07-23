"use client";

import { useState, type FormEvent } from "react";
import { Pencil } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useUpdateAdminUser } from "@/lib/hooks/use-admin-user-mutations";
import { AdminApiError, type AdminUser } from "@/lib/domain/user";

export function EditUserDialog({ user }: { user: AdminUser }) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState(user.email);
  const [displayName, setDisplayName] = useState(user.displayName);

  const mutation = useUpdateAdminUser();

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      setEmail(user.email);
      setDisplayName(user.displayName);
      mutation.reset();
    }
  }

  const isValid = email.trim().length > 0 && displayName.trim().length > 0;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isValid || mutation.isPending) return;

    mutation.mutate(
      { userId: user.id, input: { email, displayName } },
      {
        onSuccess: () => {
          toast("Usuário atualizado", { description: displayName });
          setOpen(false);
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" aria-label={`Editar ${user.displayName}`}>
          <Pencil />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Editar usuário</DialogTitle>
          </DialogHeader>

          <div className="flex flex-col gap-2">
            <Label htmlFor={`edit-user-email-${user.id}`}>E-mail</Label>
            <Input
              id={`edit-user-email-${user.id}`}
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor={`edit-user-name-${user.id}`}>Nome</Label>
            <Input
              id={`edit-user-name-${user.id}`}
              required
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
            />
          </div>

          {mutation.isError && (
            <p className="text-sm text-danger" role="alert">
              {mutation.error instanceof AdminApiError
                ? mutation.error.message
                : "Falha ao atualizar usuário."}
            </p>
          )}

          <DialogFooter>
            <Button type="submit" disabled={!isValid || mutation.isPending}>
              {mutation.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
