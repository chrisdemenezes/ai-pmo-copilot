# Wave 4 Domain Blueprint — Enterprise Operations

**Status:** documento mestre da Wave 4. Produzido em resposta a "Founder Kickoff — Wave 4 / Enterprise Operations". Nenhum Epic é implementado por este documento — apenas o levantamento obrigatório e o modelo operacional que nasce dele, per mandato explícito do Founder ("O modelo operacional deverá nascer desse levantamento. Nunca do contrário.").
**Precondição cumprida:** Wave 3 oficialmente encerrada (D-070); roadmap harmonizado em 8 Waves (D-071/D-072); nenhuma pendência estrutural de roadmap.

---

## 0. Mandato do Founder (referência condensada, não reescrita)

- **Missão:** construir infraestrutura operacional Enterprise reutilizável — eventos, processos, integrações — não Advisors, não Knowledge Platform.
- **7 princípios mandatórios:** Event First; Domain Events (fatos, nunca comandos/intenções/decisões); Workflow ≠ Business Logic; Integrações desacopladas (contratos, nunca implementações concretas); Observabilidade nativa (Event ID, Correlation ID, Timestamp, Tenant, Origin, Payload Version); Auditoria permanece responsabilidade própria (eventos não a substituem); Sem arquitetura paralela (nenhum Event Registry genérico/Plugin Engine/Dynamic Bus/Workflow DSL/Generic Automation Engine sem consumidor real).
- **Grounding obrigatório antes do primeiro Blueprint** — Seção 1 abaixo.
- **Escopo permitido:** Event Model, Event Contracts, Event Publisher, Event Dispatcher, Workflow Runtime, Workflow Context, Execution Tracking, Retry Policies, Dead Letter Strategy, Integration Contracts, Integration Gateway, Event Audit, Event Metrics.
- **Escopo proibido:** Enterprise Advisors, Executive Intelligence, Analytics/BI/Dashboards, Multi-Agent Systems, Agent Routing, Plugin Marketplace, Generic Automation Studio, BPM completo, Low-Code Engine, Workflow Designer visual.
- **Success Metric do Founder:** um evento novo atravessa toda a plataforma — publicação, propagação, execução de um workflow simples, auditoria — sem exigir alteração estrutural em módulos existentes.

---

## 1. Levantamento obrigatório (Grounding Audit)

Auditoria direta do código-fonte, não de documentação aspiracional. Cada achado abaixo cita o arquivo real.

### 1.1 Eventos que já existem implicitamente em código

Busca exaustiva por `.emit(` em `src/` encontra **exatamente 5 sítios de emissão real**, todos em `src/services/domain_service.py`:

| Evento | Emitido por | Payload atual |
|---|---|---|
| `portfolio.created` | `DomainService.create_portfolio` | `{"portfolio_id": ...}` |
| `program.created` | `DomainService.create_program` | `{"program_id": ..., "portfolio_id": ...}` |
| `program.linked_to_portfolio` | `DomainService.create_program` | idem |
| `project_delivery.created` | `DomainService.create_project` | `{"project_id": ..., "program_id": ...}` |
| `project_delivery.linked_to_program` | `DomainService.create_project` | idem |

Todos os 5 passam por `EventEmitter` (Protocol, `src/services/events/interfaces.py`) → `NoOpEventEmitter` (`src/services/events/noop_emitter.py`, apenas `logger.info`, Wave 1/D-049). **Nenhum tem Event ID, Correlation ID, Timestamp explícito, Tenant como campo nomeado (apenas `organization_id` posicional), Origin ou Payload Version** — a lacuna exata que o Princípio 5 do Founder (Observabilidade nativa) exige corrigir.

`docs/product/stratech-v2/Event-Map.html` (taxonomia de referência, não código) lista adicionalmente `user.invited`, `role.granted`, `project.created`, `risk.raised`, `decision.pending`, `sync.completed`/`sync.failed`, `document.linked`/`document.expiring`, `process.deviation_detected`, `analysis.completed`, `recommendation.pending_validation`, `action.approved`/`action.rejected` — **nenhum destes tem um `.emit()` real em código hoje**. São aspiracionais desde a era V1/V2 inicial, antes de qualquer Knowledge Platform ou Advisor Framework existir. Não são grounding para esta Wave — são candidatos futuros, a serem emitidos apenas quando um consumidor real e um produtor real existirem simultaneamente (mesma disciplina de "nenhuma abstração sem consumidor real" já aplicada a toda a Wave 3).

### 1.2 Operações que já executam "workflows" manuais (sequências de passos, hoje só em código síncrono)

| Sequência | Local | Passos | Observação |
|---|---|---|---|
| Resposta de um Advisor | `AdvisorFramework.run()` (`src/services/advisor_framework/framework.py`) | audita pergunta → checa evidência → (gate: sem evidência) → chama Advisor → valida saída → constrói recomendação → explica | **Pertence ao domínio do Advisor Framework, não é candidato ao Workflow Runtime desta Wave** — é orquestração de domínio (Fase 3, Founder: "Framework executa exatamente um Advisor por chamada"), nunca deve ser absorvida ou substituída por infraestrutura operacional genérica. Citado aqui só para demarcar a fronteira, não como escopo. |
| Ingestão de documento | `KnowledgeRepository.ingest()` → `KnowledgeRepository.index()` (`src/services/knowledge_platform/knowledge_repository.py`) | criar/encontrar `Document` → criar `DocumentVersion` → (chamada separada, manual) → chunk → embed cada chunk → persistir `Chunk`s | Duas chamadas hoje **exigem que o caller sequencie manualmente** `ingest()` depois `index()` — nenhum evento emitido em nenhuma das duas etapas. Nenhum consumidor real ainda (TD-012: nenhum Advisor ingere documento binário real hoje). |
| Criação de convite | `AdministrationService.create_invitation()` (`src/services/administration_service.py:311`) | gerar token → hash → criar registro → notificar via `NotificationProvider` (hoje `NoOpNotificationProvider`) | Síncrono, in-process, sem evento emitido (`EventEmitter` não é injetado em `AdministrationService` hoje — usado apenas por `DomainService`). |
| Criação de Program/Project | `DomainService.create_program`/`create_project` | validar pai existe/pertence à organização → escrever → registrar auditoria → emitir 2 eventos | Já é o único fluxo com emissão real (§1.1) — modelo de referência para os demais. |

### 1.3 Integrações atualmente síncronas

Toda integração cross-module hoje é uma chamada de método direta, in-process, no mesmo processo Python/mesma transação de banco — nunca através de fila, broker ou processo separado:

- `RiskAdvisorAgent` → `AdvisorFramework` → `RagPipeline` → `KnowledgeRepository` → `PgVectorRepository`/`EmbeddingProvider` (Fase 4, validado ponta a ponta).
- `AdministrationService` → `NotificationProvider` (Protocol) → `NoOpNotificationProvider` (concreto).
- `DomainService`/rotas de intelligence → `AnalysisRepository`/`AdministrationRepository.record_audit` (auditoria síncrona, na mesma escrita).
- Rotas de `intelligence.py` (análises, Risk Advisor) **nunca emitem nenhum evento hoje** — nenhuma chamada a `EventEmitter` existe em `src/api/routes/intelligence.py`. Gap real e concreto: uma análise submetida, um risco identificado, uma decisão registrada são fatos de domínio que hoje não produzem nenhum evento.

**Já decoupladas via contrato (Protocol), não implementação concreta — padrão a reaproveitar, não recriar:** `EventEmitter`/`NoOpEventEmitter` (D-049), `NotificationProvider`/`NoOpNotificationProvider` (D-054), `EmbeddingProvider`/`MockEmbeddingProvider` (D-065), `LLMProvider` (factory-selecionado), `PermissionChecker`/`SqlPermissionChecker`, `CredentialVerifier`/`IdentityResolver`. Todo esse conjunto já cumpre o Princípio 4 do Founder ("Integrações desacopladas... sempre depender de contratos") — nada disso precisa ser reconstruído pela Wave 4, apenas reaproveitado como referência de estilo.

### 1.4 Infraestrutura de execução assíncrona/confiabilidade — busca por precedente

Busca exaustiva por `asyncio`, filas, `Celery`/`RQ`, `BackgroundTasks`, retry, dead-letter em todo `src/`: **zero resultados**. Não existe hoje nenhum mecanismo de processamento assíncrono, fila, retry ou dead-letter em nenhuma parte da STRATECH. A Wave 4 constrói esses três conceitos (Retry Policies, Dead Letter Strategy, execução assíncrona) inteiramente do zero — sem nenhum precedente a migrar, e sem nenhum consumidor real hoje que exija mais do que o mínimo absoluto (nenhum SLA de latência documentado, nenhum volume de eventos que justifique um broker externo).

### 1.5 Achado crítico — `src/workflows/pmo_workflow.py` e `05-ai-orchestration-design.md`

CLAUDE.md já nomeia `workflows/` como parte da arquitetura oficial (`src/{api,agents,database,llm,prompts,services,workflows}/`). O diretório já existe e já contém código:

```python
# src/workflows/pmo_workflow.py
class PMOWorkflow:
    def execute(self, document, ai, repository):
        return repository.save(ai.process(document))
```

Com o comentário explícito no próprio arquivo: *"Reservado intencionalmente para a próxima fase do projeto (orquestração multi-agente, conforme architecture/05-ai-orchestration-design.md). Ainda não conectado ao MVP atual. Não remover nem tratar como órfão em futuras reavaliações de débito técnico."*

`docs/architecture/05-ai-orchestration-design.md` é um documento de 26 linhas, era pré-V2 (antes de qualquer Domain Blueprint desta STRATECH existir), descrevendo um `Orchestrator` genérico que "recebe requisições, seleciona agentes, controla fluxo de execução" — exatamente o padrão de **roteamento autônomo entre agentes** que o Founder rejeitou explicitamente na Fase 3 do Advisor Framework ("nenhum roteamento autônomo, nenhuma delegação entre Advisors, nenhum multiagente") e rejeita de novo nesta Wave 4 ("Multi-Agent Systems, Agent Routing... pertencem a Waves futuras" — na verdade, nem futuras: a disciplina desde a Fase 3 é não construir isso sem consumidor real).

**Dois problemas concretos que este achado expõe:**
1. `PMOWorkflow.execute()` mistura orquestração com lógica de negócio na mesma linha (`ai.process(document)` é uma decisão de domínio, não uma etapa de infraestrutura) — viola diretamente o Princípio 3 desta própria Wave ("Workflow ≠ Business Logic. O motor de workflow jamais poderá conter regras de negócio.").
2. Se a Wave 4 criar um novo `WorkflowRuntime` em qualquer outro diretório, coexistindo com `PMOWorkflow` não resolvido no mesmo `src/workflows/`, isso é literalmente **duas arquiteturas de workflow paralelas** — a violação mais básica que CLAUDE.md proíbe.

**Este achado não é decidido silenciosamente aqui** — vai para a Seção 8 (Decision Proposal) porque envolve uma instrução explícita anterior ("não remover") que não pode ser revogada sem confirmação do Founder.

### 1.6 Processos que realmente necessitam desacoplamento hoje

Com base em 1.1–1.5, apenas três pontos têm um gap real e concreto (produtor existe, consumidor futuro plausível, mas nenhum evento é emitido hoje):

1. **Criação de Portfolio/Program/Project** — já emite, mas sem envelope de observabilidade completo (Event ID/Correlation ID/Timestamp/Origin/Payload Version).
2. **Indexação de documento na Knowledge Platform** — `ingest()`→`index()` não emite nada; um `document.indexed` seria o primeiro evento real de uma Wave futura (Document Advisor, Wave 5) sem exigir mudança estrutural quando esse consumidor existir.
3. **Criação de convite (Administration)** — não emite nada; um `invitation.created` seria o análogo ao que `DomainService` já faz, estendendo a mesma disciplina à Administration.

Nenhum outro ponto do código hoje tem um produtor real E um consumidor plausível simultaneamente — construir eventos para qualquer outro caso seria abstração sem consumidor real, exatamente o que o Princípio 7 do Founder proíbe.

---

## 2. Modelo operacional proposto (nasce integralmente da Seção 1)

### 2.1 Event Model — envelope único

Todo evento passa a ter um envelope padrão, resolvendo a lacuna de observabilidade encontrada em 1.1:

```python
@dataclass(frozen=True)
class DomainEvent:
    event_id: str            # UUID, cunhado no Publisher
    event_type: str           # "portfolio.created" -- mesma convenção já em uso, aditiva
    correlation_id: str       # propagado por toda a cadeia de um mesmo pedido/workflow
    timestamp: datetime       # UTC, no momento da publicação
    organization_id: int      # "Tenant" do mandato do Founder -- reaproveita o campo já usado em toda a STRATECH desde o Épico 1, nunca um novo conceito de tenant
    origin: str                # módulo/serviço produtor, ex. "domain_service"
    payload_version: int      # inicia em 1, incrementado só em mudança de forma do payload
    payload: dict
```

`organization_id` é reaproveitado como o "Tenant" do mandato — nenhum novo conceito de tenant é introduzido, mesma disciplina de reuso já aplicada em toda a Wave 2/3.

### 2.2 Event Contracts — primeiro lote real (grounded, não especulativo)

Apenas os eventos identificados em 1.6 como tendo produtor real ganham um contrato tipado nesta Wave:

| Contrato | Extensão de | Payload |
|---|---|---|
| `PortfolioCreated`/`ProgramCreated`/`ProgramLinkedToPortfolio`/`ProjectDeliveryCreated`/`ProjectDeliveryLinkedToProgram` | Os 5 já emitidos por `DomainService` | Mesmo payload de hoje, envelopado |
| `DocumentIndexed` | `KnowledgeRepository.index()` | `{document_id, version_id, chunk_count}` |
| `InvitationCreated` | `AdministrationService.create_invitation()` | `{invitation_id, email, role_name}` (nunca o token) |

Nenhum outro contrato é criado nesta Wave — nenhum `RiskIdentified`/`DecisionRegistered`/`AnalysisSubmitted` (exemplos do próprio Founder) é implementado ainda, porque nenhum deles tem hoje um produtor **e** um consumidor real simultâneos; ficam registrados como candidatos de Wave futura (Wave 5, quando os Advisors existirem e precisarem consumir/produzir esses fatos).

### 2.3 Event Publisher

Substitui `EventEmitter.emit(event_name, payload, organization_id)` por uma interface que cunha o envelope completo, mantendo assinatura aditiva (retrocompatível com o único consumidor real hoje, `DomainService`):

```python
class EventPublisher(Protocol):
    def publish(self, event_type: str, payload: dict, organization_id: int, correlation_id: str, origin: str) -> DomainEvent: ...
```

`NoOpEventEmitter` é promovido a um publisher real que persiste o envelope (ver 2.6, Execution Tracking/Event Audit) e o repassa ao Dispatcher — nenhuma mudança de assinatura nos 5 call sites existentes além de prover `correlation_id`/`origin`.

### 2.4 Event Dispatcher

Pub/sub **in-process** — nenhum broker externo, nenhuma fila distribuída, per Princípio 7 (sem infraestrutura sem consumidor real; hoje não há volume nem SLA que justifique um broker). Mantém uma tabela `event_type -> [handlers]` registrada em processo; a promoção para um broker real (Kafka/SQS/etc.) fica para quando um consumidor cross-processo existir — mesma disciplina "seam agora, mecanismo depois" já usada por `NoOpEventEmitter`/`NoOpNotificationProvider`.

### 2.5 Workflow Runtime + Workflow Context

Um executor mínimo de sequência de passos, cada passo uma função pura `(WorkflowContext) -> WorkflowContext`, nunca contendo regra de negócio (Princípio 3) — apenas orquestra a ordem e captura o resultado/erro de cada passo. `WorkflowContext` carrega o `correlation_id` (o mesmo que os eventos publicados durante a execução do workflow), permitindo reconstruir toda a cadeia publicação→propagação→execução→auditoria de um único evento (o Success Metric do Founder).

**Não substitui `AdvisorFramework.run()`** (1.2) — o primeiro consumidor real do Workflow Runtime é um workflow de infraestrutura simples (ex.: "ao receber `document.indexed`, registrar métrica + auditoria"), nunca a lógica de um Advisor.

### 2.6 Execution Tracking

Uma tabela `workflow_executions` (organization_id, correlation_id, workflow_name, status, started_at, finished_at, error) registra cada execução — a base mínima para provar o Success Metric do Founder sem construir um dashboard (proibido pelo escopo).

### 2.7 Retry Policies + Dead Letter Strategy

Dado o achado de 1.4 (zero precedente, zero consumidor com requisito de confiabilidade hoje), a política inicial é deliberadamente mínima: `max_attempts` fixo + backoff simples (sem biblioteca externa), e uma tabela `dead_letter_events` para eventos que esgotam as tentativas — nunca descartados silenciosamente. Nenhuma fila de retry distribuída; suficiente para o único caso de uso comprovado (falha transiente de indexação/notificação).

### 2.8 Integration Contracts + Integration Gateway

`Integration Gateway` é uma fachada única (mesmo padrão de `KnowledgeRepository` como fachada única da Knowledge Platform) sobre `Integration Contracts` (Protocols) — reaproveitando o padrão já provado por `NotificationProvider`/`EmbeddingProvider`, não uma abstração nova. Nenhuma integração concreta (SMTP, SES, sistema externo) é escolhida nesta Wave — os contratos existem, a implementação concreta permanece um `NoOp`, exatamente como `NotificationProvider` hoje.

### 2.9 Event Audit — extensão, nunca substituição (Princípio 6)

Eventos **não substituem** `AdministrationRepository.record_audit`/`AIFoundationAudit.record_question` — ambos continuam existindo exatamente como hoje. `Event Audit` é apenas o registro do próprio evento (envelope completo) na tabela de execução (2.6), para que a cadeia publicação→propagação→execução seja rastreável — uma auditoria de *infraestrutura*, complementar, nunca substituta da auditoria de *domínio* já estabelecida.

### 2.10 Event Metrics

Contadores/durações mínimos (nº de eventos publicados por tipo, duração de execução de workflow) — dado bruto apenas, nunca um dashboard, painel ou visualização (Analytics/BI/Dashboards estão no escopo proibido desta Wave).

---

## 3. Bounded Context e camadas

```
┌─────────────────────────────────────────────────────────────────┐
│ Enterprise Domain / Knowledge Platform / Advisor Framework        │
│ (Waves 1-3, existentes -- produtores e futuros consumidores)     │
└───────────────┬───────────────────────────────────────────────────┘
                │ publica eventos via EventPublisher
┌───────────────▼───────────────────────────────────────────────────┐
│ Enterprise Operations (Wave 4, este Blueprint)                    │
│  Event Publisher → Event Dispatcher → Workflow Runtime            │
│  Execution Tracking · Retry/Dead Letter · Event Audit · Metrics   │
│  Integration Gateway (Integration Contracts)                      │
└───────────────┬───────────────────────────────────────────────────┘
                │ consumido por (Wave futura)
┌───────────────▼───────────────────────────────────────────────────┐
│ Enterprise Advisors (Wave 5) / Executive Intelligence (Wave 6)    │
└─────────────────────────────────────────────────────────────────────┘
```

**Nenhuma seta sobe.** Enterprise Operations nunca conhece o conceito de "Advisor" ou "Portfolio" especificamente — apenas processa envelopes de evento genéricos, mesma disciplina de camada já usada pela Knowledge Platform (Wave 3) em relação ao Enterprise Domain.

---

## 4. Primeiro(s) consumidor(es) real(is) — prova de grounding-before-abstraction

1. **Migração dos 5 `emit()` existentes** (`DomainService`) para o novo `EventPublisher`/envelope — o único produtor real hoje, prova a infraestrutura sem inventar um cenário hipotético.
2. **`document.indexed`** emitido por `KnowledgeRepository.index()` — fecha o gap de 1.6 item 2; nenhum consumidor real ainda, mas o evento em si tem produtor real, disponível para a Wave 5 (Document Advisor) sem exigir mudança estrutural quando esse consumidor existir (prova direta do Success Metric do Founder).
3. **`invitation.created`** emitido por `AdministrationService.create_invitation()` — fecha o gap de 1.6 item 3, estendendo a mesma disciplina de `DomainService` à Administration.
4. **Um Workflow Runtime de exemplo mínimo**: ao publicar `document.indexed`, um workflow de um único passo registra a execução (2.6) e uma métrica (2.10) — a prova ponta a ponta exigida pelo Success Metric ("publicação, propagação, execução de um workflow simples e auditoria").

Nenhum destes exige alteração estrutural em `DomainService`, `KnowledgeRepository` ou `AdministrationService` além de injetar o novo `EventPublisher` no lugar exato onde `EventEmitter` já era chamado (ou, para os dois novos casos, no ponto onde a operação já termina hoje) — confirmando o próprio critério de sucesso do Founder antes mesmo da implementação começar.

---

## 5. Restrições de sobre-engenharia (checklist explícito)

| Proibido pelo Founder | Confirmação nesta Wave |
|---|---|
| Enterprise Advisors | Não implementado — nenhum Advisor novo, nenhuma mudança em `RiskAdvisorAgent` |
| Executive Intelligence | Não implementado — permanece Wave 6 |
| Analytics/BI/Dashboards | Event Metrics (2.10) é dado bruto, nunca visualização |
| Multi-Agent Systems / Agent Routing | Confirmado ausente — achado de 1.5 (`PMOWorkflow`/orchestration design) é tratado como Decision Proposal (Seção 8), nunca reimplementado |
| Plugin Marketplace / Generic Automation Studio | Nenhum plugin engine, nenhum marketplace — Integration Gateway é uma fachada fixa, não uma superfície de plugins |
| BPM completo / Low-Code Engine / Workflow Designer visual | Workflow Runtime (2.5) é um executor de sequência fixa de passos Python, nunca uma DSL, nunca um designer visual |
| Event Registry genérico / Dynamic Bus | Event Dispatcher (2.4) é um pub/sub in-process fixo, nunca um registry dinâmico de tipos desconhecidos |

---

## 6. Decision Proposal — destino de `src/workflows/pmo_workflow.py` e `05-ai-orchestration-design.md`

**Achado (Seção 1.5):** código legado, nunca conectado ao MVP, com instrução explícita anterior de não remover, descrevendo um padrão de orquestração multi-agente que o Founder rejeitou explicitamente (Fase 3 do Advisor Framework, e de novo nesta própria Wave 4). O arquivo mistura workflow com lógica de negócio, violando o Princípio 3 desta Wave. Construir o novo Workflow Runtime em qualquer lugar que não seja `src/workflows/` — o diretório que o próprio CLAUDE.md já reserva oficialmente — arriscaria uma segunda arquitetura de workflow paralela.

**Opções:**

| Opção | Descrição | Impacto |
|---|---|---|
| **A — Reclassificar como superado, sem remover o arquivo** | `PMOWorkflow` permanece no disco (respeitando a instrução original de não remover), mas é formalmente marcado como superado por este Blueprint no Decision Log/Technical Debt — o novo `WorkflowRuntime` desta Wave nasce em `src/workflows/`, coexistindo apenas como registro histórico, nunca estendido ou referenciado pelo código novo |
| **B — Remover o arquivo e o design doc** | Apagaria o código e o documento — contradiz a instrução original explícita de não remover, sem uma nova autorização do Founder que a revogue |
| **C — Manter intocado e construir o Workflow Runtime em outro diretório** | Preserva o status quo, mas cria exatamente o risco de arquitetura paralela que o achado descreve |

**Recomendação deste documento:** Opção A. Nenhuma das 3 é aplicada unilateralmente — decisão do Founder antes da Architecture Review.

### 6.1 Decisão do Founder (2026-07-27, D-074 — "Founder Decision: Wave 4 Decision Proposal — pmo_workflow.py")

**Aprovada a Opção A**, com classificação formal: **Historical Superseded Architecture — non-production, non-reference implementation**. O arquivo não é removido nesta missão (valor de rastreabilidade histórica, referências no CLAUDE.md), mas não pode mais ser interpretado como arquitetura oficial, componente futuro, ou base válida para a Wave 4.

**Ações executadas em resposta às 6 diretrizes obrigatórias do Founder:**

1. **Aviso explícito adicionado ao topo de `src/workflows/pmo_workflow.py`** — declara a classificação Historical Superseded Architecture; que o arquivo não deve ser importado/estendido/usado; que a orquestração de Advisors foi substituída pelo `AdvisorFramework`; que a orquestração operacional é responsabilidade do Workflow Runtime desta Wave; que é preservado apenas por rastreabilidade histórica. O texto histórico original do docstring foi preservado abaixo do novo aviso, não substituído.
2. **`CLAUDE.md` atualizado** — nota adicionada imediatamente após a árvore de "Arquitetura oficial", esclarecendo que `workflows/` é reservado para o Workflow Runtime da Wave 4 (não para orquestração multiagente) e que `pmo_workflow.py` é Historical Superseded Architecture, não a arquitetura vigente. A árvore de diretórios em si não foi alterada — `workflows/` continua reservado, agora com seu propósito correto explícito.
3. **Evidência de busca global (executada, não apenas afirmada):**
   - `grep -rn "pmo_workflow\|PMOWorkflow" --include="*.py" src/ tests/` → único resultado: a própria definição da classe em `src/workflows/pmo_workflow.py:10`. **Nenhum import em nenhum outro arquivo Python.**
   - `grep -rn "from src.workflows\|import.*workflows" --include="*.py" src/ tests/` → **zero resultados.**
   - `grep -n "workflow" src/main.py` e `grep -n "workflows" src/api/dependencies.py` → **zero resultados** — nenhuma rota, nenhuma injeção de dependência referencia este módulo.
   - `grep -rln "pmo_workflow\|PMOWorkflow" web/` (excluindo `node_modules`) → apenas as próprias entradas de Mission Control desta missão de governança (documentais, não código).
   - **Conclusão:** confirmado que não existem imports, não existem rotas dependentes, não existem testes dependentes, e não existe nenhum uso em produção — o arquivo está genuinamente isolado, exatamente como o Blueprint original já indicava.
4. **Nenhuma reutilização/adaptação/refatoração/extração de componentes deste arquivo para a Wave 4** — confirmado: o `EventPublisher`/`WorkflowRuntime` propostos na Seção 2 não referenciam `PMOWorkflow` em nenhum ponto; nascem inteiramente do levantamento da Seção 1, não deste arquivo.
5. **Registrado no Decision Log (D-074) e no CHANGELOG.**
6. **Gatilho de remoção futura registrado:** uma missão específica de limpeza arquitetural, com (a) ausência comprovada de dependências reconfirmada no momento da missão, (b) referências históricas (CLAUDE.md, Decision Log, este Blueprint) atualizadas para refletir a remoção, e (c) a remoção tratada como isolada — nunca acoplada à entrega de uma implementação funcional nova.

**Restrição permanente confirmada:** proibida a coexistência de duas arquiteturas de workflow. O `WorkflowRuntime` desta Wave é a única arquitetura de workflow ativa em `src/workflows/`; `PMOWorkflow` é histórico, não ativo, não estendido.

**Com esta decisão, o Wave 4 Domain Blueprint está autorizado a seguir para Architecture Review.**

---

## 7. Epic Ledger (sequenciamento, ciclo institucional completo por Epic)

Cada Epic abaixo segue obrigatoriamente: Domain Blueprint (este documento cobre todos) → Architecture Review → Founder Approval → Technical Design → Implementation → Governance → Executive Review. Nenhum código inicia antes da aprovação explícita do Founder a este Blueprint e à Architecture Review subsequente.

| Epic | Escopo | Depende de |
|---|---|---|
| **W4-1** | Event Model (envelope) + Event Publisher + migração dos 5 eventos existentes de `DomainService` | Nenhum — primeiro Epic |
| **W4-2** | Event Dispatcher (pub/sub in-process) + Event Audit + Event Metrics | W4-1 |
| **W4-3** | `document.indexed` (Knowledge Platform) + `invitation.created` (Administration) — primeiros novos produtores reais | W4-1, W4-2 |
| **W4-4** | Workflow Runtime + Workflow Context + Execution Tracking + workflow de exemplo mínimo (consumindo `document.indexed`) | W4-2, W4-3 |
| **W4-5** | Retry Policies + Dead Letter Strategy | W4-4 |
| **W4-6** | Integration Contracts + Integration Gateway | W4-1 (independente de W4-3/4/5, pode paralelizar após W4-2) |

---

## 8. Critérios de sucesso (mapeados ao Success Metric do Founder)

| Critério do Founder | Onde é provado |
|---|---|
| Publicar eventos | W4-1 (Event Publisher) |
| Consumir eventos | W4-2 (Event Dispatcher) |
| Executar workflows simples | W4-4 (Workflow Runtime, exemplo mínimo) |
| Integrar módulos internos | W4-3 (Knowledge Platform + Administration como primeiros produtores reais fora de `DomainService`) |
| Preservar rastreabilidade completa | 2.1 (envelope) + 2.6 (Execution Tracking) + 2.9 (Event Audit) |
| Manter isolamento entre tenants | `organization_id` como campo obrigatório do envelope (2.1), mesma disciplina desde o Épico 1 |
| Operar desacoplada do domínio | Seção 3 — nenhuma seta sobe; Enterprise Operations nunca conhece Portfolio/Advisor especificamente |
| Servir de base para os Enterprise Advisors da Wave 5 | Seção 4 — `document.indexed` disponível sem mudança estrutural quando o Document Advisor existir |

---

## 9. Próximos passos

1. Founder decide a Decision Proposal (Seção 6).
2. Architecture Review deste Blueprint (equivalente à AR-6 da Wave 3).
3. Aprovação explícita do Founder antes de qualquer Technical Design ou implementação.
