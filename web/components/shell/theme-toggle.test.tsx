import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ThemeToggle } from "./theme-toggle";
import { THEME_STORAGE_KEY } from "@/lib/theme";

describe("ThemeToggle", () => {
  afterEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    vi.restoreAllMocks();
  });

  it("resolves to the system preference (light) when nothing is stored", async () => {
    render(<ThemeToggle />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Mudar para tema escuro" })).toBeInTheDocument();
    });
  });

  it("resolves to the stored preference over the system preference", async () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");
    render(<ThemeToggle />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Mudar para tema claro" })).toBeInTheDocument();
    });
  });

  it("clicking toggles the theme, applies data-theme, and persists it", async () => {
    render(<ThemeToggle />);
    const button = await screen.findByRole("button", { name: "Mudar para tema escuro" });

    await userEvent.click(button);

    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(screen.getByRole("button", { name: "Mudar para tema claro" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Mudar para tema claro" }));

    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
  });
});
