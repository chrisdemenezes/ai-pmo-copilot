/**
 * STRATECH V2 — Executive Cockpit mock data (Sprint 1).
 *
 * Explicitly simulated: Portfolio/Program are not real entities yet
 * (Release 0.2). This module is the single source of mock data for the
 * Cockpit so every Entrega (2.1-2.5) reads from here, never from ad hoc
 * literals scattered across components -- when Release 0.2/0.3 wire real
 * data, only this file's callers change, not every component.
 */

export interface CockpitKPI {
  label: string;
  value: string;
  href?: string;
}

export const COCKPIT_KPIS: CockpitKPI[] = [
  { label: "Portfólios Ativos", value: "3" },
  { label: "Programas em Execução", value: "8" },
  { label: "Projetos em Andamento", value: "24" },
  { label: "Decisões Pendentes", value: "5", href: "/decisions" },
];

export type CockpitHealth = "green" | "yellow" | "red";

export interface PortfolioSituation {
  name: string;
  health: CockpitHealth;
  progress: number;
  programsCount: number;
  projectsCount: number;
  owner: string;
}

export const PORTFOLIO_SITUATIONS: PortfolioSituation[] = [
  {
    name: "Portfólio Corporativo",
    health: "yellow",
    progress: 58,
    programsCount: 4,
    projectsCount: 14,
    owner: "Diretoria de Estratégia",
  },
  {
    name: "Portfólio de Transformação Digital",
    health: "green",
    progress: 74,
    programsCount: 3,
    projectsCount: 8,
    owner: "CIO",
  },
  {
    name: "Portfólio de Expansão Regional",
    health: "red",
    progress: 31,
    programsCount: 1,
    projectsCount: 2,
    owner: "VP de Operações",
  },
];

export interface ProgramSituation {
  name: string;
  portfolio: string;
  health: CockpitHealth;
  progress: number;
  projectsCount: number;
  owner: string;
}

export const PROGRAM_SITUATIONS: ProgramSituation[] = [
  {
    name: "Modernização de Plataformas",
    portfolio: "Portfólio de Transformação Digital",
    health: "green",
    progress: 80,
    projectsCount: 3,
    owner: "Gerente de Programa — Ana Ribeiro",
  },
  {
    name: "Eficiência Operacional",
    portfolio: "Portfólio Corporativo",
    health: "yellow",
    progress: 52,
    projectsCount: 5,
    owner: "Gerente de Programa — Bruno Castro",
  },
  {
    name: "Entrada em Novos Mercados",
    portfolio: "Portfólio de Expansão Regional",
    health: "red",
    progress: 28,
    projectsCount: 2,
    owner: "Gerente de Programa — Carla Mendes",
  },
];

export interface WorkItemBreakdown {
  category: "Demandas" | "Riscos" | "Issues" | "Mudanças";
  description: string;
  total: number;
  open: number;
  inProgress: number;
  resolved: number;
  critical: number;
}

/**
 * Entrega 2.3 -- nenhuma destas 4 categorias tem entidade real hoje.
 * "Riscos" aqui é deliberadamente distinto do Risk Intelligence real (V1,
 * RiskConcentrationRanking) -- este é o inventário de gestão de risco de
 * portfólio (Demandas/Issues/Mudanças/Riscos como itens de trabalho
 * formais), não a análise de IA sobre transcrições/reuniões.
 */
export const WORK_ITEM_BREAKDOWN: WorkItemBreakdown[] = [
  {
    category: "Demandas",
    description: "Solicitações em triagem, ainda não aprovadas como projeto",
    total: 12,
    open: 7,
    inProgress: 3,
    resolved: 2,
    critical: 2,
  },
  {
    category: "Riscos",
    description: "Riscos formais de portfólio/programa, com plano de mitigação",
    total: 19,
    open: 9,
    inProgress: 6,
    resolved: 4,
    critical: 3,
  },
  {
    category: "Issues",
    description: "Problemas já realizados, exigindo ação corretiva",
    total: 8,
    open: 5,
    inProgress: 2,
    resolved: 1,
    critical: 1,
  },
  {
    category: "Mudanças",
    description: "Solicitações formais de mudança de escopo, prazo ou custo",
    total: 6,
    open: 2,
    inProgress: 3,
    resolved: 1,
    critical: 1,
  },
];
