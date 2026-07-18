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

const PROJECTS: Project[] = [
  Project.create({
    id: "PJ-001",
    name: "Multilift",
    code: "PJ-001",
    description: "Modernização da linha de elevadores industriais.",
    programId: "PG-001",
    sponsor: "Diretoria de Estratégia",
    projectManager: "Fernanda Lima",
    objective: "Reduzir tempo de parada não planejada em 30%.",
    startDate: "2025-09-01",
    plannedEndDate: "2026-06-01",
    actualEndDate: null,
    progressPercentage: 30,
    health: "red",
    status: "Ativo",
    priority: "Alta",
    lastUpdated: "2026-07-15",
    nextReview: "2026-07-20",
    owner: { name: "Bruno Castro", role: "Product Owner" },
    milestones: [
      { name: "Diagnóstico concluído", dueDate: "2025-11-01", status: "Concluído" },
      { name: "Piloto em planta 1", dueDate: "2026-07-01", status: "Atrasado" },
    ],
    team: { size: 8, leadName: "Fernanda Lima" },
  }),
  Project.create({
    id: "PJ-002",
    name: "Automação de Faturamento",
    code: "PJ-002",
    description: "Automação do ciclo de faturamento corporativo.",
    programId: "PG-001",
    sponsor: "Diretoria de Estratégia",
    projectManager: "Rafael Nunes",
    objective: "Eliminar retrabalho manual no faturamento mensal.",
    startDate: "2026-01-15",
    plannedEndDate: "2026-09-01",
    actualEndDate: null,
    progressPercentage: 55,
    health: "yellow",
    status: "Ativo",
    priority: "Média",
    lastUpdated: "2026-07-12",
    nextReview: "2026-07-26",
    owner: { name: "Bruno Castro", role: "Product Owner" },
    milestones: [{ name: "MVP em produção", dueDate: "2026-08-01", status: "Pendente" }],
    team: { size: 5, leadName: "Rafael Nunes" },
  }),
  Project.create({
    id: "PJ-003",
    name: "Revisão de Controles Internos",
    code: "PJ-003",
    description: "Padronização de controles internos entre unidades.",
    programId: "PG-002",
    sponsor: "Diretoria de Estratégia",
    projectManager: "Diego Souza",
    objective: "Unificar o checklist de controles até o fim da Release 0.2.",
    startDate: "2026-02-15",
    plannedEndDate: "2026-10-01",
    actualEndDate: null,
    progressPercentage: 70,
    health: "green",
    status: "Ativo",
    priority: "Média",
    lastUpdated: "2026-07-10",
    nextReview: "2026-08-02",
    owner: { name: "Diego Souza", role: "Product Owner" },
    milestones: [{ name: "Checklist unificado publicado", dueDate: "2026-09-01", status: "Pendente" }],
    team: { size: 4, leadName: "Diego Souza" },
  }),
  Project.create({
    id: "PJ-004",
    name: "Implantação SAP S/4HANA",
    code: "PJ-004",
    description: "Migração da plataforma ERP legada para SAP S/4HANA.",
    programId: "PG-003",
    sponsor: "CIO",
    projectManager: "Ana Ribeiro",
    objective: "Migrar os módulos financeiro e de suprimentos.",
    startDate: "2025-08-01",
    plannedEndDate: "2026-08-01",
    actualEndDate: null,
    progressPercentage: 62,
    health: "yellow",
    status: "Ativo",
    priority: "Alta",
    lastUpdated: "2026-07-13",
    nextReview: "2026-07-27",
    owner: { name: "Ana Ribeiro", role: "Product Owner" },
    milestones: [
      { name: "Go-live financeiro", dueDate: "2026-06-01", status: "Atrasado" },
      { name: "Go-live suprimentos", dueDate: "2026-08-01", status: "Pendente" },
    ],
    team: { size: 10, leadName: "Ana Ribeiro" },
  }),
  Project.create({
    id: "PJ-005",
    name: "Migração de Data Center",
    code: "PJ-005",
    description: "Migração da infraestrutura on-premise para a nuvem.",
    programId: "PG-003",
    sponsor: "CIO",
    projectManager: "Ana Ribeiro",
    objective: "Descomissionar o data center físico até o fim da Release 0.2.",
    startDate: "2025-07-01",
    plannedEndDate: "2026-07-01",
    actualEndDate: null,
    progressPercentage: 88,
    health: "green",
    status: "Ativo",
    priority: "Alta",
    lastUpdated: "2026-07-14",
    nextReview: "2026-07-24",
    owner: { name: "Ana Ribeiro", role: "Product Owner" },
    milestones: [{ name: "Corte final de tráfego", dueDate: "2026-07-15", status: "Pendente" }],
    team: { size: 6, leadName: "Ana Ribeiro" },
  }),
  Project.create({
    id: "PJ-006",
    name: "Aurora",
    code: "PJ-006",
    description: "Estruturação da operação comercial no novo mercado.",
    programId: "PG-004",
    sponsor: "VP de Operações",
    projectManager: "Carla Mendes",
    objective: "Abrir a primeira unidade comercial no mercado-alvo.",
    startDate: "2026-02-01",
    plannedEndDate: "2026-10-01",
    actualEndDate: null,
    progressPercentage: 74,
    health: "green",
    status: "Ativo",
    priority: "Alta",
    lastUpdated: "2026-07-11",
    nextReview: "2026-07-25",
    owner: { name: "Carla Mendes", role: "Product Owner" },
    milestones: [{ name: "Unidade inaugurada", dueDate: "2026-09-01", status: "Pendente" }],
    team: { size: 7, leadName: "Carla Mendes" },
  }),
  Project.create({
    id: "PJ-007",
    name: "Abertura Operação LATAM",
    code: "PJ-007",
    description: "Estruturação regulatória e operacional para entrada na LATAM.",
    programId: "PG-004",
    sponsor: "VP de Operações",
    projectManager: "Carla Mendes",
    objective: "Obter licenças operacionais nos 2 países-alvo.",
    startDate: "2026-03-01",
    plannedEndDate: "2026-11-01",
    actualEndDate: null,
    progressPercentage: 22,
    health: "red",
    status: "Ativo",
    priority: "Alta",
    lastUpdated: "2026-07-14",
    nextReview: "2026-07-21",
    owner: { name: "Carla Mendes", role: "Product Owner" },
    milestones: [{ name: "Licenças protocoladas", dueDate: "2026-06-01", status: "Atrasado" }],
    team: { size: 4, leadName: "Carla Mendes" },
  }),
];

/** Repository-shaped accessor, same convention as listPortfolios()/listPrograms(). */
export async function listProjects(): Promise<Project[]> {
  return PROJECTS;
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
