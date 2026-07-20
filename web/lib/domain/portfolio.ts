/**
 * STRATECH V2 — Portfolio domain entity (Release 0.2, Capability 01;
 * wired to the real Enterprise Domain API in Wave 2, Sprint 5).
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
 * are at-rest values only — `consolidatePortfolios()` in `program.ts`
 * derives the values actually shown in the Executive Cockpit from real
 * Programs, per Domain Blueprint CB-002 §2.
 *
 * `listPortfolios()` resolves from the real backend via the BFF
 * (`/api/bff/portfolio` → `GET /api/portfolios`, org-scoped and
 * RBAC-protected) — the repository-shaped seam promised since Capability
 * 01 (D-011) paid off exactly as designed: only this module changed when
 * the real backend arrived; no hook, page, or component was touched. The
 * seed rows previously hardcoded here live in the database now (migration
 * 0008), so what every page shows is unchanged.
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

/** Wire shape of GET /api/portfolios (PortfolioResponse, snake_case). */
interface PortfolioApiRow {
  id: number;
  name: string;
  code: string;
  description: string | null;
  category: string | null;
  executive_owner: string | null;
  strategic_objective: string | null;
  status: string;
  health: string;
  priority: string;
  start_date: string | null;
  planned_end_date: string | null;
  actual_end_date: string | null;
  progress_percentage: number;
  program_count: number;
  project_count: number;
  linked_demands: number;
  linked_risks: number;
  linked_issues: number;
  pending_decisions: number;
  sponsor: string | null;
  pmo_owner: string | null;
  last_updated: string | null;
  next_review: string | null;
}

function toPortfolio(row: PortfolioApiRow): Portfolio {
  return {
    id: String(row.id),
    name: row.name,
    code: row.code,
    description: row.description ?? "",
    category: row.category ?? "",
    executiveOwner: row.executive_owner ?? "",
    strategicObjective: row.strategic_objective ?? "",
    status: row.status as PortfolioStatus,
    health: row.health as PortfolioHealth,
    priority: row.priority as PortfolioPriority,
    startDate: row.start_date ?? "",
    plannedEndDate: row.planned_end_date ?? "",
    actualEndDate: row.actual_end_date,
    progressPercentage: row.progress_percentage,
    programCount: row.program_count,
    projectCount: row.project_count,
    linkedDemands: row.linked_demands,
    linkedRisks: row.linked_risks,
    linkedIssues: row.linked_issues,
    pendingDecisions: row.pending_decisions,
    sponsor: row.sponsor ?? "",
    pmoOwner: row.pmo_owner ?? "",
    lastUpdated: row.last_updated ?? "",
    nextReview: row.next_review ?? "",
  };
}

/** Repository-shaped accessor — real BFF call since Wave 2 Sprint 5. */
export async function listPortfolios(): Promise<Portfolio[]> {
  const response = await fetch("/api/bff/portfolio");
  if (!response.ok) {
    throw new Error(`Falha ao carregar portfólios (${response.status})`);
  }
  const rows = (await response.json()) as PortfolioApiRow[];
  return rows.map(toPortfolio);
}
