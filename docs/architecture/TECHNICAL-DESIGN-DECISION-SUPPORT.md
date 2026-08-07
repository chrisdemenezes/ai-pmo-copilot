# Technical Design — Decision Support (primeiro consumidor de produção da Executive Intelligence)

Produzida sob mandato da "Founder Decision — Wave 6 / Decision Support" (APPROVED do Wave 6 Progress Assessment, D-148; próximo ciclo institucional: Decision Support), que autoriza exclusivamente este Technical Design — **nenhum código nesta etapa**. Objetivo: entregar a primeira Capability funcional da Wave 6 com consumidor HTTP real, preservando integralmente o Executive Orchestrator e os princípios permanentes já estabelecidos, resolvendo nesta mesma missão as questões arquiteturais remanescentes necessárias ao Decision Support.

**Precondição:** Executive Orchestrator encerrado (D-147), 5/5 etapas, 54 testes, suíte completa 822 passed; `WAVE-6-PROGRESS-ASSESSMENT.md` (D-148) — achado central: nenhuma rota HTTP, nenhum consumidor de produção, Decision Support é a Capability com maior cobertura de evidência real (E2E, D-146).

---

## 0. O que já é oficial (não reaberto aqui)

| Decisão | Origem |
|---|---|
| `ExecutiveOrchestrator.run(capability, session, question, signals) -> ExecutiveIntelligenceResult` — assinatura, ciclo, request-scoped | Technical Design Executive Orchestrator §1/§8 (D-141) |
| `Selection Rule` determinística, nunca LLM; `explicit` sempre tem precedência sobre `question` | D-137/D-138/D-143 |
| `AdvisorFramework.run()` executa exatamente um Advisor por chamada, preservado integralmente | Vision, Princípio 2; D-138 §2.4 |
| Correlação estritamente estrutural (`STRUCTURAL_PAIRS`), nunca julga conteúdo | D-144; AR-17 §2 |
| Síntese consome exclusivamente `Explanation`s já coletadas, nunca evidência bruta | D-145; AR-17 §2/§6 |
| `ExecutiveIntelligenceResult`: dois estados exaustivos, `.complete()`/`.insufficient_basis()` | D-140; `types.py` |
| Decision Support = Seleção → Execução → Correlação → Síntese (as quatro operações) | AR-17 §2, Camada 2 |
| Nenhuma Capability implementa `AdvisorContract`, nenhuma acessa `AIContextEngine`/`DomainService`/repositório diretamente | Vision, Princípios 1/3/8/11; AR-17 §6 |
| `EnterpriseMemoryService` fora do escopo desta Capability (Founder, §9) | Founder Decision — Wave 6/Decision Support |
| Workflow Runtime fora do caminho síncrono do Decision Support (Founder, §10) | Founder Decision — Wave 6/Decision Support |
| Executive Briefing e Recommendation Package permanecem fora de escopo (Founder, §11) | Founder Decision — Wave 6/Decision Support |

Este documento nunca reabre nenhuma destas decisões.

---

## 1. Questões arquiteturais remanescentes resolvidas nesta missão

Per o Wave 6 Progress Assessment (D-148, §9), seis questões do Kickoff §8 permaneciam sem decisão explícita. Duas já foram resolvidas diretamente pelo Founder nesta própria "Founder Decision — Wave 6/Decision Support" (§9 EnterpriseMemory, §10 Workflow Runtime, formalizadas em §0 acima). As quatro restantes, necessárias para Decision Support especificamente, são resolvidas agora:

### 1.1 §8.3 — Execuções paralelas ou sequenciais?

**Decisão: sequenciais, mantendo a implementação já existente e testada (`orchestrator.py`, `for identity in outcome.selected`).**

Fundamentação: cada execução já é independente (nenhuma depende do resultado de outra — Technical Design original §3), então paralelizar seria uma otimização pura de performance, nunca uma mudança de comportamento. Decision Support tipicamente seleciona 2-3 Advisors (AR-17 §3); nenhuma evidência real de que a latência sequencial de 2-3 chamadas seja um problema para o usuário existe hoje — introduzir paralelismo agora seria generalizar sem necessidade demonstrada (Grounded before Generalized, D-104/D-118). Sequencial também mantém a ordem de execução determinística e idêntica à ordem do catálogo (`ADVISOR_IDENTITY_CATALOG`), o que simplifica observabilidade e reprodutibilidade do Composition Trace em produção. Paralelismo fica explicitamente **deferred**, revisitável apenas se medição real de latência em produção demonstrar necessidade.

### 1.2 §8.4 — Existe cache?

**Decisão: nenhum cache nesta primeira Capability.**

Fundamentação: nenhum dos 8 Advisors da Wave 5 usa cache hoje; introduzir cache exclusivamente para Decision Support criaria um componente de infraestrutura paralelo sem que nenhum outro caminho de código o reaproveite — exatamente o tipo de arquitetura paralela que o Tech Lead nunca deve criar (CLAUDE.md). Sem tráfego de produção real, qualquer política de invalidação seria especulativa. Deferred, revisitável apenas com dado real de custo/latência em produção.

### 1.3 §8.7 — Como medir confiança?

**Decisão: nenhum score de confiança numérico. O único sinal exposto é o binário `had_evidence` já existente em `ExecutionTraceEntry`.**

Fundamentação: o Princípio 9 (Vision) proíbe permanentemente qualquer ranking/score que decida o que é mais importante — um score de confiança seria lido pelo executivo exatamente como um ranking implícito entre Advisors, violando esse princípio por interpretação razoável. O binário já produzido (`had_evidence`, Composition Trace) é suficiente para o contrato de resposta desta Capability (§4 abaixo).

### 1.4 §8.8 — Como evitar duplicação de citação?

**Decisão: não resolvida algoritmicamente nesta Capability — citações são expostas por Advisor, nunca deduplicadas ou mescladas.**

Fundamentação: o Princípio 4 (Vision) exige que toda citação permaneça atribuível a exatamente um Advisor de origem, usando a citação real já produzida — deduplicar exigiria decidir qual Advisor "é dono" da citação compartilhada, uma forma de julgamento de conteúdo que nenhum componente da Wave 6 tem autorização para fazer (mesmo tripwire de AR-17 §6). Se dois Advisors selecionados citam o mesmo `AnalysisRecord` subjacente, a resposta mostra a citação duas vezes, uma por Advisor — transparente, nunca escondido. Deferred, revisitável apenas se confusão real do usuário for observada em produção.

---

## 2. Consumidor de Produção — Rota HTTP

**`POST /decision-support/ask`**, em `src/api/routes/intelligence.py` (mesmo módulo dos outros 8 `ask_*_advisor`, nunca um módulo paralelo).

A rota é um **adaptador fino** — sua única responsabilidade é: (1) construir `SessionContext` a partir do `RequestContext` já autenticado (idêntico a `ask_executive_advisor`/`ask_strategy_advisor`); (2) construir `AdvisorFramework` e `ExecutiveOrchestrator` via injeção de dependência (mesmo padrão de composição de todo objeto de domínio nesta camada, nunca lógica nova); (3) construir `SelectionSignals` a partir do `DecisionSupportRequest`; (4) chamar `orchestrator.run(Capability.DECISION_SUPPORT, session, request.question, signals)` dentro de um `try/except AdvisorExecutionError` (mesma tradução de erro de fronteira já usada nas 8 rotas — não é uma decisão de domínio, é mapeamento HTTP); (5) mapear o `ExecutiveIntelligenceResult` retornado para `DecisionSupportResponse` — uma transformação de dados pura, nenhuma lógica condicional além de espelhar os campos já decididos pelo Orchestrator.

**A rota nunca:** seleciona Advisors, correlaciona respostas, sintetiza, consulta evidências, acessa `DomainService`/repositório, acessa `AIContextEngine`/`RagPipeline` diretamente. Todas essas responsabilidades permanecem exclusivamente no `ExecutiveOrchestrator` e nos Advisors — a rota nunca importa `AIContextEngine`, `KnowledgeRepository`, `PgVectorRepository`, ou qualquer `EvidenceAssembler` diretamente (mesma checagem estrutural via `ast` já aplicada a `orchestrator.py`/`provisioning.py` nos testes da Etapa 3, D-144, estendida a este módulo na Etapa 1 de implementação, §9).

**Dependências FastAPI (todas já existentes, uma nova adicionada):**

| Dependência | Origem | Nova? |
|---|---|---|
| `get_request_context` | `src/api/identity_context.py` | Não |
| `require_permission("intelligence.read")` | `src/api/authorization.py` | Não — mesma permissão que protege as 8 rotas de Advisor (leitura, nunca cria/edita/dispara análise); nenhuma nova permissão é criada (CLAUDE.md: nunca criar novo registry) |
| `build_repository` | `src/api/dependencies.py` | Não |
| `build_provider` | `intelligence.py` | Não |
| `build_prompt_registry` (`base_path="src/agents"`) | `intelligence.py` | Não — usada para `AdvisorFramework`, exatamente como nas 8 rotas |
| `build_rag_pipeline` | `intelligence.py` | Não |
| `build_domain_service` | `portfolio.py`, já importada por `intelligence.py` | Não |
| `build_orchestrator_prompt_registry` (`base_path="src/services"`) | Nova, `intelligence.py` | **Sim** — função de uma linha, `return PromptRegistry(base_path="src/services")`, espelhando exatamente `build_prompt_registry()`; nunca um novo `PromptRegistry` construído inline na rota. Necessária porque `synthesize()` exige `base_path="src/services"` (D-145: nunca `"src/agents"`, para preservar o catálogo fechado de 8 Advisors) — distinto do `PromptRegistry` que o `AdvisorFramework` usa |

Nenhuma outra dependência nova. `enforce_rate_limit`/`verify_api_key` já protegem todo o router (`APIRouter(dependencies=[...])`), herdados automaticamente.

---

## 3. Contrato de Entrada

**`DecisionSupportRequest`**

| Campo | Tipo | Obrigatório | Propósito |
|---|---|---|---|
| `question` | `str` (3-2000 chars, mesma validação `_ensure_has_content` das 8 rotas) | Sim | Identifica a pergunta — alimenta `SelectionSignals.question` (correspondência lexical determinística) e é repassada como a própria pergunta a cada Advisor selecionado |
| `project_name` | `str \| None` | Não | Sinal de escopo — alimenta `OrchestrationScope.project_name`, usado apenas pelos Advisors project-scoped selecionados (Risk, Delivery) |
| `portfolio_id` | `int \| None` | Não | Sinal de escopo — alimenta `OrchestrationScope.portfolio_id`, precondição estrutural para o Portfolio Advisor ser selecionável (`ADVISOR_NAMES_REQUIRING_PORTFOLIO_ID`) |

**Nenhum campo de Capability** — a Capability é `DECISION_SUPPORT` por construção da própria rota (`/decision-support/ask`), nunca um parâmetro do corpo. Isso segue exatamente a mesma simetria já estabelecida pelas 8 rotas de Advisor: nenhuma delas pergunta "qual Advisor" no corpo, porque a própria rota já o identifica. Uma Capability futura (ex.: `/cross-advisor-correlation/ask`) teria sua própria rota dedicada, nunca um parâmetro compartilhado — decisão consistente com o próprio AR-17 §2 ("nenhuma Capability inventa mecânica própria... mas cada uma é uma composição fixa").

**Nenhum campo `explicit` (sinais lexicais avançados) é exposto.** `SelectionSignals.explicit` continua acessível apenas internamente — expor uma lista de termos/nomes de Advisor no contrato HTTP vazaria vocabulário interno do catálogo (`catalog.VOCABULARY`) para o consumidor externo, acoplando a rota a detalhes de implementação da Selection Rule. A correspondência lexical via `question` já é suficiente, determinística e reproduzível para o primeiro consumidor. Campo especulativo evitado (Founder, §2: "não adicionar campos especulativos").

---

## 4. Contrato de Saída

**`DecisionSupportResponse`**, derivado inteiramente de `ExecutiveIntelligenceResult` (nenhum campo interno novo inventado — apenas exposição funcional dos campos já decididos pela Camada 4 da AR-17):

| Campo | Tipo | Origem em `ExecutiveIntelligenceResult` |
|---|---|---|
| `capability` | `str` | `result.capability.value` (`"decision_support"`) |
| `insufficient_basis` | `bool` | `result.is_insufficient_basis` |
| `insufficient_basis_reason` | `str \| None` | `result.insufficient_basis_reason.value` se presente, senão `None` (`"selection_empty"` / `"collection_empty"`) |
| `answer` | `str \| None` | `result.synthesis` — `None` sempre que `insufficient_basis` é `True` (nunca síntese sem base, `__post_init__` do próprio tipo já garante isso) |
| `advisors_used` | `list[str]` | `[identity.name for identity in result.advisor_identities]` |
| `citations` | `list[DecisionSupportCitation]` | Achatado de `result.explanations`: para cada `AttributedExplanation`, para cada `Evidence` em `.explanation.recommendation.cited_evidence` → `{advisor_name, source_type, source_id, source_label}` |
| `composition_trace` | `DecisionSupportCompositionTrace` | Mapeamento direto de `result.composition_trace` (abaixo) |

**`DecisionSupportCompositionTrace`** (espelha `CompositionTrace`, AR-17 §4/Camada 3):

| Campo | Tipo | Origem |
|---|---|---|
| `selection_signals` | `list[str]` | `composition_trace.selection.signals` |
| `selected_advisor_names` | `list[str]` | `composition_trace.selection.selected_advisor_names` |
| `advisors_used` | `list[{advisor_name, had_evidence}]` | `composition_trace.executions` |
| `correlations` | `list[{advisor_names, is_structural_pair}]` | `composition_trace.correlations` |
| `synthesis_source_advisor_names` | `list[str] \| None` | `composition_trace.synthesis.source_advisor_names` se presente, senão `None` |

**Não expostos:** `Explanation.rationale` bruto de cada Advisor individualmente (a `answer` da Síntese já consolida a narrativa; expor 2-3 rationales brutos adicionais seria a "estrutura interna desnecessária" que o Founder pediu para evitar, §3) e qualquer campo de `Evidence.content`/`Evidence.metadata` completo (apenas `source_type`/`source_id`/`source_label`, suficiente para rastreabilidade sem vazar o payload bruto do `AnalysisRecord`/`Chunk`).

**Quando `insufficient_basis` é `True`:** `answer` é `None`, `citations` é `[]`, `composition_trace.correlations` é `[]`, `composition_trace.synthesis_source_advisor_names` é `None` — o cliente nunca precisa inspecionar `answer` para decidir se há resposta; o campo `insufficient_basis` é a fonte de verdade única, exatamente como `ExecutiveIntelligenceResult.is_insufficient_basis` já é no domínio.

---

## 5. Fluxo Completo

```
Usuário (frontend)
  │  pergunta executiva + escopo opcional (project_name/portfolio_id)
  ▼
POST /decision-support/ask                         (rota, adaptador fino)
  │  constrói SessionContext, AdvisorFramework, ExecutiveOrchestrator, SelectionSignals
  ▼
ExecutiveOrchestrator.run(DECISION_SUPPORT, ...)    (preservado integralmente, D-141/D-146)
  │
  ├─ Selection Rule (determinística)                → Advisor Identities selecionadas
  │     Selection Empty? → insufficient_basis, resposta HTTP imediata, zero chamadas LLM
  │
  ├─ Execução: AdvisorFramework.run() × N            → Explanations (uma chamada por Advisor)
  │     Collection Empty? → insufficient_basis, resposta HTTP, zero chamada de Síntese
  │
  ├─ Correlação estrutural                           → CorrelationFinding(s)
  │
  └─ Síntese (synthesize(), reutiliza render_analyst_prompt()/
     ObservabilityRecorder.record_call())            → resposta executiva única
  ▼
ExecutiveIntelligenceResult                          (dois estados exaustivos)
  ▼
DecisionSupportResponse                              (mapeamento puro, rota)
  ▼
Resposta HTTP → BFF (proxy fino, idêntico ao de risk-advisor) → hook → componente → usuário
```

Nenhuma etapa deste fluxo introduz um componente novo além da rota e dos contratos Pydantic — `ExecutiveOrchestrator`, `AdvisorFramework`, os 8 Advisors, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine` permanecem exatamente como estão.

---

## 6. Selection Rules aplicáveis

Nenhuma mudança à `Selection Rule` em si (`evaluate_selection_rule()`, D-143) — Decision Support consome a mesma e única regra que qualquer outra Capability consumiria (AR-17 §5: "toda Capability, sem exceção, consome a mesma e única Selection Rule"). A rota apenas traduz o `DecisionSupportRequest` em `SelectionSignals(question=request.question, scope=OrchestrationScope(project_name=request.project_name, portfolio_id=request.portfolio_id))` — `explicit` permanece `frozenset()` (vazio), então a correspondência é sempre lexical via `question` (§1.1 da Selection Rule já implementada, D-143).

**Risco de escopo identificado e resolvido nesta seção:** se `project_name` é omitido e a Selection Rule seleciona um Advisor project-scoped (Risk, Delivery), `provisioning.py` chama `framework.gather_context(org_id, None, kind=...)`, que resolve para "sem filtro de projeto" (`AIContextEngine.gather()`, `resolve_scope_id(project_name=None)` → `scope_id=None` → nenhum filtro de projeto aplicado) — ou seja, evidência agregada de **todos** os projetos da organização daquele `kind`, não de um projeto específico. Isso já é o comportamento real e testado de `AIContextEngine.gather()` desde a Wave 3 (D-008), nunca alterado aqui — mas é a **primeira vez que um caminho de produção o alcança com `project_name=None`** (as 8 rotas de Advisor individuais sempre exigem `project_name` quando usam esse `kind`). **Decisão: comportamento aceito, documentado explicitamente como intencional** — uma pergunta de Decision Support sem projeto nomeado razoavelmente produz uma síntese que considera risco/status de toda a organização, o mesmo padrão que PMO/Executive/Strategy Advisor já produzem quando confrontados com o mesmo `kind` sem escopo de projeto. Nenhum código muda por esta decisão; é uma confirmação de comportamento já existente, registrada como risco monitorado (§10).

---

## 7. Composition Trace

Nenhuma alteração ao tipo `CompositionTrace` (`types.py`) — a rota apenas expõe seus campos já existentes via `DecisionSupportCompositionTrace` (§4). Nenhum campo novo é adicionado ao domínio para satisfazer o contrato HTTP — o contrato HTTP é estritamente um subconjunto serializável do que o domínio já produz.

## 8. Base Insuficiente

Os dois estados estruturais (`InsufficientBasisReason.SELECTION_EMPTY`/`COLLECTION_EMPTY`) são preservados sem alteração. A rota:

- Nunca chama `synthesize()` quando `result.is_insufficient_basis` é `True` — já garantido pelo próprio `ExecutiveOrchestrator.run()` (D-144/D-145), a rota não precisa (e não deve) reimplementar essa checagem.
- Sempre retorna **HTTP 200** com `insufficient_basis: true` no corpo — nunca um código de erro HTTP (4xx/5xx). Base insuficiente não é uma falha da requisição; é uma resposta estrutural válida e esperada (Domain Blueprint §4, D-138: "dois estados exaustivos", nenhum dos dois é um erro).

---

## 9. Preservação Arquitetural

Preservados integralmente, sem alteração estrutural: `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, Workflow Runtime, Event Pipeline, Knowledge Platform, Enterprise Domain, os 8 Enterprise Advisors, contratos públicos/HTTP existentes (nenhuma rota de Advisor individual é alterada). O Executive Orchestrator (`src/services/executive_orchestrator/`) recebe **zero alteração de código** — a rota apenas o instancia e chama `.run()`, exatamente como já testado em `tests/test_executive_orchestrator_e2e.py` (D-146). Toda checagem `ast` que já garante ausência de importação direta de infraestrutura em `orchestrator.py`/`provisioning.py`/`synthesis.py` é estendida, na Etapa 1 de implementação, para cobrir também o novo bloco de rota em `intelligence.py` (mesma disciplina de teste, escopo ampliado apenas ao novo código).

---

## 10. Riscos

| Risco | Mitigação decidida nesta TD |
|---|---|
| `project_name=None` agrega evidência de todos os projetos para Advisors project-scoped (§6) | Comportamento aceito e documentado como intencional; monitorado, nunca escondido — citações sempre mostram de qual projeto cada evidência veio (`Evidence.metadata`) |
| Latência: até 2-3 chamadas de Advisor + 1 de Síntese, sequenciais | Timeout do BFF proporcionalmente maior que o de rotas de Advisor único (que usam 60s para 1 chamada) — recomendado 120s para a Etapa 2 (frontend); decisão de paralelismo deferida (§1.1) |
| Rate limiting compartilhado (`enforce_rate_limit`) atingido mais rápido por requisição (múltiplas chamadas LLM por requisição HTTP) | Nenhuma mudança ao limitador nesta Capability — risco operacional, não arquitetural; revisitar apenas com abuso real observado |
| Citação duplicada entre Advisors que compartilham a mesma evidência subjacente (§1.4) | Aceito, transparente, nunca deduplicado nem escondido; revisitar apenas com confusão real do usuário observada |
| `AdvisorExecutionError` de qualquer Advisor selecionado propaga e aborta toda a requisição (nenhum resultado parcial) | Comportamento idêntico ao já estabelecido em toda a Wave 5 (qualquer rota de Advisor individual já retorna 502 inteiro em falha do LLM) — Decision Support não introduz uma semântica de falha parcial nova, nem deveria (uma síntese sobre resultado parcial violaria a integridade da Síntese, Princípio 6) |

Nenhum risco listado é bloqueante para a implementação.

---

## 11. Consumidor Frontend Mínimo

**Objetivo único: demonstrar usuário → pergunta executiva → Decision Support → Executive Orchestrator → Advisors → resposta integrada. Nenhum dashboard novo, nenhuma experiência ampla (Founder, §12).**

Três arquivos novos, seguindo exatamente o único precedente real de consumidor de Advisor já existente (`risk-advisor`, único dos 8 Advisors com frontend, D-0xx anterior à Wave 6):

1. **`web/app/api/bff/decision-support/route.ts`** — proxy fino, mesmo formato de `.../risk-advisor/route.ts` (timeout, validação de `question`, mapeamento de erro 429/422/502/504) — sem segmento `[projectName]` na URL (Decision Support não é sempre project-scoped); `project_name`/`portfolio_id` opcionais no corpo JSON repassados verbatim ao backend. **Primeira rota BFF org-level de uma Capability/Advisor** (nenhum dos 8 Advisors Classe B/D tem hoje frontend algum) — estruturalmente consistente com o único padrão existente, apenas sem o parâmetro de rota fixo.
2. **`web/lib/hooks/use-ask-decision-support.ts`** — hook de mutação, mesmo formato de `use-ask-risk-advisor.ts` (estado de pending/erro/dados, chama o BFF acima).
3. **`web/components/dashboard/decision-support-panel.tsx`** — um painel autocontido: campo de pergunta, botão de envio, e exibição do resultado (`answer` quando presente; banner explícito quando `insufficient_basis`; lista de `advisors_used`; citações agrupadas por Advisor). Adicionado como **mais um painel** em `web/app/dashboard/page.tsx`, seguindo a mesma composição já existente de painéis independentes (`AIRecommendationsPanel`, `DecisionCenterPanel`, `ExecutiveFocusPanel`, etc.) — nenhuma reestruturação da página, nenhuma nova rota de navegação.

Nenhuma tela nova, nenhum item de menu novo — a Capability aparece dentro do Dashboard Executivo já existente.

---

## 12. Segurança / RBAC

Idêntico ao padrão das 8 rotas de Advisor: `require_permission("intelligence.read")` (leitura, nunca cria/edita/dispara análise — Decision Support nunca persiste nada), organization-scoped via `context.organization.organization_id` (nunca um valor fornecido pelo cliente), `verify_api_key`/`enforce_rate_limit` herdados do router. **Nenhuma nova permissão criada** (CLAUDE.md: nunca criar novo registry) — reuso exato da permissão já validada em toda a Security Hardening Gate (D-05x) e em todas as 8 rotas de Advisor.

---

## 13. Testes (planejados para a implementação, não escritos nesta TD)

**Backend:**
- Unitários de mapeamento `ExecutiveIntelligenceResult → DecisionSupportResponse` (sem banco) — resultado completo, `insufficient_basis` (ambos os dois motivos), citações achatadas corretamente atribuídas por Advisor.
- Integração via `TestClient`, Advisors reais (`RiskAdvisorAgent`/`DeliveryAdvisorAgent`), PostgreSQL real — mesmo padrão de `test_executive_orchestrator_e2e.py`: pergunta real → 200 com `answer`/`advisors_used`/`composition_trace` íntegros; pergunta sem sinal relevante → 200 com `insufficient_basis: true`; `AdvisorExecutionError` → 502; ausência de `intelligence.read` → 403; `question` inválida → 422.
- `ast`: nenhuma importação direta de `AIContextEngine`/`DomainService`/repositório/`KnowledgeRepository` no bloco de rota (mesma disciplina de `orchestrator.py`/`provisioning.py`).

**Frontend:**
- `route.test.ts` do BFF (mesmo formato de `risk-advisor/route.test.ts`): validação de corpo, timeout, mapeamento de erro.
- `use-ask-decision-support.test.tsx` (mesmo formato de `use-ask-risk-advisor.test.tsx`).
- Teste de componente do painel: estado vazio, resposta completa, banner de base insuficiente.

**E2E (Playwright):** um spec provando a cadeia visível ao usuário — pergunta digitada no painel do Dashboard → resposta integrada exibida, citando ao menos dois Advisors, mesmo padrão de `e2e/workspace.spec.ts` (Risk Advisor).

---

## 14. Estratégia Incremental de Implementação

Três etapas independentes, cada uma com verificação completa antes da próxima (mesma disciplina do Executive Orchestrator, D-142 a D-146) — **nenhuma etapa depende de comportamento ainda não implementado da próxima**:

- **Etapa 1 — Rota HTTP backend**: `DecisionSupportRequest`/`DecisionSupportResponse` (e tipos auxiliares), `build_orchestrator_prompt_registry()`, `POST /decision-support/ask`, testes backend completos (§13). Sem frontend. Resultado: Decision Support alcançável via HTTP real, verificável por `curl`/Postman/teste automatizado.
- **Etapa 2 — Consumidor frontend mínimo**: BFF, hook, `DecisionSupportPanel`, integração ao Dashboard, testes frontend (§13). Resultado: usuário real consegue perguntar e ver a resposta integrada na aplicação.
- **Etapa 3 — Validação E2E e fechamento do Epic**: spec Playwright, `git diff --stat` confirmando preservação dos componentes protegidos (§9), atualização da Wave 6 Delivery Matrix (Decision Support: Partially Delivered → **Delivered**, único critério objetivo do Kickoff §11.3 agora satisfeito), Executive Report.

Cada etapa recebe seu próprio commit independente, sua própria entrada no Decision Log, e verificação completa (`ruff`/`tsc`/`eslint`/suíte completa) antes de avançar — mesma disciplina já validada em toda a implementação do Executive Orchestrator.

---

## 15. Critérios de Encerramento deste Epic

1. `POST /decision-support/ask` em produção, respondendo com Advisors e evidência reais.
2. Contrato de resposta estável, documentado, cobrindo os dois estados exaustivos.
3. Consumidor frontend mínimo funcional, sem dashboard novo.
4. Testes backend + frontend + E2E passando, suíte completa sem regressão.
5. Preservação de todos os componentes protegidos confirmada por `git diff --stat`.
6. Wave 6 Delivery Matrix atualizada: Decision Support reclassificada de Partially Delivered para Delivered.

---

## Recomendação

**GO para a implementação, sujeito a nova autorização explícita do Founder.**

Este Technical Design resolveu as quatro questões arquiteturais remanescentes necessárias ao Decision Support (§1: paralelismo, cache, confiança, duplicação de citação — todas deferred por ausência de necessidade real demonstrada, nunca decididas contra, per Grounded before Generalized) e definiu integralmente: a rota HTTP como adaptador fino (§2), o contrato de entrada mínimo sem campos especulativos (§3), o contrato de saída derivado exclusivamente de `ExecutiveIntelligenceResult` (§4), o fluxo completo ponta a ponta (§5), a aplicação inalterada da Selection Rule com um risco de escopo identificado e explicitamente aceito (§6), a preservação do Composition Trace e dos dois estados de Base Insuficiente (§7/§8), a preservação arquitetural total (§9), os riscos residuais e suas mitigações (§10), o consumidor frontend mínimo sem nova experiência (§11), a reutilização da permissão RBAC existente sem novo registry (§12), o plano de testes (§13) e a estratégia incremental de três etapas (§14). Nenhuma inconsistência arquitetural foi encontrada entre este desenho e qualquer decisão já registrada na Vision, AR-16, AR-17, no Domain Blueprint, ou no Technical Design original do Executive Orchestrator. **Nenhum código foi escrito nesta etapa.** Retornando obrigatoriamente para Executive Review — nenhuma implementação deverá começar antes da aprovação explícita do Founder.
