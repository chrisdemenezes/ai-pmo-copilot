import type { RiskItem } from "./types";

/**
 * Decision Momentum for Risk Review -- same principle as
 * web/lib/workspace/decision-momentum.ts (Decision Experience Review, Rev.
 * 2), applied to a different real schema: risk_review has no health_status,
 * but probability/impact are real, structured fields per risk. Every
 * function here is a fixed UI rule over those fields, never an AI claim,
 * and never concatenated with the agent's verbatim description/mitigation.
 */

/**
 * "Attention" risks are the classic red zone of a probability x impact
 * heatmap (high x high, high x medium, medium x high) -- not an invented
 * score, the same 3x3 grid already computed by buildRiskMatrix. Every risk
 * stays visible regardless; this only decides what's promoted to the top.
 */
export function isHighAttentionRisk(risk: RiskItem): boolean {
  return (
    (risk.probability === "high" && risk.impact === "high") ||
    (risk.probability === "high" && risk.impact === "medium") ||
    (risk.probability === "medium" && risk.impact === "high")
  );
}

export function riskContextHeading(highAttentionCount: number): string {
  return highAttentionCount > 0 ? "Riscos que exigem atenção" : "Sem riscos críticos no momento";
}

export function suggestedRiskDecision(highAttentionCount: number): string {
  return highAttentionCount > 0 ? "Priorizar mitigação imediata" : "Manter monitoramento de rotina";
}

/**
 * The Brief always closes on a "next step" (Decision Momentum). Prefers the
 * agent's own escalation_recommendation when present -- it's already the
 * most direct real signal for "what to do next" this schema offers.
 */
export const RISK_NEXT_STEP_FALLBACK =
  "Nenhuma recomendação de escalonamento registrada nesta análise — continue monitorando os riscos identificados.";
