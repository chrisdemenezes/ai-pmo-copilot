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
