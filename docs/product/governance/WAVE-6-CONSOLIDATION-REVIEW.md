# WAVE 6 CONSOLIDATION REVIEW — Executive Intelligence

**Data:** 2026-08-10
**Autor:** Claude / Tech Lead
**Gatilho:** "Founder Decision — Wave 6 Executive Intelligence Consolidation" (APPROVED), que consolidou institucionalmente a taxonomia da Wave 6 a partir do Progress Assessment V3 (D-163) e mandatou esta missão de diagnóstico técnico. **Missão exclusivamente de verificação e diagnóstico. Nenhuma implementação.**

---

## 1. Taxonomia consolidada da Executive Intelligence

Conforme determinado pelo Founder, registrada aqui como referência única:

| Categoria | Item(ns) |
|---|---|
| **Produto** (Capability com consumidor próprio) | Decision Support, Executive Narrative |
| **Operação estrutural interna** (mecanismo, nunca produto autônomo) | Selection, Execution, Correlation / Conflict Detection, Synthesis |
| **Deferred** (não cancelada, sem caso de uso novo aprovado) | Executive Briefing |
| **Absorvida** | Recommendation Package → Executive Narrative |

O enum `Capability` (`types.py`) permanece com os seis valores originais — nenhuma alteração de código foi autorizada ou é necessária para esta reclassificação, que é institucional/documental, não estrutural. `CROSS_ADVISOR_CORRELATION` e `CONFLICT_ANALYSIS` continuam existindo como valores de enum porque `correlate()`/o filtro de `is_structural_pair` (`orchestrator.py:114-116`) já usam essa distinção internamente — preservá-los é reuso, não taxonomia artificial.

---

## 2. Wave 6 Delivery Matrix (revisada)

| Capability/Item | Classificação | Evidência |
|---|---|---|
| Decision Support | **DELIVERED** | Inalterado desde V2/V3. |
| Executive Narrative | **DELIVERED** | Inalterado desde D-161/D-162. |
| Cross Advisor Correlation | **INTERNAL EXECUTIVE INTELLIGENCE OPERATION** | `correlate()` roda em toda execução real (§3). |
| Conflict Analysis | **INTERNAL EXECUTIVE INTELLIGENCE OPERATION** | Filtro `is_structural_pair` sobre o mesmo `correlate()` (`orchestrator.py:114-116`). |
| Recommendation Package | **ABSORBED BY EXECUTIVE NARRATIVE** | Confirmado mecanicamente idêntico em V3 §4.4 — nenhuma nova evidência a acrescentar. |
| Executive Briefing | **DEFERRED** | Exige `OrchestrationScope` multi-unidade, inexistente (V3 §4.5, reconfirmado nesta missão — `resolve_decision_support_scope()` inalterado, continua resolvendo exatamente um Project/Portfolio/organização por chamada). |

Duas Capabilities de produto, quatro itens resolvidos institucionalmente sem pendência de classificação.

---

## 3. Diagnóstico — Composition Trace já contém o necessário?

**Sim, integralmente — verificado ponta a ponta, sem lacuna.**

| Camada | Evidência |
|---|---|
| Backend (`ExecutiveIntelligenceCompositionTrace`, `intelligence.py:1476-1490`/equivalente em `_executive_narrative_response`) | `selection_signals`, `selected_advisor_names`, `advisors_used` (com `had_evidence`), `correlations` (com `advisor_names`+`is_structural_pair`), `synthesis_source_advisor_names`. |
| Contrato TS (`web/lib/dashboard/types.ts:41-46`) | `DecisionSupportCompositionTrace` replica exatamente os mesmos campos, incluindo `correlations: DecisionSupportCorrelation[]` com `advisor_names`/`is_structural_pair`. `ExecutiveNarrativeResponse` reutiliza o mesmo tipo (nenhuma duplicação). |
| BFF (`web/app/api/bff/decision-support/route.ts:108`, `.../executive-narrative/route.ts:96`) | `const data = (await backendResponse.json()) as DecisionSupportResponse` — repassa o corpo JSON completo, **sem** seleção de campos, sem descarte. |
| Hook (`use-ask-decision-support.ts:24`, `use-generate-executive-narrative.ts:27`) | `return body as DecisionSupportResponse` — mesmo padrão, corpo completo entregue a `mutation.data`. |

**Conclusão:** `composition_trace` (incluindo `correlations`, `is_structural_pair`, `advisors_used` com `had_evidence`) já chega intacto a `mutation.data` dentro de `DecisionSupportPanel`/`ExecutiveNarrativePanel`. Nada precisa ser adicionado ao contrato, ao BFF ou ao hook. **Trata-se de evolução de apresentação, não de nova Capability** — exatamente a condição que o Founder estabeleceu para autorizar apenas avaliação técnica mínima, não uma nova rota.

---

## 4. Diagnóstico — Citation Duplication

### 4.1 Existem duplicações reais possíveis em cenários multi-Advisor?

**Sim — um caso concreto identificado por leitura direta de `provisioning.py`, não hipotético.**

```python
# provisioning.py:110-118
if advisor_name == "document_advisor":
    rag_context = framework.gather_rag_context(session.organization_id, question, top_k=5)
    evidence = framework.normalize_rag_evidence(rag_context)
    ...
if advisor_name == "governance_advisor":
    rag_context = framework.gather_rag_context(session.organization_id, question, top_k=5)
    evidence = framework.normalize_rag_evidence(rag_context)
    ...
```

`document_advisor` e `governance_advisor` chamam `gather_rag_context()` com **argumentos idênticos** — mesma `organization_id`, mesma `question` (para Executive Narrative, literalmente a mesma constante `EXECUTIVE_NARRATIVE_PROMPT` para toda a execução; para Decision Support, o mesmo `request.question` já é passado sem alteração a cada Advisor selecionado, confirmado em `orchestrator.py:88-96`), mesmo `top_k=5`. `RagPipeline.retrieve()` é uma busca semântica determinística sobre a mesma base de conhecimento — os dois Advisors recebem, por construção, o **mesmo pool de candidatos** (os mesmos `document_chunk`s). Sob `scope=organization`, ambos são elegíveis e selecionados simultaneamente (`ADVISOR_ELIGIBLE_SCOPES`, D-154) — este não é um cenário raro, é o comportamento padrão de qualquer pergunta/narrativa em escopo organizacional.

Se ambos os Advisors citarem (via sua própria chamada de LLM independente) o mesmo `document_chunk` do pool compartilhado — plausível, já que ambos recebem o mesmo top-5 — o `citations` plano em `_decision_support_response`/`_executive_narrative_response` (`intelligence.py:1457-1466`/equivalente) produzirá **duas entradas com `source_type`/`source_id`/`source_label` idênticos**, atribuídas a `advisor_name` diferentes, sem qualquer deduplicação (o list comprehension itera `result.explanations` × `cited_evidence` sem filtro de unicidade).

### 4.2 A duplicação é apenas apresentação ou possui impacto semântico?

**Impacto semântico real, não apenas cosmético.** Duas citações do mesmo `document_chunk`, atribuídas a dois Advisors distintos, na lista plana de `citations`, **parecem** duas confirmações independentes de fontes diferentes — quando são, estruturalmente, a mesma fonte consultada duas vezes pela mesma pergunta. Isso pode inflar artificialmente a percepção de robustez de uma resposta ("dois Advisors corroboram") quando na verdade é uma única evidência subjacente. Diferente de `risk_advisor`/`delivery_advisor` (que leem `kind="risk"`/`kind="status"` — populações de `AnalysisRecord` estruturalmente distintas, sem sobreposição possível por desenho, `provisioning.py:53-66`), o par `document_advisor`/`governance_advisor` não tem essa proteção — ambos consultam a **mesma** base RAG com a **mesma** pergunta.

Nota adicional: este par não está em `STRUCTURAL_PAIRS` (`correlation.py:19-24` — apenas `delivery+risk`, `strategy+risk`, `strategy+executive`, `governance+delivery`). Isso significa que `correlate()` ainda produz um `CorrelationFinding` para o par `document_advisor`/`governance_advisor` quando ambos têm evidência (todo par de Advisors com evidência gera um finding, `correlation.py:38-40`), mas com `is_structural_pair=False` — o catálogo estático foi desenhado para capturar "perspectivas estruturalmente distintas esperadas" (AR-17 §3), não "risco de sobreposição de evidência por identidade de consulta", que é uma dimensão diferente e não coberta por nenhum mecanismo hoje.

### 4.3 Este achado bloqueia o Wave 6 Completion?

**Não bloqueia — é exatamente a pendência que o Founder já nomeou como §8.8 OPEN**, a ser diagnosticada (feito, aqui) e avaliada antes do Completion Review, sem implementação de deduplicação sem diagnóstico prévio (mandato explícito do Founder, respeitado nesta missão).

---

## 5. Menor delta técnico para tornar Correlation/Conflict visíveis (quando o Founder autorizar)

Com base em §3 (contrato já completo), o delta é estritamente de apresentação, confinado a dois arquivos já existentes:

- `web/components/dashboard/decision-support-panel.tsx`
- `web/components/dashboard/executive-narrative-panel.tsx`

Nenhuma alteração necessária em: `intelligence.py`, `types.py` (backend ou frontend), BFF, hooks, `orchestrator.py`, `correlation.py`. Nenhuma rota nova, nenhum componente novo além dos dois painéis já existentes — exatamente a restrição do Founder (§4 da Founder Decision). **Esta missão não implementa esse delta** — apenas confirma que ele é pequeno e localizado, para informar a decisão do Founder sobre se/quando autorizá-lo.

---

## 6. Outras pendências técnicas concretas

Revisão de tudo que poderia impedir Wave 6 Completion, além do já coberto:

- **Nenhuma pendência de preservação arquitetural** — nenhuma alteração de código ocorreu desde D-163; `git status` permanece limpo de alterações em `src/`/`tests/`/`web/` além desta missão documental.
- **Nenhuma pendência de teste quebrado** — última execução completa (D-161/D-163): backend 860, frontend 541, E2E 316/2 skipped/0 failed, todas verdes; nenhum código foi tocado desde então.
- **§8.8 (citation duplication)** é a única pendência técnica genuinamente aberta identificada (§4) — nenhuma outra lacuna estrutural foi encontrada na leitura de `orchestrator.py`, `provisioning.py`, `correlation.py`, `synthesis.py`, `selection_rule.py`, `catalog.py`.

---

## 7. Itens formalmente Deferred (per Founder Decision)

- **Executive Briefing** — sem novo caso de uso e nova Founder Decision, nenhuma implementação inicia.
- **§8.3 Paralelismo** — DEFERRED UNTIL MEASURED NEED. Execução sequencial permanece padrão.
- **§8.4 Cache** — DEFERRED UNTIL MEASURED NEED. Nenhum cache introduzido antecipadamente.
- **§8.9 EnterpriseMemoryService** — DEFERRED. Existência não justifica integração artificial.

## 8. Itens Closed (per Founder Decision)

- **§8.7 Confidence** — CLOSED. Não haverá confidence score; `insufficient_basis` + evidência rastreável permanecem o mecanismo institucional.
- **§8.10 Workflow Runtime** — CLOSED FOR SYNCHRONOUS EXECUTIVE INTELLIGENCE. Permanece fora do caminho síncrono; qualquer integração futura exige caso de uso explícito.

## 9. Item permanece OPEN

- **§8.8 Citation Duplication** — diagnosticado nesta missão (§4): duplicação real e semanticamente relevante identificada no par `document_advisor`/`governance_advisor` sob `scope=organization`. Avaliação concreta concluída; **deduplicação não implementada** (mandato explícito: não implementar sem diagnóstico prévio — o diagnóstico está pronto, a decisão de implementar ou não permanece do Founder).

---

## 10. Caminho mínimo para Wave 6 Completion

1. **Decisão do Founder sobre §8.8**: autorizar (ou não) a implementação de deduplicação de citações no par `document_advisor`/`governance_advisor` (e quaisquer outros pares que usem `gather_rag_context` com argumentos idênticos) antes do Completion Review — ou aceitar o risco residual e documentá-lo como conhecido.
2. **Decisão do Founder sobre a visibilidade de Composition Trace (§5)**: autorizar (ou não) o delta mínimo de apresentação identificado — puramente incremental, sem nova Capability, sem impacto em nenhum componente protegido.
3. **Wave 6 Completion Review** — produzido nos mesmos termos institucionais da Wave 5, uma vez 1-2 decididos (mesmo que a decisão seja "não implementar agora, aceitar como risco documentado").

Nenhum item do caminho mínimo exige nova implementação de Capability — confirmando e reforçando a conclusão do Progress Assessment V3.

---

## 11. Percentual atualizado, fundamentado

A consolidação institucional (taxonomia §1) resolve objetivamente a ambiguidade que mantinha W6-2/W6-4 parcialmente indefinidos no V3 — Cross Advisor Correlation/Conflict Analysis não são mais avaliadas como Capabilities pendentes de consumidor, e sim como operações internas já 100% providas pelo mecanismo compartilhado; Executive Briefing é formalmente Deferred, não mais um item "Not Started" pendente de decisão sobre iniciar ou não.

| Epic/Dimensão | V3 | Consolidation Review | Justificativa |
|---|---|---|---|
| W6-1 — Executive Orchestration Foundation | 100% | **100%** | Inalterado. |
| W6-2 — Cross-Advisor Correlation & Conflict Detection | ~70% | **100%** (como operação interna) | Reclassificada — deixou de ser avaliada como Capability própria pendente; o objetivo real do Epic (mecanismo de correlação/conflito funcionando) está integralmente entregue e provado 2x em produção. A pendência remanescente (§8.8, deduplicação) é uma refinamento de qualidade da operação, não uma lacuna de entrega do Epic. |
| W6-3 — Executive Narrative & Citation Model | ~90% | **90%** (inalterado) | Executive Narrative Delivered; resta apenas a decisão de exposição de Composition Trace (§5), incremental. |
| W6-4 — Briefing/Organizational Intelligence | 0% | **Deferred** (fora do cálculo de conclusão da Wave corrente) | Formalmente não é mais "trabalho pendente da Wave 6 atual" — é trabalho explicitamente adiado para um ciclo futuro com novo caso de uso. |

**Estimativa consolidada: ~95% da Wave 6 tal como agora institucionalmente delimitada** (produto: Decision Support + Executive Narrative; operações: Selection/Execution/Correlation/Synthesis, todas providas) — **considerando Executive Briefing formalmente fora do escopo de conclusão desta Wave** (Deferred, não uma dívida da Wave 6 atual). Se Executive Briefing for contado como quarto Epic obrigatório (leitura mais conservadora, tratando "Deferred" como "ainda parte da Wave"), a estimativa recua para **~72%** ((100+100+90+0)/4). Ambas as leituras são apresentadas porque a diferença depende exclusivamente de uma decisão de enquadramento do Founder (Executive Briefing conta como escopo da Wave 6 ou como próximo ciclo institucional distinto) — este documento não decide isso silenciosamente.

---

## 12. Recomendação

**GO/NO-GO: GO condicional.** A Wave 6, na taxonomia agora consolidada, está tecnicamente pronta para o Completion Review assim que as duas decisões de §10 forem tomadas (§8.8 citation duplication; visibilidade de Composition Trace). Nenhuma delas exige nova implementação de Capability; a primeira pode inclusive ser resolvida por "aceitar como risco documentado, sem implementação" sem bloquear o encerramento.

**Nenhuma implementação foi realizada nesta missão** — todos os achados acima são diagnósticos de leitura de código, reproduzíveis e citados por arquivo/linha.

Retornando obrigatoriamente para Executive Review. Nenhum trabalho posterior inicia automaticamente.

---

## 13. Atualização — Resolução implementada (2026-08-10, D-165)

O Founder aprovou este Consolidation Review ("Wave 6 Final Consolidation Actions") e mandatou a implementação das duas pendências de §10, com princípios explícitos. Ambas resolvidas:

**§8.8 Citation Duplication — RESOLVIDO (não mais OPEN).** `_consolidate_citations()` (`src/api/routes/intelligence.py`), reusada por `_decision_support_response()`/`_executive_narrative_response()`, agrupa citações pela identidade real e estável da fonte (`Evidence.source_type`/`source_id` — nunca texto, label, similaridade ou hash inventado), preservando todo Advisor que citou aquela fonte em `advisor_names: list[str]` (contrato evoluído de `advisor_name: str`). Localizada exclusivamente na camada de composição/apresentação — `Document Advisor`, `Governance Advisor`, demais Advisors, RAG Pipeline, Knowledge Platform, `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine` preservados integralmente (`git diff --stat` vazio). Provado: (1) unitariamente, 8 cenários A-G em `tests/test_executive_intelligence_citation_consolidation.py`; (2) ponta a ponta, com documento real ingerido/indexado e `document_advisor`/`governance_advisor` citando o mesmo `chunk_id` sob `scope=organization` via HTTP real, em `tests/test_executive_narrative_api.py::TestCitationConsolidation`.

**Composition Trace visível — RESOLVIDO.** `CompositionTraceSummary` (`web/components/dashboard/composition-trace-summary.tsx`), componente compartilhado (mesmo padrão de reuso do `ScopeSelector`, D-161), reutilizado por `DecisionSupportPanel`/`ExecutiveNarrativePanel` sem nenhuma rota, BFF, página ou contrato backend novo — confirmando a análise de §3/§5: o contrato já continha tudo o necessário. Exibe Advisors utilizados, correlações identificadas, possíveis conflitos (correlações `is_structural_pair`, sempre expostos, nunca resolvidos automaticamente) e fontes consolidadas — nunca JSON bruto. Provado por 5 testes de componente (`composition-trace-summary.test.tsx`) e por asserções E2E novas nos dois cenários de escopo organização (`dashboard.spec.ts`).

**Suítes finais:** backend 869 passed (860 + 9 novos); frontend 546 passed (541 + 5 novos); E2E 65 passed no run completo + 1 flake de cold-start confirmado por reexecução isolada (mesmo padrão documentado em toda a missão) — 0 falhas reais. `ruff`/`tsc`/`eslint` limpos. Preservação arquitetural confirmada.

**Pendências remanescentes:** nenhuma técnica. A Wave 6, na taxonomia consolidada (§1), não tem mais bloqueio identificado para o Completion Review.

**GO/NO-GO revisado: GO para iniciar imediatamente o Wave 6 Completion Review.**
