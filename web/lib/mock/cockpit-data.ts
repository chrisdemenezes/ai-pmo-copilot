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
