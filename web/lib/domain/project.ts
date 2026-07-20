/**
 * STRATECH V2 — Project domain entity (Release 0.2, Capability 03).
 *
 * Represents Execução in the STRATECH hierarchy: Portfolio (Estratégia)
 * -> Program (Transformação) -> Project (Execução). Every Project
 * belongs to exactly one Program -- enforced at construction, same
 * pattern as Program -> Portfolio (Capability 02).
 *
 * NOT to be confused with two other "Project" concepts already in this
 * codebase (Decision Log D-019):
 *  1. The real backend `Project` model (`src/database/models.py`, Épico
 *     1) -- persisted, currently only used for org-scoped membership.
 *  2. `ProjectSummary` (`lib/dashboard/types.ts`) -- real V1 data from
 *     the BFF, keyed by free-text `project_name`, powering the existing
 *     "Projetos" grid/Risk Concentration/Health Distribution widgets.
 * All three stay deliberately disconnected (no shared ID) until the
 * Épico 4 unification. This module never imports from either.
 */

import { Program, type ProgramProps } from "./program";
import { consolidateFromChildren, type DomainHealth, type DomainStatus, type DomainPriority } from "./shared";

export interface Owner {
  name: string;
  role: string;
}

export interface Milestone {
  name: string;
  dueDate: string;
  status: "Pendente" | "Concluído" | "Atrasado";
}

export interface Team {
  size: number;
  leadName: string;
}

export interface ProjectProps {
  // Identificação
  id: string;
  name: string;
  code: string;
  description: string;

  // Organização (portfolioId é derivado, nunca armazenado -- ver belongsToPortfolio())
  programId: string;
  sponsor: string;
  projectManager: string;

  // Planejamento
  objective: string;
  startDate: string;
  plannedEndDate: string;
  actualEndDate: string | null;

  // Indicadores
  progressPercentage: number;
  health: DomainHealth;
  status: DomainStatus;
  priority: DomainPriority;

  // Governança
  lastUpdated: string;
  nextReview: string;

  // Objetos de apoio internos (Domain Blueprint CB-003 §1) -- não são
  // entidades próprias ainda.
  owner: Owner;
  milestones: Milestone[];
  team: Team;
}

export class Project {
  readonly id: string;
  readonly name: string;
  readonly code: string;
  readonly description: string;
  readonly programId: string;
  readonly sponsor: string;
  readonly projectManager: string;
  readonly objective: string;
  readonly startDate: string;
  readonly plannedEndDate: string;
  readonly actualEndDate: string | null;
  readonly status: DomainStatus;
  readonly priority: DomainPriority;
  readonly lastUpdated: string;
  readonly nextReview: string;
  readonly owner: Owner;
  readonly milestones: Milestone[];
  readonly team: Team;

  private readonly _progressPercentage: number;
  private readonly _health: DomainHealth;

  private constructor(props: ProjectProps) {
    this.id = props.id;
    this.name = props.name;
    this.code = props.code;
    this.description = props.description;
    this.programId = props.programId;
    this.sponsor = props.sponsor;
    this.projectManager = props.projectManager;
    this.objective = props.objective;
    this.startDate = props.startDate;
    this.plannedEndDate = props.plannedEndDate;
    this.actualEndDate = props.actualEndDate;
    this.status = props.status;
    this.priority = props.priority;
    this.lastUpdated = props.lastUpdated;
    this.nextReview = props.nextReview;
    this.owner = props.owner;
    this.milestones = props.milestones;
    this.team = props.team;
    this._progressPercentage = props.progressPercentage;
    this._health = props.health;
  }

  /** Every Project must belong to a Program -- same invariant discipline as Program -> Portfolio. */
  static create(props: ProjectProps): Project {
    if (!props.programId) {
      throw new Error(
        `Project "${props.name}" precisa de um programId — todo Project pertence a um Program.`,
      );
    }
    return new Project(props);
  }

  belongsToProgram(programId: string): boolean {
    return this.programId === programId;
  }

  /** Portfolio is derived, never stored on Project (Domain Blueprint CB-003 §1) -- found through the parent Program. */
  belongsToPortfolio(portfolioId: string, programs: Program[]): boolean {
    const parent = programs.find((program) => program.id === this.programId);
    return parent ? parent.belongsToPortfolio(portfolioId) : false;
  }

  isOverdue(referenceDate: Date = new Date()): boolean {
    return (
      this.actualEndDate === null &&
      this.status !== "Encerrado" &&
      new Date(this.plannedEndDate) < referenceDate
    );
  }

  isAtRisk(): boolean {
    return this._health === "red";
  }

  completionPercentage(): number {
    return this._progressPercentage;
  }

  health(): DomainHealth {
    return this._health;
  }
}

/** Wire shape of GET /api/projects-delivery (ProjectDeliveryResponse, snake_case). */
interface ProjectApiRow {
  id: number;
  program_id: number;
  name: string;
  code: string | null;
  description: string | null;
  objective: string | null;
  sponsor: string | null;
  project_manager: string | null;
  status: string | null;
  health: string | null;
  priority: string | null;
  start_date: string | null;
  planned_end_date: string | null;
  actual_end_date: string | null;
  progress_percentage: number | null;
  last_updated: string | null;
  next_review: string | null;
  owner: Owner | null;
  milestones: Milestone[] | null;
  team: Team | null;
}

function toProject(row: ProjectApiRow): Project {
  // Project.create() keeps enforcing the programId invariant on API data
  // too -- the API only serves domain-linked Projects (program_id IS NOT
  // NULL), so a missing programId here means a real contract break.
  return Project.create({
    id: String(row.id),
    name: row.name,
    code: row.code ?? "",
    description: row.description ?? "",
    programId: String(row.program_id),
    sponsor: row.sponsor ?? "",
    projectManager: row.project_manager ?? "",
    objective: row.objective ?? "",
    startDate: row.start_date ?? "",
    plannedEndDate: row.planned_end_date ?? "",
    actualEndDate: row.actual_end_date,
    progressPercentage: row.progress_percentage ?? 0,
    health: (row.health ?? "green") as DomainHealth,
    status: (row.status ?? "Ativo") as DomainStatus,
    priority: (row.priority ?? "Média") as DomainPriority,
    lastUpdated: row.last_updated ?? "",
    nextReview: row.next_review ?? "",
    owner: row.owner ?? { name: "", role: "" },
    milestones: row.milestones ?? [],
    team: row.team ?? { size: 0, leadName: "" },
  });
}

/** Repository-shaped accessor — real BFF call since Wave 2 Sprint 5, same convention as listPortfolios()/listPrograms(). */
export async function listProjects(): Promise<Project[]> {
  const response = await fetch("/api/bff/project-delivery");
  if (!response.ok) {
    throw new Error(`Falha ao carregar projetos (${response.status})`);
  }
  const rows = (await response.json()) as ProjectApiRow[];
  return rows.map(toProject);
}

/**
 * Derives each Program's projectCount/progressPercentage/health from its
 * real Projects (Domain Blueprint CB-003 §2) -- feeds consolidatePortfolios()
 * (program.ts), making Portfolio -> Program -> Project rollup transitive.
 * A Program with no Projects yet keeps its own values (nothing to derive).
 * Algorithm lives in consolidateFromChildren() (shared.ts, AR-1) -- only
 * the rebuild step (Program.create(), since Program is a class) is
 * specific to Program.
 */
export function consolidatePrograms(programs: Program[], projects: Project[]): Program[] {
  return consolidateFromChildren(
    programs,
    projects,
    (project, program) => project.belongsToProgram(program.id),
    (project) => project.completionPercentage(),
    (project) => project.health(),
    (program, projectCount, progressPercentage, health) => {
      const props: ProgramProps = { ...program.toProps(), projectCount, progressPercentage, health };
      return Program.create(props);
    },
  );
}

/**
 * Top N Projects needing executive attention, ranked by severity (red
 * before yellow before green) then by ascending progress within the same
 * severity -- the closest proxy to "risco" available on Project today
 * (it has no linkedRisks indicator of its own, unlike Program/Portfolio).
 */
export function rankProjectsNeedingAttention(projects: Project[], limit = 5): Project[] {
  const severity: Record<DomainHealth, number> = { red: 0, yellow: 1, green: 2 };
  return [...projects]
    .sort((a, b) => {
      const severityDiff = severity[a.health()] - severity[b.health()];
      if (severityDiff !== 0) return severityDiff;
      return a.completionPercentage() - b.completionPercentage();
    })
    .slice(0, limit);
}

/** Projects belonging to a Program with health "red" -- used by the Program Execution panel's "Projetos Críticos" count. */
export function countCriticalProjects(programId: string, projects: Project[]): number {
  return projects.filter((project) => project.belongsToProgram(programId) && project.isAtRisk()).length;
}
