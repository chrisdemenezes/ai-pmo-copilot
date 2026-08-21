import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ExecutiveMetricCard } from "./executive-metric-card";

describe("ExecutiveMetricCard", () => {
  it("renders the label and a formatted value for a real metric", () => {
    render(
      <ExecutiveMetricCard
        label="CPI"
        metric={{ value: 1.05, reason: null }}
        format="ratio"
      />,
    );

    expect(screen.getByText("CPI")).toBeInTheDocument();
    expect(screen.getByText("1,05")).toBeInTheDocument();
  });

  it("renders an em dash, never a zero, when the metric is N/A", () => {
    render(
      <ExecutiveMetricCard
        label="SPI"
        metric={{ value: null, reason: "no_baseline_defined" }}
        format="ratio"
      />,
    );

    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("shows a data-quality indicator when the metric is N/A", () => {
    render(
      <ExecutiveMetricCard
        label="SPI"
        metric={{ value: null, reason: "no_baseline_defined" }}
        format="ratio"
      />,
    );

    expect(
      screen.getByLabelText("Por que este dado não está disponível?"),
    ).toBeInTheDocument();
  });

  it("does not show a data-quality indicator when the metric has a real value", () => {
    render(
      <ExecutiveMetricCard label="CPI" metric={{ value: 1, reason: null }} format="ratio" />,
    );

    expect(
      screen.queryByLabelText("Por que este dado não está disponível?"),
    ).not.toBeInTheDocument();
  });
});
