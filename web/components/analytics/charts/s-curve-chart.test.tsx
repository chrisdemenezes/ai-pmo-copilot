import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { SCurveChart } from "./s-curve-chart";

describe("SCurveChart", () => {
  it("shows the insufficient-history empty state when there is no data", () => {
    render(<SCurveChart points={[]} />);

    expect(
      screen.getByText(
        "Dados históricos insuficientes -- nenhum snapshot de performance capturado ainda.",
      ),
    ).toBeInTheDocument();
  });

  it("renders the chart (not the empty state) once at least one point exists", () => {
    render(
      <SCurveChart
        points={[
          {
            asOf: "2026-02-01",
            pv: { value: 25000, reason: null },
            ev: { value: 20000, reason: null },
            ac: { value: 20000, reason: null },
          },
        ]}
      />,
    );

    expect(
      screen.queryByText(/Dados históricos insuficientes/),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Curva S (Planejado x Agregado x Real)")).toBeInTheDocument();
  });
});
