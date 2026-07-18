/**
 * STRATECH V2 — Portfolio domain entity (Release 0.2, Capability 01).
 *
 * Distinct from `lib/mock/cockpit-data.ts` (PortfolioSituation, a flat
 * demonstration shape) and from `lib/portfolio-intelligence/` (V1's real
 * project-level executive prioritization feature — unrelated to this
 * entity, see Decision Log D-012).
 *
 * First implementation of Portfolio → Program → Project → Demand → Risk →
 * Decision → Action → Knowledge (Diretriz Arquitetural Permanente,
 * Release 0.2). Since Capability 02, Program is a real entity
 * (`./program.ts`) and `programCount`/`progressPercentage`/`health` below
 * are seed defaults only — `consolidatePortfolios()` in `program.ts`
 * derives the values actually shown in the Executive Cockpit from real
 * Programs, per Domain Blueprint CB-002 §2.
 *
 * `listPortfolios()` is async and repository-shaped on purpose: no backend
 * schema/migration exists yet for Portfolio (Domain Blueprint CB-001,
 * §4), so this resolves from seeded in-memory data today, but the
 * contract is the one a real BFF call would have. Swapping the body for a
 * real fetch later requires no change to any caller.
 */

import type { DomainHealth, DomainStatus, DomainPriority } from "./shared";

export type PortfolioHealth = DomainHealth;
export type PortfolioStatus = DomainStatus;
export type PortfolioPriority = DomainPriority;

export interface Portfolio {
  // Identificação
  id: string;
  name: string;
  code: string;
  description: string;
  category: string;

  // Gestão
  executiveOwner: string;
  strategicObjective: string;
  status: PortfolioStatus;
  health: PortfolioHealth;
  priority: PortfolioPriority;
  startDate: string;
  plannedEndDate: string;
  actualEndDate: string | null;

  // Indicadores
  progressPercentage: number;
  programCount: number;
  projectCount: number;
  linkedDemands: number;
  linkedRisks: number;
  linkedIssues: number;
  pendingDecisions: number;

  // Governança
  sponsor: string;
  pmoOwner: string;
  lastUpdated: string;
  nextReview: string;
}

const PORTFOLIOS: Portfolio[] = [
  {
    id: "PF-001",
    name: "Portfólio Corporativo",
    code: "PF-001",
    description: "Iniciativas estratégicas corporativas de maior visibilidade executiva.",
    category: "Corporativo",
    executiveOwner: "Diretoria de Estratégia",
    strategicObjective: "Sustentar o crescimento consolidado do grupo nos próximos 3 anos.",
    status: "Ativo",
    health: "yellow",
    priority: "Alta",
    startDate: "2025-02-01",
    plannedEndDate: "2027-02-01",
    actualEndDate: null,
    progressPercentage: 58,
    programCount: 4,
    projectCount: 14,
    linkedDemands: 6,
    linkedRisks: 9,
    linkedIssues: 4,
    pendingDecisions: 2,
    sponsor: "Diretoria de Estratégia",
    pmoOwner: "PMO Corporativo",
    lastUpdated: "2026-07-10",
    nextReview: "2026-08-01",
  },
  {
    id: "PF-002",
    name: "Portfólio de Transformação Digital",
    code: "PF-002",
    description: "Modernização de plataformas e processos digitais.",
    category: "Transformação Digital",
    executiveOwner: "CIO",
    strategicObjective: "Modernizar a base tecnológica e reduzir débito técnico crítico.",
    status: "Ativo",
    health: "green",
    priority: "Alta",
    startDate: "2025-06-01",
    plannedEndDate: "2026-12-01",
    actualEndDate: null,
    progressPercentage: 74,
    programCount: 3,
    projectCount: 8,
    linkedDemands: 3,
    linkedRisks: 4,
    linkedIssues: 2,
    pendingDecisions: 1,
    sponsor: "CIO",
    pmoOwner: "PMO de Tecnologia",
    lastUpdated: "2026-07-12",
    nextReview: "2026-07-25",
  },
  {
    id: "PF-003",
    name: "Portfólio de Expansão Regional",
    code: "PF-003",
    description: "Entrada em novos mercados regionais.",
    category: "Expansão",
    executiveOwner: "VP de Operações",
    strategicObjective: "Estabelecer presença operacional em 2 novos mercados até o fim da Release 0.2.",
    status: "Ativo",
    health: "red",
    priority: "Alta",
    startDate: "2026-01-15",
    plannedEndDate: "2026-11-30",
    actualEndDate: null,
    progressPercentage: 31,
    programCount: 1,
    projectCount: 2,
    linkedDemands: 2,
    linkedRisks: 5,
    linkedIssues: 1,
    pendingDecisions: 1,
    sponsor: "VP de Operações",
    pmoOwner: "PMO Regional",
    lastUpdated: "2026-07-15",
    nextReview: "2026-07-22",
  },
];

/** Repository-shaped accessor — see module docstring for why this is async. */
export async function listPortfolios(): Promise<Portfolio[]> {
  return PORTFOLIOS;
}
