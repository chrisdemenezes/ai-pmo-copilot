/**
 * STRATECH V2 — Mission Control data (Founder panel).
 *
 * Unlike cockpit-data.ts (simulated Portfolio/Program/Project data), this
 * reflects REAL, current governance facts from this repository's own
 * docs/governance and PR history -- manually embedded for Sprint 1 (no
 * backend wiring yet). A future increment can replace this with a real
 * read of docs/governance/*.md or a GitHub API call; the shape stays the
 * same either way.
 */

export type EpicStatus = "Merged" | "In Progress" | "Not Started";

export interface EpicStatusEntry {
  code: string;
  name: string;
  status: EpicStatus;
  detail: string;
}

export const EPIC_STATUS: EpicStatusEntry[] = [
  { code: "Épico 1", name: "Schema Foundation", status: "Merged", detail: "PR #39, #40" },
  { code: "Épico 2", name: "Identity Foundation", status: "Merged", detail: "PR #41, #42" },
  { code: "Épico 3", name: "Organização e RBAC inicial", status: "Not Started", detail: "Próximo da Release 0.1" },
  { code: "Épico 4", name: "Projeto como entidade real", status: "Not Started", detail: "—" },
  { code: "Épico 5", name: "Auditoria e administração mínima", status: "Not Started", detail: "—" },
  { code: "Épico 6", name: "Validação e documentação", status: "Not Started", detail: "Contínuo" },
];

export interface ReleaseStatusEntry {
  version: string;
  name: string;
  status: "In Progress" | "Not Started";
  progress: number;
}

export const RELEASE_STATUS: ReleaseStatusEntry[] = [
  { version: "0.1", name: "Enterprise Foundation", status: "In Progress", progress: 33 },
  { version: "0.2", name: "Portfolio & Governance Foundation", status: "In Progress", progress: 35 },
  { version: "0.3", name: "AI Foundation", status: "Not Started", progress: 0 },
  { version: "0.4", name: "Integration Hub", status: "Not Started", progress: 0 },
  { version: "0.5", name: "Event Orchestration", status: "Not Started", progress: 0 },
];

export interface PullRequestEntry {
  number: number;
  title: string;
  status: "Merged" | "Open";
}

export const PULL_REQUESTS: PullRequestEntry[] = [
  { number: 43, title: "Product Engineering Framework (EO-021)", status: "Open" },
  { number: 42, title: "Close Epic 2 and update Release 0.1", status: "Merged" },
  { number: 41, title: "Épico 2 — Identity Foundation", status: "Merged" },
  { number: 40, title: "Governance Package GP-001 — Epic 1 Closure", status: "Merged" },
  { number: 39, title: "Release 0.1 relational foundation (Épico 1)", status: "Merged" },
];

export interface GovernanceSummary {
  technicalDebtOpen: number;
  baselineDefects: number;
  adrCount: number;
  adrCollision: boolean;
  lessonsLearned: number;
}

export const GOVERNANCE_SUMMARY: GovernanceSummary = {
  technicalDebtOpen: 8,
  baselineDefects: 3,
  adrCount: 8,
  adrCollision: true,
  lessonsLearned: 2,
};

export interface SprintEntregaEntry {
  id: string;
  label: string;
  status: "Concluído" | "Em andamento" | "Pendente";
}

export const SPRINT_1_ENTREGAS: SprintEntregaEntry[] = [
  { id: "Dia 1", label: "Design System", status: "Concluído" },
  { id: "2.1", label: "Executive Cockpit — estrutura e KPIs", status: "Concluído" },
  { id: "2.2", label: "Situação do Portfólio / Programas", status: "Concluído" },
  { id: "2.3", label: "Demandas, Riscos, Issues, Mudanças", status: "Concluído" },
  { id: "Mission Control", label: "Painel do Founder", status: "Concluído" },
  { id: "2.4", label: "Executive Focus, Decision Center, Actions Center, Recent Activity, AI Recommendations", status: "Concluído" },
  {
    id: "2.5",
    label: "Refinamento + Release Notes (não realizado — Sprint 1 encerrada e aprovada em 1.4)",
    status: "Pendente",
  },
];

export interface RecentDecisionEntry {
  id: string;
  summary: string;
}

export const RECENT_DECISIONS: RecentDecisionEntry[] = [
  { id: "D-026", summary: "AR-1 não gerou nenhuma nova decisão arquitetural — arquitetura certificada sem alterações de princípio" },
  { id: "D-025", summary: "Mock morto (PortfolioSituation/ProgramSituation) removido de cockpit-data.ts" },
  { id: "D-024", summary: "Faixa de KPIs do Executive Overview corrigida para dados reais (AR-1)" },
  { id: "D-023", summary: "Regra de consolidação duplicada extraída para consolidateFromChildren() (AR-1)" },
  { id: "D-022", summary: "Founder recomenda uma Architecture Review (AR-1) antes da Capability 04" },
  { id: "D-021", summary: "ADR-V2-009 usa o número 009, não 008, para não colidir com uma reserva pendente" },
  { id: "D-020", summary: "Cadeia de consolidação passa a ser transitiva (Project → Program → Portfolio)" },
];

export interface ProductPulseEntry {
  label: string;
  done: boolean;
}

/** Release 0.2, Capability 03 -- Product Pulse (topo do Mission Control). */
export const PRODUCT_PULSE_TODAY: ProductPulseEntry[] = [
  { label: "Architecture Review AR-1 concluída: APPROVED WITH OBSERVATIONS", done: true },
  { label: "ARCHITECTURE-BASELINE-RC2.md publicado como baseline oficial pós Capabilities 01-03", done: true },
  { label: "Regra de consolidação duplicada eliminada (consolidateFromChildren)", done: true },
  { label: "Faixa de KPIs do Executive Overview corrigida para dados reais", done: true },
  { label: "436 testes de frontend executados com sucesso, build de produção limpo", done: true },
];

export const PRODUCT_DNA_STATEMENT =
  "Transformar documentos, processos, indicadores e conhecimento corporativo em inteligência para tomada de decisão.";

export interface CapabilityProgressEntry {
  code: string;
  name: string;
  progress: number;
  status: "Not Started" | "In Progress" | "Done";
  nextMilestone: string;
}

/**
 * Release 0.2 -- Capability Progress (substitui a numeração "2.N" a
 * partir desta Release, Decision Log D-010). Portfolio é a primeira
 * Capability com entidade real de domínio (lib/domain/portfolio.ts).
 */
export const CAPABILITY_PROGRESS: CapabilityProgressEntry[] = [
  {
    code: "Capability 01",
    name: "Portfolio Management",
    progress: 100,
    status: "Done",
    nextMilestone: "Program Management (aprovada pelo Founder)",
  },
  {
    code: "Capability 02",
    name: "Program Management",
    progress: 100,
    status: "Done",
    nextMilestone: "Project Delivery (aprovada pelo Founder)",
  },
  {
    code: "Capability 03",
    name: "Project Delivery",
    progress: 100,
    status: "Done",
    nextMilestone: "Capability 04 — Demand (após Architecture Review AR-1, concluída)",
  },
];

export interface ArchitectureReviewEntry {
  code: string;
  name: string;
  status: "Approved" | "Approved with Observations" | "Rework Required";
  note: string;
}

/** AR-1 (Release 0.2) -- checkpoint formal entre a Capability 03 e a Capability 04, não uma Capability em si. */
export const ARCHITECTURE_REVIEWS: ArchitectureReviewEntry[] = [
  {
    code: "AR-1",
    name: "Baseline Certification (Capabilities 01-03)",
    status: "Approved with Observations",
    note: "3 correções aplicadas (dedupe de consolidação, KPIs reais, mock morto removido); ver ARCHITECTURE-BASELINE-RC2.md",
  },
];

export interface DomainEvolutionNode {
  name: string;
  status: "Done" | "In Progress" | "Not Started";
  note?: string;
}

/**
 * Diagrama textual da Diretriz Arquitetural Permanente (Release 0.2):
 * Portfolio -> Program -> Project -> Demand -> Risk -> Decision -> Action
 * -> Knowledge. Reflete o estado real do domínio, não uma aspiração.
 */
export const DOMAIN_EVOLUTION: DomainEvolutionNode[] = [
  { name: "Portfolio", status: "Done" },
  { name: "Program", status: "Done" },
  {
    name: "Project",
    status: "In Progress",
    note: "Domínio de frontend vinculado a Program; o Project real do backend (Épico 1) segue não vinculado — unificação é o Épico 4",
  },
  { name: "Demand", status: "Not Started" },
  { name: "Risk", status: "Not Started" },
  { name: "Decision", status: "Not Started" },
  { name: "Action", status: "Not Started" },
  { name: "Knowledge", status: "Not Started" },
];
