import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { HealthDistributionChart } from "./health-distribution-chart";

describe("HealthDistributionChart", () => {
  it("shows the empty state when there are no projects", () => {
    render(<HealthDistributionChart statuses={[]} />);

    expect(screen.getByText("Nenhum projeto para distribuir.")).toBeInTheDocument();
  });

  it("shows the count for every real status bucket, including sem dado", () => {
    render(<HealthDistributionChart statuses={["green", "green", "yellow", null]} />);

    expect(screen.getByText(/Saudável: 2/)).toBeInTheDocument();
    expect(screen.getByText(/Atenção: 1/)).toBeInTheDocument();
    expect(screen.getByText(/Crítico: 0/)).toBeInTheDocument();
    expect(screen.getByText(/Sem dado: 1/)).toBeInTheDocument();
  });
});
