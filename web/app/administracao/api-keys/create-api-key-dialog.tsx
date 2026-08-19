"use client";

import { useState, type FormEvent } from "react";
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
import { useCreateAdminApiKey } from "@/lib/hooks/use-admin-api-key-mutations";
import { AdminApiError, type CreatedApiKey } from "@/lib/domain/api-key";

/**
 * API Keys (D-051) -- creation is two steps, unlike Create User: the
 * plaintext key only ever exists in this one response, so the dialog
 * stays open after success to show it, instead of closing immediately.
 */
export function CreateApiKeyDialog() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [createdKey, setCreatedKey] = useState<CreatedApiKey | null>(null);

  const mutation = useCreateAdminApiKey();

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      setName("");
      setCreatedKey(null);
      mutation.reset();
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (name.trim().length === 0 || mutation.isPending) return;

    mutation.mutate(name, {
      onSuccess: (apiKey) => setCreatedKey(apiKey),
    });
  }

  async function copyKey() {
    if (!createdKey) return;
    await navigator.clipboard.writeText(createdKey.plaintextKey);
    toast("Chave copiada");
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> Nova chave
        </Button>
      </DialogTrigger>
      <DialogContent>
        {createdKey ? (
          <>
            <DialogHeader>
              <DialogTitle>Chave criada</DialogTitle>
              <DialogDescription>
                Copie e guarde esta chave agora -- ela não será mostrada novamente.
              </DialogDescription>
            </DialogHeader>
            <div className="flex items-center gap-2 rounded-md border border-border bg-surface-2 p-3">
              <code className="flex-1 overflow-x-auto whitespace-nowrap font-mono text-sm">
                {createdKey.plaintextKey}
              </code>
              <Button type="button" variant="outline" size="sm" onClick={copyKey}>
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
              <DialogTitle>Nova chave de API</DialogTitle>
              <DialogDescription>
                Dê um nome que identifique onde esta chave será usada.
              </DialogDescription>
            </DialogHeader>

            <div className="flex flex-col gap-2">
              <Label htmlFor="create-api-key-name">Nome</Label>
              <Input
                id="create-api-key-name"
                required
                placeholder="Ex.: CI pipeline"
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </div>

            {mutation.isError && (
              <p className="text-sm text-danger" role="alert">
                {mutation.error instanceof AdminApiError
                  ? mutation.error.message
                  : "Falha ao criar chave de API."}
              </p>
            )}

            <DialogFooter>
              <Button type="submit" disabled={name.trim().length === 0 || mutation.isPending}>
                {mutation.isPending ? "Criando..." : "Criar"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
