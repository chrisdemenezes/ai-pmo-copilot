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
  { version: "0.2", name: "Portfolio & Governance Foundation", status: "In Progress", progress: 10 },
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
  { id: "D-013", summary: "Definição de Pronto por Capability: 4 dimensões (Domínio, Experiência, Engenharia, Governança)" },
  { id: "D-012", summary: "Entidade Portfolio (V2) é distinta de \"Portfolio Intelligence\" (V1)" },
  { id: "D-011", summary: "Portfolio real como domínio de frontend, ainda sem persistência em banco" },
  { id: "D-010", summary: "Numeração \"2.N\" substituída por Capabilities de produto" },
  { id: "D-009", summary: "\"Riscos\" do inventário permanece distinto do Risk Intelligence de IA (reforço de D-005)" },
  { id: "D-008", summary: "Executive Focus calculado a partir de dado real, não mock" },
  { id: "D-007", summary: "Mission Control atrás da sessão, mas sem RBAC de Founder ainda" },
];

export interface ProductPulseEntry {
  label: string;
  done: boolean;
}

/** Release 0.2, Capability 01 -- Product Pulse (topo do Mission Control). */
export const PRODUCT_PULSE_TODAY: ProductPulseEntry[] = [
  { label: "Portfolio implementado como entidade real de domínio (Capability 01)", done: true },
  { label: "Executive Cockpit consumindo Portfolio real (Situação do Portfólio)", done: true },
  { label: "Mission Control ganhou a seção Capability Progress", done: true },
  { label: "405 testes de frontend executados com sucesso", done: true },
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
    progress: 55,
    status: "In Progress",
    nextMilestone: "Program Management",
  },
];
