# Technical Design — Executive Narrative (segunda Capability de produção da Executive Intelligence)

Produzida sob mandato da "Founder Decision — Wave 6 / Executive Narrative — Abertura do próximo ciclo institucional" (APPROVED do Wave 6 Progress Assessment V2, D-159; próxima Capability oficial: Executive Narrative), que autoriza exclusivamente este Technical Design — **nenhum código nesta etapa**. Objetivo: transformar Executive Narrative de comportamento interno já exercitado pelo Executive Orchestrator em Capability funcional real, com contrato e consumidor de produção, reutilizando integralmente o padrão já construído e validado para Decision Support (D-153 a D-158).

**Precondição:** Decision Support Delivered (D-153 a D-158); `WAVE-6-PROGRESS-ASSESSMENT-V2.md` (D-159), que já demonstrou, por grounding de código, que Executive Narrative tem 10 invocações reais de `orchestrator.run(Capability.EXECUTIVE_NARRATIVE, ...)` em `tests/test_executive_orchestrator_orchestrator.py`, com Advisors reais e evidência real — Seleção→Execução→Correlação→Síntese já provada em teste, faltando exclusivamente consumidor e contrato.

---

## 0. O que já é oficial (não reaberto aqui)

| Decisão | Origem |
|---|---|
| `ExecutiveOrchestrator.run(capability, session, question, signals) -> ExecutiveIntelligenceResult` — assinatura, ciclo, request-scoped | Technical Design Executive Orchestrator §1/§8 (D-141) |
| `Selection Rule` determinística, nunca LLM; `explicit` sempre tem precedência sobre `question` | D-137/D-138/D-143 |
| `AdvisorFramework.run()` executa exatamente um Advisor por chamada, preservado integralmente | Vision, Princípio 2 |
| Correlação estritamente estrutural (`STRUCTURAL_PAIRS`), nunca julga conteúdo | D-144 |
| Síntese consome exclusivamente `Explanation`s já coletadas, nunca evidência bruta | D-145 |
| `ExecutiveIntelligenceResult`: dois estados exaustivos, `.complete()`/`.insufficient_basis()` | D-140 |
| `OrchestrationScope(project_name, portfolio_id)` já correto para os três escopos, sem evolução necessária | Technical Design Decision Support §6.1 (Decisão A) |
| `ADVISOR_ELIGIBLE_SCOPES` (`catalog.py`) — tabela de elegibilidade por escopo dos 8 Advisor Identities, aditiva, aprovada | D-154 |
| **Executive Intelligence Explicit Scope (Princípio 13)** — nenhuma Capability infere escopo pela ausência de informação; `organization` é sempre uma declaração deliberada | Founder Decision — Eliminação do Risco de Escopo Implícito; Vision |
| Decision Support = Delivered — rota, BFF, painel, RBAC, 18+6 testes de API/eligibilidade, E2E via browser | D-153 a D-158 |
| `EnterpriseMemoryService`, integração com Workflow Runtime, cache, paralelismo, confidence score, ranking, novos Advisors, Executive Briefing, Recommendation Package | Fora de escopo desta missão (Founder §8) |

Este documento nunca reabre nenhuma destas decisões, e não altera `orchestrator.py`, `correlation.py`, `synthesis.py`, `types.py`, `provisioning.py`.

---

## 1. Identidade Funcional

**Executive Narrative não cria nova inteligência — transforma o `ExecutiveIntelligenceResult` já produzido pelo Executive Orchestrator em uma narrativa executiva consumível de um escopo explicitamente declarado.**

Diferente de Decision Support (que responde a uma pergunta arbitrária, autorada livremente pelo usuário), Executive Narrative não é orientada a pergunta — é orientada a **escopo**. O usuário nunca digita uma pergunta; ele declara "quero o estado executivo deste Project/Portfolio/da organização" e recebe uma síntese estruturada, coerente e rastreável, exclusivamente derivada de:

- **Advisor Explanations** — as `AttributedExplanation`s já produzidas por `AdvisorFramework.run()` para cada Advisor Identity selecionado;
- **Correlation Findings** — os `CorrelationFinding`s já produzidos por `correlate()`;
- **Composition Trace** — o registro já produzido incrementalmente por `CompositionTrace`;
- **Executive Intelligence Result** — o produto final já produzido por `ExecutiveOrchestrator.run()`.

**Nunca consulta fontes primárias.** Nenhuma linha de código da Capability acessa `AIContextEngine`, `DomainService`, `RagPipeline`, ou qualquer repositório diretamente — exatamente a mesma garantia já demonstrada e testada para Decision Support (`TestNoDirectInfrastructureAccess`, verificação AST), reutilizada sem alteração.

---

## 2. Diferença Definitiva para Decision Support

A distinção não é apenas de rótulo — é estruturalmente demonstrável em três pontos do contrato e do fluxo, nenhum deles compartilhado:

| Dimensão | Decision Support | Executive Narrative |
|---|---|---|
| **Entrada do usuário** | `question: str` — texto livre, autorado pelo usuário, arbitrário | Nenhum campo de texto livre. Apenas `scope` |
| **Mecanismo de Seleção** | Correspondência lexical contra `question` (ou `explicit`, hoje nunca populado pela rota) — tipicamente seleciona 1-3 Advisors relevantes à pergunta específica | `explicit` sempre populado com **todos os 8 Advisor Identities** — a elegibilidade por escopo (`ADVISOR_ELIGIBLE_SCOPES`, já existente, inalterada) faz toda a filtragem real; nenhuma correspondência lexical ocorre |
| **Verbo/rota HTTP** | `POST /decision-support/ask` — "pergunte" | `POST /executive-narrative/generate` — "gere uma narrativa" (nunca "ask", para que o próprio verbo já comunique a diferença) |
| **Campo de resposta central** | `answer: str \| None` — resposta a uma pergunta específica | `narrative: str \| None` — síntese do estado do escopo, nenhuma pergunta a responder |
| **`scope` na resposta** | Ausente do contrato hoje (a pergunta já contextualiza o que foi pedido) | Presente — ecoado explicitamente, porque não há pergunta para lembrar o leitor do que está sendo sintetizado |
| **Semântica de uso** | Reativa: usuário pergunta algo específico e pontual | Panorâmica: usuário pede o estado executivo completo do escopo, sem recorte de pergunta |

**Garantia de não-aliasing:** as duas Capabilities usam o mesmo motor (`ExecutiveOrchestrator.run()`, as mesmas quatro operações estruturais) — isso é esperado e correto (AR-17 §2: "nenhuma Capability inventa mecânica própria"). A diferença nunca está na mecânica interna (que é deliberadamente compartilhada), mas em **quem decide o que é perguntado e como Advisors são selecionados** — em Decision Support, o usuário e o texto livre decidem; em Executive Narrative, o escopo e a elegibilidade estrutural decidem, nunca o usuário, nunca um texto livre. Um teste dedicado (§13, item 11) prova essa distinção diretamente: mesma organização, mesmos dados, mesmo escopo — Decision Support e Executive Narrative produzem `advisors_used` estruturalmente diferentes (Decision Support seleciona por relevância lexical à pergunta feita; Executive Narrative seleciona todos os elegíveis ao escopo).

---

## 3. Scopes Suportados — avaliação grounded

Per Founder §3, avaliado explicitamente, sem assumir que os três precisam ser expostos:

| Scope | Advisors elegíveis (via `ADVISOR_ELIGIBLE_SCOPES`, inalterada) | Narrativa produzida | Legítimo? |
|---|---|---|---|
| `project` | `risk_advisor`, `delivery_advisor` (2) | Estado de risco + entrega de um Project específico | **Sim** — 2 Advisors reais, evidência real, narrativa coerente (estado de um projeto), mesmo padrão já testado nas rotas individuais desde a Wave 5 |
| `portfolio` | `portfolio_advisor` (1, condicionado a `portfolio_id`, precondição D-143 inalterada) | Estado agregado de um Portfolio | **Sim** — 1 Advisor real, evidência real, narrativa coerente (equilíbrio/dependências do portfólio) |
| `organization` | `pmo_advisor`, `executive_advisor`, `strategy_advisor`, `document_advisor`, `governance_advisor`, `risk_advisor`, `delivery_advisor` (7 — `portfolio_advisor` estruturalmente excluído por ausência de `portfolio_id`, mesmo comportamento já demonstrado para Decision Support, D-154) | Estado executivo completo da organização | **Sim** — até 7 Advisors reais, a narrativa mais abrangente das três |

**Conclusão: os três escopos são legitimamente suportados, os mesmos três de Decision Support.** Não há fundamento para excluir nenhum — a mecânica de elegibilidade já existente produz, para cada um, um conjunto não-vazio e coerente de Advisors reais. Excluir um dos três seria uma restrição não fundamentada em comportamento real, contrária a *Grounded before Generalized* na direção oposta (recusar algo que já funciona, sem motivo).

**Distinção preventiva com Executive Briefing (fora de escopo, Not Started):** o escopo `organization` de Executive Narrative produz **uma única narrativa fundida** da organização inteira (um `OrchestrationScope()`, uma chamada ao Orchestrator). Isso não deve ser confundido com a visão multi-unidade simultânea (todos os Portfolios individualmente, cada um com sua própria composição) que o Wave 6 Progress Assessment V2 identificou como a lógica funcional própria ainda não construída de Executive Briefing (§4.5 daquele documento). Executive Narrative(organization) e uma futura Executive Briefing não são a mesma coisa sob nomes diferentes — a primeira é uma síntese, a segunda seria uma composição de N sínteses. Este Technical Design não implementa a segunda.

---

## 4. Selection Rules Aplicáveis — reuso confirmado, zero alteração

Per Founder §4: demonstrado abaixo que Executive Narrative **não precisa** da mesma tabela de elegibilidade (ela já é genérica o suficiente para servir as duas Capabilities sem modificação), não precisa de um subconjunto, e não precisa de regras próprias — precisa apenas de um uso diferente do mecanismo `explicit` já existente em `SelectionSignals`.

### 4.1 Mecanismo

```
signals = SelectionSignals(
    explicit=frozenset(identity.name for identity in ADVISOR_IDENTITY_CATALOG),  # todos os 8, reaproveitando o catalog já existente -- nunca uma lista nova hardcoded
    scope=scope,  # já resolvido, mesmo OrchestrationScope de Decision Support
)
```

`evaluate_selection_rule()` (inalterada) então aplica `_matches_vocabulary()` — que, com `explicit` contendo todos os 8 nomes, sempre casa (`advisor_name in explicit`, `selection_rule.py:55`) — e, decisivamente, `_meets_structural_precondition()` (inalterada), que já aplica `ADVISOR_ELIGIBLE_SCOPES` e `ADVISOR_NAMES_REQUIRING_PORTFOLIO_ID` exatamente como já faz para Decision Support. **O resultado é: todo Advisor Identity elegível para o escopo declarado é selecionado — nenhuma correspondência lexical, nenhuma pergunta livre envolvida.**

### 4.2 Por que isto não exige nenhuma mudança em `catalog.py`/`selection_rule.py`

`_matches_vocabulary`/`_meets_structural_precondition` já são funções puras de `(advisor_name, explicit|scope)` — nenhuma delas assume que `explicit` venha de uma seleção manual do usuário; `evaluate_selection_rule()` já é indiferente à origem de `signals.explicit`. Popular `explicit` com todos os 8 nomes é um uso do contrato já existente (o mesmo mecanismo que já permite, em teoria, que uma futura rota permita ao usuário escolher Advisors manualmente), nunca uma extensão dele.

### 4.3 `SelectionTraceEntry` continua auditável

Quando `explicit` é usado, `trace_entry.signals` registra os nomes ordenados de `explicit` (`selection_rule.py:105`) — para Executive Narrative, isso significa que o Composition Trace sempre mostrará os 8 nomes como "sinais" avaliados, com `selected_advisor_names` mostrando o subconjunto real selecionado após a elegibilidade por escopo. Esta é uma trilha de auditoria legítima e mais informativa que a de Decision Support (que registra apenas o texto da pergunta) — mostra explicitamente "todos foram considerados, X foram elegíveis para este escopo".

### 4.4 Nenhuma seleção por LLM

Inalterado — `evaluate_selection_rule()` nunca importa `LLMProvider`, nunca é tocado por esta Capability.

---

## 5. Contrato Funcional

### 5.1 Consumidor — Rota HTTP

**`POST /executive-narrative/generate`**, em `src/api/routes/intelligence.py` (mesmo módulo de todas as rotas de Advisor e de Decision Support — nunca um módulo paralelo). Adaptador fino, mesmo padrão de `ask_decision_support`: resolve escopo → constrói `SessionContext`/`AdvisorFramework`/`ExecutiveOrchestrator`/`SelectionSignals` (com `explicit` populado, §4) → `orchestrator.run(Capability.EXECUTIVE_NARRATIVE, session, EXECUTIVE_NARRATIVE_PROMPT, signals)` → mapeia o resultado. O verbo `generate` (em vez de `ask`) é deliberado — reforça a diferença semântica de §2 já na URL.

**Dependências FastAPI** — idênticas a `ask_decision_support`: `get_request_context`, `require_permission("intelligence.read")`, `build_repository`, `build_provider`, `build_prompt_registry`, `build_orchestrator_prompt_registry`, `build_rag_pipeline`, `build_domain_service`. Nenhuma dependência nova.

### 5.2 Entrada Mínima

**`ExecutiveNarrativeRequest`**

| Campo | Tipo | Obrigatório |
|---|---|---|
| `scope` | escopo estruturado (mesma forma e mesma validação de `DecisionSupportScope`) | **Sim — sem default, ausência é 422** |

**Nenhum campo de texto livre.** Esta é a diferença de contrato mais direta com Decision Support (§2).

**Decisão de reuso, proposta para a fase de implementação (não código nesta etapa):** em vez de duplicar a classe e o `model_validator` de `DecisionSupportScope`, extrair um modelo Pydantic compartilhado (`ExplicitScope`, mesmos três campos, mesma validação) usado por ambos os contratos — `DecisionSupportRequest.scope: ExplicitScope` e `ExecutiveNarrativeRequest.scope: ExplicitScope`. Mudança aditiva e estritamente de nomenclatura/organização dentro de `intelligence.py`, sem alterar nenhum comportamento já testado de Decision Support (mesma validação, mesmos códigos de erro) — evita duplicar um validador que já existe, respeitando a regra permanente "nunca duplicar código" (CLAUDE.md). Se, na implementação, esta extração se mostrar mais arriscada que o benefício (por exemplo, por acoplar release de Decision Support e Executive Narrative em um único módulo de tipos), a alternativa aceitável é duplicar a classe sob um nome próprio (`ExecutiveNarrativeScope`) — decisão a confirmar na Etapa 1 de implementação, nunca nesta etapa de design.

**Resolução de escopo:** reutiliza `resolve_decision_support_scope()` sem alteração (ou, seguindo a mesma lógica de extração acima, um `resolve_explicit_scope()` compartilhado) — já cobre os três casos, já confirma posse organizacional via `DomainService.get_project`/`get_portfolio`, já retorna `OrchestrationScope`. Nenhuma linha nova de lógica de resolução é necessária.

### 5.3 Saída Mínima

**`ExecutiveNarrativeResponse`**

| Campo | Tipo | Origem (nunca inventado) |
|---|---|---|
| `capability` | `str` | `result.capability.value` — `"executive_narrative"` |
| `scope` | objeto `{type, project_id, portfolio_id}` — eco do `scope` já validado na entrada | O próprio `request.scope`, ecoado após validação — nunca um novo cálculo |
| `insufficient_basis` | `bool` | `result.is_insufficient_basis` |
| `insufficient_basis_reason` | `str \| None` | `result.insufficient_basis_reason.value` |
| `narrative` | `str \| None` | `result.synthesis` (renomeado de "answer" para refletir a semântica de §1/§2 — mesmo dado, campo com nome que não sugere resposta a uma pergunta) |
| `advisors_used` | `list[str]` | `result.advisor_identities` |
| `citations` | `list[...]` | `result.explanations[*].explanation.recommendation.cited_evidence` — mesma estrutura de `DecisionSupportCitation` |
| `composition_trace` | objeto — mesma estrutura de `DecisionSupportCompositionTrace` | `result.composition_trace` |

**Nenhum dado é inventado que não exista em `ExecutiveIntelligenceResult`** — cada campo acima é uma projeção direta e já demonstrada (mesmo mapeamento de `_decision_support_response()`, reaproveitável quase literalmente, renomeando `answer`→`narrative` e adicionando o eco de `scope`).

### 5.4 `insufficient_basis`

Reutiliza `InsufficientBasisReason` sem alteração — `SELECTION_EMPTY`/`COLLECTION_EMPTY`, os dois estados já exaustivos.

- **`SELECTION_EMPTY`:** estruturalmente não deve ocorrer para um `scope` validamente resolvido, dado que os três escopos sempre têm ao menos 1 Advisor elegível (§3) — mas permanece exposto no contrato por integridade e defesa em profundidade (mesma garantia que `ExecutiveIntelligenceResult.__post_init__` já impõe), nunca removido do modelo de resposta.
- **`COLLECTION_EMPTY`:** o caso realista — todos os Advisors elegíveis foram selecionados e executados, mas nenhum produziu evidência real (ex.: Project novo, sem nenhuma `AnalysisRecord`). Idêntico ao comportamento já testado para Decision Support.

### 5.5 `Composition Trace`

Reutiliza `CompositionTrace`/`SelectionTraceEntry`/`ExecutionTraceEntry`/`CorrelationTraceEntry`/`SynthesisTraceEntry` sem alteração — tipos já genéricos por Capability, nunca acoplados a Decision Support. `DecisionSupportCompositionTrace` (Pydantic) é reaproveitável quase literalmente como o modelo de saída de `composition_trace` (ou, seguindo a mesma lógica de §5.2, extraído para um tipo compartilhado).

### 5.6 `citations`

Mesma estrutura, mesma origem (`Explanation.recommendation.cited_evidence`), mesma garantia de proveniência por Advisor (Princípio 4) — nenhuma mudança.

### 5.7 Segurança / RBAC

`require_permission("intelligence.read")` — mesma permissão já usada pelas 8 rotas de Advisor e por Decision Support. Nenhuma permissão nova: Executive Narrative, como Decision Support, nunca cria/edita/persiste, apenas lê e sintetiza evidência já existente.

---

## 6. Fluxo Completo

```
Usuário (frontend)
  │  escopo OBRIGATÓRIO (project | portfolio | organization) -- NENHUM texto livre
  ▼
POST /executive-narrative/generate                  (rota, adaptador fino)
  │  1. Pydantic valida ExplicitScope (mesma tabela de combinações de Decision Support) → 422 se inválido/ausente
  │  2. Resolve o identificador (apenas quando type=project|portfolio) via DomainService, 404 se cross-tenant
  │  3. Constrói OrchestrationScope -- reuso integral de resolve_decision_support_scope()/equivalente
  │  4. Constrói SessionContext, AdvisorFramework, ExecutiveOrchestrator
  │  5. Constrói SelectionSignals(explicit=todos os 8 nomes, scope=scope) -- §4
  ▼
ExecutiveOrchestrator.run(EXECUTIVE_NARRATIVE, session, EXECUTIVE_NARRATIVE_PROMPT, signals)
  │                                                   (preservado integralmente, D-141/D-146)
  ├─ Selection Rule -- todos os 8 avaliados, elegibilidade por escopo narrowing (ADVISOR_ELIGIBLE_SCOPES, inalterada)
  │     Selection Empty? (não esperado para escopo válido, §3) → insufficient_basis
  │
  ├─ Execução: AdvisorFramework.run() × N (2 para project, 1 para portfolio, até 7 para organization)
  │     Collection Empty? → insufficient_basis
  │
  ├─ Correlação estrutural (STRUCTURAL_PAIRS, inalterada)
  │
  └─ Síntese (synthesize(), inalterada) -- narrativa executiva do escopo
  ▼
ExecutiveIntelligenceResult → ExecutiveNarrativeResponse → BFF → hook → painel → usuário
```

`EXECUTIVE_NARRATIVE_PROMPT` é uma constante interna fixa (não configurável pelo usuário, não exposta no contrato) — um único texto genérico o suficiente para servir aos três escopos (ex.: "Produza uma síntese executiva do estado atual deste escopo, cobrindo riscos, entrega e quaisquer sinais relevantes segundo a evidência disponível"), passado a cada `AdvisorFramework.run()` e a `synthesize()` exatamente como `request.question` já é passado hoje para Decision Support — nenhuma mudança de assinatura em nenhum dos dois. O texto exato é decisão de implementação (Etapa 1), não uma decisão arquitetural deste documento; nenhuma variação por escopo é proposta nesta primeira versão (uma única constante), por *Grounded before Generalized* — variações podem ser adicionadas depois, se uso real demonstrar necessidade.

---

## 7. Preservação Arquitetural

Preservados integralmente, sem nenhuma alteração estrutural: `ExecutiveOrchestrator`, `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, Workflow Runtime, Event Pipeline, Knowledge Platform, Enterprise Domain, os 8 Enterprise Advisors, `catalog.py`, `selection_rule.py`, `correlation.py`, `synthesis.py`, `types.py`, `provisioning.py`, e o contrato público de Decision Support (nenhuma mudança de comportamento nas rotas já existentes — apenas, opcionalmente, uma extração de tipo Pydantic compartilhado que preserva a validação e os códigos de erro já testados, §5.2).

**Nenhum impacto identificado sobre nenhum componente protegido** — ao contrário do Technical Design de Decision Support (que precisou de uma extensão aditiva de `catalog.py`/`selection_rule.py`, já aprovada e implementada em D-154), Executive Narrative reutiliza essa extensão sem precisar de nenhuma adicional. Esta é a razão concreta pela qual o Wave 6 Progress Assessment V2 recomendou Executive Narrative como menor risco arquitetural entre as Capabilities remanescentes.

---

## 8. Fora de Escopo (reafirmado, Founder §8)

Não implementados nesta missão nem propostos por este Technical Design: Executive Briefing, Recommendation Package, `EnterpriseMemoryService`, integração com Workflow Runtime, cache, paralelismo, confidence score, ranking, novos Advisors, novas fontes primárias.

---

## 9. Consumidor Frontend Mínimo

**Reutiliza o Dashboard Executivo já existente — nenhuma página nova**, per Founder §6.

Um segundo painel, **visualmente e funcionalmente distinto** do `DecisionSupportPanel` (evitando qualquer aparência de alias, per Founder §2): `executive-narrative-panel.tsx`, adicionado à mesma seção do Dashboard.

- **Sem campo de pergunta.** Apenas o seletor de Escopo (Projeto/Portfólio/Organização), extraído do `DecisionSupportPanel` como um subcomponente compartilhado (`ScopeSelector`, reutilizando a mesma UI/lógica já testada — Selects de Projeto/Portfólio populados por `useProjects()`/`usePortfolios()`, já existentes) para evitar duplicar a lógica de seleção de escopo entre os dois painéis, sem duplicar o próprio painel.
- **Botão "Gerar Narrativa"** (nunca "Perguntar") — habilitado assim que um escopo válido e completo é escolhido (mesma regra de habilitação de Decision Support, sem a exigência de texto).
- **Exibição:** a `narrative` como texto corrido, `advisors_used` como badges, `citations` como lista — mesmo padrão visual de `DecisionSupportPanel` (reuso de componentes de apresentação, `Badge`/lista), ou o banner de Base Insuficiente quando `insufficient_basis` for verdadeiro.

BFF (`app/api/bff/executive-narrative/route.ts`) e hook (`use-generate-executive-narrative.ts`) seguem exatamente o padrão já validado três vezes para Decision Support (proxy fino, timeout equivalente — até 7 chamadas sequenciais de Advisor sob escopo organização, potencialmente mais latente que Decision Support, avaliar timeout na Etapa 2 de implementação com base em medição real).

---

## 10. Testes Obrigatórios

1. Fluxo completo para cada um dos três escopos, com Advisors reais e evidência real, narrativa real produzida (3 cenários).
2. `insufficient_basis` (`COLLECTION_EMPTY`) para um escopo válido sem evidência real.
3. `scope` ausente ou combinação estruturalmente inválida → 422 (mesma tabela de Decision Support).
4. `project_id`/`portfolio_id` de outra organização → 404, nunca confirmado como existente.
5. `scope.type=organization` → `organization_id` exclusivamente da sessão.
6. Para cada escopo, o conjunto de `advisors_used` é exatamente o previsto por `ADVISOR_ELIGIBLE_SCOPES` (2 para project, 1 para portfolio, até 7 para organization) — prova de que a seleção usa todos os 8 como sinal e a elegibilidade por escopo faz a narrowing real, nunca um subconjunto arbitrário.
7. RBAC 403 sem `intelligence.read`.
8. 502 em `AdvisorExecutionError`.
9. `Composition Trace` mapeada corretamente, incluindo os 8 nomes como `selection_signals` (§4.3).
10. Verificação AST: nenhum acesso direto a `AIContextEngine`/`gather_context`/`gather_rag_context`/repositório — mesmo padrão de `TestNoDirectInfrastructureAccess`.
11. **Prova de não-aliasing (Founder §2):** mesma organização, mesmos dados reais, mesmo `scope` — comparar a resposta de `/decision-support/ask` (com uma pergunta específica) e `/executive-narrative/generate` — confirmar que `advisors_used` difere estruturalmente entre as duas quando a pergunta de Decision Support é suficientemente específica para selecionar um subconjunto menor que o elegível por escopo, demonstrando que os dois mecanismos de seleção produzem resultados distintos por desenho, não apenas por coincidência de dados.

Todos os testes seguem o mesmo padrão de `test_decision_support_api.py`: `TestClient`, PostgreSQL real, Advisors reais — nunca mockados.

---

## 11. Riscos

| Risco | Avaliação |
|---|---|
| Narrativa fixa/genérica demais para os três escopos (um único `EXECUTIVE_NARRATIVE_PROMPT`) | Aceito nesta primeira versão — refinamento por escopo é deferred até uso real demonstrar necessidade (*Grounded before Generalized*), mesmo espírito de D-150/D-154 sobre confidence score/cache |
| Latência sob escopo `organization` (até 7 chamadas sequenciais + 1 síntese, mais que o típico de Decision Support) | Risco operacional, não arquitetural — mesma mitigação de Decision Support (timeout de BFF generoso), paralelismo permanece fora de escopo (§8) |
| Confusão de UX entre os dois painéis | Mitigado por design: painéis visualmente distintos, sem campo de texto livre em Executive Narrative, botões com verbos diferentes, verificado no teste de não-aliasing (§10, item 11) |
| Extração de `ExplicitScope`/tipos de Composition Trace compartilhados introduzir regressão em Decision Support | Mitigado: toda a suíte de Decision Support (18+6 testes) já cobre o comportamento exato a preservar; a extração, se realizada, deve manter os testes existentes verdes sem nenhuma alteração de asserção |
| Nenhum risco de reabertura de componente protegido | Confirmado em §7 — zero impacto sobre `catalog.py`/`selection_rule.py`, ao contrário de Decision Support |

**Nenhum risco residual bloqueia a implementação.**

---

## 12. Estratégia Incremental de Implementação

Mesmo padrão de 3 etapas já validado 3× para Decision Support:

- **Etapa 1 — Backend:** rota `POST /executive-narrative/generate`, contratos (`ExecutiveNarrativeRequest`/`Response`, com ou sem a extração de tipos compartilhados de §5.2/§5.5, decisão a confirmar nesta etapa), RBAC, `SelectionSignals` com `explicit`=todos os 8 (§4), testes 1-10 de §11.
- **Etapa 2 — Frontend mínimo:** BFF, hook, `ExecutiveNarrativePanel` (com `ScopeSelector` extraído/compartilhado, §9), adicionado ao Dashboard existente.
- **Etapa 3 — E2E + fechamento do Epic:** validação via browser real (3 breakpoints), teste de não-aliasing (§10, item 11), Executive Evidence, reclassificação de Executive Narrative para Delivered no próximo Wave 6 Progress Assessment.

Cada etapa: testes próprios, verificações limpas (ruff/tsc/eslint), commit íntegro — mesmo rigor institucional já demonstrado.

---

## Recomendação

**GO para implementação, sem nenhuma pré-condição de aprovação de impacto sobre componente protegido** — ao contrário de Decision Support, este Technical Design não identifica nenhuma necessidade de tocar `catalog.py`/`selection_rule.py`/qualquer parte do Executive Orchestrator: a extensão de elegibilidade por escopo já aprovada e implementada para Decision Support (D-154) já é suficiente e reutilizável sem modificação. A diferença funcional com Decision Support foi demonstrada estruturalmente (contrato de entrada sem texto livre, mecanismo de seleção por elegibilidade total em vez de correspondência lexical, verbo de rota distinto, campo de resposta renomeado) e será provada em teste dedicado (§10, item 11) — nenhum risco de as duas Capabilities se tornarem aliases. Os três escopos (project/portfolio/organization) foram avaliados e confirmados como legítimos, cada um produzindo um conjunto real e não-vazio de Advisors elegíveis. **Nenhum código foi escrito nesta etapa.** Retornando obrigatoriamente para Executive Review — nenhum trabalho posterior deverá ser iniciado automaticamente.
