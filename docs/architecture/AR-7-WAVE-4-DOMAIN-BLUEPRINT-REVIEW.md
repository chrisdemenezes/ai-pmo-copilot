# AR-7 — Architecture Review: Wave 4 Domain Blueprint (Enterprise Operations)

**Escopo:** revisão arquitetural exclusiva de `docs/architecture/WAVE-4-DOMAIN-BLUEPRINT.md`, per "Founder Decision — Wave 4 Architecture Review Authorization". Verifica exclusivamente a arquitetura proposta — **nenhum código de produção é implementado nesta missão**.
**Data:** 2026-07-27
**Contexto:** produzida logo após D-074 (Decision Proposal de `pmo_workflow.py` resolvida), antes de qualquer Technical Design ou implementação da Wave 4.
**Precondição cumprida:** Blueprint aprovado (D-073); Decision Proposal encerrada (D-074), preservando rastreabilidade histórica e eliminando ambiguidade sobre a arquitetura vigente.

---

## 1. Event Envelope

**Verificação:** o Blueprint §2.1 define um único contrato de envelope, `DomainEvent`, com exatamente os 6 campos exigidos mais o payload:

| Campo exigido pelo Founder | Presente no Blueprint |
|---|---|
| Event ID | ✅ `event_id: str` |
| Correlation ID | ✅ `correlation_id: str` |
| Timestamp | ✅ `timestamp: datetime` |
| Tenant | ✅ `organization_id: int` — reaproveita o campo de tenant já usado desde o Épico 1 em toda a base, nenhum novo conceito de tenant introduzido |
| Origin | ✅ `origin: str` |
| Payload Version | ✅ `payload_version: int` |
| Payload | ✅ `payload: dict` |

**Confirmado:** todo evento proposto — os 5 já existentes (migrados) mais `DocumentIndexed`/`InvitationCreated` — compartilha o mesmo envelope único (§2.2, tabela de Event Contracts). Nenhum evento tem forma própria fora dele.

**Achado (não bloqueante, ver Seção 6):** a promoção de `EventEmitter.emit(event_name, payload, organization_id)` para `EventPublisher.publish(...)` (§2.3) muda a assinatura do método (novo nome, novos parâmetros `correlation_id`/`origin`, retorno tipado) — o Blueprint descreve isso como "aditivo", mas é mais precisamente uma promoção do único seam existente, migrada no mesmo Epic (W4-1) que possui os 3 únicos call sites reais hoje. Não é uma inconsistência arquitetural — é uma imprecisão de linguagem a corrigir no Technical Design (chamar de "promoção", não "extensão aditiva").

---

## 2. Workflow Runtime

**Verificação item a item das 4 exigências do Founder:**

| Exigência | Onde é honrada no Blueprint |
|---|---|
| Não contém regras de negócio | §2.5: cada passo é "uma função pura `(WorkflowContext) -> WorkflowContext`, nunca contendo regra de negócio" |
| Não substitui o Advisor Framework | §1.2 e §2.5, explícito: "**Não substitui `AdvisorFramework.run()`**... o primeiro consumidor real do Workflow Runtime é um workflow de infraestrutura simples... nunca a lógica de um Advisor" |
| Não executa decisões de domínio | §2.5: o Runtime "apenas orquestra a ordem e captura o resultado/erro de cada passo" — toda decisão permanece no domínio, mesmo princípio já usado por `AdvisorFramework.run()` (Fase 3) e por `DomainService` |
| Apenas coordena a execução de processos | Confirmado pela mesma definição — o único artefato de estado que o Runtime possui é `WorkflowContext` (correlation_id + resultado de cada passo) e a tabela `workflow_executions` (Execution Tracking, §2.6), nunca uma regra de decisão |

**Confirmado:** a fronteira entre orquestração operacional (Wave 4) e orquestração de domínio (`AdvisorFramework`, Wave 3) é traçada de forma explícita e testável — o Blueprint cita `AdvisorFramework.run()` nominalmente como o exemplo do que o Workflow Runtime nunca deve absorver (§1.2), a mesma disciplina de fronteira que a Fase 3 já aplicou entre Framework e Advisor.

---

## 3. Event Publisher / Dispatcher

**Verificação da lista de proibições do Founder:**

| Proibido | Confirmação no Blueprint |
|---|---|
| Brokers | Ausente — §2.4: "nenhum broker externo, nenhuma fila distribuída" |
| Filas distribuídas | Ausente — idem |
| Registries genéricos | Ausente — o Dispatcher mantém "uma tabela `event_type -> [handlers]` registrada em processo" (§2.4): uma tabela de despacho fixa e interna, não um registry dinâmico de tipos desconhecidos em runtime (a distinção explícita já feita na Seção 5 do próprio Blueprint, "Event Registry genérico / Dynamic Bus" como item proibido separado e confirmado ausente) |
| Engines de eventos | Ausente — nenhuma engine de processamento de stream, nenhum motor de regras sobre eventos |
| Infraestrutura especulativa sem consumidor real | Ausente — §2.2 limita os Event Contracts desta Wave a exatamente 3 (migração dos 5 existentes + `DocumentIndexed` + `InvitationCreated`), recusando explicitamente os exemplos do próprio Founder (`RiskIdentified`/`DecisionRegistered`/`AnalysisSubmitted`) por não terem produtor e consumidor reais simultâneos hoje |

**Confirmado:** a arquitetura permanece mínima e diretamente rastreável ao levantamento (Seção 1 do Blueprint) — nenhum componente de Publisher/Dispatcher cobre um cenário hipotético.

---

## 4. Integration Gateway

**Verificação:** o Blueprint (§2.8) define o Integration Gateway como "uma fachada única (mesmo padrão de `KnowledgeRepository` como fachada única da Knowledge Platform) sobre Integration Contracts (Protocols) — reaproveitando o padrão já provado por `NotificationProvider`/`EmbeddingProvider`, não uma abstração nova." Nenhuma implementação concreta de integração é escolhida nesta Wave; o contrato existe, a implementação permanece um `NoOp`, exatamente como `NotificationProvider` hoje.

**Confirmado:** nenhum mecanismo paralelo é criado — o Integration Gateway é uma aplicação do mesmo padrão Protocol+NoOp já em produção desde a Wave 1 (`EventEmitter`/`NoOpEventEmitter`, D-049) e a Wave 2 (`NotificationProvider`/`NoOpNotificationProvider`, D-054), não um novo estilo de abstração.

---

## 5. Conformidade arquitetural

### 5.1 Aderência ao CLAUDE.md

| Regra | Verificação |
|---|---|
| Nunca criar arquitetura paralela | ✅ `src/workflows/` é o diretório já oficialmente reservado (a árvore do CLAUDE.md nunca mudou); nenhum novo diretório de topo é proposto. A ambiguidade histórica (`pmo_workflow.py` coexistindo sem classificação) foi eliminada em D-074 antes desta revisão — condição explícita do Founder para autorizar esta Architecture Review, já cumprida. |
| Nunca duplicar código | ✅ Event Model/Publisher promove (não duplica) `EventEmitter`/`NoOpEventEmitter`; Integration Gateway reaproveita o padrão de `NotificationProvider`/`EmbeddingProvider`; Event Audit é extensão explícita, nunca substituição, de `AdministrationRepository.record_audit`/`AIFoundationAudit.record_question` (§2.9). |
| Nunca criar novo provider | ✅ Nenhum novo Protocol de propósito equivalente a `LLMProvider` é criado. `EventPublisher`/Integration Contracts são abstrações de responsabilidades que não existiam antes (publicação de evento, integração externa) — mesma lógica já usada na AR-6 para justificar `EmbeddingProvider` como não-concorrente de `LLMProvider`. |
| Nunca criar novo registry | ✅ `PromptRegistry` permanece único e intocado. O Event Dispatcher não é um registry de prompts nem de Advisors — é uma tabela de despacho interna de um único módulo de infraestrutura (ver Seção 3). |
| Reutilizar componentes existentes | ✅ Verificado nas Seções 1-4 acima. |

### 5.2 Ausência de arquiteturas paralelas

Confirmado — ver 5.1. A única arquitetura de workflow ativa após D-074 é o Workflow Runtime desta Wave; `pmo_workflow.py` está formalmente neutralizado como Historical Superseded Architecture, não uma segunda implementação concorrente.

### 5.3 Ausência de duplicação de responsabilidades

Confirmado — Event Audit não duplica a auditoria de domínio (§2.9); Execution Tracking não duplica Event Audit (são artefatos complementares: um rastreia execuções de workflow, o outro rastreia o envelope do evento em si — recomendação de clarificação na Seção 6); Integration Gateway não duplica `NotificationProvider`, é a fachada que o consumiria quando uma integração real existir.

### 5.4 Aderência às decisões D-073 e D-074

Confirmado — o modelo operacional apresentado nesta revisão é byte-a-byte o mesmo aprovado em D-073 (nenhuma mudança de escopo desde a publicação do Blueprint); a classificação de `pmo_workflow.py` como Historical Superseded Architecture (D-074) é tratada como resolvida e vinculante — nenhuma seção do Blueprint ou desta revisão reabre, reinterpreta ou depende dele.

### 5.5 Consistência com as Waves 1, 2 e 3

| Wave | Padrão reaproveitado |
|---|---|
| Wave 1 | `EventEmitter`/`NoOpEventEmitter` (D-049) — promovido, nunca recriado; `organization_id` como escopo de tenant, desde o Épico 1 |
| Wave 2 | `NotificationProvider`/`NoOpNotificationProvider` (D-054) — padrão de referência do Integration Gateway |
| Wave 3 | `KnowledgeRepository` como fachada única — padrão de referência do Integration Gateway; `AdvisorFramework.run()` como fronteira explícita que o Workflow Runtime nunca absorve |

Nenhuma contradição de camada, direção de dependência ou nomenclatura encontrada entre a Wave 4 e as Waves anteriores.

---

## 6. Riscos identificados e ajustes recomendados (não bloqueantes)

Nenhum dos itens abaixo impede o Go — são esclarecimentos a resolver no Technical Design, não achados de violação arquitetural:

1. **Precisão de linguagem:** descrever a transição `EventEmitter.emit()` → `EventPublisher.publish()` como "promoção do seam existente" no Technical Design, não como "extensão aditiva" — a assinatura muda, ainda que dentro do único Epic (W4-1) que possui os 3 call sites reais.
2. **Origem do `correlation_id`:** o Blueprint não especifica onde um `correlation_id` nasce para uma chamada simples (ex.: `POST /portfolios`) que hoje não carrega nenhum identificador de correlação. Recomendação: o Technical Design deve definir que a API gera um novo `correlation_id` na borda quando o caller não fornecer um (mesmo padrão de "seam agora, mecanismo depois" já usado pelo próprio Event Foundation), nunca inventando uma dependência de um sistema de tracing externo.
3. **Relação entre Execution Tracking (§2.6) e Event Audit (§2.9):** o Blueprint os descreve como artefatos complementares mas não formaliza se compartilham a mesma tabela ou são tabelas distintas. Recomendação: o Technical Design deve decidir explicitamente (provavelmente tabelas distintas, dado que Execution Tracking rastreia workflows e Event Audit rastreia eventos individuais — nem todo evento publicado necessariamente dispara um workflow).
4. **Semântica de Retry/Dead Letter (§2.7):** `max_attempts` e o formato exato de `dead_letter_events` ficam para o Technical Design definir com precisão (contagem de tentativas, campo de erro, se há um endpoint/rota para inspecionar a dead letter) — o Blueprint corretamente não antecipa isso em detalhe, por não haver consumidor real com requisito de confiabilidade hoje (§1.4).

Nenhum destes riscos é uma inconsistência com o Blueprint aprovado (D-073) — são lacunas de detalhe esperadas em um documento de nível de Blueprint, a resolver no próximo estágio institucional (Technical Design).

---

## 7. Veredito — Go/No-Go

**GO.** O Wave 4 Domain Blueprint está arquiteturalmente consistente com CLAUDE.md, com as decisões D-073/D-074, e com os padrões já estabelecidos nas Waves 1-3. Nenhuma arquitetura paralela, nenhuma duplicação de responsabilidade, nenhum componente especulativo sem consumidor real. Os 4 pontos da Seção 6 são recomendações de precisão para o Technical Design, não bloqueadores.

**Autorizado avançar ao Technical Design da Wave 4**, mediante aprovação explícita do Founder a esta Architecture Review — nenhuma implementação de código inicia antes dessa aprovação.

---

## Rastreabilidade

Nenhum artefato novo além desta revisão foi criado, per a restrição explícita do Founder. Registro completo desta missão concentrado em: este documento, Decision Log (D-075), CHANGELOG e Mission Control.
