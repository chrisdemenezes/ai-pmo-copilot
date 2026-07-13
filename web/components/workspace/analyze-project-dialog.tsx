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
import { useSubmitMeetingIntelligence } from "@/lib/hooks/use-submit-meeting-intelligence";
import { ANALYSIS_CATALOG, type AnalysisCatalogEntry } from "@/lib/workspace/analysis-catalog";
import { isHighAttentionRisk } from "@/lib/workspace/risk-momentum";
import { impactHeadline } from "@/lib/workspace/meeting-momentum";
import { WorkspaceFetchError } from "@/lib/hooks/workspace-fetch-error";
import { hasMeetingShape, hasRiskShape, hasStatusShape } from "@/lib/workspace/types";

const MIN_LENGTH = 10;
const MAX_LENGTH = 20000;

/**
 * Botão + Dialog autocontidos (mesmo padrão de AnalysisHistory, TIP-004).
 * Pergunta -> Capability -> Executor (FS-006 §2.1): o usuário só vê a
 * pergunta (Tabs, já existente no Design System, reservado para este
 * momento desde a FS-005 §2); a Capability e o Executor são internos.
 * Contexto é um único campo compartilhado entre as abas -- só o rótulo
 * muda por aba ativa (a reunião usa "transcript" no backend, único caso
 * entre os 3, FS-006 §2.2).
 */
export function AnalyzeProjectDialog({ projectName }: { projectName: string }) {
  const [open, setOpen] = useState(false);
  const [context, setContext] = useState("");
  const [activeKind, setActiveKind] = useState<AnalysisCatalogEntry["kind"]>(
    ANALYSIS_CATALOG[0].kind,
  );

  const statusMutation = useSubmitProjectStatus(projectName);
  const riskMutation = useSubmitRiskReview(projectName);
  const meetingMutation = useSubmitMeetingIntelligence(projectName);
  const mutation =
    activeKind === "risk" ? riskMutation : activeKind === "meeting" ? meetingMutation : statusMutation;

  const trimmedLength = context.trim().length;
  const isValid = trimmedLength >= MIN_LENGTH && context.length <= MAX_LENGTH;

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      setContext("");
      statusMutation.reset();
      riskMutation.reset();
      meetingMutation.reset();
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

    if (activeKind === "meeting") {
      meetingMutation.mutate(context, {
        onSuccess: (data) => {
          const preview = hasMeetingShape(data.model_output)
            ? impactHeadline(
                data.model_output.decisions.length,
                data.model_output.issues.length,
                data.model_output.action_items.length,
              )
            : null;
          toast("Análise concluída", {
            description: preview
              ? `Comunicação de "${projectName}": ${preview}.`
              : `Comunicação de "${projectName}" atualizada.`,
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

  const textareaLabel = activeKind === "meeting" ? "Contexto da reunião" : "Contexto do projeto";
  const textareaPlaceholder =
    activeKind === "meeting"
      ? "Cole a ata, notas ou transcrição da reunião..."
      : "Descreva o contexto atual do projeto para a análise...";

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
          <DialogDescription>O que você quer entender sobre este projeto?</DialogDescription>
        </DialogHeader>

        <Tabs value={activeKind} onValueChange={(value) => setActiveKind(value as AnalysisCatalogEntry["kind"])}>
          <TabsList>
            {ANALYSIS_CATALOG.map((entry) => (
              <TabsTrigger key={entry.kind} value={entry.kind}>
                {entry.goalLabel}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        <div className="flex flex-col gap-2">
          <Textarea
            aria-label={textareaLabel}
            placeholder={textareaPlaceholder}
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
