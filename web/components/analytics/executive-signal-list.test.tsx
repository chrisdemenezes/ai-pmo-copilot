import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ExecutiveSignalList } from "./executive-signal-list";
import type { ExecutiveSignal } from "@/lib/domain/executive-signal";

function signal(overrides: Partial<ExecutiveSignal> = {}): ExecutiveSignal {
  return {
    type: "cost_performance_deteriorating",
    severity: "critical",
    scope: "Projeto A",
    metric: "CPI",
    currentValue: 0.8,
    baselineOrThreshold: 1,
    trend: "down",
    evidenceReference: "CPI caiu de 1.0 para 0.8",
    asOf: "2026-02-01",
    ...overrides,
  };
}

describe("ExecutiveSignalList", () => {
  it("shows a neutral message when there are no signals", () => {
    render(<ExecutiveSignalList signals={[]} />);

    expect(screen.getByText("Nenhum sinal executivo no momento.")).toBeInTheDocument();
  });

  it("renders the metric, severity badge, and evidence for each signal", () => {
    render(<ExecutiveSignalList signals={[signal()]} />);

    expect(screen.getByText("CPI")).toBeInTheDocument();
    expect(screen.getByText("Crítico")).toBeInTheDocument();
    expect(screen.getByText("CPI caiu de 1.0 para 0.8")).toBeInTheDocument();
  });

  it("never renders a Decision or Recommendation action alongside a signal", () => {
    render(<ExecutiveSignalList signals={[signal()]} />);

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
