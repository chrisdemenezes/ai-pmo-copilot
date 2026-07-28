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

### 2.1 Onde é criado

No único funil já usado por toda rota para resolver identidade/sessão/organização: `get_request_context` (`src/api/identity_context.py`). Nenhum novo ponto de entrada é criado — reaproveita a mesma dependência que já injeta `organization_id`/`actor_user_id` em toda rota protegida.

### 2.2 Quem é responsável pela criação

`RequestContext` ganha um campo `correlation_id: str`. `get_request_context` gera um `uuid4()` sempre que a requisição não traz um `X-Correlation-Id` (header opcional, aceito para permitir que um chamador externo já correlacionado propague o próprio identificador — nunca obrigatório). Esta é a **única** regra de origem de `correlation_id` em toda a STRATECH: nenhum outro componente (serviço, repositório, Advisor) gera um `correlation_id` por conta própria.

### 2.3 Como é propagado durante toda a execução

Por parâmetro explícito, exatamente como `organization_id`/`actor_user_id` já são propagados hoje — nenhum mecanismo novo (nenhum `contextvar`, nenhum thread-local, nenhuma "mágica" implícita). A rota extrai `correlation_id` de `RequestContext` e o passa para o método de serviço (`DomainService.create_portfolio(..., correlation_id=context.correlation_id)`), que o repassa ao `EventPublisher.publish(...)`.

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
  → get_request_context() gera correlation_id (Condição 2)
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
