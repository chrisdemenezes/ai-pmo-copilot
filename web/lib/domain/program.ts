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
import { worstHealth, type DomainHealth, type DomainStatus, type DomainPriority } from "./shared";

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
}

const PROGRAMS: Program[] = [
  Program.create({
    id: "PG-001",
    name: "Eficiência Operacional",
    code: "PG-001",
    description: "Redução de custo operacional e simplificação de processos internos.",
    portfolioId: "PF-001",
    sponsor: "Diretoria de Estratégia",
    programManager: "Bruno Castro",
    status: "Ativo",
    health: "yellow",
    priority: "Alta",
    objective: "Reduzir custo operacional em 12% mantendo nível de serviço.",
    startDate: "2025-08-01",
    plannedEndDate: "2026-10-01",
    actualEndDate: null,
    progressPercentage: 52,
    projectCount: 5,
    linkedDemands: 3,
    linkedRisks: 4,
    linkedIssues: 2,
    pendingDecisions: 1,
    pendingActions: 2,
    pmoOwner: "PMO Corporativo",
    lastUpdated: "2026-07-11",
    nextReview: "2026-07-28",
  }),
  Program.create({
    id: "PG-002",
    name: "Governança e Compliance Corporativa",
    code: "PG-002",
    description: "Padronização de controles de governança entre unidades de negócio.",
    portfolioId: "PF-001",
    sponsor: "Diretoria de Estratégia",
    programManager: "Diego Souza",
    status: "Ativo",
    health: "yellow",
    priority: "Média",
    objective: "Unificar o modelo de controles internos até o fim da Release 0.2.",
    startDate: "2026-02-01",
    plannedEndDate: "2026-12-15",
    actualEndDate: null,
    progressPercentage: 45,
    projectCount: 2,
    linkedDemands: 1,
    linkedRisks: 2,
    linkedIssues: 0,
    pendingDecisions: 1,
    pendingActions: 1,
    pmoOwner: "PMO Corporativo",
    lastUpdated: "2026-07-09",
    nextReview: "2026-08-05",
  }),
  Program.create({
    id: "PG-003",
    name: "Modernização de Plataformas",
    code: "PG-003",
    description: "Modernização das plataformas tecnológicas centrais.",
    portfolioId: "PF-002",
    sponsor: "CIO",
    programManager: "Ana Ribeiro",
    status: "Ativo",
    health: "green",
    priority: "Alta",
    objective: "Migrar as 3 plataformas legadas mais críticas para a nova arquitetura.",
    startDate: "2025-07-01",
    plannedEndDate: "2026-09-01",
    actualEndDate: null,
    progressPercentage: 80,
    projectCount: 3,
    linkedDemands: 2,
    linkedRisks: 2,
    linkedIssues: 1,
    pendingDecisions: 0,
    pendingActions: 1,
    pmoOwner: "PMO de Tecnologia",
    lastUpdated: "2026-07-13",
    nextReview: "2026-07-27",
  }),
  Program.create({
    id: "PG-004",
    name: "Entrada em Novos Mercados",
    code: "PG-004",
    description: "Estruturação operacional para entrada em 2 novos mercados regionais.",
    portfolioId: "PF-003",
    sponsor: "VP de Operações",
    programManager: "Carla Mendes",
    status: "Ativo",
    health: "red",
    priority: "Alta",
    objective: "Estabelecer operação local nos 2 mercados-alvo até o fim da Release 0.2.",
    startDate: "2026-02-01",
    plannedEndDate: "2026-11-01",
    actualEndDate: null,
    progressPercentage: 28,
    projectCount: 2,
    linkedDemands: 2,
    linkedRisks: 5,
    linkedIssues: 1,
    pendingDecisions: 1,
    pendingActions: 1,
    pmoOwner: "PMO Regional",
    lastUpdated: "2026-07-14",
    nextReview: "2026-07-21",
  }),
];

/** Repository-shaped accessor, same convention as listPortfolios(). */
export async function listPrograms(): Promise<Program[]> {
  return PROGRAMS;
}

/**
 * Derives each Portfolio's programCount/progressPercentage/health from its
 * real Programs (Domain Blueprint CB-002 §2) -- the Executive Cockpit
 * reads this, never the seed values baked into a Portfolio at rest. A
 * Portfolio with no Programs yet keeps its seed values (nothing to derive
 * from).
 */
export function consolidatePortfolios(portfolios: Portfolio[], programs: Program[]): Portfolio[] {
  return portfolios.map((portfolio) => {
    const ownPrograms = programs.filter((program) => program.belongsToPortfolio(portfolio.id));
    if (ownPrograms.length === 0) {
      return portfolio;
    }
    const progressPercentage = Math.round(
      ownPrograms.reduce((sum, program) => sum + program.progressPercentage, 0) / ownPrograms.length,
    );
    return {
      ...portfolio,
      programCount: ownPrograms.length,
      progressPercentage,
      health: worstHealth(ownPrograms.map((program) => program.health)),
    };
  });
}
