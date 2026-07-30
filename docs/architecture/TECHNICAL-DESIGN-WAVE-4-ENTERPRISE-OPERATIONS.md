# Technical Design — Wave 4: Enterprise Operations

**Escopo:** detalhamento de implementação do modelo operacional aprovado no `WAVE-4-DOMAIN-BLUEPRINT.md` (D-073), validado pela Architecture Review AR-7 (D-075, veredito GO) e autorizado pelo Founder em "Founder Decision — Wave 4 Architecture Review Approval". Resolve, documentalmente, as 4 condições obrigatórias impostas antes de qualquer implementação. **Nenhum código é escrito nesta missão** — este documento precede a Implementação, per o ciclo institucional (Domain Blueprint → Architecture Review → Aprovação do Founder → **Technical Design** → Implementation → Governança → Executive Review).
**Data:** 2026-07-27

---

## 1. Condição 1 — `EventPublisher`: formalização da transição `EventEmitter.emit()` → `EventPublisher.publish()`

### 1.1 Responsabilidades de cada componente

| Componente | Responsabilidade |
|---|---|
| `EventEmitter` (Protocol, Wave 1/D-049) | Seam original: `emit(event_name, payload, organization_id) -> None`. Fire-and-forget, sem envelope, sem retorno. **Removido ao final desta Wave** — não fica coexistindo com `EventPublisher` após a migração (mesma disciplina que proibiu duas arquiteturas de workflow, D-074, aplicada aqui a eventos: uma única abstração de publicação de evento ativa por vez). |
| `NoOpEventEmitter` (Wave 1) | Implementação concreta atual — apenas loga. **Removida** junto com `EventEmitter`, mesmo commit da migração. |
| `EventPublisher` (Protocol, novo) | Cunha o envelope completo (`DomainEvent`), persiste-o (Event Audit, Condição 3) e o repassa ao Event Dispatcher (§4), retornando o `DomainEvent` publicado ao chamador. |
| `InProcessEventPublisher` (implementação concreta, nova) | Única implementação nesta Wave — persiste em `events` (Condição 3) e despacha in-process (§4). Substitui `NoOpEventEmitter` na função de DI (`build_event_emitter` em `src/api/dependencies.py`, renomeada `build_event_publisher`). |

### 1.2 Contrato público

```python
# src/services/events/interfaces.py (substitui o Protocol existente)
class EventPublisher(Protocol):
    def publish(
        self,
        event_type: str,
        payload: dict,
        organization_id: int,
        correlation_id: str,
        origin: str,
    ) -> DomainEvent: ...
```

`event_type` mantém exatamente os mesmos valores em uso hoje (`"portfolio.created"`, `"program.created"`, `"program.linked_to_portfolio"`, `"project_delivery.created"`, `"project_delivery.linked_to_program"`) — nenhum evento é renomeado, preservando a taxonomia já registrada no Event Map de referência.

### 1.3 Estratégia de migração

Migração atômica, dentro do Epic W4-1, em um único commit lógico:

1. `EventPublisher`/`DomainEvent`/`InProcessEventPublisher` criados.
2. `DomainService.__init__` passa a receber `publisher: EventPublisher` em vez de `emitter: EventEmitter`.
3. Os 3 pontos de chamada (`create_portfolio`, `create_program`, `create_project`) trocam `self._emitter.emit(name, payload, organization_id)` por `self._publisher.publish(name, payload, organization_id, correlation_id=correlation_id, origin="domain_service")` — `correlation_id` chega como parâmetro do método, propagado desde a rota (Condição 2).
4. `EventEmitter`/`NoOpEventEmitter` são removidos do código (`src/services/events/interfaces.py` e `noop_emitter.py` reescritos para o novo Protocol/implementação, não mantidos em paralelo).
5. `build_event_emitter` (`src/api/dependencies.py`) renomeado para `build_event_publisher`, retornando `InProcessEventPublisher`.

Não há um período de transição com as duas abstrações coexistindo — a migração e a criação da nova abstração acontecem no mesmo Epic, eliminando o risco de uma segunda arquitetura de evento paralela (mesmo princípio de D-074 aplicado à publicação de eventos).

### 1.4 Compatibilidade com os produtores existentes

Os 5 eventos hoje emitidos por `DomainService` continuam sendo os únicos produtores reais desta Wave (per Blueprint §2.2) — nenhum payload muda de forma, apenas passa a ser envelopado. O comportamento externo observável (o que é logado/persistido) é um superconjunto estrito do atual: tudo que já era logado continua sendo, mais o envelope completo agora persistido em `events` (Condição 3) e disponível ao Dispatcher.

---

## 2. Condição 2 — Origem do `correlation_id` (regra única para toda a plataforma)

> **Nota de harmonização documental (pós-Implementação, Executive Review do Epic W4-1, D-078):** as subseções 2.1-2.3 abaixo descreviam, no momento da aprovação deste Technical Design, um novo campo `RequestContext.correlation_id` e um novo ponto de geração de `uuid4()`/header `X-Correlation-Id`. A auditoria de implementação (D-077) encontrou que a plataforma **já possuía**, desde antes desta Wave, exatamente o mecanismo de origem única aqui exigido — `RequestIDMiddleware`/`request_id_var` (`src/api/request_context.py`), já propagado em `RequestContext.request_id` (gerado via `uuid4()` ou aceito via header `X-Request-ID`). Introduzir um segundo campo/gerador teria violado a própria exigência de origem única. O texto abaixo foi atualizado para refletir o comportamento efetivamente implementado; nenhuma nova decisão arquitetural foi criada por esta atualização — apenas a harmonização do documento com D-077.

### 2.1 Onde é criado

No único funil já usado por toda rota para resolver identidade/sessão/organização/correlação: `RequestIDMiddleware` (`src/api/request_context.py`), que roda para toda requisição HTTP, anterior e independente desta Wave. Nenhum novo ponto de entrada foi criado.

### 2.2 Quem é responsável pela criação

`RequestIDMiddleware` gera um `uuid4()` sempre que a requisição não traz um `X-Request-ID` (header já existente, aceito desde antes desta Wave para permitir que um chamador externo já correlacionado propague o próprio identificador — nunca obrigatório), armazenando o valor no `request_id_var` (`contextvars.ContextVar`) e ecoando-o no header de resposta. `RequestContext.request_id` (campo já existente, não um novo campo `correlation_id`) expõe esse valor a toda rota via `get_request_context`. Esta é a **única** regra de origem de identificador de correlação em toda a STRATECH: nenhum outro componente (serviço, repositório, Advisor) gera um identificador equivalente por conta própria.

### 2.3 Como é propagado durante toda a execução

Por parâmetro explícito, exatamente como `organization_id`/`actor_user_id` já são propagados hoje — nenhum mecanismo novo além do `request_id_var` já existente. A rota extrai `request_id` de `RequestContext` e o passa como `correlation_id` para o método de serviço (`DomainService.create_portfolio(..., correlation_id=context.request_id)`), que o repassa ao `EventPublisher.publish(...)`.

**Caso do Workflow Runtime (Epic W4-4):** todo workflow desta Wave é disparado por um evento (per Blueprint §2.5/§4 — nenhum trigger manual ou agendado existe no escopo atual). `WorkflowContext.correlation_id` é sempre herdado do `DomainEvent.correlation_id` que disparou o workflow — nunca cunhado de novo. Isso preserva a regra única (a fronteira da API é a única origem) sem exceção dentro do escopo real desta Wave.

---

## 3. Condição 3 — Execution Tracking × Event Audit: componentes distintos, justificados

**Decisão: dois componentes distintos**, não compartilhando persistência além da chave de correlação.

| | Event Audit (`events`) | Execution Tracking (`workflow_executions`) |
|---|---|---|
| **Pergunta que responde** | "Que fatos foram publicados?" | "Que processos rodaram, e como foi?" |
| **Cardinalidade** | Uma linha por evento publicado | Uma linha por execução de workflow |
| **Colunas** | `event_id` (PK), `event_type`, `correlation_id`, `timestamp`, `organization_id`, `origin`, `payload_version`, `payload` (JSON) | `id` (PK), `organization_id`, `correlation_id`, `workflow_name`, `status`, `started_at`, `finished_at`, `error` |
| **Chave de junção** | `correlation_id` | `correlation_id` |

**Justificativa (simplicidade, sem duplicação):** as duas tabelas não têm relação 1:1 — nem todo evento publicado dispara um workflow (ex.: `portfolio.created` hoje não tem nenhum workflow associado), e nem toda execução de workflow precisa necessariamente de exatamente um evento de origem no futuro. Fundir as duas em uma única tabela exigiria colunas de workflow nulas em toda linha de evento sem workflow associado (ou o inverso), aproximando a estrutura de um esquema genérico "tudo em uma tabela" — exatamente a direção que o princípio de "sem arquitetura especulativa" desaconselha. Manter as duas distintas, unidas apenas por `correlation_id` (o único campo necessário para reconstruir a cadeia publicação→execução, o próprio Success Metric do Founder), é a solução mais simples que não duplica nenhuma coluna além dessa chave.

**Event Audit nunca substitui a auditoria de domínio** (`AdministrationRepository.record_audit`/`AIFoundationAudit.record_question`, Princípio 6 do Blueprint) — ambas continuam existindo exatamente como hoje, sem alteração.

---

## 4. Condição 4 — Retry / Dead Letter (mínimo necessário, sem antecipar consumidor inexistente)

Dado que nenhum consumidor real hoje tem requisito de confiabilidade além do melhor esforço (Blueprint §1.4), a política é deliberadamente fixa e mínima — sem configurabilidade por evento/workflow (configurabilidade seria infraestrutura especulativa sem consumidor que a exija):

| Item | Definição |
|---|---|
| **Número máximo de tentativas** | Constante fixa, `MAX_ATTEMPTS = 3`. Não configurável por evento/workflow nesta Wave. |
| **Critério de retry** | Qualquer exceção levantada durante a execução de um passo do Workflow Runtime dispara uma nova tentativa, até `MAX_ATTEMPTS`. Nenhuma distinção entre exceções "recuperáveis" e "não recuperáveis" — granularidade sem consumidor real que a justifique hoje. Tentativas ocorrem de forma síncrona e imediata (não há fila para agendar um retry futuro nesta Wave — nenhum broker, per as restrições permanentes). |
| **Estrutura mínima do erro** | `dead_letter_events`: `id` (PK), `event_id` (FK para `events.event_id`), `organization_id`, `correlation_id`, `attempts` (int), `last_error` (texto, `str(exception)`), `created_at`. |
| **Condições para encaminhamento ao Dead Letter** | Após a 3ª tentativa falhar, a linha correspondente em `workflow_executions` é marcada `status="failed"` e uma linha é inserida em `dead_letter_events`. Nenhum reprocessamento automático, nenhuma interface de inspeção além de consulta direta ao banco (Dashboards/Analytics permanecem fora de escopo desta Wave). |

Nenhum backoff exponencial, nenhuma fila de retry agendado — ambos seriam engenharia de confiabilidade antecipando um requisito que nenhum consumidor real desta Wave possui.

---

## 5. Modelo completo — contratos públicos e estrutura de diretórios

### 5.1 Estrutura de diretórios (`src/workflows/` e `src/services/events/`)

```
src/services/events/
  __init__.py
  interfaces.py          (EventPublisher Protocol, DomainEvent dataclass)
  in_process_publisher.py (InProcessEventPublisher)
  dispatcher.py           (EventDispatcher -- tabela event_type -> handlers, in-process)

src/workflows/
  pmo_workflow.py         (Historical Superseded Architecture, D-074 -- intocado)
  runtime.py              (WorkflowRuntime, WorkflowContext)
  execution_tracking.py   (persistência de workflow_executions)

src/services/integrations/
  interfaces.py           (Integration Contracts -- Protocols)
  gateway.py              (IntegrationGateway -- fachada única, mesmo padrão de KnowledgeRepository)
```

### 5.2 Contratos públicos adicionais (Event Contracts, Blueprint §2.2)

```python
@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    event_type: str
    correlation_id: str
    timestamp: datetime
    organization_id: int
    origin: str
    payload_version: int
    payload: dict

class WorkflowRuntime:
    def run(self, workflow_name: str, steps: list[Callable[[WorkflowContext], WorkflowContext]], context: WorkflowContext) -> WorkflowContext: ...

@dataclass
class WorkflowContext:
    correlation_id: str
    organization_id: int
    data: dict
```

### 5.3 Migração de banco

Uma única migração Alembic aditiva (numeração sequencial seguindo `0017`), criando 3 tabelas: `events`, `workflow_executions`, `dead_letter_events`. Nenhuma tabela existente é alterada.

---

## 6. Sequência de chamadas (exemplo ponta a ponta — Success Metric do Founder)

```
POST /portfolios
  → RequestIDMiddleware/request_id_var resolve o correlation_id (Condição 2, atualizada pós-implementação -- D-077/D-078)
  → DomainService.create_portfolio(..., correlation_id=...)
       → repository write
       → EventPublisher.publish("portfolio.created", ..., correlation_id, origin="domain_service")
            → persiste em `events` (Condição 3, Event Audit)
            → EventDispatcher despacha aos handlers registrados para "portfolio.created"
                 → (se houver workflow registrado) WorkflowRuntime.run(...)
                      → WorkflowContext herda correlation_id do DomainEvent
                      → cada passo executado; falha → retry até 3x (Condição 4) → dead_letter_events se esgotar
                      → resultado registrado em `workflow_executions` (Execution Tracking)
```

---

## 7. Estratégia de testes

- `tests/test_events_publisher.py` — `InProcessEventPublisher.publish()` persiste o envelope completo e retorna `DomainEvent`; `EventDispatcher` invoca os handlers corretos por `event_type`.
- `tests/test_domain_service.py` (existente, estendido) — os 3 métodos de criação passam a chamar `EventPublisher.publish` em vez de `EventEmitter.emit`, mesma asserção de payload, mais `correlation_id`/`origin` agora presentes.
- `tests/test_workflow_runtime.py` — execução de sequência de passos puros; erro em um passo aciona retry até `MAX_ATTEMPTS`; esgotamento grava em `dead_letter_events`; `WorkflowContext.correlation_id` herdado corretamente do evento disparador.
- `tests/test_migration_00XX_enterprise_operations.py` — upgrade/downgrade/re-upgrade das 3 tabelas em PostgreSQL real, mesmo padrão de todas as migrações desta STRATECH.
- Nenhum teste de integração com broker/fila externo — não existe nenhum nesta Wave.

---

## 8. Critérios de aceite

- Os 5 eventos hoje emitidos por `DomainService` fluem pelo novo `EventPublisher`, com envelope completo persistido em `events`.
- `EventEmitter`/`NoOpEventEmitter` removidos do código — nenhuma segunda abstração de publicação de evento sobrevive à migração.
- Um `correlation_id` é gerado uma única vez, na borda da API, e chega intacto a todo evento publicado e todo workflow disparado dentro da mesma requisição.
- `document.indexed` e `invitation.created` (Blueprint §2.2) disponíveis como novos produtores reais.
- Um workflow de exemplo mínimo, disparado por `document.indexed`, demonstra publicação → propagação → execução → auditoria sem exigir mudança estrutural em `KnowledgeRepository`.
- Nenhuma tabela, Protocol ou dependência nova além das listadas neste documento.

---

## 9. Restrições permanentes (reafirmadas, checklist final antes da implementação)

| Proibido | Confirmação nesta Technical Design |
|---|---|
| Brokers distribuídos | Ausente — `EventDispatcher` é in-process |
| Filas externas | Ausente |
| Registries dinâmicos | Ausente — tabela de despacho fixa, não um registry de tipos desconhecidos |
| Engines genéricas | Ausente — `WorkflowRuntime` executa uma lista fixa de passos Python, nunca uma DSL |
| Plugins | Ausente — `IntegrationGateway` é uma fachada fixa, não uma superfície de plugins |
| DSLs | Ausente |
| Infraestrutura baseada em hipóteses futuras | Ausente — cada componente listado neste documento tem produtor e/ou consumidor real identificado no levantamento do Blueprint (§1) |

**Princípio confirmado:** implementa-se somente o necessário para atender aos produtores e consumidores reais identificados na auditoria do Blueprint — nenhum componente deste documento cobre um cenário hipotético.

---

## 10. Próximos passos

Após aprovação explícita do Founder a este Technical Design, a Implementação do Epic W4-1 pode iniciar. Ao final da implementação: Technical Design (este documento, sem alteração retroativa — correções viram Decision Log), Executive Review, Decision Log, riscos residuais e recomendação Go/No-Go serão apresentados, per o ciclo institucional.

---

## 11. Implementation Note — Epic W4-3 (2026-07-30, "Founder Decision — Epic W4-3 Scope Approval")

Founder aprovou implementação direta (sem Technical Design específico) — reuso estrito do contrato já estabelecido no W4-1. Nota registrada no artefato oficial existente, per instrução explícita, sem novo documento.

**1. Pontos exatos de publicação:**
- `KnowledgeRepository.index()` (`src/services/knowledge_platform/knowledge_repository.py`) — após `session.commit()` dos `Chunk` gerados, fora do bloco `with self._session_factory()`.
- `AdministrationService.create_invitation()` (`src/services/administration_service.py`) — após `self._repository.administration.create_invitation(...)` e o registro de auditoria de domínio (`record_audit`), antes do `return`.

**2. Dependências injetadas:**
- `KnowledgeRepository.__init__` ganha `event_publisher: EventPublisher` (parâmetro obrigatório, sem default — quase todo call site já chama `.index()`, mesmo padrão do `DomainService` no W4-1). DI de produção: `src/api/routes/intelligence.py::build_knowledge_repository` injeta `Depends(build_event_publisher)` (o singleton `@lru_cache` já compartilhado com `DomainService`/`AdministrationService`).
- `AdministrationService.__init__` ganha `event_publisher: EventPublisher | None = None` (parâmetro **opcional**, default real — `InProcessEventPublisher(repository.SessionLocal, EventDispatcher(repository.SessionLocal))` — mesma convenção já usada por `password_hasher`/`notification_provider` nesta classe). Assimetria deliberada: das ~12 construções de `AdministrationService` no código, só a rota de convites (`invitations.py::build_invitation_service`) chama `create_invitation`; tornar o parâmetro obrigatório forçaria toda rota/teste de API Keys, Sessões e Admin CRUD a injetar um publisher que nunca usam. `build_invitation_service` sempre injeta explicitamente o singleton `Depends(build_event_publisher)`, garantindo que a rota de produção compartilhe a mesma tabela de despacho do `EventDispatcher` usada por `DomainService`.

**3. Origem e propagação do correlation_id:** inalterada em relação ao W4-1 — `RequestIDMiddleware`/`request_id_var`, exposta em `RequestContext.request_id`. A rota `POST /admin/invitations` passa `correlation_id=context.request_id` a `create_invitation`. `KnowledgeRepository.index()` não tem hoje nenhuma rota chamadora (achado já registrado no Blueprint §4 item 2 — produtor real sem consumidor real ainda); `correlation_id` é um parâmetro obrigatório do método, suprido por quem quer que o chame (hoje, só testes; o futuro caller real herdará `context.request_id` da mesma forma). Nenhum novo `correlation_id` é cunhado em nenhum dos dois serviços.

**4. Momento da publicação em relação à persistência:** ambos os eventos são publicados **depois** que a operação principal já foi persistida com sucesso (commit da sessão) — nunca antes, nunca dentro da mesma transação. Se a operação principal levantar uma exceção antes do commit (documento inexistente, `role_name` desconhecido), o método retorna/propaga o erro antes de alcançar a chamada a `.publish(...)` — nenhum evento é publicado.

**5. Payload definitivo (estrito, per autorização do Founder):**
- `document.indexed`: `{document_id: int, version_id: int, chunk_count: int}`.
- `invitation.created`: `{invitation_id: int, email: str, role_name: str}` — nunca o token, seu hash, ou qualquer URL de aceite.

**6. Comportamento em caso de falha de publicação:** inalterado em relação à política já implementada no W4-1 — `EventDispatcher._dispatch_to_handler` já absorve falha de handler (retry até `MAX_ATTEMPTS=3`, depois `dead_letter_events`), e uma falha de despacho nunca propaga ao chamador (o write da operação principal já teve sucesso). Nenhum tratamento paralelo foi criado para este Epic.

---

## 12. Technical Design — Epic W4-4 (Workflow Runtime + Execution Tracking)

**Escopo:** detalhamento de implementação do Epic W4-4, autorizado pelo Founder em "Founder Decision — Epic W4-4 Scope Approval", que confirmou D-079 (workflow mínimo sem métrica), fixou a separação de responsabilidade Dispatcher/Runtime como princípio arquitetural, e exigiu que este documento resolva a política de idempotência antes de qualquer implementação. **Nenhum código é escrito nesta missão.**

### 12.1 Escopo confirmado (per aprovação do Founder)

`document.indexed` → `WorkflowRuntime` → Execution Tracking. Um único passo, sem métrica, sem analytics, sem regra de negócio. Nenhum handler adicional, nenhum segundo workflow.

### 12.2 Princípio arquitetural: separação Dispatcher/Runtime (fixado pelo Founder)

`EventDispatcher` permanece exatamente como implementado no W4-1 — **nenhuma alteração de código está prevista neste Epic**. O Dispatcher:
- não conhece `workflow_executions`;
- não conhece estados de workflow (`running`/`completed`/`failed`);
- não escreve em nenhuma tabela de execução;
- apenas invoca o handler registrado para o `event_type`, com seu próprio retry (`MAX_ATTEMPTS=3`) e seu próprio `dead_letter_events` — exatamente como já faz hoje para qualquer handler, sem saber que este handler específico é um Workflow Runtime.

`WorkflowRuntime` é registrado como **um handler comum** de `EventDispatcher` para `document.indexed` (`dispatcher.register("document.indexed", <função que invoca WorkflowRuntime.run(...)>)`) — do ponto de vista do Dispatcher, é indistinguível de qualquer outro handler. Toda a responsabilidade de registrar `running`/`completed`/`failed` em `workflow_executions` pertence exclusivamente ao `WorkflowRuntime`. Se o `WorkflowRuntime` levanta uma exceção (falha de um passo), o Dispatcher a captura como faria com qualquer handler — reage com seu próprio retry, sem jamais escrever ou ler `workflow_executions`.

Consequência observável: uma falha total (3 tentativas do Dispatcher esgotadas) produz **dois registros independentes, de dois donos diferentes** — `dead_letter_events` (escrito pelo Dispatcher, per política do W4-1, inalterada) e `workflow_executions.status = "failed"` (escrito pelo `WorkflowRuntime`, per §12.4 abaixo). Nenhum dos dois componentes lê ou escreve na tabela do outro.

### 12.3 Contratos públicos

```python
@dataclass(frozen=True)
class WorkflowContext:
    correlation_id: str      # sempre herdado do DomainEvent -- nunca construído fora de WorkflowRuntime.run()
    organization_id: int     # herdado do DomainEvent
    payload: dict            # o payload do DomainEvent (ex.: document.indexed -> {document_id, version_id, chunk_count})


class WorkflowStep(Protocol):
    def __call__(self, context: WorkflowContext) -> WorkflowContext: ...


class WorkflowRuntime:
    def __init__(self, session_factory: sessionmaker, execution_tracker: ExecutionTracker): ...

    def run(
        self,
        workflow_name: str,
        steps: list[WorkflowStep],
        triggering_event: DomainEvent,
    ) -> WorkflowContext:
        """`WorkflowContext` é construído aqui, exclusivamente a partir de
        `triggering_event` -- nenhum outro ponto de entrada existe para
        criar um WorkflowContext, o que torna a herança de correlation_id
        estrutural (impossível de contornar por engano), não apenas uma
        convenção documentada."""
```

`ExecutionTracker` (`src/workflows/execution_tracking.py`, per estrutura de diretórios já definida em §5.1) é a única classe ciente de `workflow_executions` — mesmo padrão de fachada única já usado por `KnowledgeRepository`/`IntegrationGateway`. `WorkflowRuntime` nunca escreve SQL diretamente.

### 12.4 Política de idempotência (exigência explícita do Founder)

**Identificação de execuções:** chave de idempotência é o par **(`triggering_event.event_id`, `workflow_name`)** — não o `correlation_id` isoladamente. Justificativa: `event_id` é um UUID cunhado uma única vez por `InProcessEventPublisher.publish()` no momento da publicação (W4-1) — é o identificador mais preciso de "esta ocorrência específica do evento", enquanto `correlation_id` identifica a cadeia de correlação mais ampla (poderia, em tese, ser compartilhado por múltiplos eventos de uma mesma requisição). Constraint única em `workflow_executions` sobre `(event_id, workflow_name)`.

**Comportamento diante de reexecução:** a única reexecução possível hoje é o próprio retry síncrono do `EventDispatcher` (até `MAX_ATTEMPTS=3`, dentro da mesma chamada a `dispatch()`) — nunca um reprocessamento posterior ou assíncrono (proibido desde o W4-1). Quando o Dispatcher chama o handler do workflow uma segunda ou terceira vez para o mesmo evento, `WorkflowRuntime.run()` executa um **upsert** por `(event_id, workflow_name)`:
- Se não existe linha: insere com `status="running"`, `started_at=now()`.
- Se já existe linha (criada pela tentativa anterior): **reutiliza a mesma linha** — atualiza `status="running"` novamente, sem inserir uma segunda linha.

Isso é seguro porque os passos do workflow são funções puras sem efeito colateral externo (Blueprint §2.5, princípio já vigente) — o único efeito colateral é o próprio registro em `workflow_executions`, que o `WorkflowRuntime` controla integralmente. Reexecutar do zero nunca duplica um efeito de negócio, porque não há nenhum.

**Prevenção de duplicidade:** a constraint única `(event_id, workflow_name)` no banco é a garantia de última linha — mesmo que uma falha de lógica na aplicação tentasse inserir uma segunda linha para o mesmo par, o banco rejeitaria.

**Critérios para reutilização vs. criação de nova execução:** reutiliza-se a linha exclusivamente quando `event_id` e `workflow_name` coincidem (i.e., o mesmo evento publicado está sendo redespachado pelo próprio retry do Dispatcher). Um novo `DomainEvent` publicado (ainda que do mesmo `event_type`, ex.: indexação de um segundo documento) sempre carrega um `event_id` novo — portanto sempre gera uma nova linha de execução, corretamente distinta.

**Ao final (sucesso ou esgotamento das 3 tentativas):** `WorkflowRuntime` atualiza a mesma linha para `status="completed"` (sucesso, `finished_at=now()`) ou `status="failed"` (exceção, `error=str(exc)`, `finished_at=now()`) antes de repropagar a exceção ao Dispatcher (que então decide, por conta própria, se tenta de novo ou grava em `dead_letter_events` — sem qualquer conhecimento do estado do workflow).

### 12.5 Migração de banco

Reaproveita a tabela `workflow_executions` já definida (mas não criada) na Condição 3 (§3) — colunas `id` (PK), `organization_id`, `correlation_id`, `event_id`, `workflow_name`, `status`, `started_at`, `finished_at`, `error`, mais a constraint única `(event_id, workflow_name)` (adição em relação ao desenho original de §3, necessária para a política de idempotência). Migração aditiva, mesma numeração sequencial já reservada.

### 12.6 Restrições permanentes reafirmadas

Nenhuma regra de negócio em nenhum passo de workflow; nenhuma métrica/analytics; nenhum Advisor; nenhum Integration Gateway (permanece W4-6, independente); nenhuma infraestrutura distribuída; nenhuma abstração além de `WorkflowRuntime`/`WorkflowContext`/`ExecutionTracker` já previstas desde §5.1; nenhuma alteração ao `EventDispatcher` (§12.2); nenhum reprocessamento automático além do retry síncrono já existente no Dispatcher.

### 12.7 Riscos residuais

- **Acoplamento pelo tipo, não pela tabela:** `WorkflowRuntime.run()` precisa do `DomainEvent` completo (não apenas `correlation_id`) para extrair `event_id`/`payload`/`organization_id` — uma dependência direta de `src.services.events.interfaces.DomainEvent`. Isso é reuso de um contrato já público (não uma abstração nova), mas registra-se como dependência explícita entre `src/workflows/` e `src/services/events/`.
- **Ausência de consumidor de produção:** `document.indexed` continua sem nenhuma rota chamadora real (achado de W4-3, D-080) — a prova ponta a ponta deste Epic também será demonstrada por teste, não por tráfego real, até que a Wave 5 (Document Advisor) exista.
- **Granularidade única do passo:** como o exemplo mínimo tem exatamente um passo sem efeito colateral de negócio, a política de idempotência aqui descrita não foi testada contra um workflow de múltiplos passos com efeitos colaterais reais (ex.: uma chamada a um `NotificationProvider` dentro de um passo) — cenário fora do escopo autorizado deste Epic, a ser reavaliado quando (e se) um workflow futuro precisar disso.

### 12.8 Critérios de aceite

- `WorkflowRuntime`/`WorkflowContext`/`ExecutionTracker` implementados exatamente per §12.3.
- Um único workflow de exemplo, registrado no `EventDispatcher` para `document.indexed`, cujo único passo não contém regra de negócio.
- `EventDispatcher` (código) permanece byte-a-byte inalterado — confirmado por diff nulo em `src/services/events/dispatcher.py` ao final da implementação.
- Idempotência provada por teste: despachar o mesmo `DomainEvent` duas vezes produz uma única linha em `workflow_executions`.
- `WorkflowContext.correlation_id` idêntico ao do `DomainEvent` disparador, em todo teste.
- Retry/Dead Letter do Dispatcher continuam funcionando sem nenhuma alteração de comportamento para os produtores já existentes (W4-1/W4-3).
