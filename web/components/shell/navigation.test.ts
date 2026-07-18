import { describe, expect, it } from "vitest";

import { NAV_ITEMS } from "./navigation";

describe("NAV_ITEMS", () => {
  it("contains exactly eight entries -- the only fully real modules today (Capability 02, Mission Control)", () => {
    expect(NAV_ITEMS).toHaveLength(8);
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

  it("points the fourth entry at the real Program Management route", () => {
    expect(NAV_ITEMS[3].href).toBe("/program-management");
    expect(NAV_ITEMS[3].label).toBe("Program Management");
  });

  it("points the fifth entry at the real Ações route", () => {
    expect(NAV_ITEMS[4].href).toBe("/actions");
    expect(NAV_ITEMS[4].label).toBe("Ações");
  });

  it("points the sixth entry at the real Decisões route", () => {
    expect(NAV_ITEMS[5].href).toBe("/decisions");
    expect(NAV_ITEMS[5].label).toBe("Decisões");
  });

  it("points the seventh entry at the real Aprendizados (Organizational Intelligence) route", () => {
    expect(NAV_ITEMS[6].href).toBe("/aprendizados");
    expect(NAV_ITEMS[6].label).toBe("Aprendizados");
  });

  it("points the eighth entry at Mission Control", () => {
    expect(NAV_ITEMS[7].href).toBe("/mission-control");
    expect(NAV_ITEMS[7].label).toBe("Mission Control");
  });
});
