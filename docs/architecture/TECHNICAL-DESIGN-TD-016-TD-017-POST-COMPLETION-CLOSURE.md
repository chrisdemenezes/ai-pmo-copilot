# Technical Design — V1 Post-Completion Technical Closure (TD-016 / TD-017)

## 1. Contexto

Founder Mandate "STRATECH V1 — Post-Completion Technical Closure" authorizes
resolving exactly two Technical Debt items registered at Wave 8's closure
(PR #54, baseline SHA `d37f2d5c72f188a5ecef6791c78796b2f15a974c`):

- **TD-016** — Automated Performance Snapshot Capture (today: manual/on-demand only).
- **TD-017** — Executive Intelligence Integration (today: Analytics/Signals exist standalone, never reach `AdvisorFramework`/`AIContextEngine`).

Wave 8 remains COMPLETE. This is not a new Wave/Epic.

## 2. Reconciliação factual (código real, não suposição)

Antes de desenhar a captura automática, confirmei por leitura direta de código:

- **Nenhum endpoint `PUT`/`PATCH` existe para `Project`** em nenhum lugar do
  código (`grep` em `src/api/routes/*.py`). `DomainService`/`DomainRepository`
  não têm `update_project`/`update_program`/`update_portfolio`.
- **`Project.actual_cost`/`progress_percentage`/`forecast_cost` nunca são
  reatribuídos em nenhum lugar de `src/`** além do construtor `Project(**fields)`
  em `create_project_with_domain()` -- ou seja, esses campos são fixados
  apenas na criação, hoje. Não existe, portanto, nenhum evento real de
  "alteração de actual cost/progress/forecast" para se conectar -- esse
  evento simplesmente não acontece no sistema atual.
- **Nenhuma infraestrutura de scheduling/cron existe** em lugar nenhum do
  código. `WorkflowRuntime` (`src/workflows/runtime.py`) é um executor de
  passos disparado por evento (`triggering_event`), nunca por tempo.
  `EventDispatcher` (`src/services/events/dispatcher.py`) é pub/sub
  in-process síncrono, sem qualquer noção de tempo.
- **`EventDispatcher.publish()` já dispara `dispatch()` de verdade** --
  `InProcessEventPublisher.publish()` persiste o evento e imediatamente
  chama `self._dispatcher.dispatch(event)`. Hoje nenhum handler de produção
  está registrado exceto o único workflow de exemplo já autorizado
  (`document_indexed_workflow.register(dispatcher, runtime)`, Epic W4-4).
  Esse é exatamente o "seam now, mechanism later" que este fechamento
  ativa pela primeira vez para um caso de uso real.
- **`project_performance_baseline.created` já é publicado de verdade**
  hoje (Wave 8, `ProjectPerformanceService.create_baseline()`) sempre que
  um baseline é autorado/rebaselineado -- este é o evento real, já
  existente, semanticamente apropriado ("mudança relevante de
  planejamento") que a captura automática pode usar.

**Conclusão:** como não existe nenhum evento real de "campo financeiro
mudou" (porque o campo nunca muda), captura 100% event-driven não é
suficiente para dar cadência temporal quando nada muda -- exatamente o
cenário que a Seção 4 do mandato já antecipa. E como não existe nenhuma
infraestrutura de scheduling, criar uma NÃO é permitido sem STOP. A solução
abaixo evita precisar de uma.

## 3. Desenho da captura (TD-016)

### 3.A — Event-driven (evento real já existente, reutilizado)

Um handler direto é registrado em `EventDispatcher` (não em
`WorkflowRuntime` -- esse é o único workflow explicitamente autorizado
como exemplo mínimo do Epic W4-4; um segundo handler simples de pub/sub
genérico não invade essa autorização) para `project_performance_baseline.created`:
sempre que um baseline é autorado, um snapshot é capturado imediatamente,
ancorando a nova curva planejada a um ponto real do realizado.

O payload deste evento ganha um campo aditivo `actor_user_id` (o mesmo já
disponível em `create_baseline()`), preservando a auditoria correta -- o
handler nunca inventa um "actor de sistema".

### 3.B — Read-triggered checkpoint (substitui "periódico", zero infraestrutura nova)

Como nenhum scheduler existe e criar um exigiria uma nova primitiva
arquitetural (gatilho de STOP explícito, Seção 20), a alternativa
adotada -- squarely dentro de "event-driven + periodic checkpoint desde
que utilize infraestrutura existente" (Seção 4) -- é: `GET
/projects-delivery` e `GET /projects-delivery/{id}` (endpoints já
existentes, já autenticados, já org-escopados) capturam um snapshot
best-effort (idempotente, nunca falha a leitura) para cada Project que
retornam, usando o próprio usuário da requisição
(`context.user.user_id`/`context.request_id`) como o actor.

Isso faz o histórico real acumular a partir do uso real do produto --
exatamente a página Project Delivery (Wave 8) que já exibe os novos
KPIs/gráficos -- sem introduzir nenhum scheduler, nenhuma nova arquitetura
de Event Pipeline. É a interpretação honesta de "periódico" possível hoje:
não é wall-clock, é uso-driven, documentado como tal.

### 3.C — Idempotência

Inalterada da Wave 8: `UNIQUE(project_id, snapshot_date)` +
`PerformanceRepository.capture_snapshot()`'s "verifica existente, retorna
se já existe" -- qualquer combinação de chamadas manuais + automáticas
(event-driven ou read-triggered) no mesmo dia converge para exatamente uma
linha. `snapshot_date` continua `datetime.now(tz=timezone.utc).date()`
(UTC, já estabelecido na Wave 8).

### 3.D — Dados ausentes nunca é erro

Quando `Project.actual_cost`/`progress_percentage` ainda são `None`
(nenhum dado real para capturar), o handler/rota trata isso como um no-op
esperado (nunca propaga para o retry/dead-letter do `EventDispatcher`,
nunca falha a leitura) -- é um estado normal, não uma falha.

### 3.E — Baseline/rebaseline

Inalterado. A captura automática nunca cria/edita baseline -- apenas
snapshots. Rebaseline continua criando uma nova `baseline_version`,
nunca tocando `project_performance_snapshots` (Wave 8, Seção 2.G).

### 3.F — APIs preservadas

Os 4 endpoints do PR #54 permanecem com o mesmo contrato/response shape.
A captura automática é aditiva (efeito colateral best-effort), nunca
substitui a captura manual/on-demand (Seção 16 do mandato).

## 4. Desenho da integração de IA (TD-017)

### 4.A — Revalidação do Package M (D-237)

Confirmado por leitura de código: `PMOAdvisorAgent`/`ExecutiveAdvisorAgent`
recebem hoje `learnings_json` como uma variável de prompt **separada**,
nunca entrando em `evidence`/`cited_analysis_ids` -- o Evidence Gate
(`AdvisorFramework.run()`: `if not evidence: return no_evidence()`) opera
inteiramente sobre `evidence`, nunca vê Learnings. O padrão continua
arquiteturalmente adequado e é reutilizado, verbatim, para Analytics.

### 4.B — Escopo: os mesmos 2 Advisors organization-wide

Per Seção 14 do mandato ("Preferir enriquecimento no nível de Executive
Intelligence a modificar os oito Advisors separadamente" + priorizar
"Executive Orchestrator; Decision Support; Executive Narrative"): Decision
Support/Executive Narrative já fluem através do `ExecutiveOrchestrator`
via seleção determinística de Advisors (`selection_rule.py`) + Síntese
(`synthesis.py`), sem que este fechamento precise tocar nenhum dos dois.
Estender os mesmos 2 Advisors organization-wide já tocados pelo Package M
(PMO, Executive) com uma SEGUNDA variável de prompt separada
(`$analytics_context`, distinta de `$learnings_json`) alcança exatamente
essas 2 capabilities sem tocar `orchestrator.py`/`synthesis.py`/`provisioning.py`
nem os outros 6 Advisors -- a superfície mínima que já entrega o fluxo
pedido na Seção 8.

### 4.C — Executive Signal Engine (backend, novo, determinístico)

`src/services/executive_analytics/executive_signal_engine.py`: porta para
Python o mesmo algoritmo puro já validado no frontend
(`web/lib/domain/executive-signal.ts`, Wave 8) para os sinais que dependem
apenas do histórico EVM de um único Project (`cost_performance_deteriorating`/
`schedule_performance_deteriorating`/`recovery_trend`/`forecast_deviation`),
reutilizando `metrics_engine.build_history_series()`/`compute_evm_summary()`
já existentes. **Fora de escopo desta missão:** sinais de concentração de
portfólio/risco (exigiriam agregação cross-project mais ampla, não
comprovadamente necessária para o fluxo de evidência estruturada pedido) --
não fabricados, não implementados apressadamente; permanecem como próximo
incremento natural, registrado no fechamento.

### 4.D — Estrutura da evidência (Seção 10 do mandato)

Cada sinal vira um `Evidence` (mesma convenção de `gather_organizational_learnings`,
`source_type="executive_signal"`, `source_id` negativo -- nunca colide com
um `AnalysisRecord.id` real) cujo `content` carrega exatamente os campos
pedidos: scope, project, metric, current_value, baseline_or_threshold,
trend, signal_type, severity, period (as_of), timestamp, provenance
(referência determinística de onde veio). Nenhuma visualização/SVG é
enviada ao LLM -- apenas os fatos.

### 4.E — LLM nunca calcula

Todo valor em `analytics_context` já chega computado deterministicamente
(Python puro, zero chamada a LLM) antes de qualquer prompt ser montado --
o LLM apenas lê/interpreta o JSON já pronto, exatamente como já acontece
com `records_json`/`learnings_json`.

### 4.F — Signal ≠ Recommendation ≠ Decision

Nada muda em `RecommendationEngine`/`ExplanationEngine` -- a resposta do
Advisor continua sendo `{"answer", "cited_analysis_ids"}`, nunca grava uma
Decision, nunca promove um Signal a Decision automaticamente. O prompt
instrui explicitamente que Analytics é contexto de apoio, nunca citável,
nunca a base exclusiva de uma resposta -- mesma disciplina de
`learnings_json`.

## 5. Impacto arquitetural

- Nenhuma migração nova (nenhuma mudança de schema).
- Nenhuma mudança em RBAC/Tenant Isolation/Authentication.
- `EventDispatcher` ganha um segundo handler registrado (mecanismo
  genérico já existente, nenhuma mudança na classe em si).
- 2 endpoints existentes (`GET /projects-delivery`, `GET
  /projects-delivery/{id}`) ganham um efeito colateral best-effort,
  contrato de resposta inalterado.
- `AIContextEngine`/`AdvisorFramework` ganham um método passthrough
  adicional (mesma convenção de `gather_organizational_learnings`).
- 2 Advisors (PMO, Executive) ganham uma segunda variável de prompt
  separada -- os outros 6 Advisors, `ExecutiveOrchestrator`,
  `Synthesis`, `Correlation`, `RecommendationEngine`, `ExplanationEngine`
  permanecem intocados.
