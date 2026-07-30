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
  { id: "D-081", summary: "Founder aprovou a apresentacao de escopo do Epic W4-4 ('Founder Decision — Epic W4-4 Scope Approval') e autorizou o Technical Design, com 4 exigencias: confirmar D-079 (workflow minimo de exemplo e apenas document.indexed -> Workflow Runtime -> Execution Tracking, sem metrica/analytics); fixar como principio arquitetural que EventDispatcher permanece completamente agnostico ao Workflow Runtime (nao conhece workflow_executions, nao conhece estados, nao atualiza status, apenas despacha) -- o WorkflowRuntime e o unico responsavel por registrar running/completed/failed; documentar (sem implementar) a politica de idempotencia; reafirmar restricoes permanentes. Nenhum codigo escrito nesta missao. TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md secao 12 produzido: escopo confirmado; separacao Dispatcher/Runtime (Dispatcher permanece byte-a-byte inalterado, falha total produz dois registros independentes de dois donos -- dead_letter_events pelo Dispatcher, workflow_executions.status=failed pelo Runtime); contratos publicos (WorkflowContext, WorkflowStep, WorkflowRuntime.run(workflow_name, steps, triggering_event) -> WorkflowContext, com correlation_id herdado de forma estrutural, nao apenas convencionada); politica de idempotencia (chave de identificacao = par event_id+workflow_name, nao correlation_id isolado; reexecucao e apenas o proprio retry sincrono do Dispatcher, upsert seguro na mesma linha porque os passos sao funcoes puras; constraint unica no banco como garantia final; evento novo sempre gera event_id novo, logo sempre gera execucao nova e distinta); migracao (constraint adicional em workflow_executions); restricoes permanentes reafirmadas; riscos residuais registrados (dependencia direta ao contrato DomainEvent, ausencia de consumidor de producao para document.indexed, idempotencia nao validada contra workflow futuro multi-passo com efeito colateral real). Missao documental -- ruff limpo, nenhum arquivo de codigo alterado. Recomendacao Go/No-Go: GO para a implementacao, condicionado a aprovacao explicita do Founder a este Technical Design. Nenhuma implementacao iniciada" },
  { id: "D-080", summary: "Founder aprovou a apresentacao de escopo do Epic W4-3 ('Founder Decision — Epic W4-3 Scope Approval') e autorizou implementacao direta, sem Technical Design especifico -- reuso estrito do contrato ja estabelecido no W4-1 (EventPublisher, Event Envelope, origem/propagacao do correlation_id, EventDispatcher/Retry/Dead Letter), exigindo apenas uma Implementation Note breve no artefato oficial existente antes de codificar. Implementation Note registrada em TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md secao 11 (pontos de publicacao, dependencias injetadas, correlation_id, momento da publicacao vs persistencia, payload definitivo, comportamento em falha) -- nenhum novo documento criado. KnowledgeRepository.index() passou a publicar document.indexed ({document_id, version_id, chunk_count}) apos o commit dos chunks gerados; ganhou correlation_id obrigatorio e o construtor ganhou event_publisher: EventPublisher obrigatorio (DI de producao injeta o singleton compartilhado). AdministrationService.create_invitation() passou a publicar invitation.created ({invitation_id, email, role_name}, nunca o token/hash) apos a criacao e a auditoria de dominio; ganhou correlation_id obrigatorio e o construtor ganhou event_publisher opcional com default real (mesma convencao de password_hasher/notification_provider) -- assimetria deliberada e documentada, ja que so a rota de convites usa create_invitation entre as ~12 construcoes de AdministrationService no codigo; build_invitation_service sempre injeta o singleton explicitamente. Rota POST /admin/invitations passa correlation_id=context.request_id. Achado grounded (nao desvio): KnowledgeRepository.index() nao tem nenhuma rota chamadora em producao hoje -- exatamente o cenario ja identificado e autorizado pelo Blueprint (produtor real disponivel para a Wave 5 sem exigir mudanca estrutural futura). Compatibilidade funcional confirmada -- nenhuma mudanca de retorno/persistencia/regra de negocio, nenhum evento publicado quando a operacao principal falha (testes dedicados provam isso). Restricoes permanentes confirmadas respeitadas -- nenhuma abstracao nova, nenhum handler, nenhum Workflow Runtime, nenhum Event Metrics, nenhum Advisor, nenhum correlation_id gerado nos servicos, token/hash/URL nunca no payload. ruff limpo, suite de testes backend completa verde. Recomendacao Go/No-Go: GO. Ciclo institucional retorna para Executive Review antes da autorizacao do proximo Epic" },
  { id: "D-079", summary: "Founder decidiu o replanejamento do Epic Ledger da Wave 4 ('Founder Decision — Wave 4 Epic Replanning'), em resposta ao achado de reconciliacao de escopo apresentado na Executive Review do W4-1 -- registrado explicitamente como replanejamento da Wave, nao como alteracao arquitetural, nenhum componente novo introduzido. Decisao: (1) Event Dispatcher, Event Audit, Retry Policies minimas e Dead Letter minimo considerados oficialmente concluidos dentro do W4-1; (2) escopo consolidado no Epic W4-1, Epic Ledger (WAVE-4-DOMAIN-BLUEPRINT.md secao 7) atualizado para refletir a realidade da plataforma, texto original preservado em nova secao 7.1 para rastreabilidade historica; (3) o Epic W4-2 deixa de existir como Epic independente; (4) Event Metrics nao implementado neste momento, classificado Deferred — Awaiting First Consumer (nenhum consumidor real: sem rota, painel, Workflow Runtime ou Advisor, alinhado ao principio 'implementar apenas capacidades sustentadas por casos reais de uso'); (5) W4-3 (document.indexed + invitation.created) promovido a proximo Epic da Wave 4, dependendo apenas de W4-1. Nota de sobreposicao registrada, nao resolvida nesta decisao: o Ledger original tambem atribuia Retry/Dead Letter a W4-5 -- mesmo texto agora consolidado no W4-1; o Founder nao se pronunciou sobre a existencia/dissolucao de W4-5, que permanece no Ledger com escopo a confirmar quando a sequencia o alcancar. Missao de governanca/documentacao -- nenhum codigo de producao alterado, ruff/tsc/eslint seguem limpos. Ciclo institucional do Epic W4-3 autorizado a iniciar, comecando pela apresentacao de escopo" },
  { id: "D-078", summary: "Founder analisou o pacote de evidencias do Epic W4-1 ('Founder Decision — Epic W4-1 Executive Review') e emitiu veredito APPROVED — GO, encerrando formalmente o Epic W4-1. Confirmou item a item: migracao atomica de EventEmitter/NoOpEventEmitter, EventPublisher como unico contrato oficial, migracao dos 5 produtores reais, event_type preservados, Event Envelope implementado e validado, correlation_id com origem unica na borda da requisicao, Retry/Dead Letter minimo e sincrono, ausencia de infraestrutura especulativa, testes/qualidade aprovados, governanca atualizada. Harmonizacao documental (nao constitui nova decisao arquitetural): TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md secao 2 atualizado para refletir o comportamento efetivamente implementado -- reaproveitamento de RequestIDMiddleware/request_id_var/RequestContext.request_id (mecanismo ja existente antes desta Wave), em vez do campo/gerador RequestContext.correlation_id descrito no documento original aprovado em D-076; nenhum codigo alterado. Autorizado o inicio do ciclo institucional do Epic W4-2 (confirmacao do escopo no Blueprint -> Technical Design se exigido -> Implementacao -> Testes -> Governanca -> Executive Review), nenhum Epic posterior antecipado. Achado de reconciliacao de escopo apresentado ao Founder antes do Technical Design de W4-2: o Epic Ledger original atribuia Event Dispatcher + Event Audit a W4-2 e Retry/Dead Letter a W4-5, mas a propria autorizacao do Founder ao W4-1 exigiu Retry/Dead Letter como evidencia obrigatoria ja dentro do W4-1 -- os tres componentes ja foram entregues no W4-1, o escopo remanescente de W4-2 e apenas Event Metrics, sem consumidor real identificado ainda no grounding audit da Wave 4. Aguarda decisao explicita do Founder sobre o achado antes do Technical Design de W4-2" },
  { id: "D-077", summary: "Founder aprovou o Technical Design da Wave 4 ('Founder Decision — Wave 4 Technical Design Approval') e autorizou a implementacao do Epic W4-1, com 6 criterios obrigatorios. Migracao atomica concluida: EventEmitter/NoOpEventEmitter (Wave 1, D-049) removidos definitivamente, substituidos por EventPublisher/InProcessEventPublisher (src/services/events/interfaces.py, in_process_publisher.py) e EventDispatcher (dispatcher.py) para despacho in-process + Retry/Dead Letter, sem periodo de coexistencia entre as duas abstracoes. DomainEvent (envelope unico) com os 6 campos exigidos (event_id, event_type, correlation_id, timestamp, organization_id-como-tenant, origin, payload_version) mais payload. DomainService migrado -- construtor recebe publisher: EventPublisher, cada create_* recebe correlation_id explicito e publica via .publish(...). Rotas (portfolio/program/project_delivery) e DI (build_event_publisher) atualizadas na mesma migracao. Achado de implementacao (refinamento do Technical Design, nao desvio de escopo): a plataforma ja possui, desde antes desta Wave, um mecanismo de origem unica de correlacao (RequestIDMiddleware/request_id_var, ja propagado em RequestContext.request_id) -- a implementacao reusa context.request_id diretamente como correlation_id, evitando um segundo gerador de identificador; DomainService nunca cunha um correlation_id, apenas propaga o que recebe. Migracao 0018 (aditiva) cria events (Event Audit) e dead_letter_events; workflow_executions (Execution Tracking) deliberadamente nao criado -- pertence ao Workflow Runtime, Epic W4-4, ainda inexistente. Retry/Dead Letter implementado exatamente como aprovado (MAX_ATTEMPTS=3, sincrono e imediato, sem backoff, sem fila, dead-letter so apos a 3a falha, sem reprocessamento automatico, sem interface administrativa). Busca global confirma remocao completa: zero .emit(, zero import EventEmitter, zero import de noop_emitter em codigo executavel -- so mencoes historicas em comentarios/docstrings. Compatibilidade funcional confirmada: os 5 event_type existentes inalterados, suite de API pre-existente (69 casos) roda sem alteracao de asserção. Testes novos: test_events_in_process_publisher.py (3 casos), test_events_dispatcher.py (5 casos), test_migration_0018_wave4_event_publisher.py (upgrade/downgrade/re-upgrade em PostgreSQL real), test_domain_service.py reescrito com teste dedicado de propagacao de correlation_id. Restricoes permanentes confirmadas ausentes (brokers, filas externas, registries dinamicos, engines genericas, plugins, DSLs, infraestrutura especulativa). ruff limpo, suite de testes backend completa confirmada verde (503 passed). Recomendacao Go/No-Go: GO para o Epic W4-2. Ciclo institucional retorna para Executive Review antes da autorizacao do Epic W4-2, per determinacao explicita do Founder" },
  { id: "D-076", summary: "Founder aprovou formalmente a AR-7 ('Founder Decision — Wave 4 Architecture Review Approval', veredito GO sem ressalvas) e autorizou o Technical Design da Wave 4, condicionado a resolver documentalmente os 4 riscos identificados. TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md produzido, resolvendo as 4 condicoes: (1) EventPublisher -- responsabilidades de EventEmitter (removido) e EventPublisher (novo, cunha o envelope completo) formalizadas, contrato publico definido (publish(event_type, payload, organization_id, correlation_id, origin) -> DomainEvent), migracao atomica dentro do Epic W4-1 (EventEmitter/NoOpEventEmitter removidos no mesmo commit, nunca coexistindo com o novo Publisher), compatibilidade com os 5 produtores existentes confirmada (mesmos event_type, sem renomeacao); (2) correlation_id -- origem unica definida em get_request_context (mesmo funil que ja resolve organization_id/actor_user_id), gerado via uuid4() quando ausente, propagado por parametro explicito, workflows sempre herdam do evento disparador; (3) Execution Tracking x Event Audit -- decididos como componentes distintos (tabelas events/workflow_executions), unidos so por correlation_id, justificado por cardinalidade nao-1:1 entre eventos e execucoes de workflow; (4) Retry/Dead Letter -- minimo fixo definido (MAX_ATTEMPTS=3, qualquer excecao dispara retry sincrono, sem backoff, dead_letter_events com estrutura minima, encaminhamento apos a 3a falha, sem reprocessamento automatico). Restricoes permanentes reafirmadas e confirmadas ausentes (brokers, filas externas, registries dinamicos, engines genericas, plugins, DSLs, infraestrutura especulativa). Missao documental -- nenhum codigo alterado, ruff limpo. Aguarda aprovacao explicita do Founder ao Technical Design antes de qualquer implementacao do Epic W4-1" },
  { id: "D-075", summary: "AR-7 -- Architecture Review do Wave 4 Domain Blueprint concluida, veredito GO. Escopo minimo de 5 pontos exigido pelo Founder verificado item a item: (1) Event Envelope confirmado com os 6 campos obrigatorios (Event ID/Correlation ID/Timestamp/Tenant/Origin/Payload Version) mais payload, compartilhado por todos os eventos propostos; (2) Workflow Runtime confirmado como orquestracao operacional pura -- nunca regra de negocio, nunca substitui AdvisorFramework.run(), nunca decisao de dominio, apenas coordena execucao; (3) Event Publisher/Dispatcher confirmado minimo e in-process -- sem broker, fila distribuida, registry generico ou infraestrutura especulativa; (4) Integration Gateway confirmado como reaproveitamento do padrao ja provado por NotificationProvider/EmbeddingProvider; (5) Conformidade arquitetural confirmada -- aderencia ao CLAUDE.md, ausencia de arquitetura paralela (achado de pmo_workflow.py ja neutralizado por D-074), ausencia de duplicacao de responsabilidades, aderencia integral a D-073/D-074, consistencia com os padroes das Waves 1-3. 4 riscos nao bloqueantes registrados para o Technical Design resolver (precisao de linguagem na promocao do seam, origem do correlation_id, relacao Execution Tracking/Event Audit, semantica de Retry/Dead Letter). Unico artefato novo: AR-7-WAVE-4-DOMAIN-BLUEPRINT-REVIEW.md, sem documentacao redundante. Missao exclusivamente de revisao arquitetural -- nenhum codigo alterado. Autorizado avancar ao Technical Design mediante aprovacao explicita do Founder" },
  { id: "D-074", summary: "Founder resolveu a Decision Proposal do Wave 4 Domain Blueprint sobre src/workflows/pmo_workflow.py, aprovando a Opcao A: classificacao formal como Historical Superseded Architecture -- non-production, non-reference implementation. Arquivo nao removido (valor de rastreabilidade historica, referencias no CLAUDE.md), mas nao pode mais ser interpretado como arquitetura oficial, componente futuro ou base valida para a Wave 4. Aviso explicito adicionado ao topo do arquivo (docstring historico original preservado, nao substituido); CLAUDE.md atualizado com nota esclarecendo que workflows/ e reservado ao Workflow Runtime da Wave 4, nao a orquestracao multiagente; busca global executada e documentada -- zero imports, zero rotas dependentes, zero testes dependentes, zero uso em producao; nenhuma reutilizacao/adaptacao/extracao de componentes deste arquivo para a Wave 4; gatilho de remocao futura registrado (missao especifica de limpeza arquitetural). Proibida a coexistencia de duas arquiteturas de workflow. Missao documental -- nenhum comportamento de codigo alterado, ruff limpo. Wave 4 Domain Blueprint autorizado a seguir para Architecture Review" },
  { id: "D-073", summary: "Wave 4 Domain Blueprint (Enterprise Operations) produzido em resposta ao Founder Kickoff -- levantamento obrigatorio (grounding) realizado antes de qualquer Blueprint: exatamente 5 sitios de emissao real de evento em todo o codigo (DomainService.create_portfolio/program/project via EventEmitter/NoOpEventEmitter, D-049), nenhum com envelope de observabilidade completo; taxonomia aspiracional do Event-Map.html sem nenhum .emit() real; 2 workflows manuais sincronos identificados sem evento (KnowledgeRepository.ingest()/index(), AdministrationService.create_invitation()); zero precedente de fila/retry/dead-letter em toda a base; achado critico -- src/workflows/pmo_workflow.py (ja reservado por CLAUDE.md, nunca conectado ao MVP, instrucao anterior explicita de nao remover) descreve orquestracao multiagente ja rejeitada pelo Founder na Fase 3 do Advisor Framework e mistura workflow com logica de negocio, violando o principio 'Workflow != Business Logic' desta propria Wave -- registrado como Decision Proposal, nao decidido silenciosamente. Modelo operacional nascido do levantamento: Event Model (envelope com Event ID/Correlation ID/Timestamp/Tenant/Origin/Payload Version), apenas 3 Event Contracts com produtor real hoje (migracao dos 5 existentes + DocumentIndexed + InvitationCreated -- nenhum evento especulativo tipo RiskIdentified/DecisionRegistered sem consumidor real), Event Publisher/Dispatcher in-process sem broker externo, Workflow Runtime minimo que nunca substitui AdvisorFramework.run(), Execution Tracking + Retry/Dead Letter minimos, Integration Gateway reaproveitando o padrao ja provado por NotificationProvider/EmbeddingProvider, Event Audit como extensao (nunca substituicao) da auditoria de dominio ja existente. Epic Ledger W4-1 a W4-6. Missao documental, ruff limpo. Aguarda decisao do Founder sobre a Decision Proposal e a Architecture Review antes de qualquer Technical Design ou implementacao" },
  { id: "D-072", summary: "Harmonizacao do roadmap aprovada e concluida ('Founder Decision — D-072'): as 8 Waves de D-071 confirmadas sem alteracao; Enterprise Analytics deixa de ser uma Wave independente e passa a ser capacidade transversal construida ao longo das Waves 4, 5 e 6; Productization deixa de ser uma Wave independente e passa a compor o escopo da Wave 8 — STRATECH Enterprise v1.0 (distribuicao, documentacao, empacotamento, instalacao, licenciamento, lancamento oficial); nenhuma nova Wave sera criada para absorver esses temas; Mission Control permanece a fonte oficial do roadmap vigente. Missao exclusivamente de governanca -- nenhum codigo/arquitetura/dominio/API/teste alterado. Autorizado o inicio do ciclo institucional da Wave 4 — Enterprise Operations" },
  { id: "D-071", summary: "Harmonizacao oficial do roadmap ('Founder Decision — Wave 4 Authorization'): a organizacao das Waves passa a ter 8 elementos -- 1 Enterprise Foundation, 2 Enterprise Platform, 3 Enterprise Knowledge Platform (renomeada de 'Enterprise Intelligence', reflete o que foi de fato entregue), 4 Enterprise Operations, 5 Enterprise Advisors (nova -- os 7 Advisors restantes, antes W3-7b), 6 Executive Intelligence (nova -- antes W3-8), 7 Enterprise Readiness (nova, escopo a definir) e 8 STRATECH Enterprise v1.0 (nova, escopo a definir). Cada Wave passa a declarar explicitamente suas dependencias de Waves anteriores (recomendacao do Founder, adotada). Missao exclusivamente de governanca -- nenhum codigo/arquitetura/dominio/API/teste alterado. Nenhum documento publicado sob o nome 'Wave 3 — Enterprise Intelligence' foi reescrito ou renomeado, preservando o historico da evolucao arquitetural. Ciclo institucional da Wave 4 autorizado a iniciar" },
  { id: "D-070", summary: "Founder aprovou formalmente o Wave 3 Closure Review ('Founder Decision — Wave 3 Closure') e declarou a Wave 3 (Enterprise Intelligence) oficialmente encerrada -- confirmando que todos os objetivos efetivamente autorizados foram entregues, que a reclassificacao dos 7 Advisors restantes + Executive Intelligence foi explicita/documentada/rastreavel (nao omissao de escopo), que a arquitetura foi validada por implementacao e migracao reais (Knowledge Platform, Knowledge Services, Advisor Framework), que os debitos tecnicos remanescentes tem criterios e gatilhos claros, e que a governanca institucional foi atualizada de forma completa. Wave 4 autorizada a iniciar, condicionada a uma unica exigencia: harmonizar a nomenclatura oficial da Wave no Mission Control e na documentacao de planejamento antes da publicacao do primeiro Domain Blueprint -- resolvendo o achado ja registrado em D-069 (o 'Wave 4' hoje nomeado como Enterprise Operations e um escopo distinto dos 7 Advisors restantes + Executive Intelligence deferidos)" },
  { id: "D-069", summary: "Wave 3 Closure Review publicado, atendendo aos 5 elementos solicitados pelo Founder: comparacao entre objetivos planejados e entregues (7 Fases entregues 100% -- W3-1 a Fase 4; os 7 Enterprise Advisors restantes + Executive Intelligence/W3-8 nao foram entregues, mas reclassificados como deferidos por decisao explicita do Founder, nao descartados silenciosamente); validacao das 5 principais decisoes arquiteturais (pgvector sempre atras de KnowledgeRepository, fronteira do RagPipeline antes da composicao de prompt, escopo limitado do Enterprise Memory Model, contrato flat-dict do AdvisorContract sem schema generico, disciplina de migracao fiel com suite nao modificada capturando 2 bugs reais); 5 licoes aprendidas (auditoria-antes-de-abstracao, suite pre-existente como oraculo, template1 como padrao reutilizavel de privilegio, adiar sem consumidor real e decisao de arquitetura, Framework minimo gera mudancas de contrato pequenas); debitos tecnicos remanescentes (TD-011/012/013, todos Postergados com gatilho explicito, Technical Debt Register 100% classificado); recomendacao formal de GO para a Wave 4. Achado de reconciliacao de roadmap registrado (Wave 4 ja nomeada como Enterprise Operations, escopo distinto dos Advisors restantes) -- nao bloqueador. Missao documental, ruff limpo. Decisao final de encerramento da Wave 3 permanece com o Founder" },
  { id: "D-068", summary: "Wave 3 Fase 4 (migracao do Risk Advisor) concluida -- Advisor Framework validado arquiteturalmente em producao de codigo real. RiskAdvisorAgent migrado para receber um AdvisorFramework (nao mais model_client/prompt_registry diretos); rota ask_risk_advisor reescrita delegando gather_context/gather_rag_context/run; RiskAdvisorRequest/RiskAdvisorResponse inalterados. 2 achados corrigidos, ambos detectados pela suite de regressao ja existente rodada sem alteracao: retorno do Agent nao estava achatado conforme o AdvisorContract exigia; no_evidence() perdia a mensagem especifica de dominio do risco. Validacao ponta a ponta demonstrada (chunk_ids rastreaveis, no_evidence sem chamada ao LLM, ausencia de acesso direto a infraestrutura, equivalencia funcional, isolamento entre organizacoes) contra o Agent real, nunca um Advisor de teste. Suite pre-existente TestRiskAdvisor permanece 100% verde sem nenhuma alteracao de asserção. ruff limpo, pytest 494 (12 novos testes), 97% cobertura. Nenhuma capacidade nova criada. Decisao de encerramento da Wave 3 fica com o Founder" },
  { id: "D-067", summary: "Wave 3 Fase 3 (Enterprise Advisor Framework, Minimum Viable Framework) implementada -- autorizada apos auditoria obrigatoria do Risk Advisor real (fluxo de POST /risk-advisor/ask mapeado linha a linha). AdvisorContract (Protocol) nomeia a forma ja real de RiskAdvisorAgent.advise() -- sem input_schema/output_schema generico por Advisor (correcao deliberada da especulacao do Blueprint original). AdvisorFramework: gather_context/gather_rag_context/render_prompt/call_llm/run -- executa exatamente um Advisor por chamada, audita incondicionalmente, retorna no_evidence() sem custo de LLM, levanta AdvisorExecutionError para saida malformada. Nenhum Advisor migrado -- RiskAdvisorAgent/ask_risk_advisor permanecem intocados; validacao arquitetural completa do Framework fica para a Fase 4. Confirmado por busca global: nenhum acesso direto a PgVectorRepository/EmbeddingProvider fora de KnowledgeRepository/RagPipeline. ruff limpo, pytest 485 (8 novos testes), 97% cobertura (100% no novo pacote)" },
  { id: "D-066", summary: "Wave 3 Fase 2 (Enterprise Knowledge Platform, Knowledge Services) implementada -- autorizada pelo Founder apos a Fase 1, com diretrizes de separacao rigorosa infraestrutura/dominio e nenhuma logica especifica de Advisor. RagPipeline (rag_pipeline.py): retrieve() compoe KnowledgeRepository.search() com ranking deterministico (score, depois recencia da versao) e retorna um RagContext com chunk_ids rastreaveis para grounding futuro; toda chamada logada. EnterpriseMemoryService: MemoryCategory (5 categorias), classify()/list_by_category() sobre documentos ja ingeridos via KnowledgeRepository; nova entidade MemoryRecord + migracao 0017 (aditiva). Checklist de colisao contra Executive Memory revalidada -- nenhuma sobreposicao, nenhum arquivo de web/lib/executive-memory/ tocado. Escopo de ciclo de vida limitado a Captura+Classificacao+Consulta (Consolidacao/Expiracao adiadas por falta de consumidor real). ruff limpo, pytest 477 (13 novos testes), 97% cobertura. Nenhum Advisor implementado ainda" },
  { id: "D-065", summary: "Wave 3 Fase 1 (Enterprise Knowledge Platform, Foundation) implementada -- primeiro código real da Wave 3, autorizado pelo Founder apos a AR-6. Novo pacote src/services/knowledge_platform/ (KnowledgeRepository como fachada unica; PgVectorRepository, unica classe ciente de pgvector; EmbeddingProvider/MockEmbeddingProvider determinístico, backend de producao deferido a Fase 2). 3 novas entidades (Document/DocumentVersion/Chunk) em models.py, migracao 0016 (habilita pgvector + cria as 3 tabelas, aditiva). Achado de infraestrutura resolvido: CREATE EXTENSION exige superusuario no Postgres vanilla -- instalado uma unica vez em template1 (scripts/rc2-db.sh), sem elevar o privilegio do papel aipmo; docker-compose/CI trocaram a imagem para pgvector/pgvector:pg16. ruff limpo, pytest 464 (14 novos testes), 97% cobertura. Nenhum Advisor consome a plataforma ainda -- Definition of Done da Fase 1 (WAVE-3-SUCCESS-CRITERIA.md) cumprida integralmente" },
  { id: "D-064", summary: "AR-6 concluída: Architecture Review do Wave 3 Domain Blueprint aprovado sem ressalvas -- auditoria cobriu consistência com CLAUDE.md (nenhuma arquitetura paralela/duplicação/provider ou registry novo), checagem item a item das diretrizes verbatim do Founder sobre Vector Store e Framework de Orquestração, consistência interna cruzada entre os 8 documentos (1 referência desatualizada encontrada e corrigida em ENTERPRISE-ADVISOR-CATALOG.md), grounding em consumidor real (Risk Advisor, migração obrigatória na Fase 3 antes de qualquer Advisor novo) e risco de sobre-engenharia avaliado e mitigado. Nenhuma Decision Proposal adicional necessária. Wave 3 aguarda apenas aprovação explícita do Founder para iniciar a Fase 1" },
  { id: "D-063", summary: "2 Decision Proposals resolvidas (Vector Store pgvector aprovado como infraestrutura da Enterprise Knowledge Platform; Framework de Orquestração Multiagente aprovado como infraestrutura de execução dos Enterprise Advisors) + Wave 3 Domain Blueprint (8 entregáveis) concluído: WAVE-3-DOMAIN-BLUEPRINT.md (documento mestre, arquitetura em camadas unidirecionais), DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md (13 sub-componentes, Ingestion a RAG Pipeline via KnowledgeRepository/VectorRepository), DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md (5 memórias, checklist obrigatória de colisão contra Executive Memory em §0), DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md (contratos/ciclo de vida/orquestração/observabilidade/auditoria, generalizando o Risk Advisor), ENTERPRISE-ADVISOR-CATALOG.md (8 Advisors catalogados, nenhum implementado), DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md (pipeline/ranking/grounding), WAVE-3-INTEGRATION-BLUEPRINT.md (integração com os 10 domínios/módulos existentes) e WAVE-3-EXECUTION-PLAN.md (supersede WAVE-3-EXECUTIVE-PLAN.md, ordem mandatória de Fases 1-4, Gates entre elas). Nenhum Epic implementado -- apenas arquitetura, per diretriz explícita do Founder" },
  { id: "D-062", summary: "Wave 2 Closure Review concluído: Wave 2 (Enterprise Platform) formalmente encerrada. 7 entregáveis produzidos -- Wave 2 Closure Report (objetivos originais, 13 itens implementados, itens em Governança/Business Pending, débitos técnicos encerrados/remanescentes, lições aprendidas), Architecture Delta (o que mudou/permaneceu/foi eliminado, novos padrões), Domain Evolution Report (Aggregates, entidades consolidadas, novos princípios), Technical Debt Register 100% classificado (Resolvido/Postergado/Futuro Roadmap, nenhum item sem status), Governance Review (Decision Log/Mission Control/CHANGELOG/Domain Model/Blueprints validados -- 1 drift documental encontrado e corrigido em DOMAIN-MODEL.md §6), Readiness Assessment (zero bloqueadores) e o plano executivo da Wave 3. 'Wave 3 Ready' declarado formalmente" },
  { id: "D-061", summary: "Wave Completion Review retrospectivo, item 8 -- TD-008 Fase 3b, Etapa 4b concluída (destrutiva) e TD-008 RESOLVIDO. project_id é a única chave de acesso interno ao Project. Migração 0015 ativada (alembic heads = 0015): NOT NULL em analysis_records.project_id + DROP COLUMN analysis_records.project_name + drop do índice; campo project_name removido do ORM. Nome preservado como apresentação (Condição 1 do Founder): Project.name é a fonte do nome de exibição, o campo project_name PERMANECE nas responses derivado de Project.name -- nenhum campo removido das responses, zero regressão de frontend. Downgrade íntegro (Condição 2): recria a coluna e repopula project_name de projects.name via project_id, provado em PostgreSQL real. Encerramento (Condição 4): 0015 ativa, coluna removida, rollback íntegro comprovado, suíte verde (ruff/pytest 449/tsc/eslint/vitest 491/E2E 292), docs atualizadas, sem compatibilidade temporária desnecessária. O nome nunca mais funciona como chave/join/identidade" },
  { id: "D-060", summary: "Wave Completion Review retrospectivo, item 8 -- Gate Final de Migração aprovado (veredito NÃO-GO para a destrutiva estava correto: a governança funcionou) + TD-008 Fase 3b, Etapa 4a concluída (aditiva, reversível): eliminação dos consumidores residuais de project_name como chave (R1-R6). project_id vira a única chave de escopo de leitura -- list_analyses id-only (resolve_scope_id reutilizado pelo serviço e pelo AIContextEngine); display derivado de Project.name via AnalysisRecord.project/analysis_display_name; list_latest_risks dedup por id, summarize_portfolio agrupa por id; responses e joins de frontend (decision-queue/portfolio-view) por project_id; save_analysis não grava mais a coluna. ProjectSummaryResponse/Service mantidos e classificados como projeção de leitura/serviço de composição (DOMAIN-MODEL.md). Migração destrutiva 0015 definida e encenada (fora do head ativo 0014), upgrade/downgrade provados reversíveis em PostgreSQL real. ruff limpo, pytest 449 + teste 0015, tsc/eslint limpos, vitest 491, E2E 292. Etapa 4b (ativar a 0015: NOT NULL + DROP COLUMN) permanece bloqueada -- exige novo Gate + nova aprovação explícita do Founder" },
  { id: "D-059", summary: "Wave Completion Review retrospectivo, item 8 -- TD-008 Fase 3b, Etapa 5 (frontend-only, sem tocar no banco): eliminação de ProjectSummary. O Founder reordenou a sequência (Etapa 5 antes da Etapa 4 destrutiva, com Gate Final entre elas). Achado: ProjectSummary (dashboard) e WorkspaceSummary (workspace) eram dois espelhos duplicados do mesmo read-model de inteligência de um Project; a entidade de domínio Project (delivery) é outro bounded context -- fundir seria conflação, rejeitada. Consolidados no tipo canônico ProjectIntelligenceSummary, ancorado em project_id (project_name só exibição); todos os consumidores (Dashboard/Portfólio/Decision Center/Workspace) migrados, definições antigas removidas. Backend inalterado (ProjectSummaryService/Response seguem como produtor). tsc/eslint limpos, vitest 486, E2E 292. Próximo: Gate Final de Migração; a Etapa 4 (destrutiva) exige nova aprovação explícita" },
  { id: "D-058", summary: "Wave Completion Review retrospectivo, item 8 -- TD-008 Fase 3b, Etapa 3 (frontend-only, aditiva): consumidores usam project_id como chave primária, Project.name só como exibição. Novo hook compartilhado useResolvedProjectId reaproveita a resolução nome->id do summary (deduplicada pelo React Query, sem resolução redundante nem request extra); os consumidores escopados restantes (RisksPanel, CommunicationBrief, IntelligenceTimeline, AnalysisHistory, ActionsSection, ActionsContextLine) enviam project_id como chave exata; keepPreviousData mantém a troca de chave sem flash (comportamento inalterado). Independência de painéis preservada; invalidações pós-mutação casam por prefixo de chave, então o reflexo pós-análise é inalterado. project_name/ProjectSummary não removidos (Etapa 4/5). tsc/eslint limpos, vitest 486, E2E 292, backend inalterado. DROP COLUMN (Etapa 4) segue exigindo nova aprovação do Founder" },
  { id: "D-057", summary: "Wave Completion Review retrospectivo, item 8 -- TD-008 Fase 3b, Etapa 2 (frontend-only, aditiva): consumidores de frontend tornam-se dual-key, project_name e project_id coexistindo. (G1) as 4 rotas BFF de intelligence encaminham project_id opcional; (G2) WorkspaceSummary + hooks escopados (summary/latest-risks/action-items/workspace-latest/recent-analyses/timeline) carregam project_id na queryKey, encoding do nome preservado (%20); (G3) executive-brief reaproveita o project_id resolvido pelo summary como chave exata nas leituras irmãs, com fallback por nome enquanto o summary carrega (independência de painéis preservada). Nenhum caminho removido, sem provider/registry novo; tsc/eslint limpos, vitest 483, E2E 292, backend inalterado. Gate destrutivo (DROP COLUMN, Etapa 4) segue exigindo nova aprovação do Founder" },
  { id: "D-056", summary: "Wave Completion Review retrospectivo, item 8 -- TD-008 Fase 3b, Etapa 1 (aditiva): project_id introduzido como chave de acesso ao Project, sem remover nada. As rotas de intelligence (/analyses, /action-items, /risks/latest, /projects/summary) passam a aceitar project_id além de project_name; nova resolução dual-key org-escopada (resolve_project_reference) + exceções tipadas mapeadas no boundary: id inexistente/cross-org -> 404, id != nome -> 409, nome ambíguo -> 409. Nome que resolve unicamente vira filtro exato por id; nome nunca-analisado preserva a lista vazia (nunca 404) -- additividade estrita. Migração 0014 re-backfilla project_id de forma defensiva (sem NOT NULL, isso é Etapa 4). Achado: o constraint uq_projects_org_name já torna ambiguidade de nome estruturalmente impossível. Gate destrutivo (DROP COLUMN) exige nova aprovação do Founder" },
  { id: "D-055", summary: "Wave Completion Review retrospectivo, item 7: Workspace reclassificado como View/UI -- auditoria arquitetural determinou que 'workspace' é termo de apresentação (a rota /workspace/:projectName) + a sessão de autenticação Nível 1 (já = entidade Session/D-053); a suposta entidade administrável não tem identidade/ciclo de vida/invariantes/relacionamentos/persistência em nenhum documento. Classificação (A) View/UI; não promovido ao domínio (seria arquitetura paralela sobre Program/Portfolio + RBAC Organization Scope). Governança Concluída, sem código" },
  { id: "D-054", summary: "Wave Completion Review retrospectivo, item 6: Convites implementados, domínio desacoplado da infraestrutura de e-mail -- auditoria separou domínio de mecanismo de entrega (e-mail é notificação, não constituinte do domínio); Invitation (migração 0013), estados Pendente/Aceito/Expirado/Cancelado derivados de timestamps, API admin (invitations.manage) + fluxo público de aceitação sem sessão, entrega isolada em NotificationProvider/NoOp (nenhum provedor SMTP/SES escolhido); o token é devolvido uma vez para entrega manual; painel /administracao/convites" },
  { id: "D-053", summary: "Wave Completion Review retrospectivo, item 5: Sessões server-side implementadas (resolve TD-010) -- nova tabela sessions + migração 0012, session_id cunhado pelo backend no login (não mais pelo BFF), logout revoga de verdade; enforcement de revogação em require_permission (sessão revogada é rejeitada na requisição seguinte, não em até 12h), fail-open para não quebrar sessões não rastreadas; painel /administracao/sessoes com listagem e revogação" },
  { id: "D-052", summary: "Wave Completion Review retrospectivo, item 4: Configurações da Organização e Tenant/System Settings formalmente separados -- auditoria exaustiva do repositório não encontrou nenhuma definição funcional concreta para Configurações (fica 'Sem Escopo Funcional Definido', não implementado); Tenant/System Settings depende das 7 perguntas sem resposta do Business Model Blueprint (Wave 6, 'Pendente de Decisão de Negócio'); melhoria de infraestrutura (rate limit por org) rejeitada como substituto para encerrar o item -- fecha como Governança Concluída, não Implementado" },
  { id: "D-051", summary: "Wave Completion Review retrospectivo, item 3: API Keys implementado -- correção arquitetural retroativa (Nível 3 \"depende de Integration Hub\" -> Nível 1 \"fundamental\"); chave autentica como o usuário criador, reaproveita 100% do RBAC/auditoria/Argon2 já existentes; segunda via de autenticação aditiva em get_request_context (X-Stratech-Api-Key), toda rota já protegida ganha suporte sem mudança própria; princípio permanente do Founder registrado: componente fundamental nunca depende de componente futuro" },
  { id: "D-050", summary: "Wave Completion Review retrospectivo, item 2: TD-004/005/006 resolvidos -- race de invalidação do React Query corrigida (cancelQueries antes de invalidateQueries nos 3 hooks de mutação de Analisar Projeto); verificação A/B controlada confirma a causa raiz e a correção" },
  { id: "D-049", summary: "Wave Completion Review retrospectivo, item 1: Event Foundation (Wave 1) implementado -- EventEmitter Protocol + NoOpEventEmitter, DomainService emite 5 eventos de domínio já especificados na Technical Design; Wave 1 fechada -- 341 testes backend validados" },
  { id: "D-048", summary: "Superseding Decision: nova Wave Completion Policy oficial e permanente -- revoga todas as decisões anteriores que permitiam adiar Epics/Enterprise Analysts/Capabilities previstos; capacidade já planejada deixa de ser especulativa; Wave Completion Review retrospectivo (Waves 1-3) aberto" },
  { id: "D-047", summary: "Wave 3, Epic W3-2 redefinido e implementado: Digital PMO Intelligence Foundation -- infraestrutura compartilhada (Context/Recommendation/Explanation/Prompt/Audit/Observability Engines) que todo Enterprise Analyst reutiliza; Risk Advisor migrado como prova de reuso, contrato HTTP inalterado -- 335 testes backend validados" },
  { id: "D-046", summary: "Wave 3, Epic W3-3 implementado: Risk Advisor -- primeiro Enterprise Agent conversacional (somente leitura, reaproveita intelligence.read, sem entidade/migração/provider novos) -- 314 testes backend, 468 frontend, E2E ponta-a-ponta validados" },
  { id: "D-045", summary: "Security Hardening Gate concluído: C-1 (RBAC + organization scope nas 8 rotas de intelligence.py) e C-2 (organization_id em AnalysisRecord, migração 0010 com backfill seguro) fechados -- 305 testes backend, 452 frontend, E2E completo (3 projetos) validados. Risk Advisor liberado para retomar a Implementação" },
  { id: "D-044", summary: "Baseline oficial consolidada: PR #45 mergeado na main (hash d8ff04d), todos os checks essenciais revalidados (backend, frontend, PostgreSQL, migrations upgrade/downgrade/re-upgrade); bug de CI real corrigido (validate nunca provisionava Postgres). Risk Advisor ainda não iniciado -- próximo: Security Hardening Gate" },
  { id: "D-043", summary: "Wave 3, Epic W3-3: Enterprise Domain Blueprint do Risk Advisor concluído (somente leitura, reaproveita Project/AnalysisRecord, sem framework de orquestração) — Implementação bloqueada até o Founder decidir C-1/C-2 e a main ser consolidada (PR #45)" },
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
  { label: "Technical Design do Epic W4-4 produzido (D-081): Founder aprovou o escopo e autorizou o Technical Design de Workflow Runtime + Execution Tracking -- escopo confirmado (document.indexed -> WorkflowRuntime -> Execution Tracking, um unico passo, sem metrica); EventDispatcher permanece agnostico e byte-a-byte inalterado (principio arquitetural fixado pelo Founder); WorkflowRuntime e o unico dono dos estados running/completed/failed; politica de idempotencia definida (chave event_id+workflow_name, upsert seguro por passos serem funcoes puras, constraint unica no banco); contratos publicos com correlation_id herdado de forma estrutural. Missao documental, nenhum codigo escrito, ruff limpo. GO para a implementacao, aguardando aprovacao explicita do Founder a este Technical Design", done: true },
  { label: "Epic W4-3 implementado (D-080): document.indexed (KnowledgeRepository.index()) e invitation.created (AdministrationService.create_invitation()) conectados ao padrao de Event Publisher/Envelope/correlation_id ja estabelecido no W4-1 -- implementacao direta autorizada pelo Founder, sem Technical Design especifico, apenas uma Implementation Note registrada no Technical Design existente (secao 11). Payloads estritos ({document_id, version_id, chunk_count} e {invitation_id, email, role_name}, nunca token/hash), eventos publicados so apos sucesso da operacao principal, correlation_id propagado de context.request_id (rota de convites) ou explicito por parametro (indexacao, ainda sem rota chamadora em producao -- achado grounded, nao desvio). Compatibilidade funcional confirmada, restricoes permanentes respeitadas, ruff limpo, suite de testes backend completa verde. GO para o proximo Epic -- ciclo institucional retorna para Executive Review antes da proxima autorizacao", done: true },
  { label: "Wave 4 Epic Replanning (D-079): Founder decidiu dissolver o Epic W4-2, consolidando Event Dispatcher/Event Audit/Retry-Dead Letter (ja entregues no W4-1) no proprio W4-1, e classificou Event Metrics como Deferred — Awaiting First Consumer (nenhum consumidor real hoje). Registrado como replanejamento da Wave, nao alteracao arquitetural -- nenhum componente novo introduzido. Epic Ledger (Wave 4 Domain Blueprint) atualizado, texto original preservado para rastreabilidade. W4-3 (document.indexed + invitation.created) promovido a proximo Epic, dependendo apenas de W4-1. Nota de sobreposicao com W4-5 (Retry/Dead Letter) registrada para decisao futura do Founder, nao antecipada. Ciclo institucional do Epic W4-3 autorizado a iniciar", done: true },
  { label: "Executive Review do Epic W4-1 aprovada, GO (D-078): Founder confirmou item a item o pacote de evidencias -- migracao atomica, EventPublisher como unico contrato, os 5 produtores migrados, Event Envelope validado, correlation_id de origem unica, Retry/Dead Letter minimo, ausencia de infraestrutura especulativa, governanca em dia. Harmonizacao documental do Technical Design (correlation_id reusa RequestIDMiddleware/request_id_var ja existente, sem novo campo/gerador) registrada sem constituir nova decisao arquitetural. Ciclo institucional do Epic W4-2 aberto -- achado de reconciliacao de escopo apresentado ao Founder (Event Dispatcher/Event Audit/Retry-Dead Letter, originalmente atribuidos a W4-2/W4-5 no Epic Ledger, ja entregues no W4-1; escopo remanescente de W4-2 e apenas Event Metrics), aguardando decisao explicita antes do Technical Design", done: true },
  { label: "Epic W4-1 implementado (D-077): Founder aprovou o Technical Design e autorizou a implementacao -- migracao atomica de EventEmitter/NoOpEventEmitter (Wave 1) para EventPublisher/InProcessEventPublisher + EventDispatcher, sem coexistencia entre as duas abstrações. DomainEvent (envelope unico com os 6 campos exigidos) e migracao 0018 (events + dead_letter_events, workflow_executions deliberadamente deferido). Retry/Dead Letter minimo implementado exatamente como aprovado (MAX_ATTEMPTS=3, sincrono, sem backoff, sem fila). correlation_id reusa RequestIDMiddleware/request_id_var ja existente na plataforma (origem unica, achado de implementacao documentado, nao desvio de escopo). Os 5 event_type existentes inalterados, suite de API pre-existente roda sem alteracao de asserção. Busca global confirma remocao completa de EventEmitter/NoOpEventEmitter do codigo executavel. ruff limpo, suite de testes backend completa verde (503 passed). GO para o Epic W4-2 -- ciclo institucional retorna para Executive Review antes da autorizacao do proximo Epic", done: true },
  { label: "Technical Design da Wave 4 produzido (D-076): Founder aprovou a AR-7 e autorizou o Technical Design, condicionado a resolver 4 riscos documentalmente. As 4 condições resolvidas -- EventPublisher (contrato + migração atômica no Epic W4-1), correlation_id (origem única em get_request_context, propagação explícita), Execution Tracking × Event Audit (componentes distintos unidos por correlation_id), Retry/Dead Letter (mínimo fixo, MAX_ATTEMPTS=3). Restrições permanentes reafirmadas. Missão documental, ruff limpo. Aguarda aprovação explícita do Founder antes de qualquer implementação do Epic W4-1", done: true },
  { label: "AR-7 concluída, veredito GO (D-075): Architecture Review do Wave 4 Domain Blueprint -- Event Envelope, Workflow Runtime, Event Publisher/Dispatcher, Integration Gateway e Conformidade arquitetural verificados item a item contra o escopo mínimo exigido pelo Founder. 4 riscos não bloqueantes registrados para o Technical Design. Nenhuma documentação redundante criada. Missão de revisão arquitetural, nenhum código alterado. Autorizado avançar ao Technical Design mediante aprovação explícita do Founder", done: true },
  { label: "Wave 4 Decision Proposal resolvida (D-074): src/workflows/pmo_workflow.py classificado como Historical Superseded Architecture (non-production, non-reference) -- não removido, mas não representa mais a arquitetura vigente. Aviso explícito adicionado ao arquivo, CLAUDE.md atualizado, busca global documentada (zero imports/rotas/testes/uso em produção), nenhuma reutilização para a Wave 4, gatilho de remoção futura registrado. Proibida a coexistência de duas arquiteturas de workflow. Missão documental, ruff limpo. Wave 4 Domain Blueprint autorizado a seguir para Architecture Review", done: true },
  { label: "Wave 4 Domain Blueprint produzido (D-073): levantamento obrigatório concluído -- 5 eventos reais hoje (todos em DomainService, sem envelope de observabilidade completo), 2 workflows manuais síncronos sem evento, zero precedente de fila/retry/dead-letter, achado crítico em src/workflows/pmo_workflow.py (registrado como Decision Proposal, não decidido). Modelo operacional proposto: Event Model/Contracts/Publisher/Dispatcher, Workflow Runtime mínimo, Execution Tracking, Retry/Dead Letter, Integration Gateway, Event Audit como extensão da auditoria de domínio. Aguarda decisão do Founder + Architecture Review antes de qualquer implementação", done: true },
  { label: "Harmonização do roadmap aprovada e concluída (D-072): Enterprise Analytics deixa de ser Wave própria e passa a capacidade transversal (Waves 4/5/6); Productization deixa de ser Wave própria e passa a compor o escopo da Wave 8 (distribuição, documentação, empacotamento, instalação, licenciamento, lançamento oficial). Nenhuma nova Wave criada. Mission Control confirmado como fonte oficial do roadmap. Autorizado o início do ciclo institucional da Wave 4 — Enterprise Operations", done: true },
  { label: "Roadmap oficial harmonizado em 8 Waves (D-071): Wave 3 renomeada para Enterprise Knowledge Platform; Enterprise Advisors (Wave 5) e Executive Intelligence (Wave 6) destacadas como Waves próprias; Enterprise Readiness (Wave 7) e STRATECH Enterprise v1.0 (Wave 8) introduzidas. Cada Wave declara suas dependências explícitas. Missão de governança -- nenhum código alterado. Ciclo institucional da Wave 4 autorizado a iniciar", done: true },
  { label: "Wave 3 (Enterprise Intelligence) oficialmente encerrada (D-070): Founder aprovou o Wave 3 Closure Review, confirmando os 5 elementos do relatório -- objetivos entregues, reclassificação explícita dos 7 Advisors restantes + Executive Intelligence, arquitetura validada por implementação/migração reais, débitos técnicos classificados, governança atualizada. Wave 4 autorizada, condicionada à harmonização da nomenclatura oficial da Wave antes do primeiro Domain Blueprint", done: true },
  { label: "Wave 3 Closure Review publicado (D-069): 5 elementos solicitados pelo Founder entregues -- objetivos planejados vs. entregues (7 Fases 100%; 7 Advisors restantes + Executive Intelligence/W3-8 deferidos por decisão explícita do Founder), validação das 5 principais decisões arquiteturais, 5 lições aprendidas, débitos técnicos remanescentes (TD-011/012/013, Technical Debt Register 100% classificado), recomendação formal de GO para a Wave 4. Encerramento formal da Wave 3 aguarda aprovação do Founder", done: true },
  { label: "Wave 3 Fase 4 concluída (D-068): Risk Advisor migrado para o AdvisorFramework -- validação ponta a ponta demonstrada (chunk_ids rastreáveis, no_evidence sem LLM, isolamento entre organizações) contra o Agent real; suíte pré-existente TestRiskAdvisor 100% verde sem alteração. pytest 494 passando, ruff limpo. Nenhuma capacidade nova criada -- decisão de encerramento da Wave 3 fica com o Founder", done: true },
  { label: "Wave 3 Fase 3 implementada (D-067): Enterprise Advisor Framework (Minimum Viable Framework) -- grounded na auditoria do Risk Advisor real; AdvisorContract + AdvisorFramework (contexto, RAG, LLM, auditoria, tratamento de falhas), sem migrar nenhum Advisor ainda. pytest 485 passando, ruff limpo. Proximo: Fase 4 (migracao do Risk Advisor -- valida o Framework ponta a ponta)", done: true },
  { label: "Wave 3 Fase 2 implementada (D-066): Enterprise Knowledge Platform (Knowledge Services) -- RagPipeline (ranking deterministico + rastreabilidade de fontes) e EnterpriseMemoryService (5 categorias) como servicos de plataforma puros, sem logica de Advisor. pytest 477 passando, ruff limpo. Proximo: Fase 3 (Enterprise Advisor Framework)", done: true },
  { label: "Wave 3 Fase 1 implementada (D-065): Enterprise Knowledge Platform (Foundation) -- KnowledgeRepository/PgVectorRepository/EmbeddingProvider funcionais e testados (pgvector), migracao 0016 aditiva, nenhum Advisor consumidor ainda. pytest 464 passando, ruff limpo. Proximo: Fase 2 (Knowledge Services -- Semantic Search, RAG Pipeline, Enterprise Memory Model)", done: true },
  { label: "AR-6 concluída (D-064): Architecture Review do Wave 3 Domain Blueprint aprovado sem ressalvas -- consistência com CLAUDE.md, diretrizes do Founder e consumidor real (Risk Advisor) validadas; 1 referência cruzada desatualizada corrigida. Wave 3 aguarda apenas aprovação explícita do Founder para iniciar a Fase 1", done: true },
  { label: "Wave 3 Domain Blueprint concluído (D-063): 2 Decision Proposals resolvidas (Vector Store pgvector; Framework de Orquestração Multiagente) + 8 entregáveis produzidos -- documento mestre (camadas unidirecionais Advisors -> Advisor Framework + Foundation -> Knowledge Platform -> Enterprise Domain), Blueprint da Knowledge Platform (13 sub-componentes), Blueprint do Enterprise Memory Model (checklist de colisão contra Executive Memory), Blueprint do Advisor Framework, Catálogo dos 8 Advisors (nenhum implementado), Blueprint de RAG Architecture, Integration Blueprint (10 domínios) e o Wave 3 Execution Plan (Fases 1-4 mandatórias, Gates entre elas). Nenhum Epic implementado nesta missão", done: true },
  { label: "Wave 2 Closure Review concluído (D-062): Wave 2 (Enterprise Platform) formalmente encerrada. Wave 2 Closure Report, Architecture Delta, Domain Evolution Report, Technical Debt Register 100% classificado, Governance Review (1 drift documental corrigido em DOMAIN-MODEL.md), Readiness Assessment e plano executivo da Wave 3 produzidos. 'Wave 3 Ready' declarado", done: true },
  { label: "Wave Completion Review retrospectivo, item 8 -- TD-008 Fase 3b, Etapa 4b concluída (destrutiva) e TD-008 RESOLVIDO (D-061): migração 0015 ativada (NOT NULL em project_id + DROP COLUMN project_name + campo removido do ORM); project_id é a única chave de acesso interno ao Project. Nome preservado como apresentação -- Project.name é a fonte, o campo project_name permanece nas responses derivado dela (zero regressão de frontend). Downgrade íntegro repopula project_name de projects.name via project_id, provado em PostgreSQL real. Suíte verde: ruff/pytest 449/tsc/eslint/vitest 491/E2E 292. Encerramento formal do TD-008", done: true },
  { label: "Wave Completion Review retrospectivo, item 8 -- Gate Final aprovado + TD-008 Fase 3b, Etapa 4a concluída (aditiva, reversível -- D-060): project_id é a única chave de escopo de leitura; resolvidos os resíduos R1-R6 (list_analyses id-only via resolve_scope_id; display de Project.name; dedup/agrupamento por id; responses e joins de frontend por project_id; save_analysis não grava a coluna). Migração destrutiva 0015 definida e encenada (head ativo segue 0014), upgrade/downgrade provados reversíveis em PostgreSQL real. ruff limpo, pytest 449 + teste 0015, tsc/eslint limpos, vitest 491, E2E 292. Etapa 4b (DROP COLUMN) bloqueada -- exige novo Gate + nova aprovação explícita", done: true },
  { label: "Wave Completion Review retrospectivo, item 8 -- TD-008 Fase 3b, Etapa 5 (frontend-only, sem tocar no banco) concluída (D-059): ProjectSummary eliminado, inteligência consolidada sobre a identidade do Project. ProjectSummary (dashboard) + WorkspaceSummary (workspace) -- dois espelhos duplicados -- unificados no tipo canônico ProjectIntelligenceSummary, ancorado em project_id; fusão com a entidade de Entrega (bounded context distinto) rejeitada. Backend inalterado; tsc/eslint limpos, vitest 486, E2E 292. Founder reordenou: Etapa 5 antes da Etapa 4 (destrutiva), com Gate Final entre elas -- Etapa 4 exige nova aprovação", done: true },
  { label: "Wave Completion Review retrospectivo, item 8 -- TD-008 Fase 3b, Etapa 3 (frontend-only, aditiva) concluída (D-058): consumidores usam project_id como chave primária (Project.name só exibição). Hook compartilhado useResolvedProjectId reaproveita a resolução do summary (deduplicada, sem resolução redundante); RisksPanel/CommunicationBrief/IntelligenceTimeline/AnalysisHistory/ActionsSection/ActionsContextLine enviam project_id; keepPreviousData evita flash na troca de chave; independência de painéis e reflexo pós-mutação preservados. project_name/ProjectSummary não removidos; vitest 486, E2E 292, backend inalterado. Etapas 4-5 pendentes; DROP COLUMN exige nova aprovação do Founder", done: true },
  { label: "Wave Completion Review retrospectivo, item 8 -- TD-008 Fase 3b, Etapa 2 (frontend-only, aditiva) concluída (D-057): consumidores de frontend dual-key -- as 4 rotas BFF de intelligence encaminham project_id; WorkspaceSummary + hooks escopados carregam project_id coexistindo com o nome; executive-brief reaproveita o project_id resolvido pelo summary como chave exata (fallback por nome enquanto carrega, independência de painéis preservada). Nenhum caminho removido; vitest 483, E2E 292, backend inalterado. Etapas 3-5 pendentes; DROP COLUMN exige nova aprovação do Founder", done: true },
  { label: "Wave Completion Review retrospectivo, item 8 -- TD-008 Fase 3b, Etapa 1 (aditiva) concluída (D-056): project_id vira chave de acesso ao Project sem remover nada; rotas de intelligence aceitam project_id além do nome, com validação dual-key (id inexistente/cross-org -> 404, id != nome -> 409); nome único vira filtro exato, nome nunca-analisado ainda retorna lista vazia; migração 0014 (backfill defensivo, sem NOT NULL). Etapas 2-5 pendentes; DROP COLUMN exige nova aprovação do Founder", done: true },
  { label: "Wave Completion Review retrospectivo, item 7: Workspace reclassificado como View/UI (D-055) -- não é entidade de domínio (sem identidade/ciclo de vida/invariantes); Governança Concluída, sem código -- criar a entidade seria arquitetura paralela sobre Program/Portfolio + RBAC", done: true },
  { label: "Wave Completion Review retrospectivo, item 6: Convites implementados (D-054), domínio desacoplado do e-mail -- Invitation com estados Pendente/Aceito/Expirado/Cancelado, aceitação pública sem sessão, entrega abstraída em NotificationProvider/NoOp (nenhum provedor SMTP/SES escolhido); painel /administracao/convites", done: true },
  { label: "Wave Completion Review retrospectivo, item 5: Sessões server-side implementadas (D-053, resolve TD-010) -- revogação real de sessão, session_id cunhado pelo backend, painel /administracao/sessoes", done: true },
  { label: "Wave Completion Review retrospectivo, item 4: Configurações da Organização (D-052) reclassificada como Sem Escopo Funcional Definido; Tenant/System Settings Pendente de Decisão de Negócio (Wave 6) -- Governança Concluída, sem código especulativo", done: true },
  { label: "Wave Completion Review retrospectivo, item 3: API Keys implementado (D-051) -- Blueprint corrigido (API Keys é Nível 1, não depende de Integration Hub), chave autentica como o usuário criador, RBAC/auditoria/Argon2 100% reaproveitados", done: true },
  { label: "Wave Completion Review retrospectivo, item 2: TD-004/005/006 resolvidos (D-050) -- race de invalidação do React Query corrigida nos 3 hooks de mutação de Analisar Projeto", done: true },
  { label: "Wave Completion Review retrospectivo, item 1: Event Foundation (Wave 1) implementado -- EventEmitter Protocol + NoOpEventEmitter, 5 eventos de domínio emitidos por DomainService; Wave 1 fechada", done: true },
  { label: "Superseding Decision: nova Wave Completion Policy oficial e permanente -- revoga adiamento de Epics/Enterprise Analysts previstos; Wave Completion Review retrospectivo (Waves 1-3) aberto", done: true },
  { label: "Wave 3, Epic W3-2 redefinido e implementado: Digital PMO Intelligence Foundation -- infraestrutura de IA compartilhada; Risk Advisor migrado, contrato HTTP inalterado", done: true },
  { label: "Wave 3, Epic W3-3: Risk Advisor implementado -- primeiro Enterprise Agent conversacional, somente leitura, sem entidade/migração/provider novos", done: true },
  { label: "Security Hardening Gate concluído: C-1 (RBAC nas 8 rotas de intelligence.py) e C-2 (organization_id em AnalysisRecord, migração 0010) fechados -- Risk Advisor liberado para retomar a Implementação", done: true },
  { label: "Baseline oficial consolidada: PR #45 mergeado na main (d8ff04d), todos os checks essenciais revalidados; Security Hardening Gate (C-1/C-2) autorizado em seguida", done: true },
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
  /** Wave codes this Wave depends on (D-071 -- explicit roadmap dependency map, Founder recommendation). */
  dependsOn: string[];
}

/**
 * Enterprise Master Execution Program (docs/product/ENTERPRISE-MASTER-EXECUTION-PROGRAM.md)
 * -- the single active planning axis from this mission forward. Every Épico
 * and every Capability below (PROGRAM_PHASES, CAPABILITY_PROGRESS) is a
 * historical label reclassified into exactly one Wave; neither is a
 * parallel evolution track anymore (Decision Log D-030).
 *
 * Official 8-Wave roadmap harmonized by the Founder in D-071 ("Founder
 * Decision -- Wave 4 Authorization"), superseding the earlier 6-Wave
 * structure: the Enterprise Advisors and Executive Intelligence, previously
 * conceived as part of Wave 3, are now their own Waves (5 and 6). Historical
 * documents published under the earlier structure (WAVE-3-DOMAIN-BLUEPRINT.md,
 * WAVE-3-EXECUTION-PLAN.md, ENTERPRISE-MASTER-EXECUTION-PROGRAM.md §2/§5/§7/§8)
 * are preserved unrewritten as point-in-time record; this array is the current,
 * authoritative roadmap.
 */
export const ENTERPRISE_PROGRAM_WAVES: WaveEntry[] = [
  {
    code: "Wave 1",
    name: "Enterprise Foundation",
    status: "Done",
    dependsOn: [],
    detail: "Schema + Identity 100% (Épicos 1-2). Persistence (Sprint 1), API Foundation (Sprint 2), RBAC seam (Sprint 3, migração 0006 + SqlPermissionChecker) e Event Foundation (D-049 -- EventEmitter Protocol + NoOpEventEmitter, 5 eventos emitidos por DomainService) implementados. Fechada pelo Wave Completion Review retrospectivo (D-048/D-049).",
  },
  {
    code: "Wave 2",
    name: "Enterprise Platform",
    status: "Done",
    dependsOn: ["Wave 1"],
    detail: "Wave 2 formalmente encerrada (D-062, Wave 2 Closure Review). Enterprise Domain completo de ponta a ponta (Sprints 1-2-5), RBAC fino (Sprint 3), Administration completo com User Management (Sprint 4 Nível 1+2 + Capability User Management -- D-038), API Keys (D-051), Sessões server-side (D-053, resolve TD-010), Convites (D-054 -- domínio desacoplado do e-mail, entrega em NotificationProvider/NoOp) e TD-008 Fase 3b completa (D-056 a D-061 -- project_id é a única chave de acesso ao Project, coluna project_name removida). Workspace reclassificado como View/UI (D-055) e Tenant/System Settings como Business Pending (D-052) -- ambos Governança Concluída, todos os 8 itens do Wave Completion Review retrospectivo fechados (ver WAVE-2-CLOSURE-REPORT.md). Nenhum bloqueador para a Wave 3 -- \"Wave 3 Ready\" declarado.",
  },
  {
    code: "Wave 3",
    name: "Enterprise Knowledge Platform",
    status: "Done",
    dependsOn: ["Wave 1", "Wave 2"],
    detail: "Wave 3 formalmente encerrada (D-070, aprovação do Founder ao Wave 3 Closure Review) e renomeada de \"Enterprise Intelligence\" para \"Enterprise Knowledge Platform\" (D-071 -- o nome agora reflete o que foi de fato entregue). W3-1 (D-040), W3-2 Digital PMO Intelligence Foundation (D-041/D-047) e W3-3 Risk Advisor (D-046/D-047) concluídos; Security Hardening Gate (C-1/C-2) concluído (D-045). As 2 Decision Proposals pendentes (Vector Store, Framework de Orquestração) foram resolvidas, o Wave 3 Domain Blueprint (8 entregáveis, D-063) e a AR-6 (D-064) concluídos. Fase 1 (Foundation, D-065), Fase 2 (Knowledge Services, D-066), Fase 3 (Enterprise Advisor Framework, D-067) e Fase 4 (migração do Risk Advisor, D-068) implementadas e testadas -- o Advisor Framework está validado arquiteturalmente em produção de código real (D-069, Wave 3 Closure Review). Os 7 Enterprise Advisors restantes e a Executive Intelligence, antes W3-7b/W3-8, agora são Waves próprias (5 e 6 -- D-071), não mais parte do escopo desta Wave.",
  },
  {
    code: "Wave 4",
    name: "Enterprise Operations",
    status: "In Progress",
    dependsOn: ["Wave 1", "Wave 2", "Wave 3"],
    detail: "Corresponde às Releases 0.4/0.5 já aprovadas (Integration Hub, Event Orchestration). Founder autorizou o início da Wave 4 (D-070); nomenclatura oficial do roadmap harmonizada (D-071) e aprovada/concluída (D-072). Founder Kickoff formal (D-073): Domain Blueprint produzido. Decision Proposal resolvida (D-074): `pmo_workflow.py` classificado como Historical Superseded Architecture. AR-7 (D-075): Architecture Review concluída, veredito GO. AR-7 aprovada pelo Founder (D-076): Technical Design produzido. Epic W4-1 implementado (D-077) e Executive Review aprovada, GO (D-078): migração atômica de `EventEmitter`/`NoOpEventEmitter` para `EventPublisher`/`InProcessEventPublisher` + `EventDispatcher`, `DomainEvent` (envelope único), migração 0018, Retry/Dead Letter mínimo, `correlation_id` reusando `RequestIDMiddleware`/`request_id_var`. **Wave 4 Epic Replanning (D-079):** Epic W4-2 dissolvido -- Event Dispatcher/Event Audit/Retry-Dead Letter reclassificados como concluídos no W4-1; Event Metrics **Deferred — Awaiting First Consumer**; W4-3 promovido a próximo Epic. **Epic W4-3 implementado (D-080):** `document.indexed` (`KnowledgeRepository.index()`) e `invitation.created` (`AdministrationService.create_invitation()`) conectados ao padrão de Event Publisher/Envelope/correlation_id do W4-1 -- implementação direta autorizada pelo Founder, sem Technical Design específico, apenas uma Implementation Note no Technical Design existente (§11). Payloads estritos, eventos só publicados após sucesso da operação principal, compatibilidade funcional confirmada. **Technical Design do Epic W4-4 produzido (D-081):** Workflow Runtime + Execution Tracking -- escopo confirmado (`document.indexed` → `WorkflowRuntime` → Execution Tracking, um único passo, sem métrica); `EventDispatcher` permanece agnóstico e byte-a-byte inalterado (princípio arquitetural fixado pelo Founder); `WorkflowRuntime` é o único dono dos estados `running`/`completed`/`failed`; política de idempotência definida (chave `event_id`+`workflow_name`). Missão documental, nenhum código escrito. **GO para a implementação, aguardando aprovação explícita do Founder ao Technical Design.** Enterprise Analytics (D-072) é uma capacidade transversal construída ao longo desta Wave e das Waves 5/6, não uma Wave própria.",
  },
  {
    code: "Wave 5",
    name: "Enterprise Advisors",
    status: "Not Started",
    dependsOn: ["Wave 3", "Wave 4"],
    detail: "Os 7 Enterprise Advisors restantes (Executive, Strategy, PMO, Portfolio, Delivery, Governance, Document -- `ENTERPRISE-ADVISOR-CATALOG.md`), destacados formalmente da Wave 3 em D-071. Infraestrutura já pronta e validada em produção real (Wave 3): `KnowledgeRepository`/`RagPipeline`/`EnterpriseMemoryService`/`AdvisorFramework`. Nenhum dos 7 Advisors implementado ainda -- cada um exige seu próprio Domain Blueprint, seguindo o mesmo padrão de auditoria-antes-de-abstração usado na migração do Risk Advisor. Enterprise Analytics (D-072) é uma capacidade transversal construída ao longo desta Wave e das Waves 4/6, não uma Wave própria.",
  },
  {
    code: "Wave 6",
    name: "Executive Intelligence",
    status: "Not Started",
    dependsOn: ["Wave 3", "Wave 4", "Wave 5"],
    detail: "Executive Intelligence (antes W3-8), destacada formalmente da Wave 3 em D-071 -- consome os 8 Enterprise Advisors (Wave 5) e a Knowledge Platform (Wave 3) sobre Portfolio/Program/Project (`WAVE-3-INTEGRATION-BLUEPRINT.md` §5/§11). Não implementada -- depende estruturalmente da Wave 5 estar completa. Enterprise Analytics (D-072) é uma capacidade transversal construída ao longo das Waves 4/5 e desta, não uma Wave própria.",
  },
  {
    code: "Wave 7",
    name: "Enterprise Readiness",
    status: "Not Started",
    dependsOn: ["Wave 1", "Wave 2", "Wave 3", "Wave 4", "Wave 5", "Wave 6"],
    detail: "Wave inteiramente nova, introduzida em D-071 -- sem escopo definido ainda. Exige seu próprio Domain Blueprint e Architecture Review antes de qualquer Technical Design, mesmo padrão institucional já em uso em todas as Waves anteriores.",
  },
  {
    code: "Wave 8",
    name: "STRATECH Enterprise v1.0",
    status: "Not Started",
    dependsOn: ["Wave 1", "Wave 2", "Wave 3", "Wave 4", "Wave 5", "Wave 6", "Wave 7"],
    detail: "Wave inteiramente nova, introduzida em D-071 -- escopo definido em D-072: inclui Productization (deixou de ser Wave própria) -- preparação para distribuição, documentação, empacotamento, instalação, licenciamento e lançamento oficial da STRATECH Enterprise v1.0. Exige seu próprio Domain Blueprint e Architecture Review antes de qualquer Technical Design.",
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
    note: "Cadeia completa banco → API → BFF → página (Sprint 5); Fase 3a do TD-008 concluída (Wave 3, D-040). Fase 3b em execução (item 8 do Wave Completion Review retrospectivo): Etapas 1-3 (dual-key), Etapa 5 (ProjectSummary eliminado → ProjectIntelligenceSummary) e Etapa 4a (project_id é a única chave de escopo de leitura; resíduos R1-R6 resolvidos; save_analysis não grava mais a coluna) concluídas -- Gate Final aprovado (D-060); falta só a Etapa 4b destrutiva (ativar a migração 0015: NOT NULL + DROP COLUMN), bloqueada, sob novo Gate + nova aprovação do Founder",
  },
  { name: "Demand", status: "Not Started" },
  { name: "Risk", status: "Not Started" },
  { name: "Decision", status: "Not Started" },
  { name: "Action", status: "Not Started" },
  { name: "Knowledge", status: "Not Started" },
];
