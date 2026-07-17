import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ExecutivePortfolioCard } from "./executive-portfolio-card";
import type { PortfolioIntelligenceItem } from "@/lib/portfolio-intelligence/portfolio-view";

const DECISION_ITEM: PortfolioIntelligenceItem = {
  project_name: "Implantacao SAP S/4HANA",
  layer: "decision_today",
  whyAttention: "Decisão pendente hoje",
  realSignal: "Status: Crítico",
  nextMove: { label: "Ver decisão completa", href: "/decisions" },
};

const NO_SIGNAL_ITEM: PortfolioIntelligenceItem = {
  project_name: "Portal do Cliente 2.0",
  layer: "no_signal",
  whyAttention: "Sem sinal de atenção",
  realSignal: "Nenhuma decisão pendente, nenhum risco identificado",
  nextMove: null,
};

describe("ExecutivePortfolioCard", () => {
  it("answers the 3 questions from FS-009 §3.5 for a project with a pending decision", () => {
    render(<ExecutivePortfolioCard item={DECISION_ITEM} />);

    expect(screen.getByRole("heading", { name: "Implantacao SAP S/4HANA" })).toBeInTheDocument();
    expect(screen.getByText("Decisão pendente hoje")).toBeInTheDocument();
    expect(screen.getByText("Status: Crítico")).toBeInTheDocument();
    expect(screen.getByText("Ver decisão completa →")).toBeInTheDocument();
  });

  it("links to the next move's href", () => {
    render(<ExecutivePortfolioCard item={DECISION_ITEM} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/decisions");
  });

  it("renders the no_signal layer without a link, in a discreet, non-competing form", () => {
    render(<ExecutivePortfolioCard item={NO_SIGNAL_ITEM} />);

    expect(screen.getByText("Portal do Cliente 2.0")).toBeInTheDocument();
    expect(screen.getByText("Sem sinal de atenção")).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("never renders a create/edit/resolve control -- só leitura", () => {
    render(<ExecutivePortfolioCard item={DECISION_ITEM} />);
    for (const forbidden of [/criar/i, /editar/i, /resolver/i, /concluir/i]) {
      expect(screen.queryByRole("button", { name: forbidden })).toBeNull();
    }
  });

  // Incremento 2 -- camada de Risco a Monitorar: nunca uma consequência
  // inferida, sempre navegação real (Founder, aprovação da User Journey).
  it("renders the risk_to_monitor layer with its revised question and a real navigation move", () => {
    const item: PortfolioIntelligenceItem = {
      project_name: "Portal do Cliente 2.0",
      layer: "risk_to_monitor",
      whyAttention: "Por que este projeto merece acompanhamento?",
      realSignal: "3 risco(s) identificado(s)",
      nextMove: { label: "Ver riscos no Workspace", href: "/workspace/Portal%20do%20Cliente%202.0" },
    };

    render(<ExecutivePortfolioCard item={item} />);

    expect(screen.getByText("Por que este projeto merece acompanhamento?")).toBeInTheDocument();
    expect(screen.getByText("3 risco(s) identificado(s)")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute("href", "/workspace/Portal%20do%20Cliente%202.0");
  });
});
