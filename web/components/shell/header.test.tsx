import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Header } from "./header";

describe("Header", () => {
  it("renders whatever the page passes as children, unmodified", () => {
    render(
      <Header>
        <span>Dashboard Executivo</span>
      </Header>,
    );
    expect(screen.getByText("Dashboard Executivo")).toBeInTheDocument();
  });
});
