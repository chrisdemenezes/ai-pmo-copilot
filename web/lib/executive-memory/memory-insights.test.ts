import { describe, expect, it } from "vitest";

import { buildStatusInsight } from "./memory-insights";
import type { AnalysisDetail, StatusModelOutput } from "@/lib/workspace/types";

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
