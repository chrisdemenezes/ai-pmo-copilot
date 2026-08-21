"use client";

import { Header } from "@/components/shell/header";
import { DecisionSupportPanel } from "@/components/dashboard/decision-support-panel";
import { ExecutiveNarrativePanel } from "@/components/dashboard/executive-narrative-panel";

/**
 * V1 Product & Capability Completion, Pacote A (Founder Decision):
 * Decision Support e Executive Narrative deixam de estar incorporados ao
 * Dashboard Executivo e ganham uma entrada dedicada na navegação --
 * substitui a restrição anterior ("não criar dashboard novo ou experiência
 * ampla", Founder §12 do Technical Design de Decision Support), agora
 * superada por decisão explícita do Founder. Nenhum dos dois painéis foi
 * duplicado ou alterado -- apenas movidos de app/dashboard/page.tsx para
 * cá. AdvisorFramework, AIContextEngine, ExecutiveOrchestrator e os
 * contracts dos Advisors permanecem intocados.
 */
export default function InteligenciaExecutivaPage() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
      <Header>
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
            STRATECH · Executive Intelligence
          </p>
          <h1 className="font-display text-2xl font-semibold">Inteligência Executiva</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Faça uma pergunta executiva ou gere uma síntese sobre um escopo declarado --
            Executive Orchestrator, Wave 6 (Enterprise Advisors reais).
          </p>
        </div>
      </Header>

      <section className="flex flex-col gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">Decision Support</h2>
          <p className="text-sm text-ink-muted">
            Pergunta executiva — Executive Orchestrator, Wave 6 (Enterprise Advisors reais).
          </p>
        </div>
        <DecisionSupportPanel />
      </section>

      <section className="flex flex-col gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">Narrativa Executiva</h2>
          <p className="text-sm text-ink-muted">
            Síntese executiva de um escopo declarado — Executive Orchestrator, Wave 6.
          </p>
        </div>
        <ExecutiveNarrativePanel />
      </section>
    </main>
  );
}
