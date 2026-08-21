import { afterEach, describe, expect, it } from "vitest";

import { applyTheme, readStoredTheme, storeTheme, THEME_STORAGE_KEY } from "./theme";

describe("theme persistence", () => {
  afterEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("returns null when nothing is stored (follows the system)", () => {
    expect(readStoredTheme()).toBeNull();
  });

  it("stores and reads back 'dark'", () => {
    storeTheme("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(readStoredTheme()).toBe("dark");
  });

  it("stores and reads back 'light'", () => {
    storeTheme("light");
    expect(readStoredTheme()).toBe("light");
  });

  it("removes the stored value when set to null (back to following the system)", () => {
    storeTheme("dark");
    storeTheme(null);
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
    expect(readStoredTheme()).toBeNull();
  });

  it("ignores a corrupted/unexpected stored value", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "purple");
    expect(readStoredTheme()).toBeNull();
  });

  it("applyTheme sets data-theme on <html> for an explicit theme", () => {
    applyTheme("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    applyTheme("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("applyTheme(null) removes data-theme (follows the system again)", () => {
    applyTheme("dark");
    applyTheme(null);
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
  });
});
