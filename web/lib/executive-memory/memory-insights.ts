import { healthStatusLabel } from "@/components/ui/badge";
import { isHighAttentionRisk } from "@/lib/workspace/risk-momentum";
import {
  hasRiskShape,
  hasStatusShape,
  type AnalysisDetail,
  type RiskModelOutput,
  type StatusModelOutput,
  type UnstructuredModelOutput,
} from "@/lib/workspace/types";

/**
 * Executive Memory (FS-010, UX Flow §2) -- "Memory Signal" é o termo
 * técnico interno; "Executive Memory Insight" é o Executive UI Pattern
 * usado na documentação de produto (FS-010 §6). Exatamente 3 tipos nesta
 * V1, nenhum outro: mudou, persistiu, reapareceu.
 */
export type MemorySignalKind = "mudou" | "persistiu" | "reapareceu";

export interface ExecutiveMemoryInsight {
  kind: MemorySignalKind;
  /** Menor fato necessário, verbatim -- nunca narrativa (Decision Context Preservation). */
  text: string;
}

/** "Persistiu" só se aplica a um estado real de atenção -- nunca a um estado saudável repetido (User Journey §4). */
const ATTENTION_STATUSES = new Set<StatusModelOutput["health_status"]>(["red", "yellow"]);

/**
 * buildStatusInsight (FS-010 §3.3) -- Mudou e Persistiu são mutuamente
 * exclusivos por construção: a mesma comparação entre as 2 análises de
 * status mais recentes só pode produzir "mudou" OU "persistiu", nunca os
 * dois (Architecture Review §3.1). Silêncio (retorna null) quando: menos
 * de 2 análises estruturadas existem, ou o estado repetido é saudável.
 */
export function buildStatusInsight(
  recentStatusAnalyses: AnalysisDetail<StatusModelOutput | UnstructuredModelOutput>[],
): ExecutiveMemoryInsight | null {
  const structured = recentStatusAnalyses.filter(
    (analysis): analysis is AnalysisDetail<StatusModelOutput> =>
      hasStatusShape(analysis.payload.model_output),
  );

  if (structured.length < 2) return null; // sem "antes" real (UX Flow §4)

  const statuses = structured.map((analysis) => analysis.payload.model_output.health_status);
  const [current, previous] = statuses;

  if (current !== previous) {
    return {
      kind: "mudou",
      text: `Mudou: ${healthStatusLabel(previous)} → ${healthStatusLabel(current)}`,
    };
  }

  if (!ATTENTION_STATUSES.has(current)) return null; // saudável repetido -> silêncio

  let streak = 0;
  for (const status of statuses) {
    if (status !== current) break;
    streak++;
  }

  return {
    kind: "persistiu",
    text: `Persiste em ${healthStatusLabel(current)} (${streak}ª análise seguida)`,
  };
}

/**
 * buildRiskRecurrenceInsight (FS-010 §3.3) -- "Reapareceu": o mesmo risco de
 * atenção (isHighAttentionRisk, já existente no Risks Panel) volta a
 * aparecer em mais de 1 das análises de risco mais recentes. Casamento por
 * texto exato da descrição -- nunca uma heurística de similaridade
 * inventada, só o dado real que a IA já produziu. Escolhe o primeiro risco
 * de atenção da análise mais recente que recorre, na ordem em que a própria
 * IA listou (nenhuma reordenação/priorização nova).
 */
export function buildRiskRecurrenceInsight(
  recentRiskAnalyses: AnalysisDetail<RiskModelOutput | UnstructuredModelOutput>[],
): ExecutiveMemoryInsight | null {
  const structured = recentRiskAnalyses.filter(
    (analysis): analysis is AnalysisDetail<RiskModelOutput> =>
      hasRiskShape(analysis.payload.model_output),
  );

  if (structured.length < 2) return null; // sem "antes" real

  const [mostRecent] = structured;
  const currentHighAttention = mostRecent.payload.model_output.risks.filter(isHighAttentionRisk);

  for (const risk of currentHighAttention) {
    const recurrenceCount = structured.filter((analysis) =>
      analysis.payload.model_output.risks.some(
        (candidate) => isHighAttentionRisk(candidate) && candidate.description === risk.description,
      ),
    ).length;

    if (recurrenceCount > 1) {
      return {
        kind: "reapareceu",
        text: `Reapareceu: ${risk.description} (${recurrenceCount}ª vez)`,
      };
    }
  }

  return null;
}

/**
 * selectPrimaryInsight -- One Memory Insight Rule (Architecture Review
 * §3, ratificada no TIP-011): no máximo 1 Executive Memory Insight por
 * contexto, nunca uma lista. Hierarquia Persistiu > Reapareceu > Mudou --
 * Persistiu e Mudou são mutuamente exclusivos por construção
 * (buildStatusInsight), então só há 3 combinações reais a resolver aqui.
 */
export function selectPrimaryInsight(
  statusInsight: ExecutiveMemoryInsight | null,
  riskInsight: ExecutiveMemoryInsight | null,
): ExecutiveMemoryInsight | null {
  if (statusInsight?.kind === "persistiu") return statusInsight;
  if (riskInsight) return riskInsight;
  return statusInsight;
}
