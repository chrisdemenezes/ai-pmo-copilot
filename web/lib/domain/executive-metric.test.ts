import { describe, expect, it } from "vitest";

import {
  formatMetricValue,
  metricReasonLabel,
  metricSentiment,
} from "./executive-metric";

describe("formatMetricValue", () => {
  it("renders an em dash, never a zero, when the metric has no value", () => {
    expect(formatMetricValue({ value: null, reason: "no_baseline_defined" }, "currency")).toBe(
      "—",
    );
  });

  it("formats a currency value in BRL with no decimals", () => {
    expect(formatMetricValue({ value: 25000, reason: null }, "currency")).toBe("R$ 25.000");
  });

  it("formats a ratio (e.g. CPI/SPI) with up to 2 decimals", () => {
    expect(formatMetricValue({ value: 0.8, reason: null }, "ratio")).toBe("0,8");
  });

  it("formats a percentage by multiplying by 100", () => {
    expect(formatMetricValue({ value: 0.256, reason: null }, "percentage")).toBe("25,6%");
  });
});

describe("metricReasonLabel", () => {
  it("returns empty string for a metric that has a real value", () => {
    expect(metricReasonLabel(null)).toBe("");
  });

  it("maps a known reason code to PT-BR copy", () => {
    expect(metricReasonLabel("no_baseline_defined")).toBe(
      "Nenhum baseline definido para este projeto",
    );
  });

  it("falls back to the raw code for an unmapped reason rather than going blank", () => {
    expect(metricReasonLabel("some_future_reason")).toBe("some_future_reason");
  });
});

describe("metricSentiment", () => {
  it("is neutral when the metric has no value", () => {
    expect(metricSentiment({ value: null, reason: "no_snapshot_captured" }, "higher-is-better")).toBe(
      "neutral",
    );
  });

  it("is neutral at exactly zero", () => {
    expect(metricSentiment({ value: 0, reason: null }, "higher-is-better")).toBe("neutral");
  });

  it("is ok for a positive value when higher is better (e.g. cost variance)", () => {
    expect(metricSentiment({ value: 500, reason: null }, "higher-is-better")).toBe("ok");
  });

  it("is danger for a negative value when higher is better", () => {
    expect(metricSentiment({ value: -500, reason: null }, "higher-is-better")).toBe("danger");
  });

  it("is danger for a positive value when lower is better (e.g. schedule slip)", () => {
    expect(metricSentiment({ value: 5, reason: null }, "lower-is-better")).toBe("danger");
  });

  it("is ok for a negative value when lower is better", () => {
    expect(metricSentiment({ value: -5, reason: null }, "lower-is-better")).toBe("ok");
  });
});
