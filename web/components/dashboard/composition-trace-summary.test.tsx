import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { CompositionTraceSummary } from "./composition-trace-summary";
import type { DecisionSupportCompositionTrace } from "@/lib/dashboard/types";

function trace(overrides: Partial<DecisionSupportCompositionTrace> = {}): DecisionSupportCompositionTrace {
  return {
    selection_signals: [],
    selected_advisor_names: [],
    advisors_used: [],
    correlations: [],
    synthesis_source_advisor_names: null,
    ...overrides,
  };
}

describe("CompositionTraceSummary", () => {
  it("renders every Advisor used as a badge", () => {
    render(
      <CompositionTraceSummary
        advisorsUsed={["risk_advisor", "delivery_advisor"]}
        compositionTrace={trace()}
        citations={[]}
      />,
    );

    expect(screen.getByText("risk_advisor")).toBeInTheDocument();
    expect(screen.getByText("delivery_advisor")).toBeInTheDocument();
  });

  it("never fabricates a correlation or conflict section when there is none", () => {
    render(<CompositionTraceSummary advisorsUsed={["risk_advisor"]} compositionTrace={trace()} citations={[]} />);

    expect(screen.queryByText(/Correlações identificadas/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Possíveis conflitos identificados/)).not.toBeInTheDocument();
  });

  it("presents a structural-pair correlation as a possible conflict, never resolved", () => {
    render(
      <CompositionTraceSummary
        advisorsUsed={["risk_advisor", "delivery_advisor"]}
        compositionTrace={trace({
          correlations: [{ advisor_names: ["delivery_advisor", "risk_advisor"], is_structural_pair: true }],
        })}
        citations={[]}
      />,
    );

    expect(screen.getByText(/Possíveis conflitos identificados/)).toBeInTheDocument();
    expect(screen.getByText(/nunca resolvidos automaticamente/)).toBeInTheDocument();
    expect(screen.queryByText(/^Correlações identificadas/)).not.toBeInTheDocument();
  });

  it("presents a non-structural-pair correlation as a plain correlation, never a conflict", () => {
    render(
      <CompositionTraceSummary
        advisorsUsed={["document_advisor", "governance_advisor"]}
        compositionTrace={trace({
          correlations: [
            { advisor_names: ["document_advisor", "governance_advisor"], is_structural_pair: false },
          ],
        })}
        citations={[]}
      />,
    );

    expect(screen.getByText(/Correlações identificadas/)).toBeInTheDocument();
    expect(screen.queryByText(/Possíveis conflitos identificados/)).not.toBeInTheDocument();
  });

  it("renders a consolidated citation with every attributed Advisor, never one entry per Advisor", () => {
    render(
      <CompositionTraceSummary
        advisorsUsed={["document_advisor", "governance_advisor"]}
        compositionTrace={trace()}
        citations={[
          {
            advisor_names: ["document_advisor", "governance_advisor"],
            source_type: "document_chunk",
            source_id: 1,
            source_label: "Document 1 / Chunk 1",
          },
        ]}
      />,
    );

    expect(screen.getByText(/document_advisor, governance_advisor/)).toBeInTheDocument();
    expect(screen.getByText(/Document 1 \/ Chunk 1/)).toBeInTheDocument();
  });
});
