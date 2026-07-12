"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
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
import { Textarea } from "@/components/ui/textarea";
import { useSubmitProjectStatus } from "@/lib/hooks/use-submit-project-status";
import { ANALYSIS_CATALOG } from "@/lib/workspace/analysis-catalog";
import { WorkspaceFetchError } from "@/lib/hooks/workspace-fetch-error";

const MIN_LENGTH = 10;
const MAX_LENGTH = 20000;

// FS-005 §2/§4: só há 1 entrada real hoje (ANALYSIS_CATALOG), então o tipo é
// exibido como confirmação, não como escolha -- forçar um clique numa lista
// de 1 item seria ruído. risk_review/meeting_intelligence chegam como novas
// entradas nesse mesmo catálogo, e este rótulo passa a listar todas.
const analysisType = ANALYSIS_CATALOG[0];

/** Botão + Dialog autocontidos (mesmo padrão de AnalysisHistory, TIP-004). */
export function AnalyzeProjectDialog({ projectName }: { projectName: string }) {
  const [open, setOpen] = useState(false);
  const [context, setContext] = useState("");
  const mutation = useSubmitProjectStatus(projectName);

  const trimmedLength = context.trim().length;
  const isValid = trimmedLength >= MIN_LENGTH && context.length <= MAX_LENGTH;

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      setContext("");
      mutation.reset();
    }
  }

  function handleSubmit() {
    if (!isValid || mutation.isPending) return;
    mutation.mutate(context, {
      onSuccess: () => {
        toast("Análise concluída", {
          description: `Status Executivo de "${projectName}" atualizado.`,
        });
        setOpen(false);
      },
    });
  }

  const errorMessage =
    mutation.error instanceof WorkspaceFetchError
      ? mutation.error.body.detail
      : mutation.isError
        ? "Não foi possível concluir a análise. Tente novamente."
        : null;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Sparkles aria-hidden="true" />
          Analisar Projeto
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Analisar Projeto</DialogTitle>
          <DialogDescription>
            Tipo de análise: <span className="font-medium text-ink">{analysisType.goalLabel}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Textarea
            aria-label="Contexto do projeto"
            placeholder="Descreva o contexto atual do projeto para a análise..."
            value={context}
            onChange={(event) => setContext(event.target.value)}
            disabled={mutation.isPending}
            rows={6}
          />
          <div className="flex items-center justify-between text-xs text-ink-muted">
            <span>
              {context.length} / {MAX_LENGTH} caracteres (mínimo {MIN_LENGTH})
            </span>
          </div>
          {errorMessage ? <p className="text-sm text-danger">{errorMessage}</p> : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={mutation.isPending}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={!isValid || mutation.isPending}>
            {mutation.isPending ? "Executando…" : "Executar Análise"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
