import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { RiskHeatmapChart } from "./risk-heatmap-chart";

describe("RiskHeatmapChart", () => {
  it("shows the empty state when there are no risks", () => {
    render(<RiskHeatmapChart risks={[]} />);

    expect(screen.getByText("Nenhum risco registrado para esta visualização.")).toBeInTheDocument();
  });

  it("reports unclassified risks separately instead of guessing a cell", () => {
    render(
      <RiskHeatmapChart
        risks={[{ id: 1, label: "Risco incompleto", probability: null, impact: "high" }]}
      />,
    );

    expect(screen.getByText(/sem classificação completa/)).toBeInTheDocument();
  });

  it("renders the 9-cell grid when risks are fully classified", () => {
    render(
      <RiskHeatmapChart
        risks={[{ id: 1, label: "Atraso crítico", probability: "high", impact: "high" }]}
      />,
    );

    expect(screen.getByText("Mapa de Calor de Riscos")).toBeInTheDocument();
    expect(screen.queryByText(/sem classificação completa/)).not.toBeInTheDocument();
  });
});
