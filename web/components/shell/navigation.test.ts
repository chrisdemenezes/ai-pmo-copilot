import { describe, expect, it } from "vitest";

import { NAV_ITEMS } from "./navigation";

describe("NAV_ITEMS", () => {
  it("contains exactly two entries -- the only fully real modules today (TIP-004A)", () => {
    expect(NAV_ITEMS).toHaveLength(2);
  });

  it("points the first entry at the real Dashboard route", () => {
    expect(NAV_ITEMS[0].href).toBe("/dashboard");
    expect(NAV_ITEMS[0].label).toBe("Dashboard");
  });

  it("points the second entry at the real Projetos route", () => {
    expect(NAV_ITEMS[1].href).toBe("/projects");
    expect(NAV_ITEMS[1].label).toBe("Projetos");
  });
});
