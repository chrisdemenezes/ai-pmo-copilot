import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Badge, healthStatusVariant } from "./badge";

describe("healthStatusVariant", () => {
  it("maps green to ok", () => {
    expect(healthStatusVariant("green")).toBe("ok");
  });

  it("maps yellow to warn", () => {
    expect(healthStatusVariant("yellow")).toBe("warn");
  });

  it("maps red to danger", () => {
    expect(healthStatusVariant("red")).toBe("danger");
  });

  it("maps null to neutral (no status yet, not an error)", () => {
    expect(healthStatusVariant(null)).toBe("neutral");
  });

  it("maps undefined to neutral", () => {
    expect(healthStatusVariant(undefined)).toBe("neutral");
  });
});

describe("Badge", () => {
  it("renders its children", () => {
    render(<Badge variant="ok">green</Badge>);
    expect(screen.getByText("green")).toBeInTheDocument();
  });
});
