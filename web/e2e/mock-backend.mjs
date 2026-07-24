// Standalone HTTP mock of the FastAPI backend, used only by Playwright E2E
// (T9 / TIP-004). Not part of the product's API surface, does not touch
// src/ -- test infrastructure only, mirrors the real, already-tested
// response shapes (docs/technical/04-api-design.md,
// src/api/routes/intelligence.py).
import http from "node:http";
import { URL } from "node:url";

let scenario = "data";

// Per-endpoint scenario for the Workspace's 3 independent panels (TIP-004
// §1) -- lets an E2E test make one panel slow/error while the others
// succeed, to prove none of them blocks the others. "analyze" added in
// TIP-005 for the Analisar Projeto (project_status) submission flow.
const workspaceScenario = {
  summary: "data",
  analyses: "data",
  detail: "data",
  analyze: "data",
  analyzeRisk: "data",
  analyzeMeeting: "data",
  actionItems: "data",
  latestRisks: "data",
};

// Action Intelligence buckets (atrasado / vence em breve / ...) are computed
// against the real "today" at render time -- fixture due dates must be
// relative to the run date, never hardcoded, or the E2E assertions rot.
function daysFromNow(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

let nextAnalysisId = 1000;

const SAMPLE = [
  {
    project_name: "Multilift",
    total_analyses: 5,
    open_risks: 3,
    pending_action_items: 2,
    latest_health_status: "red",
  },
  {
    project_name: "Aurora",
    total_analyses: 2,
    open_risks: 0,
    pending_action_items: 1,
    latest_health_status: "green",
  },
  // Real hazard already hit once this Release: a "/" in the project name
  // (curl to /api/projects/{name}/summary broke on an unencoded slash).
  // Kept in the default portfolio so the Workspace's encodeURIComponent
  // chain has a real project to exercise end-to-end.
  {
    project_name: "Implantacao SAP S/4HANA",
    total_analyses: 2,
    open_risks: 1,
    pending_action_items: 1,
    latest_health_status: "yellow",
  },
];

// Enterprise Domain fixtures (Wave 2 Sprint 5) -- mirror of the rows
// migration 0008 seeds into the real database (the Capability 01-03 seed
// data), in the real API's snake_case shape (PortfolioResponse/
// ProgramResponse/ProjectDeliveryResponse).
const DOMAIN_PORTFOLIOS = [
  {
    id: 1, organization_id: 1, name: "Portfólio Corporativo", code: "PF-001",
    description: "Iniciativas estratégicas corporativas de maior visibilidade executiva.",
    category: "Corporativo", executive_owner: "Diretoria de Estratégia",
    strategic_objective: "Sustentar o crescimento consolidado do grupo nos próximos 3 anos.",
    status: "Ativo", health: "yellow", priority: "Alta",
    start_date: "2025-02-01", planned_end_date: "2027-02-01", actual_end_date: null,
    progress_percentage: 58, program_count: 4, project_count: 14,
    linked_demands: 6, linked_risks: 9, linked_issues: 4, pending_decisions: 2,
    sponsor: "Diretoria de Estratégia", pmo_owner: "PMO Corporativo",
    last_updated: "2026-07-10", next_review: "2026-08-01",
  },
  {
    id: 2, organization_id: 1, name: "Portfólio de Transformação Digital", code: "PF-002",
    description: "Modernização de plataformas e processos digitais.",
    category: "Transformação Digital", executive_owner: "CIO",
    strategic_objective: "Modernizar a base tecnológica e reduzir débito técnico crítico.",
    status: "Ativo", health: "green", priority: "Alta",
    start_date: "2025-06-01", planned_end_date: "2026-12-01", actual_end_date: null,
    progress_percentage: 74, program_count: 3, project_count: 8,
    linked_demands: 3, linked_risks: 4, linked_issues: 2, pending_decisions: 1,
    sponsor: "CIO", pmo_owner: "PMO de Tecnologia",
    last_updated: "2026-07-12", next_review: "2026-07-25",
  },
  {
    id: 3, organization_id: 1, name: "Portfólio de Expansão Regional", code: "PF-003",
    description: "Entrada em novos mercados regionais.",
    category: "Expansão", executive_owner: "VP de Operações",
    strategic_objective: "Estabelecer presença operacional em 2 novos mercados até o fim da Release 0.2.",
    status: "Ativo", health: "red", priority: "Alta",
    start_date: "2026-01-15", planned_end_date: "2026-11-30", actual_end_date: null,
    progress_percentage: 31, program_count: 1, project_count: 2,
    linked_demands: 2, linked_risks: 5, linked_issues: 1, pending_decisions: 1,
    sponsor: "VP de Operações", pmo_owner: "PMO Regional",
    last_updated: "2026-07-15", next_review: "2026-07-22",
  },
];

const DOMAIN_PROGRAMS = [
  {
    id: 1, portfolio_id: 1, name: "Eficiência Operacional", code: "PG-001",
    description: "Redução de custo operacional e simplificação de processos internos.",
    sponsor: "Diretoria de Estratégia", program_manager: "Bruno Castro",
    status: "Ativo", health: "yellow", priority: "Alta",
    objective: "Reduzir custo operacional em 12% mantendo nível de serviço.",
    start_date: "2025-08-01", planned_end_date: "2026-10-01", actual_end_date: null,
    progress_percentage: 52, project_count: 5,
    linked_demands: 3, linked_risks: 4, linked_issues: 2, pending_decisions: 1, pending_actions: 2,
    pmo_owner: "PMO Corporativo", last_updated: "2026-07-11", next_review: "2026-07-28",
  },
  {
    id: 2, portfolio_id: 1, name: "Governança e Compliance Corporativa", code: "PG-002",
    description: "Padronização de controles de governança entre unidades de negócio.",
    sponsor: "Diretoria de Estratégia", program_manager: "Diego Souza",
    status: "Ativo", health: "yellow", priority: "Média",
    objective: "Unificar o modelo de controles internos até o fim da Release 0.2.",
    start_date: "2026-02-01", planned_end_date: "2026-12-15", actual_end_date: null,
    progress_percentage: 45, project_count: 2,
    linked_demands: 1, linked_risks: 2, linked_issues: 0, pending_decisions: 1, pending_actions: 1,
    pmo_owner: "PMO Corporativo", last_updated: "2026-07-09", next_review: "2026-08-05",
  },
  {
    id: 3, portfolio_id: 2, name: "Modernização de Plataformas", code: "PG-003",
    description: "Modernização das plataformas tecnológicas centrais.",
    sponsor: "CIO", program_manager: "Ana Ribeiro",
    status: "Ativo", health: "green", priority: "Alta",
    objective: "Migrar as 3 plataformas legadas mais críticas para a nova arquitetura.",
    start_date: "2025-07-01", planned_end_date: "2026-09-01", actual_end_date: null,
    progress_percentage: 80, project_count: 3,
    linked_demands: 2, linked_risks: 2, linked_issues: 1, pending_decisions: 0, pending_actions: 1,
    pmo_owner: "PMO de Tecnologia", last_updated: "2026-07-13", next_review: "2026-07-27",
  },
  {
    id: 4, portfolio_id: 3, name: "Entrada em Novos Mercados", code: "PG-004",
    description: "Estruturação operacional para entrada em 2 novos mercados regionais.",
    sponsor: "VP de Operações", program_manager: "Carla Mendes",
    status: "Ativo", health: "red", priority: "Alta",
    objective: "Estabelecer operação local nos 2 mercados-alvo até o fim da Release 0.2.",
    start_date: "2026-02-01", planned_end_date: "2026-11-01", actual_end_date: null,
    progress_percentage: 28, project_count: 2,
    linked_demands: 2, linked_risks: 5, linked_issues: 1, pending_decisions: 1, pending_actions: 1,
    pmo_owner: "PMO Regional", last_updated: "2026-07-14", next_review: "2026-07-21",
  },
];

const DOMAIN_PROJECTS = [
  {
    id: 1, organization_id: 1, program_id: 1, name: "Multilift", code: "PJ-001",
    description: "Modernização da linha de elevadores industriais.",
    objective: "Reduzir tempo de parada não planejada em 30%.",
    sponsor: "Diretoria de Estratégia", project_manager: "Fernanda Lima",
    status: "Ativo", health: "red", priority: "Alta",
    start_date: "2025-09-01", planned_end_date: "2026-06-01", actual_end_date: null,
    progress_percentage: 30, last_updated: "2026-07-15", next_review: "2026-07-20",
    owner: { name: "Bruno Castro", role: "Product Owner" },
    milestones: [
      { name: "Diagnóstico concluído", dueDate: "2025-11-01", status: "Concluído" },
      { name: "Piloto em planta 1", dueDate: "2026-07-01", status: "Atrasado" },
    ],
    team: { size: 8, leadName: "Fernanda Lima" },
  },
  {
    id: 2, organization_id: 1, program_id: 1, name: "Automação de Faturamento", code: "PJ-002",
    description: "Automação do ciclo de faturamento corporativo.",
    objective: "Eliminar retrabalho manual no faturamento mensal.",
    sponsor: "Diretoria de Estratégia", project_manager: "Rafael Nunes",
    status: "Ativo", health: "yellow", priority: "Média",
    start_date: "2026-01-15", planned_end_date: "2026-09-01", actual_end_date: null,
    progress_percentage: 55, last_updated: "2026-07-12", next_review: "2026-07-26",
    owner: { name: "Bruno Castro", role: "Product Owner" },
    milestones: [{ name: "MVP em produção", dueDate: "2026-08-01", status: "Pendente" }],
    team: { size: 5, leadName: "Rafael Nunes" },
  },
  {
    id: 3, organization_id: 1, program_id: 2, name: "Revisão de Controles Internos", code: "PJ-003",
    description: "Padronização de controles internos entre unidades.",
    objective: "Unificar o checklist de controles até o fim da Release 0.2.",
    sponsor: "Diretoria de Estratégia", project_manager: "Diego Souza",
    status: "Ativo", health: "green", priority: "Média",
    start_date: "2026-02-15", planned_end_date: "2026-10-01", actual_end_date: null,
    progress_percentage: 70, last_updated: "2026-07-10", next_review: "2026-08-02",
    owner: { name: "Diego Souza", role: "Product Owner" },
    milestones: [{ name: "Checklist unificado publicado", dueDate: "2026-09-01", status: "Pendente" }],
    team: { size: 4, leadName: "Diego Souza" },
  },
  {
    id: 4, organization_id: 1, program_id: 3, name: "Implantação SAP S/4HANA", code: "PJ-004",
    description: "Migração da plataforma ERP legada para SAP S/4HANA.",
    objective: "Migrar os módulos financeiro e de suprimentos.",
    sponsor: "CIO", project_manager: "Ana Ribeiro",
    status: "Ativo", health: "yellow", priority: "Alta",
    start_date: "2025-08-01", planned_end_date: "2026-08-01", actual_end_date: null,
    progress_percentage: 62, last_updated: "2026-07-13", next_review: "2026-07-27",
    owner: { name: "Ana Ribeiro", role: "Product Owner" },
    milestones: [
      { name: "Go-live financeiro", dueDate: "2026-06-01", status: "Atrasado" },
      { name: "Go-live suprimentos", dueDate: "2026-08-01", status: "Pendente" },
    ],
    team: { size: 10, leadName: "Ana Ribeiro" },
  },
  {
    id: 5, organization_id: 1, program_id: 3, name: "Migração de Data Center", code: "PJ-005",
    description: "Migração da infraestrutura on-premise para a nuvem.",
    objective: "Descomissionar o data center físico até o fim da Release 0.2.",
    sponsor: "CIO", project_manager: "Ana Ribeiro",
    status: "Ativo", health: "green", priority: "Alta",
    start_date: "2025-07-01", planned_end_date: "2026-07-01", actual_end_date: null,
    progress_percentage: 88, last_updated: "2026-07-14", next_review: "2026-07-24",
    owner: { name: "Ana Ribeiro", role: "Product Owner" },
    milestones: [{ name: "Corte final de tráfego", dueDate: "2026-07-15", status: "Pendente" }],
    team: { size: 6, leadName: "Ana Ribeiro" },
  },
  {
    id: 6, organization_id: 1, program_id: 4, name: "Aurora", code: "PJ-006",
    description: "Estruturação da operação comercial no novo mercado.",
    objective: "Abrir a primeira unidade comercial no mercado-alvo.",
    sponsor: "VP de Operações", project_manager: "Carla Mendes",
    status: "Ativo", health: "green", priority: "Alta",
    start_date: "2026-02-01", planned_end_date: "2026-10-01", actual_end_date: null,
    progress_percentage: 74, last_updated: "2026-07-11", next_review: "2026-07-25",
    owner: { name: "Carla Mendes", role: "Product Owner" },
    milestones: [{ name: "Unidade inaugurada", dueDate: "2026-09-01", status: "Pendente" }],
    team: { size: 7, leadName: "Carla Mendes" },
  },
  {
    id: 7, organization_id: 1, program_id: 4, name: "Abertura Operação LATAM", code: "PJ-007",
    description: "Estruturação regulatória e operacional para entrada na LATAM.",
    objective: "Obter licenças operacionais nos 2 países-alvo.",
    sponsor: "VP de Operações", project_manager: "Carla Mendes",
    status: "Ativo", health: "red", priority: "Alta",
    start_date: "2026-03-01", planned_end_date: "2026-11-01", actual_end_date: null,
    progress_percentage: 22, last_updated: "2026-07-14", next_review: "2026-07-21",
    owner: { name: "Carla Mendes", role: "Product Owner" },
    milestones: [{ name: "Licenças protocoladas", dueDate: "2026-06-01", status: "Atrasado" }],
    team: { size: 4, leadName: "Carla Mendes" },
  },
];

// The E2E login (POST /api/auth/login below) always resolves to user_id 1
// -- used to exercise the self-deactivation guard for User Management.
const E2E_ACTOR_USER_ID = 1;

// User Management (Enterprise Administration Capability) fixtures --
// mutable (create/edit/status/roles all write here), reset via
// resetFixtures() like SAMPLE/ANALYSES.
const PRISTINE_ADMIN_USERS = [
  { id: 1, email: "ana.admin@example.com", display_name: "Ana Souza", identity_type: "standard", is_active: true },
  { id: 2, email: "bruno.pmo@example.com", display_name: "Bruno Castro", identity_type: "standard", is_active: true },
  { id: 3, email: "carla.viewer@example.com", display_name: "Carla Mendes", identity_type: "standard", is_active: false },
];
const PRISTINE_ADMIN_USER_ROLES = {
  1: ["organization_admin"],
  2: ["pmo"],
  3: ["viewer"],
};
const ADMIN_ROLES = [
  { id: 1, name: "organization_admin", description: "Administra a organização" },
  { id: 2, name: "pmo", description: "Visão e governança" },
  { id: 3, name: "project_manager", description: "Execução de Program/Project" },
  { id: 4, name: "viewer", description: "Somente leitura" },
];

const ADMIN_USERS = [];
const ADMIN_USER_ROLES = {};
let nextAdminUserId = 1000;

// D-051 -- API Keys (Enterprise Administration): a foundational
// credential, not an Integration Hub artifact.
const ADMIN_API_KEYS = [];
let nextAdminApiKeyId = 1;

function omitHashedSecret(apiKey) {
  const copy = { ...apiKey };
  delete copy.hashed_secret;
  return copy;
}

// Item 5 -- server-side sessions (resolves TD-010). Login mints one, logout
// and the admin DELETE revoke it, GET lists the active (non-revoked) ones.
const ADMIN_SESSIONS = [];
let nextAdminSessionSeq = 1;

// Item 6 -- Convites (D-054). A foundational onboarding credential; the
// invite token is returned once at creation. State is derived from the
// timestamps (accepted_at/cancelled_at/expires_at), same as the backend.
const ADMIN_INVITATIONS = [];
let nextAdminInvitationId = 1;

function omitHashedToken(invitation) {
  const copy = { ...invitation };
  delete copy.hashed_token;
  delete copy.plaintext_token;
  return copy;
}

function invitationStatus(invitation) {
  if (invitation.cancelled_at !== null) return "cancelled";
  if (invitation.accepted_at !== null) return "accepted";
  if (new Date(invitation.expires_at).getTime() <= Date.now()) return "expired";
  return "pending";
}

function invitationResponse(invitation) {
  const base = omitHashedToken(invitation);
  return { ...base, status: invitationStatus(invitation) };
}

function resetAdminFixtures() {
  ADMIN_USERS.length = 0;
  ADMIN_USERS.push(...JSON.parse(JSON.stringify(PRISTINE_ADMIN_USERS)));
  for (const key of Object.keys(ADMIN_USER_ROLES)) delete ADMIN_USER_ROLES[key];
  Object.assign(ADMIN_USER_ROLES, JSON.parse(JSON.stringify(PRISTINE_ADMIN_USER_ROLES)));
  nextAdminUserId = 1000;
  ADMIN_API_KEYS.length = 0;
  nextAdminApiKeyId = 1;
  ADMIN_SESSIONS.length = 0;
  nextAdminSessionSeq = 1;
  ADMIN_INVITATIONS.length = 0;
  nextAdminInvitationId = 1;
}
resetAdminFixtures();

const WORKSPACE_SUMMARY = {
  Aurora: {
    project_name: "Aurora",
    total_analyses: 2,
    open_risks: 0,
    pending_action_items: 1,
    latest_health_status: "green",
  },
  "Implantacao SAP S/4HANA": {
    project_name: "Implantacao SAP S/4HANA",
    total_analyses: 2,
    open_risks: 1,
    pending_action_items: 1,
    latest_health_status: "yellow",
  },
};

const ANALYSES = [
  {
    id: 201,
    kind: "risk",
    project_name: "Aurora",
    created_at: "2026-07-10T14:00:00Z",
    payload: {
      agent: "risk_review",
      project_name: "Aurora",
      model_output: {
        structured: true,
        risks: [
          { description: "Atraso na entrega", probability: "medium", impact: "high", mitigation: "Replanejar sprint" },
        ],
        escalation_recommendation: null,
      },
    },
  },
  {
    id: 202,
    kind: "meeting",
    project_name: "Aurora",
    created_at: "2026-07-09T10:00:00Z",
    payload: {
      agent: "meeting_intelligence",
      project_name: "Aurora",
      model_output: {
        structured: true,
        summary: "Reunião semanal de acompanhamento.",
        decisions: ["Adiar o go-live em 1 semana"],
        action_items: [{ description: "Atualizar cronograma", owner: "Ana", due_date: daysFromNow(2) }],
        issues: [],
        dependencies: ["Aprovação do cliente"],
      },
    },
  },
  {
    id: 203,
    kind: "status",
    project_name: "Aurora",
    created_at: "2026-07-08T09:00:00Z",
    payload: {
      agent: "project_status",
      project_name: "Aurora",
      model_output: {
        structured: true,
        health_status: "green",
        key_findings: ["Projeto dentro do prazo"],
        recommendations: ["Manter cadência atual"],
      },
    },
  },
  // Older Aurora meeting (TIP-008): keeps id 202 as the latest meeting the
  // Comunicação brief reads, while giving GET /api/action-items an overdue
  // item and a no-deadline item to bucket.
  {
    id: 204,
    kind: "meeting",
    project_name: "Aurora",
    created_at: "2026-07-05T10:00:00Z",
    payload: {
      agent: "meeting_intelligence",
      project_name: "Aurora",
      model_output: {
        structured: true,
        summary: "Reunião de alinhamento com o fornecedor.",
        decisions: [],
        action_items: [
          { description: "Cobrar plano de contingência do fornecedor", owner: "Bruno", due_date: daysFromNow(-3) },
          { description: "Documentar acordos da reunião", owner: null, due_date: null },
        ],
        issues: [],
        dependencies: [],
      },
    },
  },
  // Meeting for a second project (TIP-008 Incremento 2): proves the
  // portfolio "Ações" page aggregates across projects, and gives the
  // encodeURIComponent chain a project name with "/" to exercise.
  {
    id: 302,
    kind: "meeting",
    project_name: "Implantacao SAP S/4HANA",
    created_at: "2026-07-06T09:00:00Z",
    payload: {
      agent: "meeting_intelligence",
      project_name: "Implantacao SAP S/4HANA",
      model_output: {
        structured: true,
        summary: "Reunião de preparação do cutover.",
        decisions: [],
        action_items: [
          { description: "Validar plano de cutover com o cliente", owner: "Carla", due_date: daysFromNow(1) },
        ],
        issues: [],
        dependencies: [],
      },
    },
  },
  {
    id: 301,
    kind: "status",
    project_name: "Implantacao SAP S/4HANA",
    created_at: "2026-07-11T08:00:00Z",
    payload: {
      agent: "project_status",
      project_name: "Implantacao SAP S/4HANA",
      model_output: {
        structured: true,
        health_status: "yellow",
        key_findings: ["Atenção ao cronograma de testes"],
        recommendations: ["Revisar plano de testes"],
      },
    },
  },
  // Executive Memory (TIP-011, Incremento 1) -- older status analysis for
  // the same project, same attention-zone status as id 301: gives the
  // Executive Brief 2 consecutive "yellow" analyses to compute a real
  // "Persistiu" Memory Signal from, without touching WORKSPACE_SUMMARY/SAMPLE
  // (both stay "yellow" -- no other spec's assertions depend on this list).
  {
    id: 300,
    kind: "status",
    project_name: "Implantacao SAP S/4HANA",
    created_at: "2026-07-04T08:00:00Z",
    payload: {
      agent: "project_status",
      project_name: "Implantacao SAP S/4HANA",
      model_output: {
        structured: true,
        health_status: "yellow",
        key_findings: ["Cronograma de testes ainda apertado"],
        recommendations: ["Acompanhar de perto"],
      },
    },
  },
  // Executive Memory (TIP-011, Incremento 2) -- análise de risco mais antiga
  // para Aurora, mesma descrição de atenção da já existente id 201: gera um
  // "Reapareceu" real sem mexer no que /api/risks/latest devolve para Aurora
  // (continua sendo a mais recente, id 201 -- Decision Center/Portfolio
  // Intelligence continuam vendo exatamente o mesmo risco de atenção de
  // sempre, mesmo texto/probabilidade/impacto). Data anterior a 201
  // (2026-07-10) para nunca virar a "mais recente" em nenhuma leitura.
  {
    id: 205,
    kind: "risk",
    project_name: "Aurora",
    created_at: "2026-07-03T09:00:00Z",
    payload: {
      agent: "risk_review",
      project_name: "Aurora",
      model_output: {
        structured: true,
        risks: [
          { description: "Atraso na entrega", probability: "medium", impact: "high", mitigation: "Replanejar sprint" },
        ],
        escalation_recommendation: null,
      },
    },
  },
];

// TIP-005's /api/projects/analyze mutates SAMPLE/WORKSPACE_SUMMARY/ANALYSES
// in place, and this webServer process is shared across every spec file and
// every breakpoint project in a single Playwright invocation -- without a
// reset, a mutation from one test leaks into every test that runs after it,
// anywhere in the run. Snapshotted once, before anything can mutate them.
const PRISTINE_SAMPLE = JSON.parse(JSON.stringify(SAMPLE));
const PRISTINE_WORKSPACE_SUMMARY = JSON.parse(JSON.stringify(WORKSPACE_SUMMARY));
const PRISTINE_ANALYSES = JSON.parse(JSON.stringify(ANALYSES));
const PRISTINE_NEXT_ANALYSIS_ID = nextAnalysisId;
// Same cross-file leak risk as SAMPLE/WORKSPACE_SUMMARY/ANALYSES above: a
// test that sets a workspaceScenario key to "unavailable"/"timeout" (e.g.
// actions.spec.ts's error-boundary test) previously left it that way for
// every test that ran after it in the same Playwright invocation, in any
// spec file -- real hazard hit by dashboard.spec.ts's new KPI-link test
// (TIP-008 Incremento 3) failing only when run after actions.spec.ts.
const PRISTINE_WORKSPACE_SCENARIO = JSON.parse(JSON.stringify(workspaceScenario));

function resetFixtures() {
  SAMPLE.length = 0;
  SAMPLE.push(...JSON.parse(JSON.stringify(PRISTINE_SAMPLE)));

  for (const key of Object.keys(WORKSPACE_SUMMARY)) delete WORKSPACE_SUMMARY[key];
  Object.assign(WORKSPACE_SUMMARY, JSON.parse(JSON.stringify(PRISTINE_WORKSPACE_SUMMARY)));

  ANALYSES.length = 0;
  ANALYSES.push(...JSON.parse(JSON.stringify(PRISTINE_ANALYSES)));

  nextAnalysisId = PRISTINE_NEXT_ANALYSIS_ID;

  Object.assign(workspaceScenario, JSON.parse(JSON.stringify(PRISTINE_WORKSPACE_SCENARIO)));

  resetAdminFixtures();
}

function send(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

function applyScenario(res, key) {
  const current = workspaceScenario[key];
  if (current === "timeout") {
    return true; // never respond
  }
  if (current === "unavailable") {
    send(res, 500, { detail: "internal error" });
    return true;
  }
  return false;
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://localhost");

  if (req.method === "POST" && url.pathname === "/__control/scenario") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      scenario = JSON.parse(body).scenario;
      res.writeHead(204).end();
    });
    return;
  }

  if (req.method === "POST" && url.pathname === "/__control/reset-fixtures") {
    resetFixtures();
    res.writeHead(204).end();
    return;
  }

  if (req.method === "POST" && url.pathname === "/__control/workspace-scenario") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      const { endpoint, scenario: value } = JSON.parse(body);
      workspaceScenario[endpoint] = value;
      res.writeHead(204).end();
    });
    return;
  }

  // Identity Foundation (STRATECH V2 Epic 2 / EO-015) -- mirrors the real
  // backend's contract (src/api/routes/auth.py): {organization, email,
  // password} -> 200 {user_id, organization_id} or a uniform 401, never
  // distinguishing "unknown organization" from "unknown e-mail" from "wrong
  // password". E2E's fixed test account below is the only one login
  // recognizes; nothing else is a special case.
  const E2E_USER = {
    organization: "e2e-organization",
    email: "e2e@stratech.local",
    password: "e2e-workspace-password",
  };

  if (req.method === "POST" && url.pathname === "/api/auth/login") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      const { organization, email, password } = JSON.parse(body);
      if (
        organization === E2E_USER.organization &&
        email === E2E_USER.email &&
        password === E2E_USER.password
      ) {
        const sessionId = `e2e-session-${nextAdminSessionSeq++}`;
        ADMIN_SESSIONS.push({
          id: sessionId,
          user_id: 1,
          organization_id: 1,
          created_at: new Date().toISOString(),
          last_seen_at: null,
          revoked_at: null,
        });
        return send(res, 200, { user_id: 1, organization_id: 1, session_id: sessionId });
      }
      return send(res, 401, { detail: "Invalid organization, email or password" });
    });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/auth/logout") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      const { session_id: sessionId } = JSON.parse(body);
      const session = ADMIN_SESSIONS.find((s) => s.id === sessionId);
      if (session && session.revoked_at === null) {
        session.revoked_at = new Date().toISOString();
      }
      return send(res, 200, { acknowledged: true });
    });
    return;
  }

  if (url.pathname === "/api/portfolio/summary") {
    if (scenario === "timeout") return;
    if (scenario === "unavailable") return send(res, 500, { detail: "internal error" });
    return send(res, 200, scenario === "empty" ? [] : SAMPLE);
  }

  // Enterprise Domain API (Wave 2 Sprint 5) -- same rows migration 0008
  // seeds into the real database, in the real API's snake_case wire shape,
  // so the frontend's list*() fetch path is exercised end to end.
  if (url.pathname === "/api/portfolios") {
    return send(res, 200, DOMAIN_PORTFOLIOS);
  }
  if (url.pathname === "/api/programs") {
    return send(res, 200, DOMAIN_PROGRAMS);
  }
  if (url.pathname === "/api/projects-delivery") {
    return send(res, 200, DOMAIN_PROJECTS);
  }

  // User Management (Enterprise Administration Capability) -- mirrors
  // src/api/routes/administration.py's User Management routes.
  if (url.pathname === "/api/admin/user-roles-index") {
    const index = {};
    for (const [userId, roleNames] of Object.entries(ADMIN_USER_ROLES)) {
      index[userId] = roleNames;
    }
    return send(res, 200, index);
  }

  if (url.pathname === "/api/admin/roles") {
    return send(res, 200, ADMIN_ROLES);
  }

  if (req.method === "GET" && url.pathname === "/api/admin/users") {
    return send(res, 200, ADMIN_USERS);
  }

  if (req.method === "POST" && url.pathname === "/api/admin/users") {
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      const { email, display_name: displayName, role_name: roleName } = JSON.parse(raw);
      const normalizedEmail = email.trim().toLowerCase();
      if (ADMIN_USERS.some((u) => u.email === normalizedEmail)) {
        return send(res, 409, { detail: `Email '${email}' already exists in this organization` });
      }
      if (!ADMIN_ROLES.some((r) => r.name === roleName)) {
        return send(res, 400, { detail: `Role '${roleName}' does not exist` });
      }
      const user = {
        id: nextAdminUserId++,
        email: normalizedEmail,
        display_name: displayName,
        identity_type: "standard",
        is_active: true,
      };
      ADMIN_USERS.push(user);
      ADMIN_USER_ROLES[user.id] = [roleName];
      return send(res, 201, user);
    });
    return;
  }

  const userRolesMatch = url.pathname.match(/^\/api\/admin\/users\/(\d+)\/roles$/);
  if (userRolesMatch) {
    const userId = Number(userRolesMatch[1]);
    const user = ADMIN_USERS.find((u) => u.id === userId);
    if (!user) return send(res, 404, { detail: "User not found" });

    if (req.method === "GET") {
      const names = ADMIN_USER_ROLES[userId] ?? [];
      return send(res, 200, ADMIN_ROLES.filter((r) => names.includes(r.name)));
    }
    if (req.method === "POST") {
      let raw = "";
      req.on("data", (chunk) => (raw += chunk));
      req.on("end", () => {
        const { role_name: roleName } = JSON.parse(raw);
        if (!ADMIN_ROLES.some((r) => r.name === roleName)) {
          return send(res, 400, { detail: `Role '${roleName}' does not exist` });
        }
        const names = ADMIN_USER_ROLES[userId] ?? (ADMIN_USER_ROLES[userId] = []);
        if (!names.includes(roleName)) names.push(roleName);
        return send(res, 200, user);
      });
      return;
    }
  }

  const removeRoleMatch = url.pathname.match(/^\/api\/admin\/users\/(\d+)\/roles\/([^/]+)$/);
  if (removeRoleMatch && req.method === "DELETE") {
    const userId = Number(removeRoleMatch[1]);
    const roleName = decodeURIComponent(removeRoleMatch[2]);
    const user = ADMIN_USERS.find((u) => u.id === userId);
    if (!user) return send(res, 404, { detail: "User not found" });
    if (!ADMIN_ROLES.some((r) => r.name === roleName)) {
      return send(res, 400, { detail: `Role '${roleName}' does not exist` });
    }
    const names = ADMIN_USER_ROLES[userId] ?? [];
    const activeAdminCount = ADMIN_USERS.filter(
      (u) => u.is_active && (ADMIN_USER_ROLES[u.id] ?? []).includes("organization_admin"),
    ).length;
    if (roleName === "organization_admin" && user.is_active && activeAdminCount <= 1) {
      return send(res, 409, { detail: "Cannot remove the last active administrator's role" });
    }
    ADMIN_USER_ROLES[userId] = names.filter((name) => name !== roleName);
    return send(res, 200, user);
  }

  const userStatusMatch = url.pathname.match(/^\/api\/admin\/users\/(\d+)\/status$/);
  if (userStatusMatch && req.method === "PATCH") {
    const userId = Number(userStatusMatch[1]);
    const user = ADMIN_USERS.find((u) => u.id === userId);
    if (!user) return send(res, 404, { detail: "User not found" });
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      const { is_active: isActive } = JSON.parse(raw);
      if (!isActive && userId === E2E_ACTOR_USER_ID) {
        return send(res, 400, { detail: "An administrator cannot deactivate their own account" });
      }
      if (!isActive && user.is_active) {
        const names = ADMIN_USER_ROLES[userId] ?? [];
        const activeAdminCount = ADMIN_USERS.filter(
          (u) => u.is_active && (ADMIN_USER_ROLES[u.id] ?? []).includes("organization_admin"),
        ).length;
        if (names.includes("organization_admin") && activeAdminCount <= 1) {
          return send(res, 409, {
            detail: "Cannot deactivate the last active administrator of this organization",
          });
        }
      }
      user.is_active = isActive;
      return send(res, 200, user);
    });
    return;
  }

  const userMatch = url.pathname.match(/^\/api\/admin\/users\/(\d+)$/);
  if (userMatch) {
    const userId = Number(userMatch[1]);
    const user = ADMIN_USERS.find((u) => u.id === userId);
    if (!user) return send(res, 404, { detail: "User not found" });

    if (req.method === "GET") {
      return send(res, 200, user);
    }
    if (req.method === "PATCH") {
      let raw = "";
      req.on("data", (chunk) => (raw += chunk));
      req.on("end", () => {
        const { email, display_name: displayName } = JSON.parse(raw);
        if (email !== undefined) {
          const normalizedEmail = email.trim().toLowerCase();
          if (ADMIN_USERS.some((u) => u.id !== userId && u.email === normalizedEmail)) {
            return send(res, 409, {
              detail: `Email '${email}' already exists in this organization`,
            });
          }
          user.email = normalizedEmail;
        }
        if (displayName !== undefined) user.display_name = displayName;
        return send(res, 200, user);
      });
      return;
    }
  }

  if (req.method === "GET" && url.pathname === "/api/admin/api-keys") {
    return send(res, 200, ADMIN_API_KEYS.map(omitHashedSecret));
  }

  if (req.method === "POST" && url.pathname === "/api/admin/api-keys") {
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      const { name } = JSON.parse(raw);
      const id = nextAdminApiKeyId++;
      const plaintextKey = `sk_live_e2e-mock-key-${id}`;
      const apiKey = {
        id,
        name,
        key_prefix: plaintextKey.slice(0, 16),
        hashed_secret: "mock-hash",
        created_at: new Date().toISOString(),
        last_used_at: null,
        revoked_at: null,
      };
      ADMIN_API_KEYS.push(apiKey);
      return send(res, 201, { ...omitHashedSecret(apiKey), plaintext_key: plaintextKey });
    });
    return;
  }

  const apiKeyMatch = url.pathname.match(/^\/api\/admin\/api-keys\/(\d+)$/);
  if (apiKeyMatch && req.method === "DELETE") {
    const apiKeyId = Number(apiKeyMatch[1]);
    const apiKey = ADMIN_API_KEYS.find((k) => k.id === apiKeyId);
    if (!apiKey) return send(res, 404, { detail: "API key not found" });
    apiKey.revoked_at = new Date().toISOString();
    // 200 with the revoked resource, not a bare 204 -- the real backend's
    // route returns the same shape (forwardDomainRequest always parses a
    // JSON body, which a body-less 204 can't satisfy).
    return send(res, 200, omitHashedSecret(apiKey));
  }

  // Sessions (item 5, resolves TD-010).
  if (req.method === "GET" && url.pathname === "/api/admin/sessions") {
    return send(res, 200, ADMIN_SESSIONS.filter((s) => s.revoked_at === null));
  }

  const sessionMatch = url.pathname.match(/^\/api\/admin\/sessions\/([^/]+)$/);
  if (sessionMatch && req.method === "DELETE") {
    const sessionId = decodeURIComponent(sessionMatch[1]);
    const session = ADMIN_SESSIONS.find((s) => s.id === sessionId);
    if (!session || session.revoked_at !== null) {
      return send(res, 404, { detail: "Session not found" });
    }
    session.revoked_at = new Date().toISOString();
    // 200 with the revoked resource, not a bare 204 (same reason as api-keys).
    return send(res, 200, session);
  }

  // Invitations (item 6, Convites -- D-054).
  if (req.method === "GET" && url.pathname === "/api/admin/invitations") {
    return send(res, 200, ADMIN_INVITATIONS.map(invitationResponse));
  }

  if (req.method === "POST" && url.pathname === "/api/admin/invitations") {
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      const { email, role_name } = JSON.parse(raw);
      if (!ADMIN_ROLES.some((r) => r.name === role_name)) {
        return send(res, 400, { detail: `Role '${role_name}' does not exist` });
      }
      const id = nextAdminInvitationId++;
      const plaintextToken = `inv_e2e-mock-token-${id}`;
      const now = Date.now();
      const invitation = {
        id,
        email,
        role_name,
        token_prefix: plaintextToken.slice(0, 12),
        hashed_token: "mock-hash",
        created_at: new Date(now).toISOString(),
        expires_at: new Date(now + 7 * 24 * 60 * 60 * 1000).toISOString(),
        accepted_at: null,
        cancelled_at: null,
      };
      ADMIN_INVITATIONS.push(invitation);
      return send(res, 201, {
        ...invitationResponse(invitation),
        plaintext_token: plaintextToken,
      });
    });
    return;
  }

  const invitationMatch = url.pathname.match(/^\/api\/admin\/invitations\/(\d+)$/);
  if (invitationMatch && req.method === "DELETE") {
    const invitationId = Number(invitationMatch[1]);
    const invitation = ADMIN_INVITATIONS.find((i) => i.id === invitationId);
    if (!invitation || invitationStatus(invitation) !== "pending") {
      return send(res, 404, { detail: "Invitation not found or not pending" });
    }
    invitation.cancelled_at = new Date().toISOString();
    // 200 with the cancelled resource, not a bare 204 (same reason as api-keys).
    return send(res, 200, invitationResponse(invitation));
  }

  // Public invitation flow (no session -- the token is the authorization).
  const invitationPreviewMatch = url.pathname.match(/^\/api\/invitations\/([^/]+)$/);
  if (invitationPreviewMatch && req.method === "GET") {
    const token = decodeURIComponent(invitationPreviewMatch[1]);
    const invitation = ADMIN_INVITATIONS.find(
      (i) => `inv_e2e-mock-token-${i.id}` === token,
    );
    if (!invitation) return send(res, 404, { detail: "Invalid invitation" });
    return send(res, 200, {
      organization_name: "e2e-organization",
      role_name: invitation.role_name,
      status: invitationStatus(invitation),
      email: invitation.email,
    });
  }

  if (req.method === "POST" && url.pathname === "/api/invitations/accept") {
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      const { token } = JSON.parse(raw);
      const invitation = ADMIN_INVITATIONS.find(
        (i) => `inv_e2e-mock-token-${i.id}` === token,
      );
      if (!invitation || invitationStatus(invitation) !== "pending") {
        return send(res, 404, { detail: "Invalid, expired, or already-used invitation" });
      }
      invitation.accepted_at = new Date().toISOString();
      return send(res, 200, { user_id: 9000 + invitation.id, organization_id: 1 });
    });
    return;
  }

  // project_name is a query param here, not a path segment -- matches the
  // real backend's route shape after the TIP-004 follow-up migration
  // (GET /api/projects/{name}/summary could never actually serve a "/" in
  // the name, regardless of client-side encoding; query params can).
  if (url.pathname === "/api/projects/summary") {
    if (applyScenario(res, "summary")) return;
    const projectName = url.searchParams.get("project_name");
    const found = projectName ? WORKSPACE_SUMMARY[projectName] : undefined;
    if (!found) return send(res, 404, { detail: "not found" });
    return send(res, 200, found);
  }

  if (url.pathname === "/api/analyses") {
    if (applyScenario(res, "analyses")) return;
    const projectName = url.searchParams.get("project_name");
    const kind = url.searchParams.get("kind");
    const limit = Number(url.searchParams.get("limit") ?? "20");
    const offset = Number(url.searchParams.get("offset") ?? "0");

    let items = ANALYSES.filter((a) => !projectName || a.project_name === projectName);
    if (kind) items = items.filter((a) => a.kind === kind);
    items = items
      .slice()
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    const page = items.slice(offset, offset + limit).map(({ id, kind: k, project_name, created_at }) => ({
      id,
      kind: k,
      project_name,
      created_at,
    }));
    return send(res, 200, page);
  }

  // TIP-008 -- Action Intelligence. Mirrors GET /api/action-items
  // (src/api/routes/intelligence.py): derived from the same meeting
  // analyses, flattened newest-first, malformed items excluded -- never a
  // separate store the real backend doesn't have.
  if (url.pathname === "/api/action-items") {
    if (applyScenario(res, "actionItems")) return;
    const projectName = url.searchParams.get("project_name");
    const meetings = ANALYSES.filter(
      (a) => a.kind === "meeting" && (!projectName || a.project_name === projectName),
    )
      .slice()
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    const items = [];
    for (const record of meetings) {
      const modelOutput = record.payload?.model_output;
      if (!modelOutput || modelOutput.structured !== true) continue;
      for (const item of modelOutput.action_items ?? []) {
        if (typeof item?.description !== "string") continue;
        items.push({
          project_name: record.project_name,
          description: item.description,
          owner: typeof item.owner === "string" ? item.owner : null,
          due_date: typeof item.due_date === "string" ? item.due_date : null,
          source_analysis_id: record.id,
          source_created_at: record.created_at,
        });
      }
    }
    return send(res, 200, items);
  }

  // TIP-009 -- Decision Center. Mirrors GET /api/risks/latest
  // (src/api/routes/intelligence.py): only the most recent risk analysis
  // per project counts, same principle as latest_health_status.
  if (url.pathname === "/api/risks/latest") {
    if (applyScenario(res, "latestRisks")) return;
    const projectName = url.searchParams.get("project_name");
    const risksAnalyses = ANALYSES.filter(
      (a) => a.kind === "risk" && (!projectName || a.project_name === projectName),
    )
      .slice()
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    const seenProjects = new Set();
    const items = [];
    for (const record of risksAnalyses) {
      if (seenProjects.has(record.project_name)) continue;
      const modelOutput = record.payload?.model_output;
      if (!modelOutput || modelOutput.structured !== true) continue;
      seenProjects.add(record.project_name);
      const escalationRecommendation =
        typeof modelOutput.escalation_recommendation === "string"
          ? modelOutput.escalation_recommendation
          : null;
      for (const risk of modelOutput.risks ?? []) {
        if (typeof risk?.description !== "string") continue;
        items.push({
          project_name: record.project_name,
          description: risk.description,
          probability: risk.probability ?? null,
          impact: risk.impact ?? null,
          mitigation: risk.mitigation ?? null,
          escalation_recommendation: escalationRecommendation,
          source_analysis_id: record.id,
          source_created_at: record.created_at,
        });
      }
    }
    return send(res, 200, items);
  }

  const detailMatch = url.pathname.match(/^\/api\/analyses\/(\d+)$/);
  if (detailMatch) {
    if (applyScenario(res, "detail")) return;
    const found = ANALYSES.find((a) => a.id === Number(detailMatch[1]));
    if (!found) return send(res, 404, { detail: "Analysis not found" });
    return send(res, 200, found);
  }

  // TIP-005 -- Analisar Projeto (project_status). Mirrors
  // src/api/routes/intelligence.py:119 (POST /api/projects/analyze): the
  // response is the raw agent.analyze() shape, not the AnalysisDetail
  // wrapper, and a successful call both persists a new analysis and moves
  // the project's latest_health_status -- visible afterwards in the
  // Workspace panels *and* the Dashboard/portfolio list.
  if (req.method === "POST" && url.pathname === "/api/projects/analyze") {
    if (workspaceScenario.analyze === "timeout") return; // never respond
    if (workspaceScenario.analyze === "rate_limited") {
      return send(res, 429, { detail: "Rate limit exceeded" });
    }
    if (workspaceScenario.analyze === "unavailable") {
      return send(res, 500, { detail: "internal error" });
    }

    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      const { project_context: projectContext, project_name: projectName } = JSON.parse(raw);
      if (!projectContext || projectContext.trim().length < 10) {
        return send(res, 422, { detail: "project_context inválido" });
      }

      const id = nextAnalysisId++;
      const createdAt = new Date().toISOString();
      const modelOutput = {
        structured: true,
        health_status: "green",
        key_findings: ["Cronograma recuperado após a última análise"],
        recommendations: ["Manter o novo ritmo de acompanhamento"],
      };

      ANALYSES.push({
        id,
        kind: "status",
        project_name: projectName,
        created_at: createdAt,
        payload: { agent: "project_status", project_name: projectName, model_output: modelOutput },
      });

      const summary = WORKSPACE_SUMMARY[projectName];
      if (summary) {
        summary.total_analyses += 1;
        summary.latest_health_status = modelOutput.health_status;
      }
      const portfolioEntry = SAMPLE.find((p) => p.project_name === projectName);
      if (portfolioEntry) {
        portfolioEntry.total_analyses += 1;
        portfolioEntry.latest_health_status = modelOutput.health_status;
      }

      return send(res, 200, {
        agent: "project_status",
        project_name: projectName,
        model_output: modelOutput,
      });
    });
    return;
  }

  // TIP-006 -- Avaliação de Riscos (risk_review), same pattern as
  // /api/projects/analyze above. open_risks is cumulative across every risk
  // analysis ever run for the project (src/services/project_summary_service.py
  // sums risks[] length over all "risk" records, not just the latest), so
  // the mock increments rather than replaces it.
  if (req.method === "POST" && url.pathname === "/api/risks/analyze") {
    if (workspaceScenario.analyzeRisk === "timeout") return; // never respond
    if (workspaceScenario.analyzeRisk === "rate_limited") {
      return send(res, 429, { detail: "Rate limit exceeded" });
    }
    if (workspaceScenario.analyzeRisk === "unavailable") {
      return send(res, 500, { detail: "internal error" });
    }

    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      const { project_context: projectContext, project_name: projectName } = JSON.parse(raw);
      if (!projectContext || projectContext.trim().length < 10) {
        return send(res, 422, { detail: "project_context inválido" });
      }

      const id = nextAnalysisId++;
      const createdAt = new Date().toISOString();
      const modelOutput = {
        structured: true,
        risks: [
          {
            description: "Atraso no fornecedor de middleware compromete o go-live",
            probability: "high",
            impact: "high",
            mitigation: "Escalar ao patrocinador executivo do fornecedor",
          },
          {
            description: "Pequeno atraso na documentação de testes",
            probability: "low",
            impact: "low",
            mitigation: "Acompanhar na reunião semanal",
          },
        ],
        escalation_recommendation: "Escalar o atraso do fornecedor ao comitê executivo",
      };

      ANALYSES.push({
        id,
        kind: "risk",
        project_name: projectName,
        created_at: createdAt,
        payload: { agent: "risk_review", project_name: projectName, model_output: modelOutput },
      });

      const summary = WORKSPACE_SUMMARY[projectName];
      if (summary) {
        summary.total_analyses += 1;
        summary.open_risks += modelOutput.risks.length;
      }
      const portfolioEntry = SAMPLE.find((p) => p.project_name === projectName);
      if (portfolioEntry) {
        portfolioEntry.total_analyses += 1;
        portfolioEntry.open_risks += modelOutput.risks.length;
      }

      return send(res, 200, {
        agent: "risk_review",
        project_name: projectName,
        model_output: modelOutput,
      });
    });
    return;
  }

  // Epic W3-3 -- Risk Advisor: read-only synthesis over the latest risk
  // analysis already stored for the project, mirroring
  // src/api/routes/intelligence.py's POST /api/risk-advisor/ask. No new
  // analysis is created here -- ANALYSES is only ever read.
  if (req.method === "POST" && url.pathname === "/api/risk-advisor/ask") {
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      const { project_name: projectName, question } = JSON.parse(raw);
      if (!question || question.trim().length < 3) {
        return send(res, 422, { detail: "question inválida" });
      }

      const latestRisk = ANALYSES.filter(
        (a) => a.kind === "risk" && a.project_name === projectName,
      ).sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0];

      if (!latestRisk) {
        return send(res, 200, {
          answer: "Nenhum risco identificado ainda para este projeto.",
          cited_analyses: [],
        });
      }

      const firstRisk = latestRisk.payload.model_output.risks[0];
      return send(res, 200, {
        answer: `O risco mais crítico identificado é: ${firstRisk.description}.`,
        cited_analyses: [
          { source_analysis_id: latestRisk.id, source_created_at: latestRisk.created_at },
        ],
      });
    });
    return;
  }

  // TIP-007 -- Meeting Intelligence (Comunicação / FS-006). The only one of
  // the 3 analyze routes whose body uses "transcript", not "project_context"
  // -- matches web/app/api/bff/.../analyze/meeting/route.ts, which is the
  // single place that renames it before calling this endpoint.
  // pending_action_items is cumulative across every meeting analysis ever
  // run for the project (same summation rule as open_risks), so the mock
  // increments rather than replaces it.
  if (req.method === "POST" && url.pathname === "/api/meetings/analyze") {
    if (workspaceScenario.analyzeMeeting === "timeout") return; // never respond
    if (workspaceScenario.analyzeMeeting === "rate_limited") {
      return send(res, 429, { detail: "Rate limit exceeded" });
    }
    if (workspaceScenario.analyzeMeeting === "unavailable") {
      return send(res, 500, { detail: "internal error" });
    }

    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      const { transcript, project_name: projectName } = JSON.parse(raw);
      if (!transcript || transcript.trim().length < 10) {
        return send(res, 422, { detail: "transcript inválido" });
      }

      const id = nextAnalysisId++;
      const createdAt = new Date().toISOString();
      const modelOutput = {
        structured: true,
        summary: "Fornecedor confirmou atraso adicional na integração fiscal, sem plano de contingência apresentado.",
        decisions: ["Escalar o atraso ao comitê executivo antes do próximo go-live"],
        action_items: [
          { description: "Solicitar plano de contingência formal ao fornecedor", owner: "Ana", due_date: "2026-07-20" },
          { description: "Atualizar o cronograma de testes de integração", owner: null, due_date: null },
        ],
        issues: ["Fornecedor sem plano de contingência para o atraso na integração fiscal"],
        dependencies: ["Aprovação do comitê executivo para replanejar o go-live"],
      };

      ANALYSES.push({
        id,
        kind: "meeting",
        project_name: projectName,
        created_at: createdAt,
        payload: { agent: "meeting_intelligence", project_name: projectName, model_output: modelOutput },
      });

      const summary = WORKSPACE_SUMMARY[projectName];
      if (summary) {
        summary.total_analyses += 1;
        summary.pending_action_items += modelOutput.action_items.length;
      }
      const portfolioEntry = SAMPLE.find((p) => p.project_name === projectName);
      if (portfolioEntry) {
        portfolioEntry.total_analyses += 1;
        portfolioEntry.pending_action_items += modelOutput.action_items.length;
      }

      return send(res, 200, {
        agent: "meeting_intelligence",
        project_name: projectName,
        model_output: modelOutput,
      });
    });
    return;
  }

  res.writeHead(404).end();
});

const port = Number(process.env.MOCK_BACKEND_PORT ?? 4100);
server.listen(port, () => {
  console.log(`[mock-backend] listening on :${port}`);
});
