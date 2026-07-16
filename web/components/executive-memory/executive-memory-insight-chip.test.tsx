import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ExecutiveMemoryInsightChip } from "./executive-memory-insight-chip";
import type { ExecutiveMemoryInsight } from "@/lib/executive-memory/memory-insights";

const INSIGHT: ExecutiveMemoryInsight = { kind: "mudou", text: "Mudou: Atenção → Crítico" };

describe("ExecutiveMemoryInsightChip", () => {
  it("renders the insight text verbatim", () => {
    render(<ExecutiveMemoryInsightChip insight={INSIGHT} />);
    expect(screen.getByText("Mudou: Atenção → Crítico")).toBeInTheDocument();
  });

  it("is never interactive -- no link, no button", () => {
    render(<ExecutiveMemoryInsightChip insight={INSIGHT} />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
