// TD-008 Fase 3b, Etapa 5: o read-model `ProjectSummary` foi consolidado em
// `ProjectIntelligenceSummary` (`lib/project/intelligence-summary.ts`) --
// uma única projeção de inteligência sobre a entidade Project, ancorada no
// `project_id`. Este módulo mantém apenas o corpo de erro do BFF do Dashboard.

export interface DashboardErrorBody {
  error: string;
  detail: string;
}
