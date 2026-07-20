/**
 * STRATECH V2 — Program domain entity (Release 0.2, Capability 02).
 *
 * Represents Transformação in the STRATECH hierarchy: Portfolio
 * (Estratégia) -> Program (Transformação) -> Project (Execução). Every
 * Program belongs to exactly one Portfolio -- enforced at construction,
 * not just documented (Domain Blueprint CB-002 §1).
 *
 * Implemented as a class per the Diretriz Arquitetural Permanente
 * introduced in this Capability: entities from here on encapsulate their
 * own behavior instead of being anemic data bags. `Portfolio` (Capability
 * 01) predates this rule and is intentionally left as-is (Blueprint §1) --
 * no unnecessary refactor.
 */

import type { Portfolio } from "./portfolio";
import { consolidateFromChildren, type DomainHealth, type DomainStatus, type DomainPriority } from "./shared";

export interface ProgramProps {
  // Identificação
  id: string;
  name: string;
  code: string;
  description: string;

  // Gestão
  portfolioId: string;
  sponsor: string;
  programManager: string;
  status: DomainStatus;
  health: DomainHealth;
  priority: DomainPriority;

  // Planejamento
  objective: string;
  startDate: string;
  plannedEndDate: string;
  actualEndDate: string | null;

  // Indicadores
  progressPercentage: number;
  projectCount: number;
  linkedDemands: number;
  linkedRisks: number;
  linkedIssues: number;
  pendingDecisions: number;
  pendingActions: number;

  // Governança
  pmoOwner: string;
  lastUpdated: string;
  nextReview: string;
}

export class Program {
  readonly id: string;
  readonly name: string;
  readonly code: string;
  readonly description: string;
  readonly portfolioId: string;
  readonly sponsor: string;
  readonly programManager: string;
  readonly status: DomainStatus;
  readonly health: DomainHealth;
  readonly priority: DomainPriority;
  readonly objective: string;
  readonly startDate: string;
  readonly plannedEndDate: string;
  readonly actualEndDate: string | null;
  readonly progressPercentage: number;
  readonly projectCount: number;
  readonly linkedDemands: number;
  readonly linkedRisks: number;
  readonly linkedIssues: number;
  readonly pendingDecisions: number;
  readonly pendingActions: number;
  readonly pmoOwner: string;
  readonly lastUpdated: string;
  readonly nextReview: string;

  private constructor(props: ProgramProps) {
    this.id = props.id;
    this.name = props.name;
    this.code = props.code;
    this.description = props.description;
    this.portfolioId = props.portfolioId;
    this.sponsor = props.sponsor;
    this.programManager = props.programManager;
    this.status = props.status;
    this.health = props.health;
    this.priority = props.priority;
    this.objective = props.objective;
    this.startDate = props.startDate;
    this.plannedEndDate = props.plannedEndDate;
    this.actualEndDate = props.actualEndDate;
    this.progressPercentage = props.progressPercentage;
    this.projectCount = props.projectCount;
    this.linkedDemands = props.linkedDemands;
    this.linkedRisks = props.linkedRisks;
    this.linkedIssues = props.linkedIssues;
    this.pendingDecisions = props.pendingDecisions;
    this.pendingActions = props.pendingActions;
    this.pmoOwner = props.pmoOwner;
    this.lastUpdated = props.lastUpdated;
    this.nextReview = props.nextReview;
  }

  /** Every Program must belong to a Portfolio -- Diretriz Arquitetural Permanente, not an optional convention. */
  static create(props: ProgramProps): Program {
    if (!props.portfolioId) {
      throw new Error(
        `Program "${props.name}" precisa de um portfolioId — todo Program pertence a um Portfolio.`,
      );
    }
    return new Program(props);
  }

  belongsToPortfolio(portfolioId: string): boolean {
    return this.portfolioId === portfolioId;
  }

  isAtRisk(): boolean {
    return this.health === "red";
  }

  isOverdue(referenceDate: Date = new Date()): boolean {
    return (
      this.actualEndDate === null &&
      this.status !== "Encerrado" &&
      new Date(this.plannedEndDate) < referenceDate
    );
  }

  /** Plain-object snapshot -- lets consolidatePrograms() (project.ts) rebuild a Program via create() with updated indicators, without re-listing every field by hand at each call site. */
  toProps(): ProgramProps {
    return {
      id: this.id,
      name: this.name,
      code: this.code,
      description: this.description,
      portfolioId: this.portfolioId,
      sponsor: this.sponsor,
      programManager: this.programManager,
      status: this.status,
      health: this.health,
      priority: this.priority,
      objective: this.objective,
      startDate: this.startDate,
      plannedEndDate: this.plannedEndDate,
      actualEndDate: this.actualEndDate,
      progressPercentage: this.progressPercentage,
      projectCount: this.projectCount,
      linkedDemands: this.linkedDemands,
      linkedRisks: this.linkedRisks,
      linkedIssues: this.linkedIssues,
      pendingDecisions: this.pendingDecisions,
      pendingActions: this.pendingActions,
      pmoOwner: this.pmoOwner,
      lastUpdated: this.lastUpdated,
      nextReview: this.nextReview,
    };
  }
}

/** Wire shape of GET /api/programs (ProgramResponse, snake_case). */
interface ProgramApiRow {
  id: number;
  portfolio_id: number;
  name: string;
  code: string;
  description: string | null;
  sponsor: string | null;
  program_manager: string | null;
  status: string;
  health: string;
  priority: string;
  objective: string | null;
  start_date: string | null;
  planned_end_date: string | null;
  actual_end_date: string | null;
  progress_percentage: number;
  project_count: number;
  linked_demands: number;
  linked_risks: number;
  linked_issues: number;
  pending_decisions: number;
  pending_actions: number;
  pmo_owner: string | null;
  last_updated: string | null;
  next_review: string | null;
}

function toProgram(row: ProgramApiRow): Program {
  // Program.create() keeps enforcing the portfolioId invariant on API data
  // too -- a backend row without a portfolio (impossible by schema, the FK
  // is NOT NULL) would fail loudly here instead of rendering broken.
  return Program.create({
    id: String(row.id),
    name: row.name,
    code: row.code,
    description: row.description ?? "",
    portfolioId: String(row.portfolio_id),
    sponsor: row.sponsor ?? "",
    programManager: row.program_manager ?? "",
    status: row.status as DomainStatus,
    health: row.health as DomainHealth,
    priority: row.priority as DomainPriority,
    objective: row.objective ?? "",
    startDate: row.start_date ?? "",
    plannedEndDate: row.planned_end_date ?? "",
    actualEndDate: row.actual_end_date,
    progressPercentage: row.progress_percentage,
    projectCount: row.project_count,
    linkedDemands: row.linked_demands,
    linkedRisks: row.linked_risks,
    linkedIssues: row.linked_issues,
    pendingDecisions: row.pending_decisions,
    pendingActions: row.pending_actions,
    pmoOwner: row.pmo_owner ?? "",
    lastUpdated: row.last_updated ?? "",
    nextReview: row.next_review ?? "",
  });
}

/** Repository-shaped accessor — real BFF call since Wave 2 Sprint 5, same convention as listPortfolios(). */
export async function listPrograms(): Promise<Program[]> {
  const response = await fetch("/api/bff/program");
  if (!response.ok) {
    throw new Error(`Falha ao carregar programas (${response.status})`);
  }
  const rows = (await response.json()) as ProgramApiRow[];
  return rows.map(toProgram);
}

/**
 * Derives each Portfolio's programCount/progressPercentage/health from its
 * real Programs (Domain Blueprint CB-002 §2) -- the Executive Cockpit
 * reads this, never the seed values baked into a Portfolio at rest. A
 * Portfolio with no Programs yet keeps its seed values (nothing to derive
 * from). Algorithm lives in consolidateFromChildren() (shared.ts, AR-1) --
 * only the rebuild step (plain object spread) is specific to Portfolio.
 */
export function consolidatePortfolios(portfolios: Portfolio[], programs: Program[]): Portfolio[] {
  return consolidateFromChildren(
    portfolios,
    programs,
    (program, portfolio) => program.belongsToPortfolio(portfolio.id),
    (program) => program.progressPercentage,
    (program) => program.health,
    (portfolio, programCount, progressPercentage, health) => ({
      ...portfolio,
      programCount,
      progressPercentage,
      health,
    }),
  );
}
