/**
 * ProjectIntelligenceSummary — a projeção de inteligência de um Project
 * (TD-008 Fase 3b, Etapa 5). Consolida os dois read-models antes duplicados
 * (`ProjectSummary` do Dashboard e `WorkspaceSummary` do Workspace), ambos
 * espelhos de `ProjectSummaryResponse` (`src/api/routes/intelligence.py`).
 *
 * É uma projeção sobre a entidade `Project` — nunca a entidade de *Entrega*
 * (`lib/domain/project.ts`, Capability 03), que é outro bounded context.
 * A identidade é o `project_id` técnico (a chave, TD-008 Etapas 1-3);
 * `project_name` permanece **exclusivamente como atributo de exibição**.
 *
 * `project_id` é `number | null`: null apenas no caso degenerado de um
 * Project ainda sem nenhuma análise registrada (nada a projetar). Os
 * agregados (`total_analyses`/`open_risks`/`pending_action_items`/
 * `latest_health_status`) derivam de `AnalysisRecord`, não da entidade de
 * Entrega.
 */
export interface ProjectIntelligenceSummary {
  /** Chave de acesso — a identidade técnica do Project (TD-008). */
  project_id: number | null;
  /** Atributo de exibição — nunca uma chave. */
  project_name: string;
  total_analyses: number;
  open_risks: number;
  pending_action_items: number;
  latest_health_status: "green" | "yellow" | "red" | null;
}
