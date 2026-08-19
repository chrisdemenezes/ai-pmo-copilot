# WAVE 6 PROGRESS ASSESSMENT V3 — Executive Intelligence (pós-Executive Narrative)

**Data:** 2026-08-10
**Autor:** Claude / Tech Lead
**Gatilho:** "Founder Decision — Executive Narrative Closure" (APPROVED, Executive Narrative = Delivered, D-162), que mandatou exclusivamente esta reavaliação integral da Wave 6 com base no código real atual, agora com duas Capabilities efetivamente entregues. **Missão exclusivamente de avaliação e replanejamento. Nenhum código. Nenhum Technical Design. Nenhuma implementação.**

**Princípio aplicado rigorosamente:** *Grounded before Generalized* — nenhuma Capability é classificada como entregue apenas porque suas operações estruturais existem em código, porque um mecanismo compartilhado tem consumidor real através de *outra* Capability, ou porque um valor de enum/teste interno a menciona. Toda classificação demonstra consumidor real, contrato real e comportamento real para a própria Capability avaliada, ou nomeia explicitamente sua ausência.

**Relação com V1/V2:** este documento é uma reavaliação integral, não uma correção retroativa. V1 e V2 permanecem preservados, intocados, como registro histórico do estado da Wave 6 em cada momento anterior. Onde este V3 diverge, a divergência é justificada explicitamente por evidência de código nova, nunca por mudança de critério não fundamentada.

---

## 1. Método

Reavaliação por leitura direta de código (nunca inferida do Decision Log isoladamente), cobrindo: `src/services/executive_orchestrator/` (types, orchestrator, catalog, selection_rule, correlation, synthesis, provisioning), `src/api/routes/intelligence.py`, `tests/test_executive_orchestrator_*.py`, `tests/test_decision_support_api.py`, `tests/test_executive_narrative_api.py`, e todo `web/` (rotas BFF, hooks, componentes, `e2e/`). Toda afirmação de "nunca invocada", "nenhum consumidor" ou "nunca renderizado" é verificada por busca textual exaustiva (`grep -rn`), reproduzida abaixo.

---

## 2. Achado central

**Duas Capabilities da Wave 6 têm agora um caminho de código alcançável por um usuário real: Decision Support e Executive Narrative.**

```
$ grep -rn "orchestrator.run\|\.run(Capability\." src/ web/ --include="*.py" --include="*.ts" --include="*.tsx" | grep -v "/tests/\|test_"
src/api/routes/intelligence.py: result = orchestrator.run(Capability.DECISION_SUPPORT, session, request.question, signals)
src/api/routes/intelligence.py: result = orchestrator.run(Capability.EXECUTIVE_NARRATIVE, session, EXECUTIVE_NARRATIVE_PROMPT, signals)

$ grep -n "@router\." src/api/routes/intelligence.py | grep -i "briefing\|correlation\|conflict\|recommendation-package"
(nenhum resultado)

$ grep -rln "executive-briefing\|cross-advisor-correlation\|conflict-analysis\|recommendation-package" web/app web/lib web/components
(nenhum resultado)
```

Nenhuma rota HTTP, nenhum contrato de resposta, nenhuma tela em `web/` expõe Cross Advisor Correlation, Conflict Analysis, Executive Briefing ou Recommendation Package. Este achado central de V1/V2 permanece verdadeiro para essas quatro Capabilities — a mudança desde V2 é exclusivamente sobre Executive Narrative.

**Achado novo nesta reavaliação — a Correlação já roda em produção real, mas seu resultado é invisível ao usuário:**

```
$ sed -n '113,122p' src/services/executive_orchestrator/orchestrator.py
        correlation = correlate(tuple(explanations))
        if capability == Capability.CONFLICT_ANALYSIS:
            correlation = tuple(finding for finding in correlation if finding.is_structural_pair)
        trace = trace.with_correlations(...)

$ grep -n "composition_trace\|correlations" web/components/dashboard/decision-support-panel.tsx web/components/dashboard/executive-narrative-panel.tsx
(nenhum resultado)
```

`correlate()` é chamado **incondicionalmente** em todo `orchestrator.run()`, para toda Capability, sem exceção — inclusive Decision Support e Executive Narrative, ambas em produção real. O achado de correlação (`composition_trace.correlations`, incluindo `is_structural_pair`) já trafega no contrato HTTP de ambas (`DecisionSupportResponse`/`ExecutiveNarrativeResponse`) e já chega ao BFF e ao browser. **Mas nenhum dos dois painéis (`decision-support-panel.tsx`, `executive-narrative-panel.tsx`) renderiza `composition_trace` em nenhuma forma** — o dado chega ao cliente e é descartado sem exibição. Isto é evidência direta e central para as perguntas 1-3 do Founder (§4.1 abaixo).

---

## 3. Wave 6 Delivery Matrix V3 — as seis Capabilities (AR-17 §1/§2)

| Capability | Composição (AR-17 §2) | Classificação V2 | Classificação V3 | Evidência |
|---|:---:|---|---|---|
| **Decision Support** | Seleção → Execução → Correlação → Síntese | Delivered | **Delivered** (inalterado) | V2 §4.1, reconfirmado nesta missão. |
| **Executive Narrative** | Seleção → Execução → Correlação → Síntese | Partially Delivered | **Delivered** | D-161/D-162; consumidor real, 3 scopes, não-aliasing provado. |
| **Cross Advisor Correlation** | Seleção → Execução → Correlação | Partially Delivered | **Partially Delivered** (reclassificação recomendada — ver §4.1) | Mecanismo roda em produção real (via Decision Support/Executive Narrative), mas nunca como Capability nomeada, e seu output nunca chega a um usuário real (ver §2). |
| **Conflict Analysis** | Seleção → Execução → Correlação | Partially Delivered | **Partially Delivered** (mesma ressalva) | Idêntico a Cross Advisor Correlation, com filtro adicional (`is_structural_pair`). |
| **Executive Briefing** | Seleção → Execução → Correlação → Síntese | Not Started | **Not Started** (inalterado) | Zero teste que invoque `orchestrator.run(Capability.EXECUTIVE_BRIEFING, ...)`; requer lógica de domínio multi-escopo inexistente. |
| **Recommendation Package** | Seleção → Execução → Correlação → Síntese | Not Started | **Not Started** (inalterado, risco de alias confirmado — ver §4.4) | Zero teste em qualquer arquivo; mecanicamente indistinguível de Executive Narrative se exposta hoje. |

**Duas de seis Capabilities agora Delivered** (Decision Support, Executive Narrative) — up de uma em V2.

---

## 4. As oito perguntas do Founder, respondidas com evidência de código

### 4.1 Cross Advisor Correlation e Conflict Analysis precisam realmente de consumidor próprio?

**Não, com alta confiança — a evidência aponta na direção oposta.** Três fatos, juntos, sustentam esta resposta:

1. O mecanismo (`correlate()`) já é executado, sem exceção, dentro de toda chamada a `orchestrator.run()` — inclusive nas duas Capabilities já em produção. Não há nenhuma incógnita técnica restante sobre se ele funciona ponta a ponta com Advisors reais, evidência real, RBAC real (provado 5× em teste + 2× em produção, ver §2).
2. O que uma Capability "Cross Advisor Correlation" dedicada produziria — uma lista de pares de Advisors estruturalmente relacionados, sem narrativa — **já está presente, hoje, no contrato HTTP de Decision Support e Executive Narrative** (`composition_trace.correlations`). Um consumidor dedicado replicaria a mesma Seleção/Execução/Correlação que Decision Support/Executive Narrative já fazem, exigindo do usuário fazer uma segunda pergunta separada só para ver a mesma correlação que a primeira resposta já calculou e descartou.
3. O único gap real não é "falta mecanismo" nem "falta consumidor novo" — é que **o dado que já existe no contrato nunca chega à tela.** Isso é um problema de UI de duas linhas de escopo (exibir `composition_trace.correlations` dentro dos painéis já existentes), não um problema de nova Capability.

### 4.2 Ou já funcionam legitimamente como operações internas reutilizadas pelas Capabilities de produção?

**Sim, no sentido estrito de "operação" (mecanismo) — não, ainda, no sentido de "entrega de valor ao usuário".** A operação `correlate()` está legitimamente absorvida e reutilizada por Decision Support e Executive Narrative, exatamente como a AR-17 previu (mecanismo compartilhado, nenhuma Capability inventa mecânica própria). Mas "reutilizada internamente" não é o mesmo que "entrega valor" enquanto o resultado permanecer invisível na UI. A classificação honesta, por isso, permanece **Partially Delivered** (não Delivered, não Not Started) — o mecanismo é real e provado; o valor específico que essas duas Capabilities nomeadas prometem (visibilidade explícita de correlação/conflito) ainda não chega a ninguém.

### 4.3 Existe valor de produto real em expô-las diretamente ao usuário?

**Valor real, mas incremental, e mais barato como extensão de UI do que como Capability nova.** Um executivo que já recebeu uma Narrativa Executiva ou uma resposta de Decision Support se beneficiaria de ver, na mesma tela, "estes dois Advisors concordam/discordam estruturalmente" — isso é exatamente `composition_trace.correlations`, já calculado, já no contrato. Não há evidência de valor adicional em uma tela *separada* dedicada a "pergunte apenas pela correlação, sem narrativa" — isso duplicaria o fluxo de escopo/seleção já existente para produzir uma fração do que a resposta completa já entrega. **Recomendação: se o Founder decidir que este valor deve ser exposto, o caminho de menor risco é renderizar `composition_trace` (incluindo `correlations`) dentro de `DecisionSupportPanel`/`ExecutiveNarrativePanel` já existentes — não construir duas novas rotas/páginas.** Esta é uma decisão de produto do Founder, não implementada nesta missão (exclusivamente documental).

### 4.4 Recommendation Package ainda representa comportamento distinto de Executive Narrative?

**Não — e agora isso pode ser demonstrado com uma Capability real como referência, não apenas em teoria.** `CAPABILITIES_WITH_SYNTHESIS` (`orchestrator.py:44-50`) inclui ambas `EXECUTIVE_NARRATIVE` e `RECOMMENDATION_PACKAGE` no mesmo conjunto; `synthesize()` tem uma única assinatura, produz um único texto de prosa, e é chamada de forma idêntica para qualquer Capability desse conjunto. Se Recommendation Package fosse exposta hoje com o mesmo padrão já validado (reutilizando `resolve_decision_support_scope()`/`ExecutiveOrchestrator` como Executive Narrative fez), o resultado seria, mecanicamente, **idêntico a Executive Narrative** — mesma Seleção, mesma Execução, mesma Correlação, mesma chamada a `synthesize()` produzindo a mesma forma de prosa — divergindo apenas no rótulo `capability` na resposta. Nenhuma linha de código, em nenhum lugar do repositório, diferencia "narrativa coerente" de "organização não-ranqueada de achados lado a lado" (a definição da AR-17 §1 para esta Capability). **Não está pronta para Delivered nem para implementação — precisa de uma decisão explícita do Founder sobre o que a diferencia em comportamento observável, ou de Deferred formal.**

### 4.5 Executive Briefing ainda necessita lógica própria ou pode ser uma composição/configuração de mecanismos já existentes?

**Ainda necessita lógica própria — inalterado desde V2, reconfirmado.** `grep -n "class OrchestrationScope" src/api/routes/intelligence.py` e a leitura de `resolve_decision_support_scope()` confirmam que toda resolução de escopo produz exatamente um `OrchestrationScope` por chamada (um Project, um Portfolio, ou a organização inteira em um único disparo). A noção central desta Capability (Kickoff §4/§9: visão periódica ou sob demanda cobrindo múltiplas unidades organizacionais simultaneamente, ex. "todos os Portfolios de uma organização, cada um com sua própria composição") não existe em nenhuma camada — não é uma questão de expor um caminho já existente, como foi o caso de Executive Narrative. Diferente das outras três Capabilities pendentes, esta não pode se tornar Delivered apenas por replicação de padrão.

### 4.6 Quais questões remanescentes do Kickoff (§8) continuam efetivamente necessárias?

Reavaliação das seis pendências identificadas em V2 (§7.8):

| # | Questão (Kickoff §8) | Status nesta reavaliação |
|---|---|---|
| §8.3 | Execução paralela ou sequencial? | **De facto resolvida operacionalmente, nunca formalizada.** Tanto a Founder Decision de Decision Support quanto a de Executive Narrative mandataram explicitamente "não implementar paralelismo" e confirmaram execução sequencial medida (`orchestrator.py`, sem paralelismo estrutural, ordem de logs). Duas decisões independentes convergindo no mesmo resultado é, na prática, uma decisão — falta apenas registrá-la como princípio permanente. Baixo risco, custo de registro quase nulo. |
| §8.4 | Existe cache? | **Mesmo padrão de §8.3** — "nenhuma otimização prematura" mandatado duas vezes, nenhum cache implementado, nenhuma pressão real (latência medida em 0,22s de piso estrutural). De facto resolvida, não formalizada. |
| §8.7 | Como medir confiança? | **Ainda genuinamente em aberto.** Decision Support e Executive Narrative explicitamente excluíram "confidence score" do escopo (Founder, "FORA DE ESCOPO"), mas isso foi uma decisão de escopo por missão, não uma decisão arquitetural sobre se/como a Wave 6 deve medir confiança. Continua necessária se qualquer Capability futura precisar comunicar graus de robustez de evidência. |
| §8.8 | Como evitar duplicação de citação entre Advisors? | **Ainda em aberto, e agora mais relevante, não menos.** Com duas Capabilities reais em produção citando múltiplos Advisors simultaneamente (até 7, sob `scope=organization`), o risco descrito no Kickoff (dois Advisors citarem o mesmo `AnalysisRecord`/`Chunk` subjacente como se fossem fatos independentes) deixou de ser hipotético — é um cenário que já ocorre estruturalmente em produção real toda vez que `scope=organization` é usado. `correlate()` identifica pares estruturais pré-declarados (`STRUCTURAL_PAIRS`), nunca compara *conteúdo* de citação. Recomendado para avaliação antes de expor uma terceira Capability multi-Advisor. |
| §8.9 | `EnterpriseMemoryService` participa da Wave 6? | **Inalterado.** `grep -n "EnterpriseMemoryService\|MemoryRecord" src/services/executive_orchestrator/*.py` → zero ocorrências, reconfirmado nesta missão. Continua sem papel decidido. |
| §8.10 | Workflow Runtime tem papel na Wave 6? | **Inalterado.** `git log -- src/workflows/` não mostra nenhum commit desde a Wave 4 (`Epic W4-4`). Continua sem papel decidido; só se tornaria relevante se Executive Briefing (§4.5, ainda Not Started) avançar. |

**Conclusão:** de seis pendências, duas (§8.3/§8.4) são hoje risco de governança, não risco técnico — a decisão já foi tomada na prática duas vezes, só falta registrá-la formalmente. As outras quatro (§8.7/§8.8/§8.9/§8.10) continuam genuinamente sem decisão, e §8.8 ganhou urgência real com a segunda Capability em produção.

### 4.7 Qual é o caminho mínimo restante para encerrar a Wave 6?

Em ordem de dependência, considerando que **nenhum item abaixo exige nova implementação de Capability**:

1. **Formalizar §8.3/§8.4** como princípio permanente (registro de governança, ~1 parágrafo) — "execução sempre sequencial, sem cache, revisitar apenas mediante evidência real de latência" já é o comportamento de fato em duas Capabilities.
2. **Decisão explícita do Founder sobre Cross Advisor Correlation / Conflict Analysis** (§4.1-§4.3): formalmente absorver como mecanismo interno já exposto via `composition_trace` (com ou sem trabalho futuro de UI para renderizá-lo), em vez de persegui-las como Capabilities autônomas — elimina a pendência sem exigir dois novos consumidores.
3. **Decisão explícita do Founder sobre Executive Briefing e Recommendation Package** — Deferred formal (com a justificativa já grounded em §4.4/§4.5: Recommendation Package é hoje um alias funcional de Executive Narrative sem decisão de diferenciação; Executive Briefing exige lógica de domínio multi-escopo nunca iniciada) ou abertura de um novo ciclo institucional dedicado a cada uma, à escolha do Founder.
4. **Decisão sobre §8.7/§8.8/§8.9/§8.10** — mínimo necessário é a decisão em si (inclusive "Deferred" é uma decisão válida), não implementação.
5. **Wave 6 Completion Review** — produzida nos mesmos termos institucionais da Wave 5, somente depois de 1-4 resolvidos.

**Consequência direta desta reavaliação:** é hoje estruturalmente possível encerrar a Wave 6 institucionalmente **sem nenhuma nova linha de código de Capability**, desde que o Founder decida formalmente o destino das quatro Capabilities restantes (absorver/Deferred) e as quatro questões §8 remanescentes. Isso é uma mudança de caminho crítico em relação a V2, que recomendava expor uma segunda Capability como próximo passo — esse passo já foi dado.

### 4.8 Qual é o novo percentual de conclusão da Wave 6, baseado exclusivamente em entregas reais?

| Epic | V2 | V3 | Justificativa da variação |
|---|---|---|---|
| **W6-1 — Executive Orchestration Foundation** | 100% | **100%** | Inalterado. |
| **W6-2 — Cross-Advisor Correlation & Conflict Detection** | ~65% | **~70%** | Mecanismo agora provado em produção real por **duas** Capabilities (não uma), reduzindo ainda mais o risco técnico residual; §8.8 (duplicação de citação) permanece em aberto e agora com urgência real (§4.6), o que impede uma nota mais alta. |
| **W6-3 — Executive Narrative & Citation Model** | ~65% | **~90%** | Executive Narrative, a Capability nomeada deste Epic, está **Delivered** — consumidor real, contrato completo, três scopes provados, não-aliasing provado. Resta exclusivamente §8.7 (medição de confiança), nunca resolvida formalmente. |
| **W6-4 — Briefing/Organizational Intelligence** | 0% | **0%** | Inalterado — nenhuma lógica de domínio multi-escopo existe em qualquer camada. |
| **Consumidor de produção (transversal)** | 1 de 6 Capabilities | **2 de 6 Capabilities** | Decision Support + Executive Narrative. |

**Estimativa consolidada da Wave 6: ~65% concluída** (subiu de ~50% em V2), média simples dos quatro Epics — refletindo que a segunda Capability em produção não apenas soma um ponto de dados, mas **fecha objetivamente o Epic W6-3** e demonstra, pela primeira vez, que o padrão de exposição generaliza (a pergunta que V2 §8 deixou explicitamente em aberto: "sem esse segundo ponto de dados, qualquer conclusão sobre 'quão barato é expor as Capabilities restantes' permanece uma extrapolação de amostra de tamanho um" — essa extrapolação agora tem uma segunda amostra confirmando o custo baixo).

A Wave permanece **não encerrada**: quatro de seis Capabilities nomeadas seguem sem consumidor próprio — mas, por §4.7, isso não significa necessariamente mais trabalho de implementação; pode significar decisões formais de absorção/Deferred que fecham a Wave sem código adicional.

---

## 5. Recomendação

**Próximo ciclo institucional recomendado: exclusivamente decisório, não de implementação.** O caminho crítico restante (§4.7) é inteiramente composto de decisões do Founder sobre o destino das quatro Capabilities pendentes e das quatro questões §8 remanescentes — nenhuma delas exige um novo Technical Design ou nova implementação para ser respondida. Uma vez respondidas, o Wave 6 Completion Review pode ser produzido.

**Risco identificado, não bloqueante:** se o Founder decidir expor Cross Advisor Correlation e/ou Conflict Analysis como Capabilities autônomas (contrariamente à recomendação de §4.1-§4.3), o trabalho de implementação seria de baixo risco técnico (mesmo padrão replicado 2× com sucesso), mas a análise desta missão sugere que o valor de produto está majoritariamente em tornar `composition_trace` visível dentro dos painéis já existentes, não em novas rotas.

**GO/NO-GO para abrir o próximo ciclo institucional: GO**, condicionado exclusivamente a uma nova Founder Decision explícita que resolva as pendências de §4.7 — nenhuma implementação, Domain Blueprint ou Technical Design é produzido por esta avaliação. **Nenhum trabalho posterior inicia automaticamente.**

---

## 6. Nota de preservação

Missão exclusivamente documental — `git status` confirma zero alteração em `src/`/`tests/`/`web/` durante a produção deste documento. Todas as citações de código acima são leituras, nenhuma escrita.
