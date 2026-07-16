import { describe, expect, it } from "vitest";

import { NAV_ITEMS } from "./navigation";

describe("NAV_ITEMS", () => {
  it("contains exactly five entries -- the only fully real modules today (TIP-010)", () => {
    expect(NAV_ITEMS).toHaveLength(5);
  });

  it("points the first entry at the real Dashboard route", () => {
    expect(NAV_ITEMS[0].href).toBe("/dashboard");
    expect(NAV_ITEMS[0].label).toBe("Dashboard");
  });

  it("points the second entry at the real Priorização (Portfolio Intelligence) route", () => {
    expect(NAV_ITEMS[1].href).toBe("/portfolio");
    expect(NAV_ITEMS[1].label).toBe("Priorização");
  });

  it("points the third entry at the real Projetos route", () => {
    expect(NAV_ITEMS[2].href).toBe("/projects");
    expect(NAV_ITEMS[2].label).toBe("Projetos");
  });

  it("points the fourth entry at the real Ações route", () => {
    expect(NAV_ITEMS[3].href).toBe("/actions");
    expect(NAV_ITEMS[3].label).toBe("Ações");
  });

  it("points the fifth entry at the real Decisões route", () => {
    expect(NAV_ITEMS[4].href).toBe("/decisions");
    expect(NAV_ITEMS[4].label).toBe("Decisões");
  });
});
