import type { StatusModelOutput } from "./types";

type HealthStatus = StatusModelOutput["health_status"];

/**
 * Decision Momentum (Decision Experience Review, Rev. 2 -- Founder). Every
 * string here is a fixed UI rule over a real field (health_status,
 * recommendations), never an AI claim -- kept isolated in this file so
 * derived text is never concatenated into the same string as the agent's
 * verbatim key_findings/recommendations. No priority ranking is implied:
 * these only react to health_status, never to individual list items.
 */
const CONTEXT_HEADING: Record<HealthStatus, string> = {
  red: "Pontos de atenção",
  yellow: "Pontos de atenção",
  green: "Notas do período",
};

export function contextHeading(healthStatus: HealthStatus): string {
  return CONTEXT_HEADING[healthStatus];
}

const SUGGESTED_DECISION: Record<HealthStatus, string> = {
  red: "Escalar ao patrocinador",
  yellow: "Acompanhar de perto",
  green: "Manter o curso atual",
};

export function suggestedDecision(healthStatus: HealthStatus): string {
  return SUGGESTED_DECISION[healthStatus];
}

/**
 * The Brief always closes on a "next step" -- never absent, never
 * fabricated. When there is no real recommendation to promote, this is the
 * honest continuity statement (Decision Momentum §"ponto de continuidade").
 */
export const NEXT_STEP_FALLBACK =
  "Nenhuma recomendação registrada nesta análise — continue acompanhando o projeto.";
