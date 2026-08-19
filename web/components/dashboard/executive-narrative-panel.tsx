"use client";

import { useState } from "react";
import { FileText } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { CompositionTraceSummary } from "@/components/dashboard/composition-trace-summary";
import { ScopeSelector } from "@/components/dashboard/scope-selector";
import type { DecisionSupportScope, DecisionSupportScopeType } from "@/lib/dashboard/types";
import {
  ExecutiveNarrativeFetchError,
  useGenerateExecutiveNarrative,
} from "@/lib/hooks/use-generate-executive-narrative";

/**
 * Executive Narrative (Wave 6) -- segundo consumidor de produção da
 * Executive Intelligence. Painel autocontido, distinto do
 * `DecisionSupportPanel` (Founder -- Technical Design Executive Narrative,
 * §2: as duas Capabilities nunca podem parecer aliases da mesma
 * funcionalidade): nenhum campo de pergunta, apenas o escopo -- botão
 * "Gerar Narrativa". Adicionado ao Dashboard Executivo já existente
 * (Founder §6: "não criar página nova"). Escopo explicitamente obrigatório
 * (Vision, Princípio 13) -- "Organização" nunca é a seleção inicial.
 */
export function ExecutiveNarrativePanel() {
  const [scopeType, setScopeType] = useState<DecisionSupportScopeType | "">("");
  const [projectId, setProjectId] = useState("");
  const [portfolioId, setPortfolioId] = useState("");

  const mutation = useGenerateExecutiveNarrative();

  const scope: DecisionSupportScope | null =
    scopeType === "project" && projectId
      ? { type: "project", project_id: Number(projectId) }
      : scopeType === "portfolio" && portfolioId
        ? { type: "portfolio", portfolio_id: Number(portfolioId) }
        : scopeType === "organization"
          ? { type: "organization" }
          : null;

  const canSubmit = scope !== null && !mutation.isPending;

  function handleScopeTypeChange(value: DecisionSupportScopeType) {
    setScopeType(value);
    setProjectId("");
    setPortfolioId("");
  }

  function handleSubmit() {
    if (!scope) return;
    mutation.mutate(scope);
  }

  const result = mutation.data;
  const errorDetail =
    mutation.error instanceof ExecutiveNarrativeFetchError
      ? mutation.error.body.detail
      : mutation.isError
        ? "Não foi possível gerar a narrativa agora."
        : null;

  return (
    <Card className="border-accent-soft">
      <CardContent className="flex flex-col gap-4 p-5">
        <div className="flex items-center gap-2">
          <FileText className="size-4 text-accent" aria-hidden="true" />
          <p className="font-display text-sm font-semibold text-ink">Narrativa Executiva</p>
        </div>

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
            {mutation.isPending ? "Gerando..." : "Gerar Narrativa"}
          </Button>
        </div>

        {errorDetail && (
          <p className="text-sm text-danger" role="alert">
            {errorDetail}
          </p>
        )}

        {result && result.insufficient_basis && (
          <p className="text-sm text-ink-muted" role="status">
            Base insuficiente para gerar uma narrativa com o escopo selecionado.
          </p>
        )}

        {result && !result.insufficient_basis && (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-ink">{result.narrative}</p>
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
