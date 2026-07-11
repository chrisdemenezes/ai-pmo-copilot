import { describe, expect, it } from "vitest";

import { NAV_ITEMS } from "./navigation";

describe("NAV_ITEMS", () => {
  it("contains exactly one entry -- the only real route today (FS-002)", () => {
    expect(NAV_ITEMS).toHaveLength(1);
  });

  it("points the single entry at the real Dashboard route", () => {
    expect(NAV_ITEMS[0].href).toBe("/dashboard");
    expect(NAV_ITEMS[0].label).toBe("Dashboard");
  });
});
