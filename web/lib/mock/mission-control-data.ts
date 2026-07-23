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

/**
 * Historical label, reclassified into the Enterprise Master Execution
 * Program's Waves (Decision Log D-030) -- kept here as a record, not
 * deleted, same convention as PROGRAM_PHASES/CAPABILITY_PROGRESS below.
 * Statuses corrected during the Wave 3 Repository Audit (2026-07-23):
 * Épicos 3-5 were stale at "Not Started" despite being done since Wave 2.
 */
export const EPIC_STATUS: EpicStatusEntry[] = [
  { code: "Épico 1", name: "Schema Foundation", status: "Merged", detail: "PR #39, #40" },
  { code: "Épico 2", name: "Identity Foundation", status: "Merged", detail: "PR #41, #42" },
  { code: "Épico 3", name: "Organização e RBAC inicial", status: "Merged", detail: "Wave 2 Sprint 3 (D-034)" },
  { code: "Épico 4", name: "Projeto como entidade real", status: "Merged", detail: "Wave 2 Sprints 1/5 (D-032, D-036); Fase 3a (D-040)" },
  { code: "Épico 5", name: "Auditoria e administração mínima", status: "Merged", detail: "Wave 2 Sprint 4 + User Management (D-035, D-038)" },
  { code: "Épico 6", name: "Validação e documentação", status: "In Progress", detail: "Contínuo -- AR-1/AR-2/RC-2/Repository Audit" },
];

export interface ReleaseStatusEntry {
  version: string;
  name: string;
  status: "Done" | "In Progress" | "Not Started";
  progress: number;
}

/**
 * Historical label, superseded by the Enterprise Master Execution Program's
 * Waves as the single active planning axis (Decision Log D-028/D-030) --
 * kept here as a record, not deleted. Statuses corrected during the Wave 3
 * Repository Audit (2026-07-23): 0.1/0.2 were stale at "In Progress" despite
 * mapping to Wave 1/2, both fully done; 0.3 maps to Wave 3, now in progress.
 */
export const RELEASE_STATUS: ReleaseStatusEntry[] = [
  { version: "0.1", name: "Enterprise Foundation", status: "Done", progress: 100 },
  { version: "0.2", name: "Portfolio & Governance Foundation", status: "Done", progress: 100 },
  { version: "0.3", name: "AI Foundation", status: "In Progress", progress: 10 },
  { version: "0.4", name: "Integration Hub", status: "Not Started", progress: 0 },
  { version: "0.5", name: "Event Orchestration", status: "Not Started", progress: 0 },
];

export interface PullRequestEntry {
  number: number;
  title: string;
  status: "Merged" | "Open";
}

export const PULL_REQUESTS: PullRequestEntry[] = [
  { number: 44, title: "Sprint 1 + Capabilities 01-03 + AR-1 + RC-2 Certification", status: "Merged" },
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
  { id: "D-042", summary: "Repository Audit Wave 3: Go with Conditions — 2 achados críticos de segurança pré-existentes (intelligence.py sem RBAC; AnalysisRecord sem organization_id) registrados como Decision Proposal; Epic W3-3 não avança para Implementação até o Founder decidir" },
  { id: "D-041", summary: "Wave 3, Epic W3-2 avaliado e adiado: AI Platform Foundation não tem consumidor real hoje (nenhum caso de uso de multi-provider, versionamento de prompt ou custo/token) — nenhum código produzido, Wave avança para W3-3" },
  { id: "D-040", summary: "Wave 3, Epic W3-1 concluído: Project Identity Unification (TD-008 Fase 3a) — ProjectSummaryService agrupa por project_id, corrige bug de duplicidade por variação de espaço; Fase 3b (aposentar ProjectSummary) documentada, não implementada" },
  { id: "D-039", summary: "Wave 3 aberta: Architecture Review AR-2 concluída, Epic Ledger definido (W3-1 Project Identity Unification, W3-2 AI Platform Foundation, W3-3 Risk Advisor PoC); Knowledge Platform e demais Enterprise Agents bloqueados por Decision Proposal ao Founder" },
  { id: "D-038", summary: "Wave 2 encerrada: Capability User Management implementada (migração 0009, RBAC, auditoria, Backend→BFF→Frontend) — Épico Enterprise Administration completo para o escopo mínimo aprovado" },
  { id: "D-037", summary: "RC-2: PostgreSQL torna-se o banco oficial (dev + produção); suíte de testes migrada de SQLite para bancos Postgres efêmeros por teste — nenhuma mudança de domínio/arquitetura" },
  { id: "D-036", summary: "Wave 2 Sprint 5: frontend migrado para a API real — arrays semeados deletados, seed movido para o banco (migração 0008), demo user com papel viewer" },
  { id: "D-035", summary: "Wave 2 Sprint 4: Enterprise Administration implementado (Nível 1+2) — auditoria retroativa nas mutações de Portfolio/Program/Project; Sessões não implementado (não existe session store)" },
  { id: "D-034", summary: "Wave 2 Sprint 3: RBAC fine-grained enforcement aplicado às 9 rotas — permissões seedadas via migração 0006, checagem via SqlPermissionChecker" },
  { id: "D-033", summary: "Wave 2 Sprint 2: Enterprise API Layer entregue (Portfolio/Program/Project), autenticação + escopo por organização prontos, RBAC fino na próxima Sprint" },
  { id: "D-032", summary: "Wave 2 Sprint 1: persistência real de Portfolio/Program/Project implementada (Project unificado, sem tabela projects_delivery); TD-007 resolvido" },
  { id: "D-031", summary: "5 Blueprints de fechamento produzidos; Architecture Freeze declarado como parcial (Wave 6 fora, pendente decisão de negócio)" },
  { id: "D-030", summary: "Épicos e Capabilities deixam de ser linhas paralelas de evolução — Waves do Enterprise Master Execution Program passam a ser o único eixo" },
  { id: "D-029", summary: "Phase 2 Foundation Technical Design produzido (5 áreas, 15 elementos cada) — ainda sem código, sem ADR, sem alteração de Baseline" },
  { id: "D-028", summary: "Phase 2 Foundation Architecture produzida como proposta, não como ADR aprovada" },
  { id: "D-027", summary: "CI encontrou uma regressão real de E2E que a suíte local não pegou (e2e/shell.spec.ts)" },
  { id: "D-026", summary: "AR-1 não gerou nenhuma nova decisão arquitetural — arquitetura certificada sem alterações de princípio" },
  { id: "D-025", summary: "Mock morto (PortfolioSituation/ProgramSituation) removido de cockpit-data.ts" },
  { id: "D-024", summary: "Faixa de KPIs do Executive Overview corrigida para dados reais (AR-1)" },
  { id: "D-023", summary: "Regra de consolidação duplicada extraída para consolidateFromChildren() (AR-1)" },
  { id: "D-022", summary: "Founder recomenda uma Architecture Review (AR-1) antes da Capability 04" },
];

export interface ProductPulseEntry {
  label: string;
  done: boolean;
}

/** Release 0.2, Capability 03 -- Product Pulse (topo do Mission Control). */
export const PRODUCT_PULSE_TODAY: ProductPulseEntry[] = [
  { label: "Repository Audit Wave 3: Go with Conditions — 2 achados críticos de segurança pré-existentes registrados como Decision Proposal; Epic W3-3 aguarda decisão do Founder antes da Implementação", done: true },
  { label: "Wave 3, Epic W3-2 avaliado e adiado (sem consumidor real hoje) — Wave avança para o Epic W3-3 (Risk Advisor)", done: true },
  { label: "Wave 3, Epic W3-1 concluído: Project Identity Unification (TD-008 Fase 3a) — bug de agrupamento de portfólio corrigido, project_id aditivo na API/frontend", done: true },
  { label: "Wave 3 aberta: Architecture Review AR-2 concluída, Epic Ledger definido — W3-1/W3-2/W3-3 liberados, Knowledge Platform e demais Enterprise Agents bloqueados aguardando decisão do Founder", done: true },
  { label: "Wave 2 encerrada: Capability User Management implementada (migração 0009, RBAC, auditoria, Backend→BFF→Frontend) — Épico Enterprise Administration completo, Wave 2 declarada 100% concluída", done: true },
  { label: "RC-2 Enterprise Certification concluída e publicada", done: true },
  { label: "PR #44 mergeado em main — baseline oficial pós Capabilities 01-03 + AR-1 + RC-2", done: true },
  { label: "Phase 1 — Enterprise Platform Foundation encerrada", done: true },
  { label: "Phase 2 — Enterprise AI Platform iniciada (Foundation Architecture proposta, sem implementação)", done: true },
  { label: "Phase 2 Foundation Technical Design produzido (API, Persistence, Org Scoping, RBAC, Events) — ainda sem implementação", done: true },
  { label: "Enterprise Master Execution Program publicado — Épicos e Capabilities unificados em Waves, dualidade encerrada", done: true },
  { label: "5 Domain Blueprints de fechamento + Architecture Freeze parcial declarado", done: true },
  { label: "Wave 2 Sprint 1: Portfolio/Program/Project persistidos (migração 0005), Project unificado sem tabela projects_delivery — TD-007 resolvido", done: true },
  { label: "Wave 2 Sprint 2: Enterprise API Layer (9 rotas, OpenAPI/Swagger, org scoping via get_request_context) — RBAC fino na próxima Sprint", done: true },
  { label: "Wave 2 Sprint 3: RBAC fine-grained enforcement aplicado (migração 0006, permission catalog, SqlPermissionChecker) — as 9 rotas exigem permissão real", done: true },
  { label: "Wave 2 Sprint 4: Enterprise Administration (Organizações/Usuários/Papéis/Auditoria/Logs/Segurança) — 8 novos endpoints, auditoria retroativa nas mutações do Domain", done: true },
  { label: "Wave 2 Sprint 5: frontend migrado para a API real — fim do mock de domínio; Portfolio/Program/Project agora fluem banco → API → BFF → página", done: true },
  { label: "Regressão real de E2E encontrada pelo CI e corrigida (e2e/shell.spec.ts)", done: true },
  { label: "RC-2: PostgreSQL oficial, make dev/test reproduzível, suíte completa (245+436+203 testes) validada em Postgres real — pronta para Homologação Oficial da Wave 2", done: true },
];

export const PRODUCT_DNA_STATEMENT =
  "Transformar documentos, processos, indicadores e conhecimento corporativo em inteligência para tomada de decisão.";

export interface WaveEntry {
  code: string;
  name: string;
  status: "Not Started" | "In Progress" | "Done";
  detail: string;
}

/**
 * Enterprise Master Execution Program (docs/product/ENTERPRISE-MASTER-EXECUTION-PROGRAM.md)
 * -- the single active planning axis from this mission forward. Every Épico
 * and every Capability below (PROGRAM_PHASES, CAPABILITY_PROGRESS) is a
 * historical label reclassified into exactly one Wave; neither is a
 * parallel evolution track anymore (Decision Log D-030).
 */
export const ENTERPRISE_PROGRAM_WAVES: WaveEntry[] = [
  {
    code: "Wave 1",
    name: "Enterprise Foundation",
    status: "In Progress",
    detail: "Schema + Identity 100% (Épicos 1-2). Persistence (Sprint 1), API Foundation (Sprint 2) e RBAC seam (Sprint 3, migração 0006 + SqlPermissionChecker) implementados. Event Foundation: Technical Design produzido, ainda não implementado.",
  },
  {
    code: "Wave 2",
    name: "Enterprise Platform",
    status: "Done",
    detail: "100% concluída para os 3 Épicos (Identity, Administration, Domain): Enterprise Domain completo de ponta a ponta (Sprints 1-2-5), RBAC fino (Sprint 3), Administration completo com User Management (Sprint 4 Nível 1+2 + Capability User Management -- D-038). Sessões/Convites/Workspaces/API Keys/Tenant Settings permanecem fora, por decisão explícita do Founder (Decision Proposal §9, não bloqueiam o fechamento). Ver USER-MANAGEMENT-EXECUTIVE-REPORT.md.",
  },
  {
    code: "Wave 3",
    name: "Enterprise Intelligence",
    status: "In Progress",
    detail: "Architecture Review AR-2 concluída (D-039). Epic W3-1 (Project Identity Unification, TD-008 Fase 3a) concluído (D-040). Epic W3-2 (AI Platform Foundation) avaliado e adiado -- sem consumidor real hoje (D-041). Próximo: W3-3 Risk Advisor (liberado condicionalmente, guarda-corpo contra framework de orquestração). Knowledge Platform e os demais 7 Enterprise Agents bloqueados -- Decision Proposal ao Founder (Master Execution Program §15).",
  },
  {
    code: "Wave 4",
    name: "Enterprise Operations",
    status: "Not Started",
    detail: "Corresponde às Releases 0.4/0.5 já aprovadas (Integration Hub, Event Orchestration) -- não implementado.",
  },
  {
    code: "Wave 5",
    name: "Enterprise Analytics",
    status: "Not Started",
    detail: "Executive Cockpit já cobre uma fatia (~15-20%); Operational/AI/Audit Analytics não existem.",
  },
  {
    code: "Wave 6",
    name: "Productization",
    status: "Not Started",
    detail: "Sem nenhuma base aprovada -- requer decisão de modelo de negócio do Founder antes de qualquer planejamento técnico.",
  },
];

export interface ProgramPhaseEntry {
  code: string;
  name: string;
  status: "Not Started" | "In Progress" | "Done";
  detail: string;
}

/**
 * Histórico -- Phase 1/Phase 2 (Executive Directive, RC-2 Enterprise
 * Certification). Substituído por ENTERPRISE_PROGRAM_WAVES como eixo ativo
 * de planejamento a partir do Enterprise Master Execution Program
 * (Decision Log D-030); mantido aqui como registro, não apagado.
 */
export const PROGRAM_PHASES: ProgramPhaseEntry[] = [
  {
    code: "Phase 1",
    name: "Enterprise Platform Foundation",
    status: "Done",
    detail: "Release 0.1 (Épicos 1-2) + Release 0.2 Capabilities 01-03 + AR-1 + RC-2 Certification",
  },
  {
    code: "Phase 2",
    name: "Enterprise AI Platform",
    status: "In Progress",
    detail: "Foundation Architecture aprovada conceitualmente; Technical Design produzido (docs/architecture/PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md) -- nenhuma implementação ainda",
  },
];

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
 *
 * Histórico -- reclassificado como item da Wave 2 (Enterprise Platform) no
 * Enterprise Master Execution Program; mantido aqui como registro, deixa
 * de ser uma linha de evolução paralela aos Épicos (Decision Log D-030).
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
    code: "AR-2",
    name: "Wave 3 Readiness (Enterprise Intelligence)",
    status: "Approved with Observations",
    note: "Baseline aprovado sem correções de código; 2 sub-áreas (Knowledge Platform, Enterprise Agents além do Risk Advisor) bloqueadas por Decision Proposal ao Founder; ver AR-2-WAVE-3-ARCHITECTURE-REVIEW.md",
  },
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
    status: "Done",
    note: "Cadeia completa banco → API → BFF → página (Sprint 5); Fase 3a do TD-008 concluída (Wave 3, D-040) -- Fase 3b (aposentar ProjectSummary em toda a superfície de frontend) permanece futura, sem data",
  },
  { name: "Demand", status: "Not Started" },
  { name: "Risk", status: "Not Started" },
  { name: "Decision", status: "Not Started" },
  { name: "Action", status: "Not Started" },
  { name: "Knowledge", status: "Not Started" },
];
