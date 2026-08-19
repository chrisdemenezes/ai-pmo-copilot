# Technical Design — Decision Support (primeiro consumidor de produção da Executive Intelligence)

Produzida sob mandato da "Founder Decision — Wave 6 / Decision Support" (APPROVED do Wave 6 Progress Assessment, D-148; próximo ciclo institucional: Decision Support), que autoriza exclusivamente este Technical Design — **nenhum código nesta etapa**. Objetivo: entregar a primeira Capability funcional da Wave 6 com consumidor HTTP real, preservando integralmente o Executive Orchestrator e os princípios permanentes já estabelecidos, resolvendo nesta mesma missão as questões arquiteturais remanescentes necessárias ao Decision Support.

**Revisão (esta versão):** incorpora a "Founder Decision — Eliminação do Risco de Escopo Implícito", que reviu a primeira versão deste Technical Design (D-150) e determinou a eliminação estrutural — não mitigação — do risco "`project_name` omitido agrega evidência da organização inteira" identificado na §6/§10 originais. Toda referência a esse risco como "aceito e monitorado" está **superada** por esta revisão; §1.5, §3, §5, §6, §9, §10 e §11 foram reescritos.

**Precondição:** Executive Orchestrator encerrado (D-147), 5/5 etapas, 54 testes, suíte completa 822 passed; `WAVE-6-PROGRESS-ASSESSMENT.md` (D-148); Technical Design v1 (D-150) revisado por esta Founder Decision antes de qualquer código.

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
| `EnterpriseMemoryService` fora do escopo desta Capability | Founder Decision — Wave 6/Decision Support, §9 |
| Workflow Runtime fora do caminho síncrono do Decision Support | Founder Decision — Wave 6/Decision Support, §10 |
| Executive Briefing e Recommendation Package permanecem fora de escopo | Founder Decision — Wave 6/Decision Support, §11 |
| **Executive Intelligence Explicit Scope** — nenhuma Capability infere escopo pela ausência de informação; todo escopo é `project`/`portfolio`/`organization`, sempre declarado explicitamente, nunca um fallback | Founder Decision — Eliminação do Risco de Escopo Implícito; registrado como Princípio 13 permanente (§12 abaixo) |

Este documento nunca reabre nenhuma destas decisões.

---

## 1. Questões arquiteturais remanescentes resolvidas nesta missão

Per o Wave 6 Progress Assessment (D-148, §9), seis questões do Kickoff §8 permaneciam sem decisão explícita. Duas já haviam sido resolvidas diretamente pelo Founder na "Founder Decision — Wave 6/Decision Support" (§9 EnterpriseMemory, §10 Workflow Runtime, formalizadas em §0 acima). Quatro foram resolvidas na primeira versão deste TD (D-150):

### 1.1 §8.3 — Execuções paralelas ou sequenciais?

**Decisão: sequenciais, mantendo a implementação já existente e testada (`orchestrator.py`, `for identity in outcome.selected`).** Fundamentação inalterada desde D-150: cada execução já é independente; paralelizar seria otimização pura, deferred por ausência de necessidade real demonstrada (Grounded before Generalized).

### 1.2 §8.4 — Existe cache?

**Decisão: nenhum cache nesta primeira Capability.** Inalterado desde D-150 — evita infraestrutura paralela sem consumidor comprovado.

### 1.3 §8.7 — Como medir confiança?

**Decisão: nenhum score numérico; apenas o binário `had_evidence` já existente.** Inalterado desde D-150 — respeito ao Princípio 9 (nenhum ranking).

### 1.4 §8.8 — Como evitar duplicação de citação?

**Decisão: não deduplicada, exposta por Advisor.** Inalterado desde D-150 — respeito ao Princípio 4 (proveniência exclusiva por Advisor).

### 1.5 Risco de escopo implícito — eliminação estrutural (esta revisão)

O risco identificado em D-150 §6/§10 ("`project_name` omitido agrega evidência da organização inteira para Advisors project-scoped") não é mais tratado como risco residual aceito. A Founder Decision determinou que esse comportamento nunca deveria ter sido classificado como aceitável — a causa raiz não é "o que acontece quando `project_name` é `None`" (isso está correto e documentado, §6 abaixo), mas sim **que o contrato permitia `project_name` ser `None` por omissão, sem o consumidor jamais ter declarado a intenção de um escopo organizacional.** A eliminação é estrutural: o contrato de entrada deixa de aceitar campos de escopo opcionais soltos e passa a exigir um `scope` explícito, com três variantes estruturalmente exaustivas e mutuamente exclusivas (`project`/`portfolio`/`organization`) — detalhado em §3, §5, §6 e §7 abaixo.

---

## 2. Consumidor de Produção — Rota HTTP

**`POST /decision-support/ask`**, em `src/api/routes/intelligence.py` (mesmo módulo dos outros 8 `ask_*_advisor`, nunca um módulo paralelo). Seção inalterada desde D-150: a rota permanece um **adaptador fino** — constrói `SessionContext`/`AdvisorFramework`/`ExecutiveOrchestrator` via DI, chama `orchestrator.run(...)` dentro de um `try/except AdvisorExecutionError`, mapeia o resultado. A única adição desta revisão é a etapa de **resolução de escopo** entre a validação do contrato de entrada e a construção de `SelectionSignals` — descrita em §5/§6, ainda inteiramente dentro da rota (nunca dentro do Executive Orchestrator), e ainda sem nenhuma decisão de domínio: apenas tradução de um identificador validado (`project_id`/`portfolio_id`) para o `OrchestrationScope` que o Orchestrator já aceita.

**Dependências FastAPI** — inalteradas desde D-150 (`get_request_context`, `require_permission("intelligence.read")`, `build_repository`, `build_provider`, `build_prompt_registry`, `build_rag_pipeline`, `build_domain_service`, `build_orchestrator_prompt_registry` — esta última nova desde D-150, nenhuma outra adicionada por esta revisão). `DomainService`, já uma dependência existente da rota (necessária para `ExecutiveOrchestrator`), é reaproveitada também para a resolução de escopo (§6) — nenhuma dependência nova.

---

## 3. Contrato de Entrada (revisado — Explicit Scope)

**`DecisionSupportRequest`**

| Campo | Tipo | Obrigatório |
|---|---|---|
| `question` | `str` (3-2000 chars, mesma validação `_ensure_has_content` das 8 rotas) | Sim |
| `scope` | `DecisionSupportScope` (objeto aninhado, abaixo) | **Sim — sem valor default. Ausência de `scope` é rejeitada pela validação do próprio contrato (422), nunca interpretada como escopo organizacional implícito.** |

**`DecisionSupportScope`**

| Campo | Tipo | Obrigatório |
|---|---|---|
| `type` | `"project" \| "portfolio" \| "organization"` (enum fechado, três valores, nenhum quarto) | Sim |
| `project_id` | `int \| None` | Obrigatório quando `type == "project"`; **proibido** (deve ser omitido/`None`) nos outros dois casos |
| `portfolio_id` | `int \| None` | Obrigatório quando `type == "portfolio"`; **proibido** nos outros dois casos |

**Validação estrutural (na camada Pydantic do contrato, antes de qualquer chamada ao Executive Orchestrator):**

| `type` | `project_id` | `portfolio_id` | Resultado |
|---|---|---|---|
| `"project"` | presente | ausente | Válido |
| `"project"` | ausente | qualquer | **422** — identificador do Project obrigatório |
| `"project"` | presente | presente | **422** — `portfolio_id` proibido quando `type=project` |
| `"portfolio"` | ausente | presente | Válido |
| `"portfolio"` | qualquer | ausente | **422** — `portfolio_id` obrigatório |
| `"portfolio"` | presente | presente | **422** — `project_id` proibido quando `type=portfolio` |
| `"organization"` | ausente | ausente | Válido |
| `"organization"` | presente ou presente | — | **422** — nenhum identificador permitido quando `type=organization` |
| (campo `scope` ausente do corpo da requisição) | — | — | **422** — ausência de escopo é sempre rejeitada, nunca convertida em `organization` |

Esta tabela satisfaz integralmente o Founder §3 ("qualquer combinação inválida deverá falhar antes da execução do Executive Orchestrator") — a validação ocorre inteiramente na camada de contrato (Pydantic), antes de qualquer construção de `SessionContext`/`ExecutiveOrchestrator`/`SelectionSignals`.

### 3.1 `project_id` vs. `project_name` — decisão e evidência de código

**Decisão: `project_id`.** O identificador estrutural correto de Project é `project_id`, nunca `project_name`, fundamentado inteiramente no modelo de domínio já existente:

- `AIContextEngine.gather()` (`src/services/ai_foundation/context_engine.py:19-27`), no próprio comentário de código: *"TD-008 Fase 3b, Etapa 4a: scope by project_id. The Analyst still receives the project by name (the user informs a name); it is resolved to an id before the query -- never used as a filter key."* — o próprio Foundation já declara `project_id` como a chave estrutural; `project_name` é tratado, desde a Wave 3, como conveniência de entrada humana, nunca como identidade.
- `AnalysisRepository.resolve_scope_id()` (`src/database/repository.py:103-133`) já aceita `project_id` diretamente como "chave exata" (`if project_id is not None: return project_id, False`), preferido sobre resolução por nome.
- `EnterpriseRepository.resolve_project_reference()` (`src/database/enterprise_repository.py:257-291`) já implementa a checagem de posse organizacional exata necessária (§4 abaixo) exclusivamente para o caminho por `project_id`: *"project_id given -> must exist AND belong to organization_id, else ProjectNotFoundError (a cross-organization id is reported as not-found, never confirmed)."*
- `Project` (`src/database/models.py:199-213`) tem `UniqueConstraint("organization_id", "name")` — `name` é único dentro da organização, mas `id` é a chave primária real; toda a migração TD-008 Fase 3b (Épico W3-1, D-05x) já existiu especificamente para mover a plataforma de `project_name` para `project_id` como identidade de filtro.
- O próprio `PortfolioAdvisorRequest` (já em produção desde a Wave 5) usa `portfolio_id: int`, nunca um nome — o precedente já estabelecido para o outro escopo estrutural (`Portfolio`) é `id`, nunca `name`.

Preferir `project_id` não é conveniência de API — é a única opção consistente com uma migração institucional já concluída (D-05x/TD-008) e com o próprio comentário do componente que a evidência atravessa.

**`project_name` nunca aparece no contrato do Decision Support.** A rota resolve `project_id` → `Project` (via `DomainService.get_project`, §6) → `project.name` internamente, apenas para alimentar o campo já existente `OrchestrationScope.project_name` (§6) — o nome nunca é fornecido pelo cliente, apenas derivado, sempre a partir de um `project_id` já validado como pertencente à organização autenticada.

**Nenhum campo de Capability, nenhum campo `explicit`** — inalterado desde D-150 (§3 original), mesma fundamentação.

---

## 4. Contrato de Saída

Inalterado desde D-150 — `DecisionSupportResponse` continua derivado inteiramente de `ExecutiveIntelligenceResult` (`capability`/`insufficient_basis`/`insufficient_basis_reason`/`answer`/`advisors_used`/`citations`/`composition_trace`). Um novo motivo de resposta 4xx é adicionado antes que qualquer resultado seja produzido (§6):

| Situação | HTTP | Corpo |
|---|---|---|
| `scope` ausente ou combinação estruturalmente inválida (tabela §3) | 422 | Erro de validação Pydantic padrão |
| `scope.type=project`, `project_id` não pertence à organização autenticada | 404 | `{"detail": "Project not found"}` — mesmo formato de `ask_portfolio_advisor`/`resolve_project_scope` |
| `scope.type=portfolio`, `portfolio_id` não pertence à organização autenticada | 404 | `{"detail": "Portfolio not found"}` — idêntico a `ask_portfolio_advisor` |
| Escopo válido e resolvido | 200 | `DecisionSupportResponse`, como já definido |

---

## 5. Fluxo Completo (revisado)

```
Usuário (frontend)
  │  pergunta executiva + escopo OBRIGATÓRIO (project | portfolio | organization)
  ▼
POST /decision-support/ask                         (rota, adaptador fino)
  │  1. Pydantic valida DecisionSupportScope (tabela §3) → 422 se inválido/ausente
  │  2. Resolve o identificador (apenas quando type=project|portfolio):
  │       type=project    → DomainService.get_project(project_id, org_id) → 404 se None
  │       type=portfolio  → DomainService.get_portfolio(portfolio_id, org_id) → 404 se None
  │       type=organization → nada a resolver
  │  3. Constrói OrchestrationScope (campo por campo, §6) — NUNCA por omissão
  │  4. Constrói SessionContext, AdvisorFramework, ExecutiveOrchestrator, SelectionSignals
  ▼
ExecutiveOrchestrator.run(DECISION_SUPPORT, ...)    (preservado integralmente, D-141/D-146)
  │
  ├─ Selection Rule (determinística, com elegibilidade por escopo, §6)  → Advisor Identities
  │     Selection Empty? → insufficient_basis, resposta HTTP imediata, zero chamadas LLM
  │
  ├─ Execução: AdvisorFramework.run() × N            → Explanations (uma chamada por Advisor)
  │     Collection Empty? → insufficient_basis, resposta HTTP, zero chamada de Síntese
  │
  ├─ Correlação estrutural                           → CorrelationFinding(s)
  │
  └─ Síntese                                         → resposta executiva única
  ▼
ExecutiveIntelligenceResult → DecisionSupportResponse → BFF → hook → componente → usuário
```

Os passos 1-3 do bloco da rota são **inteiramente validação e resolução de identidade já existente** (Pydantic + `DomainService.get_project`/`get_portfolio`, ambos já em produção) — nenhuma decisão de domínio nova, nenhuma chamada ao Executive Orchestrator antes que o escopo esteja integralmente resolvido e validado.

---

## 6. Selection Rules e `OrchestrationScope` (revisado — Explicit Scope)

### 6.1 `OrchestrationScope` — Decisão A: contrato existente já correto, sem evolução

Per Founder §5, avaliado explicitamente: **`OrchestrationScope(project_name: str | None, portfolio_id: int | None)` já representa corretamente os três escopos — nenhuma evolução aditiva é necessária.**

Fundamentação: a distinção entre os três tipos de escopo é inferível, sem ambiguidade, a partir de qual campo está preenchido — `project_name` preenchido ⇒ escopo `project`; `portfolio_id` preenchido ⇒ escopo `portfolio`; ambos `None` ⇒ escopo `organization`. Essa inferência **já era estruturalmente correta antes desta revisão** — o que faltava não era um terceiro campo em `OrchestrationScope`, mas a **garantia, na fronteira HTTP, de que "ambos `None`" só pode significar "organização escolhida deliberadamente"**, nunca "nada foi informado". Essa garantia agora existe: `OrchestrationScope` só é construído pela rota (§5, passo 3) depois que `DecisionSupportScope` já foi validado como uma das três combinações exaustivas — nunca a partir de um corpo de requisição parcialmente preenchido. `OrchestrationScope` em si permanece **inteiramente inalterado** — zero linha de código modificada em `selection_rule.py` quanto a este tipo.

### 6.2 Impacto identificado sobre a Selection Rule interna do Executive Orchestrator — REQUER CONFIRMAÇÃO EXPLÍCITA

Per Founder §10: *"Se o grounding demonstrar que algum [componente protegido] precisa necessariamente mudar... PARAR. Apresentar a inconsistência e o impacto para Executive Review antes de qualquer alteração."* Este parágrafo é exatamente esse apresentar — nenhuma implementação prossegue sobre este ponto sem aprovação explícita.

**Achado de grounding:** dos 8 Enterprise Advisors, apenas 3 (`risk_advisor`, `delivery_advisor`, `portfolio_advisor`) efetivamente consomem `OrchestrationScope` em `provisioning.py`. Os outros 5 (`pmo_advisor`, `executive_advisor`, `strategy_advisor`, `document_advisor`, `governance_advisor`) são **incondicionalmente organization-scoped por desenho já estabelecido na Wave 5** — cada um deles ignora `scope.project_name`/`scope.portfolio_id` inteiramente, mesmo que estejam presentes (confirmado por leitura de `provisioning.py`: `PMOEvidenceAssembler.assemble(session.organization_id)`, `ExecutiveEvidenceAssembler.assemble(session.organization_id)`, `StrategyEvidenceAssembler.assemble(session.organization_id)`, `gather_rag_context(session.organization_id, question, ...)` para Document/Governance — nenhum recebe `scope` como parâmetro). Isso é consistente com os próprios contratos HTTP desses 5 Advisors, que hoje **não aceitam nenhum campo de escopo** (`PMOAdvisorRequest`/`ExecutiveAdvisorRequest`/`StrategyAdvisorRequest`: apenas `question`; Document/Governance: idem).

**Consequência para o Princípio 13 (Explicit Scope) sob `scope.type=project` ou `scope.type=portfolio`:** se a Selection Rule, hoje, selecionar por correspondência lexical um desses 5 Advisors sob uma pergunta de Decision Support com `scope.type=project`, esse Advisor executaria normalmente e retornaria evidência **de toda a organização** — fora do escopo `project` explicitamente solicitado, uma violação direta do Founder §7 ("Nenhum Advisor poderá receber evidência fora do scope explicitamente solicitado"). O mesmo vale para `risk_advisor`/`delivery_advisor` sob `scope.type=portfolio` (eles só sabem filtrar por `project_name`, nunca por `portfolio_id` — `gather_context()` não tem noção de portfólio).

**Correção necessária, estritamente aditiva:** uma nova tabela de elegibilidade por escopo em `catalog.py` (mesmo arquivo, mesmo padrão já usado por `ADVISOR_NAMES_REQUIRING_PORTFOLIO_ID`, adicionado sem remoção durante a própria Etapa 2 do Executive Orchestrator, D-143), consumida por uma nova condição em `_meets_structural_precondition()` (`selection_rule.py`) — a mesma função que já aplica a precondição do Portfolio Advisor, generalizada para todos os 8:

| Advisor | Escopos elegíveis | Fundamentação |
|---|---|---|
| `risk_advisor`, `delivery_advisor` | `project`, `organization` | `provisioning.py` já sabe filtrar por `project_name` (escopo `project`) ou agregar org-wide quando `project_name=None` (escopo `organization`, agora sempre deliberado, nunca acidental) — nunca sabe filtrar por `portfolio_id` |
| `portfolio_advisor` | `portfolio` | Já é a precondição existente desde D-143 (`ADVISOR_NAMES_REQUIRING_PORTFOLIO_ID`) — permanece, apenas reexpressa em termos de `scope.type` |
| `pmo_advisor`, `executive_advisor`, `strategy_advisor`, `document_advisor`, `governance_advisor` | `organization` | Incondicionalmente organization-scoped por desenho da Wave 5 (achado acima) — nunca elegíveis sob `scope.type=project`/`portfolio`, para que nunca produzam evidência mais ampla do que o escopo declarado |

**Por que isto é apresentado como impacto que requer confirmação, e não decidido silenciosamente:** `selection_rule.py`/`catalog.py` são parte do `ExecutiveOrchestrator`, nomeado explicitamente na lista de componentes protegidos do Founder (§10). Embora a mudança seja estritamente aditiva (uma nova tabela + uma nova condição dentro da função de precondição já existente, exatamente a mesma categoria de mudança que a introdução de `ADVISOR_NAMES_REQUIRING_PORTFOLIO_ID` já foi durante a Etapa 2 original, sem quebra de nenhum teste existente, sem alteração de comportamento para nenhuma seleção já testada e aprovada), este Technical Design **não presume autorização** para tocar esse arquivo — apresenta o achado e a mudança proposta para aprovação explícita do Founder, precisamente como mandatado. Nenhuma outra parte do Executive Orchestrator (`orchestrator.py`, `correlation.py`, `synthesis.py`, `types.py`, `provisioning.py`) precisa de qualquer alteração — apenas esta tabela de elegibilidade, isolada em `catalog.py`/`selection_rule.py`.

**Recomendação deste TD sobre o impacto:** aprovar. É a única forma de satisfazer o Princípio 13/Founder §7 sem duplicar lógica de seleção na rota (o que violaria AR-17 §5: "nenhuma Capability implementa sua própria lógica de seleção paralela") e sem inventar nova capacidade de evidência para os 5 Advisors organization-only (o que seria mudança de comportamento, não elegibilidade).

### 6.3 A seleção continua determinística, reproduzível, auditável, independente de LLM

Nenhuma mudança a essa garantia — a nova condição de elegibilidade por escopo é, como a precondição de portfólio que já existe, uma função pura de `(advisor_name, scope)`, nunca do LLM, avaliada exatamente no mesmo ponto (`_meets_structural_precondition`) já coberto pelos testes `TestNeverTheLlm` (checagem AST) desde a Etapa 2.

---

## 7. Comportamento exato por escopo (Founder §7)

Demonstração explícita de qual conjunto de evidência pode alcançar cada Advisor selecionável, para os três casos — assumindo a correção de §6.2 aprovada:

### A. `scope.type = "project"` (identificador: `project_id`, resolvido e validado)

- **Advisors elegíveis:** `risk_advisor`, `delivery_advisor` (únicos com escopo `project` na tabela §6.2).
- **Evidência que alcança cada um:** `gather_context(organization_id, project.name, kind="risk"|"status")` — exclusivamente `AnalysisRecord`s daquele Project específico, mesmo comportamento já testado nas rotas `/risk-advisor/ask`/`/delivery-advisor/ask` desde a Wave 5.
- **Nunca alcançam:** `portfolio_advisor` (exige `portfolio_id`, ausente), os 5 Advisors organization-only (fora da tabela de elegibilidade, §6.2).

### B. `scope.type = "portfolio"` (identificador: `portfolio_id`, resolvido e validado)

- **Advisors elegíveis:** apenas `portfolio_advisor`.
- **Evidência que alcança:** `PortfolioEvidenceAssembler.assemble(organization_id, portfolio_id)` — exclusivamente `AnalysisRecord`s de `kind="status"` dos Projects pertencentes àquele Portfolio (via `Program`s do Portfolio), o mesmo comportamento já testado em `/portfolio-advisor/ask`.
- **Nunca alcançam:** `risk_advisor`/`delivery_advisor` (não sabem filtrar por portfólio), os 5 Advisors organization-only.

### C. `scope.type = "organization"` (nenhum identificador — `organization_id` exclusivamente da sessão)

- **Advisors elegíveis:** todos os 8 (o único escopo que todos honram).
- **Evidência que alcança cada um:** exatamente a mesma que cada Advisor já produz hoje em sua própria rota HTTP org-scoped — `risk_advisor`/`delivery_advisor` agregam `kind="risk"`/`"status"` de **todos** os Projects da organização (via `project_name=None`, comportamento correto e intencional aqui, porque `organization` foi explicitamente declarado); `pmo_advisor`/`executive_advisor`/`strategy_advisor` produzem exatamente a mesma composição org-wide que já produzem sem receber nenhum escopo hoje; `document_advisor`/`governance_advisor` fazem RAG sobre toda a base documental da organização, como já fazem hoje.
- **Nunca ocorre:** vazamento cross-organization — `organization_id` vem exclusivamente da sessão autenticada em todos os 8 casos (§4/8 abaixo), nunca de um campo do corpo da requisição.

**Garantia central desta seção:** para nenhum dos três casos, nenhum Advisor selecionado recebe evidência de fora do escopo declarado — a tabela de elegibilidade (§6.2) impede a seleção de qualquer Advisor cuja única evidência disponível excederia o escopo pedido.

---

## 8. Isolamento Organizacional (Founder §4)

Confirmado por leitura direta de código, nenhuma suposição:

| Escopo | Mecanismo de isolamento | Evidência de código |
|---|---|---|
| `project` | `DomainService.get_project(project_id, organization_id)` → `EnterpriseRepository.get_project`/`resolve_project_reference`: um `project_id` que existe mas pertence a outra organização é reportado como **não encontrado** (404), nunca confirmado como existente em outro lugar — "a cross-organization id is reported as not-found, never confirmed" (`enterprise_repository.py:269-271`, comentário literal do código) | `src/database/enterprise_repository.py:257-291`; `src/services/domain_service.py:138-139` |
| `portfolio` | `DomainService.get_portfolio(portfolio_id, organization_id)` → `EnterpriseRepository.get_portfolio`: a query já filtra por `Portfolio.id == portfolio_id AND Portfolio.organization_id == organization_id` na mesma consulta — "a cross-organization id never distinguishes 'not found' from 'not yours'" (comentário literal do código) | `src/database/domain_repository.py:60-70`; `src/services/domain_service.py:51-52` |
| `organization` | `organization_id` obtido exclusivamente de `context.organization.organization_id` (`RequestContext`, já resolvido pela camada de autenticação/`get_request_context`) — nunca um campo do corpo da requisição, nunca aceito do cliente | Mesmo padrão já usado por toda rota em `intelligence.py` desde a Security Hardening Gate (D-05x) |

**Nenhum código novo é necessário para esta garantia** — os dois métodos de `DomainService` (`get_project`/`get_portfolio`) e o padrão de `organization_id` exclusivamente de sessão já existem, já são usados em produção (o segundo, por todas as 8 rotas de Advisor; o primeiro, já testado desde TD-008 Fase 3b/Security Hardening Gate), e já cobrem exatamente os três casos exigidos.

---

## 9. Preservação Arquitetural (revisado)

Preservados integralmente, sem alteração estrutural: `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, Workflow Runtime, Event Pipeline, Knowledge Platform, Enterprise Domain, os 8 Enterprise Advisors, contratos públicos/HTTP existentes das 8 rotas individuais. `OrchestrationScope`, `orchestrator.py`, `correlation.py`, `synthesis.py`, `types.py`, `provisioning.py` — **inalterados**.

**Único impacto identificado, apresentado para confirmação explícita, não presumido:** a extensão aditiva de `catalog.py`/`selection_rule.py` com uma tabela de elegibilidade por escopo (§6.2) — necessária para que o Princípio 13 (Explicit Scope) seja estruturalmente garantido, não apenas documentado. Sem esta extensão, o risco que esta missão existe para eliminar permaneceria parcialmente presente (para os 5 Advisors organization-only sob escopo `project`/`portfolio`). Recomendação deste TD: aprovar, por ser estritamente aditiva e da mesma categoria de mudança já precedente (D-143).

---

## 10. Riscos (revisado)

| Risco | Estado |
|---|---|
| `project_name`/escopo omitido causando agregação implícita não solicitada | **ELIMINADO** (não mitigado) — `scope` é obrigatório, validado estruturalmente antes de qualquer execução; "organização" só ocorre por declaração explícita (§3/§7) |
| Advisor organization-only selecionado sob escopo `project`/`portfolio`, retornando evidência mais ampla que o solicitado | **ELIMINADO**, condicionado à aprovação do impacto §6.2 — tabela de elegibilidade impede a seleção |
| Latência: até 2-3 chamadas de Advisor + 1 de Síntese, sequenciais | Inalterado desde D-150 — timeout de BFF proporcionalmente maior recomendado (120s), paralelismo deferred (§1.1) |
| Rate limiting compartilhado atingido mais rápido por requisição | Inalterado desde D-150 — risco operacional, não arquitetural |
| Citação duplicada entre Advisors que compartilham evidência subjacente | Inalterado desde D-150 — aceito, transparente, deferred (§1.4) |
| `AdvisorExecutionError` propaga e aborta toda a requisição | Inalterado desde D-150 — mesmo comportamento de toda a Wave 5 |

**Nenhum risco residual bloqueia a implementação, exceto a aprovação explícita do impacto §6.2.**

---

## 11. Consumidor Frontend Mínimo (revisado — Explicit Scope)

**Objetivo único inalterado: usuário → pergunta executiva → Decision Support → Executive Orchestrator → Advisors → resposta integrada. Nenhum dashboard novo (Founder §12).**

O painel `decision-support-panel.tsx` (`web/components/dashboard/`, adicionado ao Dashboard Executivo já existente, mesmo padrão de composição de painéis — inalterado desde D-150) passa a exigir seleção explícita de escopo antes de permitir o envio da pergunta:

- **Seletor "Escopo":** três opções mutuamente exclusivas — **Projeto** / **Portfólio** / **Organização** — nenhuma pré-selecionada por padrão (o formulário não pode ser enviado sem uma escolha explícita, espelhando a exigência de `scope` no backend).
- **Quando "Projeto":** um segundo campo aparece, seletor do Project correspondente (lista dos Projects da organização, já disponível via `usePortfolios`/`usePrograms`/`useProjects`, hooks já existentes no Dashboard) — envia `project_id`.
- **Quando "Portfólio":** um segundo campo aparece, seletor do Portfolio correspondente (`usePortfolios`, já existente) — envia `portfolio_id`.
- **Quando "Organização":** nenhum campo adicional — envia `scope: {type: "organization"}` apenas após confirmação explícita do usuário nessa opção, nunca como estado inicial do formulário.

O BFF (`app/api/bff/decision-support/route.ts`) e o hook (`use-ask-decision-support.ts`) — inalterados desde D-150 em sua estrutura — passam a validar/repassar `scope` como objeto estruturado em vez de `project_name`/`portfolio_id` soltos, espelhando o novo contrato do backend (§3).

---

## 12. Princípio Permanente — Executive Intelligence Explicit Scope (Founder §11)

**Avaliação de compatibilidade:** revisão feita contra os 12 princípios já registrados na Vision, contra AR-17 (Camadas 1-4) e contra o Domain Blueprint do Executive Orchestrator (D-138). **Nenhuma incompatibilidade encontrada.** AR-17 §7 já descrevia o Orchestrator como operando exclusivamente sobre "sinais estruturados extraídos de uma pergunta" — Explicit Scope é inteiramente compatível com essa descrição, apenas torna um desses sinais (o escopo) obrigatório em vez de opcional. Nenhuma decisão anterior presumia ou dependia de escopo implícito/omitido.

**Registrado como Princípio 13, permanente, aplicável a toda Capability futura da Wave 6 — não apenas Decision Support:**

> **13. Executive Intelligence Explicit Scope.** A Executive Intelligence nunca infere o escopo de uma análise pela ausência de informação. Toda execução de uma Capability deve possuir um escopo explicitamente declarado pelo consumidor, dentre os escopos permitidos (`project`, `portfolio`, `organization`) — `organization` é um escopo válido e intencional, nunca um fallback implícito decorrente da ausência de `project`/`portfolio`. Qualquer combinação de escopo estruturalmente inválida, ou a ausência de escopo, deve falhar antes da execução do Executive Orchestrator, nunca silenciosamente ampliar o escopo.

Nenhuma decisão anterior é reescrita retroativamente — este princípio se aplica a partir desta revisão, a toda Capability que ainda não tem contrato HTTP (Executive Briefing, Cross Advisor Correlation, Conflict Analysis, Recommendation Package permanecem fora de escopo de implementação, mas herdam esta obrigação quando, no futuro, forem implementadas).

---

## 13. Testes Obrigatórios (revisado — 10 cenários adicionados, Founder §9)

Além dos já planejados em D-150 (mapeamento de resposta, `AdvisorExecutionError`→502, RBAC 403, `question` inválida→422, checagem `ast`):

1. Requisição sem `scope` → rejeitada (422).
2. `scope.type=project` sem `project_id` → rejeitada (422).
3. `scope.type=portfolio` sem `portfolio_id` → rejeitada (422).
4. `scope.type=organization` com `project_id`/`portfolio_id` presente → rejeitada (422).
5. `project_id` de outra organização → rejeitado (404), nunca confirmado como existente.
6. `portfolio_id` de outra organização → rejeitado (404), nunca confirmado como existente.
7. `scope.type=organization` → `organization_id` usado é exclusivamente o da sessão autenticada (nenhum campo do corpo influencia).
8. A mesma pergunta, executada com `scope=project`, `scope=portfolio`, `scope=organization` (mesma organização, dados reais preparados para os três) → produz três `advisors_used`/composições estruturalmente distintas, demonstráveis por asserção direta.
9. Para cada um dos três escopos, nenhum Advisor selecionado recebe evidência fora do escopo solicitado — verificado com Advisors reais e dados reais que tornariam a violação detectável (ex.: dois Projects em Portfolios diferentes, evidência de um nunca aparecendo na resposta de outro).
10. Ausência de `scope` nunca produz execução organizacional implícita — mesmo teste do item 1, reafirmado como uma garantia negativa explícita (nenhuma chamada ao Executive Orchestrator ocorre antes da validação falhar).

Todos os 10 cenários serão implementados como testes de integração via `TestClient`, com Advisors reais e PostgreSQL real, mesmo padrão de `test_executive_orchestrator_e2e.py`.

---

## 14. Estratégia Incremental de Implementação

Inalterada desde D-150 em sua estrutura de três etapas — Etapa 1 (rota HTTP backend + testes, agora incluindo os 10 cenários de §13), Etapa 2 (consumidor frontend mínimo com seletor de escopo, §11), Etapa 3 (validação E2E + fechamento do Epic). A única adição: a aprovação explícita do impacto §6.2 é uma precondição da Etapa 1 — nenhuma linha de `catalog.py`/`selection_rule.py` é tocada antes dela.

---

## 15. Critérios de Encerramento deste Epic

Inalterados desde D-150 (§15), mais um item:

7. Confirmação de que o risco de escopo implícito foi eliminado — não apenas mitigado — demonstrada pelos testes 1-10 de §13.

---

## Recomendação

**GO condicional para a implementação — condicionado exclusivamente à aprovação explícita, pelo Founder, do impacto identificado em §6.2 (extensão aditiva de `catalog.py`/`selection_rule.py` com a tabela de elegibilidade por escopo).**

Esta revisão eliminou estruturalmente, não mitigou, o risco de escopo implícito identificado na primeira versão deste Technical Design (D-150): o contrato de entrada passa a exigir `scope` explícito e estruturalmente validado (§3); a identidade estrutural correta de Project foi determinada como `project_id`, groundada em código real e em uma migração institucional já concluída (§3.1); o comportamento exato de cada Advisor sob cada um dos três escopos foi demonstrado (§7); o isolamento organizacional foi confirmado por mecanismos já existentes e já testados, sem necessidade de código novo (§8); `OrchestrationScope` foi avaliado e confirmado como já correto, sem evolução necessária (§6.1); um único impacto real sobre o Executive Orchestrator foi identificado — a tabela de elegibilidade por escopo em `catalog.py`/`selection_rule.py` — e apresentado explicitamente para aprovação, nunca decidido silenciosamente (§6.2/§9); dez novos cenários de teste obrigatórios foram adicionados (§13); e o princípio Executive Intelligence Explicit Scope foi avaliado contra toda a governança já aprovada, nenhuma incompatibilidade encontrada, e registrado como permanente (§12). **Nenhum código foi escrito nesta etapa.** Retornando obrigatoriamente para Executive Review — nenhuma implementação deverá começar antes da aprovação explícita do Founder, incluindo, especificamente, do impacto §6.2.
