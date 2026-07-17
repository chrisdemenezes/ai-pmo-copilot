import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { OrganizationalLearningCard } from "./organizational-learning-card";
import type { OrganizationalLearning } from "@/lib/organizational-intelligence/organizational-learnings";

const LEARNING: OrganizationalLearning = {
  category: "risco",
  description: "Atraso do fornecedor de middleware",
  occurrences: 3,
  projectNames: ["Aurora", "Multilift", "Portal do Cliente 2.0"],
};

describe("OrganizationalLearningCard", () => {
  it("renders the executive phrase, the verbatim text, and the real project names", () => {
    render(<OrganizationalLearningCard learning={LEARNING} />);
    expect(screen.getByText("Este risco apareceu em 3 projetos diferentes.")).toBeInTheDocument();
    expect(screen.getByText('"Atraso do fornecedor de middleware"')).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Aurora" })).toHaveAttribute(
      "href",
      "/workspace/Aurora",
    );
    expect(screen.getByRole("link", { name: "Multilift" })).toHaveAttribute(
      "href",
      "/workspace/Multilift",
    );
    expect(screen.getByRole("link", { name: "Portal do Cliente 2.0" })).toHaveAttribute(
      "href",
      "/workspace/Portal%20do%20Cliente%202.0",
    );
  });

  it("never renders a concept label/chip -- Zero Labels Rule (FS-011 §5)", () => {
    render(<OrganizationalLearningCard learning={LEARNING} />);
    for (const forbiddenLabel of [
      "Aprendizado Organizacional",
      "Organizational Finding",
      "Executive Finding",
    ]) {
      expect(screen.queryByText(forbiddenLabel)).toBeNull();
    }
  });
});
