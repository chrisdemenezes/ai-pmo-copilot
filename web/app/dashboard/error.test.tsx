import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import DashboardError from "./error";
import { DashboardFetchError } from "@/lib/hooks/use-portfolio-summary";

describe("DashboardError", () => {
  it("shows the safe copy and lets the user retry", () => {
    const reset = vi.fn();
    render(
      <DashboardError
        error={new DashboardFetchError({ error: "backend_error", detail: "Backend respondeu 500." })}
        reset={reset}
      />,
    );

    expect(screen.getByText("Não foi possível carregar o portfólio agora")).toBeInTheDocument();
    expect(screen.getByText("Backend respondeu 500.")).toBeInTheDocument();
    expect(screen.queryByText(/at DashboardPage/i)).not.toBeInTheDocument();

    screen.getByRole("button", { name: "Tentar novamente" }).click();
    expect(reset).toHaveBeenCalledOnce();
  });

  it("never renders a stack trace for a plain Error", () => {
    render(<DashboardError error={new Error("boom")} reset={vi.fn()} />);
    expect(screen.queryByText("boom")).not.toBeInTheDocument();
  });
});
