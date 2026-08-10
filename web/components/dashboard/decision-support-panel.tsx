"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { CompositionTraceSummary } from "@/components/dashboard/composition-trace-summary";
import { ScopeSelector } from "@/components/dashboard/scope-selector";
import type { DecisionSupportScope, DecisionSupportScopeType } from "@/lib/dashboard/types";
import { DecisionSupportFetchError, useAskDecisionSupport } from "@/lib/hooks/use-ask-decision-support";

/**
 * Decision Support (Wave 6) -- primeiro consumidor de produção da
 * Executive Intelligence. Painel autocontido, adicionado ao Dashboard
 * Executivo já existente (Founder §12: "não criar dashboard novo ou
 * experiência ampla"). Escopo explicitamente obrigatório (Vision,
 * Princípio 13) -- "Organização" nunca é a seleção inicial.
 */
export function DecisionSupportPanel() {
  const [question, setQuestion] = useState("");
  const [scopeType, setScopeType] = useState<DecisionSupportScopeType | "">("");
  const [projectId, setProjectId] = useState("");
  const [portfolioId, setPortfolioId] = useState("");

  const mutation = useAskDecisionSupport();

  const scope: DecisionSupportScope | null =
    scopeType === "project" && projectId
      ? { type: "project", project_id: Number(projectId) }
      : scopeType === "portfolio" && portfolioId
        ? { type: "portfolio", portfolio_id: Number(portfolioId) }
        : scopeType === "organization"
          ? { type: "organization" }
          : null;

  const canSubmit = question.trim().length >= 3 && scope !== null && !mutation.isPending;

  function handleScopeTypeChange(value: string) {
    setScopeType(value as DecisionSupportScopeType);
    setProjectId("");
    setPortfolioId("");
  }

  function handleSubmit() {
    if (!scope) return;
    mutation.mutate({ question, scope });
  }

  const result = mutation.data;
  const errorDetail =
    mutation.error instanceof DecisionSupportFetchError
      ? mutation.error.body.detail
      : mutation.isError
        ? "Não foi possível obter uma resposta agora."
        : null;

  return (
    <Card className="border-accent-soft">
      <CardContent className="flex flex-col gap-4 p-5">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-accent" aria-hidden="true" />
          <p className="font-display text-sm font-semibold text-ink">Decision Support</p>
        </div>

        <Textarea
          placeholder="Pergunta executiva -- ex.: existe risco que ameace o alinhamento estratégico deste projeto?"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          aria-label="Pergunta executiva"
        />

        <div className="flex flex-wrap items-end gap-2">
          <ScopeSelector
            scopeType={scopeType}
            onScopeTypeChange={handleScopeTypeChange}
            projectId={projectId}
            onProjectIdChange={setProjectId}
            portfolioId={portfolioId}
            onPortfolioIdChange={setPortfolioId}
          />

          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {mutation.isPending ? "Perguntando..." : "Perguntar"}
          </Button>
        </div>

        {errorDetail && (
          <p className="text-sm text-danger" role="alert">
            {errorDetail}
          </p>
        )}

        {result && result.insufficient_basis && (
          <p className="text-sm text-ink-muted" role="status">
            Base insuficiente para responder a esta pergunta com o escopo selecionado.
          </p>
        )}

        {result && !result.insufficient_basis && (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-ink">{result.answer}</p>
            <CompositionTraceSummary
              advisorsUsed={result.advisors_used}
              compositionTrace={result.composition_trace}
              citations={result.citations}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
