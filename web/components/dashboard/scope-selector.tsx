"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { DecisionSupportScopeType } from "@/lib/dashboard/types";
import { usePortfolios } from "@/lib/hooks/use-portfolios";
import { useProjects } from "@/lib/hooks/use-projects";

const SCOPE_LABELS: Record<DecisionSupportScopeType, string> = {
  project: "Projeto",
  portfolio: "Portfólio",
  organization: "Organização",
};

/**
 * Executive Intelligence Explicit Scope picker (Vision, Princípio 13) --
 * shared between every Capability that requires a scope (Decision Support,
 * Executive Narrative), extracted so neither panel duplicates this logic
 * (Technical Design -- Executive Narrative, §9). Never pre-selects a value
 * -- "Organização" is always a deliberate choice, never the initial state.
 */
export function ScopeSelector({
  scopeType,
  onScopeTypeChange,
  projectId,
  onProjectIdChange,
  portfolioId,
  onPortfolioIdChange,
}: {
  scopeType: DecisionSupportScopeType | "";
  onScopeTypeChange: (value: DecisionSupportScopeType) => void;
  projectId: string;
  onProjectIdChange: (value: string) => void;
  portfolioId: string;
  onPortfolioIdChange: (value: string) => void;
}) {
  const { data: projects } = useProjects();
  const { data: portfolios } = usePortfolios();

  return (
    <>
      <div className="flex flex-1 flex-col gap-2">
        <Select value={scopeType} onValueChange={(value) => onScopeTypeChange(value as DecisionSupportScopeType)}>
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
          <Select value={projectId} onValueChange={onProjectIdChange}>
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
          <Select value={portfolioId} onValueChange={onPortfolioIdChange}>
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
    </>
  );
}
