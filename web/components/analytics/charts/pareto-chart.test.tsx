import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ParetoChart } from "./pareto-chart";

describe("ParetoChart", () => {
  it("shows the empty state when there is nothing to rank", () => {
    render(<ParetoChart title="Concentração de custo" items={[]} />);

    expect(screen.getByText("Dados insuficientes para esta visualização.")).toBeInTheDocument();
  });

  it("renders a bar per item label when data exists", () => {
    render(
      <ParetoChart
        title="Concentração de custo"
        items={[
          { label: "Projeto A", value: 80 },
          { label: "Projeto B", value: 20 },
        ]}
      />,
    );

    expect(screen.getByText("Projeto A: 80%")).toBeInTheDocument();
    expect(screen.getByText("Projeto B: 20%")).toBeInTheDocument();
  });
});
