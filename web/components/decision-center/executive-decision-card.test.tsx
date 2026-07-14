import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ExecutiveDecisionCard } from "./executive-decision-card";
import type { ExecutiveDecision } from "@/lib/decision-center/decision-queue";

const DECISION: ExecutiveDecision = {
  project_name: "Implantacao SAP S/4HANA",
  source: "status",
  window: "hoje",
  context: "Status: Crítico",
  decision: "Escalar ao patrocinador",
  whyItDependsOnMe: "Só um julgamento executivo decide se e como agir sobre este status.",
  consequenceOfInaction:
    "Nada muda sozinho: este status permanece assim até uma nova Análise de Status ser executada.",
  nextStep: "Escalar ao patrocinador",
};

describe("ExecutiveDecisionCard", () => {
  it("answers all 5 questions from FS-008 §3.5", () => {
    render(<ExecutiveDecisionCard decision={DECISION} />);

    expect(screen.getByRole("heading", { name: "Implantacao SAP S/4HANA" })).toBeInTheDocument();
    expect(screen.getByText("Status: Crítico")).toBeInTheDocument();
    expect(
      screen.getByText("Só um julgamento executivo decide se e como agir sobre este status."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Nada muda sozinho: este status permanece assim até uma nova Análise de Status ser executada.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Próximo passo")).toBeInTheDocument();
    expect(screen.getAllByText("Escalar ao patrocinador").length).toBeGreaterThan(0);
  });

  it("shows the window label", () => {
    render(<ExecutiveDecisionCard decision={DECISION} />);
    expect(screen.getByText("Hoje")).toBeInTheDocument();
  });

  it("links to the project's Workspace, encoded, closing the Executive Loop", () => {
    render(<ExecutiveDecisionCard decision={DECISION} />);
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/workspace/Implantacao%20SAP%20S%2F4HANA",
    );
  });

  it("never renders a create/edit/resolve control -- só leitura", () => {
    render(<ExecutiveDecisionCard decision={DECISION} />);
    for (const forbidden of [/criar/i, /editar/i, /resolver/i, /concluir/i]) {
      expect(screen.queryByRole("button", { name: forbidden })).toBeNull();
    }
  });
});
