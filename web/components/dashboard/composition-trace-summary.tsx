import { Badge } from "@/components/ui/badge";
import type { DecisionSupportCitation, DecisionSupportCompositionTrace } from "@/lib/dashboard/types";

interface CompositionTraceSummaryProps {
  advisorsUsed: string[];
  compositionTrace: DecisionSupportCompositionTrace;
  citations: DecisionSupportCitation[];
}

/**
 * "Como esta resposta foi construída" (Founder Decision -- Wave 6 Final
 * Consolidation Actions, D-165) -- a plain-language summary of the
 * Composition Trace, never raw JSON. Shared identically by
 * `DecisionSupportPanel`/`ExecutiveNarrativePanel` (no new route, BFF, or
 * backend contract involved -- `composition_trace`/`citations` already
 * arrive complete in `mutation.data`).
 *
 * A correlation flagged `is_structural_pair` is presented as a possible
 * conflict -- always exposed, never automatically resolved (Vision,
 * Princípio 5); every other correlation is presented as a plain
 * correlation. Sections render only when there is real content -- absence
 * of correlation/conflict never produces fabricated text.
 */
export function CompositionTraceSummary({
  advisorsUsed,
  compositionTrace,
  citations,
}: CompositionTraceSummaryProps) {
  const conflicts = compositionTrace.correlations.filter((entry) => entry.is_structural_pair);
  const correlations = compositionTrace.correlations.filter((entry) => !entry.is_structural_pair);

  return (
    <div className="flex flex-col gap-2 border-t border-border pt-3">
      <p className="text-xs font-semibold text-ink-muted">Como esta resposta foi construída</p>

      {advisorsUsed.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {advisorsUsed.map((advisorName) => (
            <Badge key={advisorName} variant="outline">
              {advisorName}
            </Badge>
          ))}
        </div>
      )}

      {correlations.length > 0 && (
        <p className="text-xs text-ink-muted">
          <span className="font-medium">Correlações identificadas: </span>
          {correlations.map((entry) => entry.advisor_names.join(" + ")).join("; ")}
        </p>
      )}

      {conflicts.length > 0 && (
        <p className="text-xs text-ink-muted">
          <span className="font-medium">Possíveis conflitos identificados: </span>
          {conflicts.map((entry) => entry.advisor_names.join(" + ")).join("; ")} (sinalizados, nunca
          resolvidos automaticamente)
        </p>
      )}

      {citations.length > 0 && (
        <ul className="flex flex-col gap-1 text-xs text-ink-muted">
          {citations.map((citation, index) => (
            <li key={`${citation.source_type}-${citation.source_id}-${index}`}>
              {citation.advisor_names.join(", ")}: {citation.source_label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
