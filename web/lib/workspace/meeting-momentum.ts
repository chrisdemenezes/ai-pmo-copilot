/**
 * Decision Momentum for Meeting Intelligence -- same principle as
 * decision-momentum.ts / risk-momentum.ts (FS-006 §2.4), applied to a
 * schema with no health_status or probability/impact equivalent.
 * meeting_intelligence has no severity signal at all, so "Impacto da
 * reunião" (User Journey nível 1) can only be an honest, real count --
 * never an invented score. Every function here is a fixed UI rule over
 * real array lengths, never an AI claim, and never concatenated with the
 * agent's verbatim summary/decisions/issues text.
 */

export function impactHeadline(
  decisionsCount: number,
  issuesCount: number,
  actionItemsCount: number,
): string {
  return `${decisionsCount} decisão(ões) · ${issuesCount} ponto(s) de atenção · ${actionItemsCount} responsabilidade(s)`;
}

/**
 * "Próximo passo" for Meeting Intelligence (Decision Momentum): only
 * suggests actions that already exist in the platform (Founder: "nunca
 * criar botões cenográficos"). Returns null -- never a fabricated
 * suggestion -- when nothing in the meeting warrants either.
 */
export function suggestedNextStep(
  issuesCount: number,
  decisionsCount: number,
): { label: string } | null {
  if (issuesCount > 0) return { label: "Executar Avaliação de Riscos" };
  if (decisionsCount > 0) return { label: "Atualizar Status Executivo" };
  return null;
}

export const NEXT_STEP_FALLBACK_MEETING =
  "Nenhum próximo passo adicional sugerido a partir desta reunião.";
