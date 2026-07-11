import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

import { AppShell } from "./app-shell";

describe("AppShell", () => {
  it("renders the sidebar navigation and the page content together", () => {
    render(
      <AppShell>
        <p>Conteúdo da página</p>
      </AppShell>,
    );
    expect(screen.getByText("Conteúdo da página")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /dashboard/i }).length).toBeGreaterThan(0);
  });
});
