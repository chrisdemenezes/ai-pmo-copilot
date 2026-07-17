import { describe, expect, it } from "vitest";

import { buildRiskRecurrenceInsight, buildStatusInsight, selectPrimaryInsight } from "./memory-insights";
import type { AnalysisDetail, RiskItem, RiskModelOutput, StatusModelOutput } from "@/lib/workspace/types";

function statusAnalysis(
  health_status: StatusModelOutput["health_status"],
  overrides: Partial<AnalysisDetail<StatusModelOutput>> = {},
): AnalysisDetail<StatusModelOutput> {
  return {
    id: 1,
    kind: "status",
    project_name: "Aurora",
    created_at: "2026-07-14T00:00:00Z",
    payload: {
      agent: "project_status",
      project_name: "Aurora",
      model_output: {
        structured: true,
        health_status,
        key_findings: [],
        recommendations: [],
      },
    },
    ...overrides,
  };
}

describe("buildStatusInsight", () => {
  it("returns null (silence) when there is only 1 analysis -- no real 'before'", () => {
    expect(buildStatusInsight([statusAnalysis("red")])).toBeNull();
  });

  it("returns null when there are 0 analyses", () => {
    expect(buildStatusInsight([])).toBeNull();
  });

  it("returns 'mudou' when the status changed between the 2 most recent analyses", () => {
    const insight = buildStatusInsight([statusAnalysis("green"), statusAnalysis("yellow")]);
    expect(insight).toEqual({ kind: "mudou", text: "Mudou: Atenção → Saudável" });
  });

  it("returns 'persistiu' when the same attention-zone status repeats", () => {
    const insight = buildStatusInsight([
      statusAnalysis("red"),
      statusAnalysis("red"),
      statusAnalysis("red"),
    ]);
    expect(insight).toEqual({ kind: "persistiu", text: "Persiste em Crítico (3ª análise seguida)" });
  });

  it("returns null (silence) when a healthy status repeats -- never says 'persistiu' for green", () => {
    const insight = buildStatusInsight([statusAnalysis("green"), statusAnalysis("green")]);
    expect(insight).toBeNull();
  });

  it("counts only the consecutive streak, stopping at the first different status", () => {
    const insight = buildStatusInsight([
      statusAnalysis("yellow"),
      statusAnalysis("yellow"),
      statusAnalysis("red"), // streak breaks here
    ]);
    expect(insight).toEqual({ kind: "persistiu", text: "Persiste em Atenção (2ª análise seguida)" });
  });

  it("ignores analyses without a structured status shape when computing the delta", () => {
    const unstructured = statusAnalysis("red", {
      payload: {
        agent: "project_status",
        project_name: "Aurora",
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        model_output: { structured: false, raw_output: "oops" } as any,
      },
    });
    const insight = buildStatusInsight([statusAnalysis("green"), unstructured, statusAnalysis("red")]);
    expect(insight).toEqual({ kind: "mudou", text: "Mudou: Crítico → Saudável" });
  });
});

function riskAnalysis(
  risks: RiskItem[],
  overrides: Partial<AnalysisDetail<RiskModelOutput>> = {},
): AnalysisDetail<RiskModelOutput> {
  return {
    id: 1,
    kind: "risk",
    project_name: "Aurora",
    created_at: "2026-07-14T00:00:00Z",
    payload: {
      agent: "risk_review",
      project_name: "Aurora",
      model_output: { structured: true, risks, escalation_recommendation: null },
    },
    ...overrides,
  };
}

const HIGH_ATTENTION_RISK: RiskItem = {
  description: "Atraso no fornecedor de middleware compromete o go-live",
  probability: "high",
  impact: "high",
  mitigation: "Escalar",
};

const LOW_RISK: RiskItem = {
  description: "Custo abaixo do orçamento",
  probability: "low",
  impact: "low",
  mitigation: "Monitorar",
};

describe("buildRiskRecurrenceInsight", () => {
  it("returns null (silence) when there is only 1 analysis -- no real recurrence possible", () => {
    expect(buildRiskRecurrenceInsight([riskAnalysis([HIGH_ATTENTION_RISK])])).toBeNull();
  });

  it("returns null when the most recent analysis has no high-attention risk", () => {
    const insight = buildRiskRecurrenceInsight([riskAnalysis([LOW_RISK]), riskAnalysis([HIGH_ATTENTION_RISK])]);
    expect(insight).toBeNull();
  });

  it("returns null when the high-attention risk in the most recent analysis never appeared before", () => {
    const insight = buildRiskRecurrenceInsight([
      riskAnalysis([HIGH_ATTENTION_RISK]),
      riskAnalysis([LOW_RISK]),
    ]);
    expect(insight).toBeNull();
  });

  it("returns 'reapareceu' with the real recurrence count when the same high-attention risk repeats", () => {
    const insight = buildRiskRecurrenceInsight([
      riskAnalysis([HIGH_ATTENTION_RISK]),
      riskAnalysis([LOW_RISK]),
      riskAnalysis([HIGH_ATTENTION_RISK]),
    ]);
    expect(insight).toEqual({
      kind: "reapareceu",
      text: "Reapareceu: Atraso no fornecedor de middleware compromete o go-live (2ª vez)",
    });
  });

  it("matches by exact description text only -- never a fabricated similarity heuristic", () => {
    const insight = buildRiskRecurrenceInsight([
      riskAnalysis([{ ...HIGH_ATTENTION_RISK, description: "Atraso no fornecedor" }]),
      riskAnalysis([HIGH_ATTENTION_RISK]),
    ]);
    expect(insight).toBeNull();
  });

  it("ignores unstructured analyses when computing recurrence", () => {
    const unstructured = riskAnalysis([HIGH_ATTENTION_RISK], {
      payload: {
        agent: "risk_review",
        project_name: "Aurora",
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        model_output: { structured: false, raw_output: "oops" } as any,
      },
    });
    const insight = buildRiskRecurrenceInsight([riskAnalysis([HIGH_ATTENTION_RISK]), unstructured]);
    expect(insight).toBeNull();
  });
});

describe("selectPrimaryInsight (One Memory Insight Rule)", () => {
  const persistiu = { kind: "persistiu" as const, text: "Persiste em Crítico (2ª análise seguida)" };
  const mudou = { kind: "mudou" as const, text: "Mudou: Atenção → Crítico" };
  const reapareceu = { kind: "reapareceu" as const, text: "Reapareceu: Atraso (2ª vez)" };

  it("prefers Persistiu over Reapareceu when both are present", () => {
    expect(selectPrimaryInsight(persistiu, reapareceu)).toEqual(persistiu);
  });

  it("prefers Reapareceu over Mudou when both are present", () => {
    expect(selectPrimaryInsight(mudou, reapareceu)).toEqual(reapareceu);
  });

  it("falls back to Mudou when there is no risk recurrence", () => {
    expect(selectPrimaryInsight(mudou, null)).toEqual(mudou);
  });

  it("returns null (silence) when there is no insight at all", () => {
    expect(selectPrimaryInsight(null, null)).toBeNull();
  });

  it("returns Reapareceu alone when there is no status insight", () => {
    expect(selectPrimaryInsight(null, reapareceu)).toEqual(reapareceu);
  });
});
