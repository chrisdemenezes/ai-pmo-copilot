import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push, refresh }),
}));

import { Sidebar } from "./sidebar";

describe("Sidebar", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    push.mockClear();
    refresh.mockClear();
  });

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

  // Founder Decision -- W7-7 Checkpoint Ratification + Controlled User
  // Pilot Readiness Review: Logout UI Gap correction. A real control now
  // exists in both landmarks -- these are the "buttons", never "links",
  // so they don't affect the fourteen-link count above.
  it("renders a Sair control in both landmarks, never as a link", () => {
    render(<Sidebar />);
    expect(screen.getAllByRole("button", { name: /sair/i })).toHaveLength(2);
    expect(screen.queryAllByRole("link", { name: /sair/i })).toHaveLength(0);
  });

  it("clicking Sair calls DELETE /api/bff/session, then navigates to /entrar", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<Sidebar />);
    await userEvent.click(screen.getAllByRole("button", { name: /sair/i })[0]);

    expect(fetchMock).toHaveBeenCalledWith("/api/bff/session", { method: "DELETE" });
    expect(push).toHaveBeenCalledWith("/entrar");
    expect(refresh).toHaveBeenCalled();
  });
});
