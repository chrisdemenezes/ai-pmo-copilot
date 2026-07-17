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

  // Executive Trust: para Risco, "Decisão sugerida" e "Próximo passo" são
  // textos reais e distintos -- nenhum dos dois pode ficar de fora do card.
  it("shows 'Decisão sugerida' and 'Próximo passo' as separate real texts for a risk decision", () => {
    const riskDecision: ExecutiveDecision = {
      project_name: "Aurora",
      source: "risk",
      window: "hoje",
      context: "1 risco(s) na zona de atenção",
      decision: "Priorizar mitigação imediata",
      whyItDependsOnMe: "Só um julgamento executivo decide como mitigar ou aceitar este risco.",
      consequenceOfInaction:
        "Nada muda sozinho: estes riscos permanecem na zona de atenção até uma nova Avaliação de Riscos ser executada.",
      nextStep: "Escalar ao comitê executivo",
    };

    render(<ExecutiveDecisionCard decision={riskDecision} />);

    expect(screen.getByText("Decisão sugerida")).toBeInTheDocument();
    expect(screen.getByText("Priorizar mitigação imediata")).toBeInTheDocument();
    expect(screen.getByText("Próximo passo")).toBeInTheDocument();
    expect(screen.getByText("Escalar ao comitê executivo")).toBeInTheDocument();
  });
});
