"use client";

import { useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAdminRoles } from "@/lib/hooks/use-admin-roles";
import { useCreateAdminUser } from "@/lib/hooks/use-admin-user-mutations";
import { AdminApiError } from "@/lib/domain/user";

/**
 * User Management -- cadastro. A senha inicial é definida diretamente
 * aqui pelo administrador (Technical Design §1): não existe fluxo de
 * convite por e-mail nem de reset de senha nesta Capability.
 */
export function CreateUserDialog() {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [roleName, setRoleName] = useState("");

  const roles = useAdminRoles();
  const mutation = useCreateAdminUser();

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      setEmail("");
      setDisplayName("");
      setPassword("");
      setRoleName("");
      mutation.reset();
    }
  }

  const isValid =
    email.trim().length > 0 &&
    displayName.trim().length > 0 &&
    password.length > 0 &&
    roleName.length > 0;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isValid || mutation.isPending) return;

    mutation.mutate(
      { email, displayName, password, roleName },
      {
        onSuccess: (user) => {
          toast("Usuário cadastrado", { description: `${user.displayName} (${user.email})` });
          setOpen(false);
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> Novo usuário
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Cadastrar usuário</DialogTitle>
            <DialogDescription>
              Defina uma senha inicial -- o usuário poderá usá-la para entrar imediatamente.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-2">
            <Label htmlFor="create-user-email">E-mail</Label>
            <Input
              id="create-user-email"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="create-user-name">Nome</Label>
            <Input
              id="create-user-name"
              required
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="create-user-password">Senha inicial</Label>
            <Input
              id="create-user-password"
              type="password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="create-user-role">Papel</Label>
            <Select value={roleName} onValueChange={setRoleName}>
              <SelectTrigger id="create-user-role" className="w-full">
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
                : "Falha ao cadastrar usuário."}
            </p>
          )}

          <DialogFooter>
            <Button type="submit" disabled={!isValid || mutation.isPending}>
              {mutation.isPending ? "Cadastrando..." : "Cadastrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
