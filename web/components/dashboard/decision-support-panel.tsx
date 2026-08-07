"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { DecisionSupportScope, DecisionSupportScopeType } from "@/lib/dashboard/types";
import { usePortfolios } from "@/lib/hooks/use-portfolios";
import { useProjects } from "@/lib/hooks/use-projects";
import { DecisionSupportFetchError, useAskDecisionSupport } from "@/lib/hooks/use-ask-decision-support";

const SCOPE_LABELS: Record<DecisionSupportScopeType, string> = {
  project: "Projeto",
  portfolio: "Portfólio",
  organization: "Organização",
};

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

  const { data: projects } = useProjects();
  const { data: portfolios } = usePortfolios();
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
          <div className="flex flex-1 flex-col gap-2">
            <Select value={scopeType} onValueChange={handleScopeTypeChange}>
              <SelectTrigger className="w-full" aria-label="Escopo">
                <SelectValue placeholder="Escopo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="project">{SCOPE_LABELS.project}</SelectItem>
                <SelectItem value="portfolio">{SCOPE_LABELS.portfolio}</SelectItem>
                <SelectItem value="organization">{SCOPE_LABELS.organization}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {scopeType === "project" && (
            <div className="flex flex-1 flex-col gap-2">
              <Select value={projectId} onValueChange={setProjectId}>
                <SelectTrigger className="w-full" aria-label="Projeto">
                  <SelectValue placeholder="Selecionar projeto" />
                </SelectTrigger>
                <SelectContent>
                  {(projects ?? []).map((project) => (
                    <SelectItem key={project.id} value={project.id}>
                      {project.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {scopeType === "portfolio" && (
            <div className="flex flex-1 flex-col gap-2">
              <Select value={portfolioId} onValueChange={setPortfolioId}>
                <SelectTrigger className="w-full" aria-label="Portfólio">
                  <SelectValue placeholder="Selecionar portfólio" />
                </SelectTrigger>
                <SelectContent>
                  {(portfolios ?? []).map((portfolio) => (
                    <SelectItem key={portfolio.id} value={portfolio.id}>
                      {portfolio.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

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
            <div className="flex flex-wrap gap-1">
              {result.advisors_used.map((advisorName) => (
                <Badge key={advisorName} variant="outline">
                  {advisorName}
                </Badge>
              ))}
            </div>
            {result.citations.length > 0 && (
              <ul className="flex flex-col gap-1 text-xs text-ink-muted">
                {result.citations.map((citation, index) => (
                  <li key={`${citation.advisor_name}-${citation.source_type}-${citation.source_id}-${index}`}>
                    {citation.advisor_name}: {citation.source_label}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
