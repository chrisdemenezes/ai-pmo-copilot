"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { healthStatusLabel } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useSubmitProjectStatus } from "@/lib/hooks/use-submit-project-status";
import { useSubmitRiskReview } from "@/lib/hooks/use-submit-risk-review";
import { ANALYSIS_CATALOG, type AnalysisCatalogEntry } from "@/lib/workspace/analysis-catalog";
import { isHighAttentionRisk } from "@/lib/workspace/risk-momentum";
import { WorkspaceFetchError } from "@/lib/hooks/workspace-fetch-error";
import { hasRiskShape, hasStatusShape } from "@/lib/workspace/types";

const MIN_LENGTH = 10;
const MAX_LENGTH = 20000;

/**
 * Botão + Dialog autocontidos (mesmo padrão de AnalysisHistory, TIP-004).
 * Com o catálogo em 2+ entradas (TIP-006), a escolha do tipo passa a usar
 * Tabs -- já existente no Design System, nunca antes usado em produção,
 * reservado exatamente para este momento (FS-005 §2). Contexto é um único
 * campo compartilhado entre as abas: descrever a situação do projeto não
 * muda por tipo de análise, só o agente que a interpreta.
 */
export function AnalyzeProjectDialog({ projectName }: { projectName: string }) {
  const [open, setOpen] = useState(false);
  const [context, setContext] = useState("");
  const [activeKind, setActiveKind] = useState<AnalysisCatalogEntry["kind"]>(
    ANALYSIS_CATALOG[0].kind,
  );

  const statusMutation = useSubmitProjectStatus(projectName);
  const riskMutation = useSubmitRiskReview(projectName);
  const mutation = activeKind === "risk" ? riskMutation : statusMutation;

  const trimmedLength = context.trim().length;
  const isValid = trimmedLength >= MIN_LENGTH && context.length <= MAX_LENGTH;

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      setContext("");
      statusMutation.reset();
      riskMutation.reset();
    }
  }

  function handleSubmit() {
    if (!isValid || mutation.isPending) return;

    if (activeKind === "risk") {
      riskMutation.mutate(context, {
        // "structured: true" alone doesn't guarantee this response actually
        // matches RiskModelOutput (confirmed against the real backend --
        // see hasRiskShape's doc comment), so the count preview only trusts
        // a response that passes the shape check.
        onSuccess: (data) => {
          const attentionCount = hasRiskShape(data.model_output)
            ? data.model_output.risks.filter(isHighAttentionRisk).length
            : null;
          toast("Análise concluída", {
            description:
              attentionCount !== null
                ? `Avaliação de Riscos de "${projectName}": ${attentionCount} risco(s) exigem atenção.`
                : `Avaliação de Riscos de "${projectName}" atualizada.`,
          });
          setOpen(false);
        },
      });
      return;
    }

    statusMutation.mutate(context, {
      // Decision Momentum (Decision Experience Review, Rev. 2): the
      // confirmation previews the verdict instead of a mute "concluído" --
      // health_status is already in the mutation response, zero new call.
      // Same shape caveat as the risk branch above (hasStatusShape).
      onSuccess: (data) => {
        const healthStatus = hasStatusShape(data.model_output) ? data.model_output.health_status : null;
        toast("Análise concluída", {
          description: healthStatus
            ? `Status Executivo de "${projectName}": ${healthStatusLabel(healthStatus)}.`
            : `Status Executivo de "${projectName}" atualizado.`,
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
          {ANALYSIS_CATALOG.length === 1 ? (
            <DialogDescription>
              Tipo de análise:{" "}
              <span className="font-medium text-ink">{ANALYSIS_CATALOG[0].goalLabel}</span>
            </DialogDescription>
          ) : (
            <DialogDescription>Escolha o tipo de análise</DialogDescription>
          )}
        </DialogHeader>

        {ANALYSIS_CATALOG.length > 1 ? (
          <Tabs value={activeKind} onValueChange={(value) => setActiveKind(value as AnalysisCatalogEntry["kind"])}>
            <TabsList>
              {ANALYSIS_CATALOG.map((entry) => (
                <TabsTrigger key={entry.kind} value={entry.kind}>
                  {entry.goalLabel}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        ) : null}

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
