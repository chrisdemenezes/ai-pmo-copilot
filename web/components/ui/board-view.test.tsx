import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { BoardView } from "./board-view";

describe("BoardView", () => {
  it("renders one column per entry, with its item count and items", () => {
    render(
      <BoardView
        columns={[
          { key: "a", label: "Coluna A", items: ["x", "y"] },
          { key: "b", label: "Coluna B", items: ["z"] },
        ]}
        getItemKey={(item) => item}
        renderItem={(item) => <span>{item}</span>}
      />,
    );

    expect(screen.getByText("Coluna A")).toBeInTheDocument();
    expect(screen.getByText("Coluna B")).toBeInTheDocument();
    expect(screen.getByText("x")).toBeInTheDocument();
    expect(screen.getByText("y")).toBeInTheDocument();
    expect(screen.getByText("z")).toBeInTheDocument();
  });

  it("shows an explicit empty state for a column with no items, never a blank column", () => {
    render(
      <BoardView
        columns={[{ key: "empty", label: "Vazia", items: [] }]}
        getItemKey={(item) => String(item)}
        renderItem={(item) => <span>{String(item)}</span>}
      />,
    );

    expect(screen.getByText("Nenhum item")).toBeInTheDocument();
  });
});
