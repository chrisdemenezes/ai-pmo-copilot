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
  { version: "0.2", name: "Portfolio & Governance Foundation", status: "Not Started", progress: 0 },
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
  technicalDebtOpen: 6,
  baselineDefects: 3,
  adrCount: 7,
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
  { id: "Mission Control", label: "Painel do Founder", status: "Em andamento" },
  { id: "2.4", label: "Decisões, Ações, Timeline, Atividades", status: "Pendente" },
  { id: "2.5", label: "Painel de IA + Refinamento + Release", status: "Pendente" },
];

export interface RecentDecisionEntry {
  id: string;
  summary: string;
}

export const RECENT_DECISIONS: RecentDecisionEntry[] = [
  { id: "D-004", summary: "Situação do Portfólio/Programa como grids novos, não retrofit do grid real de Projetos" },
  { id: "D-003", summary: "Dado mock do Executive Cockpit centralizado em um único arquivo" },
  { id: "D-002", summary: "Novos primitivos de Design System seguem o padrão V1, não um novo" },
  { id: "D-001", summary: "Marca visível renomeada para \"STRATECH\"" },
];
