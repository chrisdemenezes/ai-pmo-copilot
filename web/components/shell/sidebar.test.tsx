import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

import { Sidebar } from "./sidebar";

describe("Sidebar", () => {
  it("renders exactly one nav item, matching NAV_ITEMS", () => {
    render(<Sidebar />);
    // Two nav landmarks render (full sidebar + mobile bottom bar), each with
    // one "Dashboard" link -- CSS (hidden/md:hidden) decides which is
    // visible per breakpoint, both exist in the DOM.
    expect(screen.getAllByRole("link", { name: /dashboard/i })).toHaveLength(2);
  });

  it("marks the item matching the current pathname as active", () => {
    render(<Sidebar />);
    const activeLinks = screen.getAllByRole("link", { current: "page" });
    expect(activeLinks).toHaveLength(2);
  });
});
