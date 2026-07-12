import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import ProjectsError from "./error";
import { DashboardFetchError } from "@/lib/hooks/use-portfolio-summary";

describe("ProjectsError", () => {
  it("shows the safe copy and lets the user retry", () => {
    const reset = vi.fn();
    render(
      <ProjectsError
        error={new DashboardFetchError({ error: "backend_error", detail: "Backend respondeu 500." })}
        reset={reset}
      />,
    );

    expect(screen.getByText("Não foi possível carregar os projetos agora")).toBeInTheDocument();
    expect(screen.getByText("Backend respondeu 500.")).toBeInTheDocument();

    screen.getByRole("button", { name: "Tentar novamente" }).click();
    expect(reset).toHaveBeenCalledOnce();
  });

  it("never renders a stack trace for a plain Error", () => {
    render(<ProjectsError error={new Error("boom")} reset={vi.fn()} />);
    expect(screen.queryByText("boom")).not.toBeInTheDocument();
  });
});
