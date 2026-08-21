"use client";

import { useState, type FormEvent } from "react";
import { Link as LinkIcon, Plus } from "lucide-react";

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
import { useUploadAdminDocumentFromUrl } from "@/lib/hooks/use-admin-document-mutations";
import { DocumentApiError } from "@/lib/domain/document";

/**
 * External Document Sources (V1 Product & Capability Completion, Package
 * L) -- first adapter only (http_url): busca um documento de texto/markdown
 * a partir de uma URL e o indexa pelo mesmo caminho de um upload manual.
 * Um segundo adaptador para um provedor SaaS real (SharePoint/Google
 * Drive/Confluence) é REAL PROVIDER VALIDATION = PENDING EXTERNAL
 * CREDENTIAL -- não implementado aqui, por falta de credencial real neste
 * ambiente.
 */
export function AddDocumentFromUrlDialog() {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [sourceName, setSourceName] = useState("");

  const mutation = useUploadAdminDocumentFromUrl();

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      setUrl("");
      setSourceName("");
      mutation.reset();
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!url.trim() || mutation.isPending) return;

    mutation.mutate(
      { url: url.trim(), sourceName: sourceName.trim() || undefined },
      { onSuccess: () => handleOpenChange(false) },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Plus /> Adicionar por URL
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Adicionar documento por URL</DialogTitle>
            <DialogDescription>
              Busca o conteúdo de texto ou markdown de uma URL e o indexa imediatamente,
              como um upload manual.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-2">
            <Label htmlFor="add-document-url">URL</Label>
            <Input
              id="add-document-url"
              type="url"
              placeholder="https://…"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              required
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="add-document-url-source-name">Nome (opcional)</Label>
            <Input
              id="add-document-url-source-name"
              placeholder="Padrão: nome derivado da URL"
              value={sourceName}
              onChange={(event) => setSourceName(event.target.value)}
            />
          </div>

          {mutation.isError && (
            <p className="text-sm text-danger" role="alert">
              {mutation.error instanceof DocumentApiError
                ? mutation.error.message
                : "Falha ao buscar documento pela URL."}
            </p>
          )}

          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              <LinkIcon /> {mutation.isPending ? "Buscando..." : "Adicionar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
