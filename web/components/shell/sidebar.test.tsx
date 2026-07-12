import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

import { Sidebar } from "./sidebar";

describe("Sidebar", () => {
  it("renders exactly two nav items, matching NAV_ITEMS", () => {
    render(<Sidebar />);
    // Two nav landmarks render (full sidebar + mobile bottom bar), each with
    // one link per NAV_ITEMS entry -- CSS (hidden/md:hidden) decides which
    // landmark is visible per breakpoint, both exist in the DOM.
    expect(screen.getAllByRole("link", { name: /dashboard/i })).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: /projetos/i })).toHaveLength(2);
  });

  it("marks only the item matching the current pathname as active", () => {
    render(<Sidebar />);
    const activeLinks = screen.getAllByRole("link", { current: "page" });
    // Dashboard active in both landmarks (2), Projetos active in neither.
    expect(activeLinks).toHaveLength(2);
    for (const link of activeLinks) {
      expect(link).toHaveAccessibleName(/dashboard/i);
    }
  });
});
