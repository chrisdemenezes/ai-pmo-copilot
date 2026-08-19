"use client";

import { useRef, useState, type FormEvent } from "react";
import { Plus, Upload } from "lucide-react";

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
import { useUploadAdminDocument } from "@/lib/hooks/use-admin-document-mutations";
import { DocumentApiError } from "@/lib/domain/document";

/**
 * Document Ingestion (Wave 5, Epic W5-0) -- upload mínimo: apenas
 * texto/markdown já normalizado (Technical Design §11, risco residual 3 --
 * nenhum parser de PDF/binário introduzido nesta Epic).
 */
export function UploadDocumentDialog() {
  const [open, setOpen] = useState(false);
  const [sourceName, setSourceName] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const mutation = useUploadAdminDocument();

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      setSourceName("");
      mutation.reset();
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (!file || mutation.isPending) return;

    mutation.mutate(
      { file, sourceName: sourceName.trim() || undefined },
      { onSuccess: () => handleOpenChange(false) },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> Enviar documento
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Enviar documento</DialogTitle>
            <DialogDescription>
              Apenas arquivos de texto ou markdown (.txt, .md). O documento é indexado
              imediatamente após o envio.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-2">
            <Label htmlFor="upload-document-file">Arquivo</Label>
            <Input
              id="upload-document-file"
              type="file"
              accept=".txt,.md,text/plain,text/markdown"
              ref={fileInputRef}
              required
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="upload-document-source-name">Nome (opcional)</Label>
            <Input
              id="upload-document-source-name"
              placeholder="Padrão: nome do arquivo"
              value={sourceName}
              onChange={(event) => setSourceName(event.target.value)}
            />
          </div>

          {mutation.isError && (
            <p className="text-sm text-danger" role="alert">
              {mutation.error instanceof DocumentApiError
                ? mutation.error.message
                : "Falha ao enviar documento."}
            </p>
          )}

          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              <Upload /> {mutation.isPending ? "Enviando..." : "Enviar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
