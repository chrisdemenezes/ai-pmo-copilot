# AR-15 — Architecture Review do Strategy Advisor

**Etapa 3 de 6** do ciclo institucional do Strategy Advisor. Produzida sob autorização da Founder Decision que aprovou o Domain Blueprint (`DOMAIN-BLUEPRINT-STRATEGY-ADVISOR.md`) com **GO para a Architecture Review**, oficializando: as três fontes de estratégia como definitivas e exclusivas; que cada unidade responde exclusivamente pela sua própria estratégia declarada (proibição permanente de inferir objetivos entre níveis); a execução composta exclusivamente por `AnalysisRecord`/`status`/`risk`; o `StrategyEvidenceAssembler` como quarto padrão consolidado Classe B, responsável exclusivamente por reorganizar evidências segundo a estrutura estratégica da organização; e a distinção permanente entre ausência de estratégia, ausência de execução e unidade não comparável — estados que nunca podem ser tratados como equivalentes. Delegando a esta etapa cinco resoluções explícitas: regra conceitual de alinhamento; conflitos entre níveis estratégicos; ausência em níveis intermediários; precedência entre unidades; modelo definitivo de citações. Nenhum código escrito nesta etapa.

---

## 0. O que já é oficial (não reaberto aqui)

| Decisão | Origem |
|---|---|
| Fontes exclusivas: `Portfolio.strategic_objective`/`Program.objective`/`Project.objective` | Domain Blueprint + Founder Decision |
| Cada unidade responde exclusivamente pela sua própria estratégia declarada — proibido permanentemente inferir objetivos entre níveis | Founder Decision |
| Execução composta exclusivamente por `AnalysisRecord`/`status`/`risk` | Domain Blueprint + Founder Decision |
| Três unidades independentes de alinhamento: Portfolio, Program, Project | Domain Blueprint |
| `StrategyEvidenceAssembler`: quarto padrão consolidado Classe B, responsabilidade exclusiva de reorganizar evidências segundo a estrutura estratégica — nunca interpreta, nunca calcula alinhamento | Domain Blueprint + Founder Decision |
| Distinção permanente e nunca equivalente entre: ausência de estratégia / ausência de execução / unidade não comparável | Founder Decision |
| Escopo organizacional, reaproveitando a traversal Portfolio→Program→Project já estabelecida pelo Portfolio Advisor | Domain Blueprint |
| Preservação integral de `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline nesta etapa | Founder Decision |

---

## 1. Executive Summary

Esta Architecture Review resolve as cinco questões delegadas pela Founder Decision e registra um achado crítico de compatibilidade encontrado durante a revisão, com resolução que **não exige nenhuma mudança de infraestrutura compartilhada**.

**Regra conceitual de alinhamento:** nunca calculada deterministicamente em código — sempre um julgamento semântico do `StrategyAdvisorAgent`/LLM, comparando o texto do objetivo declarado com o conteúdo real da evidência de execução de uma unidade comparável, sempre fundamentado em citação explícita de ambos. Mesma disciplina já aplicada à classificação do Governance Advisor (interpretação vive no prompt, nunca em código) e ao "ordem não implica prioridade" do Portfolio/Executive Advisor (volume de evidência nunca implica grau de alinhamento).

**Conflitos entre níveis estratégicos:** comparar a declaração de um nível contra a declaração de outro (ex.: `Portfolio.strategic_objective` vs. `Program.objective`) **não é uma responsabilidade formal do Advisor** — nenhuma chamada, nenhuma regra de código, nenhuma instrução obrigatória de prompt exige essa comparação. Se as declarações de múltiplos níveis da mesma cadeia aparecerem juntas no mesmo conjunto de evidências, o LLM pode observá-las textualmente, mas nunca decide qual nível prevalece (decidir isso seria decidir estratégia, proibição permanente).

**Ausência em níveis intermediários:** confirmado que não afeta os níveis vizinhos — a agregação de execução de Portfolio já soma diretamente todos os Projects (via todos os seus Programs, tenham eles `objective` ou não); a ausência de `objective` em um Program apenas torna esse Program específico não comparável, sem propagar ausência para cima (Portfolio) nem para baixo (Project).

**Precedência entre unidades:** **não existe** — Portfolio, Program e Project são observações independentes e paralelas, nunca uma hierarquia de autoridade (diferente da hierarquia documental do Governance Advisor, que resolve qual **fonte** prevalece sobre o mesmo fato). Cada unidade responde a uma pergunta estruturalmente distinta; todas as unidades comparáveis são apresentadas juntas, rotuladas por sua própria unidade, nunca fundidas em um veredito único.

**Modelo definitivo de citações:** novo modelo isolado, `StrategyCitedEvidence` — nunca reaproveitando `CitedProject`/`ExecutiveCitedEvidence`. **Achado crítico encontrado nesta revisão, por leitura direta de código:** `RecommendationEngine.build()` indexa evidências exclusivamente por `Evidence.source_id` (`by_id = {item.source_id: item for item in evidence}`), sem considerar `source_type`/`kind` — o Strategy Advisor é o **primeiro** Advisor a combinar, no mesmo array de evidência de uma única chamada, dois espaços de identificador estruturalmente distintos (`AnalysisRecord.id` e `Portfolio`/`Program`/`Project.id`), criando risco real de colisão (um `Portfolio.id` numericamente igual a um `AnalysisRecord.id` presente na mesma resposta seria resolvido incorretamente). **Resolução que não toca `RecommendationEngine`:** o `StrategyEvidenceAssembler` usa um `source_id` sintético e disjunto (negativo, com faixas por nível) exclusivamente para evidência de estratégia declarada — nunca colide com `AnalysisRecord.id` (sempre positivo) — enquanto o id real da entidade permanece preservado em `Evidence.metadata`, nunca exposto como `source_id` sintético na resposta HTTP.

**Recomendação: GO para o Technical Design.**

---

## 2. Regra conceitual de alinhamento

### 2.1 Nunca um cálculo determinístico

Diferente de staleness (aritmética de data) ou de cobertura (contagem de nulos), "alinhamento" entre um objetivo declarado (texto livre, até 1000 caracteres) e uma evidência de execução (conteúdo estruturado de `AnalysisRecord`) é uma questão semântica — não há fórmula, comparação numérica ou regra de negócio que a plataforma possa calcular sem interpretar linguagem natural. O `StrategyEvidenceAssembler` nunca calcula alinhamento — apenas monta o par (estratégia declarada da unidade, evidência de execução da unidade) e entrega ambos como `Evidence` ao `AdvisorFramework.run()`.

### 2.2 Regra confirmada

O julgamento de alinhamento é produzido exclusivamente pelo `StrategyAdvisorAgent`/LLM, para cada unidade comparável, sempre:

- fundamentado no texto real do objetivo declarado daquela unidade específica (nunca de outra unidade);
- fundamentado no conteúdo real da evidência de execução daquela mesma unidade (direta para Project, agregada para Program/Portfolio);
- citando explicitamente ambos (o objetivo e o(s) `AnalysisRecord`(s) usados) — mesmo portão de rastreabilidade já em produção em todos os Advisors;
- nunca influenciado pela quantidade de evidência de execução disponível — mais registros de risco não implica maior desalinhamento, mesma disciplina "ordem não implica prioridade" já estabelecida no Portfolio/Executive Advisor, estendida aqui a volume também.

### 2.3 Taxonomia de saída — não decidida nesta etapa

Se o Technical Design optar por uma classificação de vocabulário controlado (análoga aos 5 estados do Governance Advisor, decidido em sua própria etapa de Technical Design, não em AR-10) é uma decisão reservada ao Technical Design do Strategy Advisor, não a esta revisão — o que esta etapa resolve é o princípio (sempre semântico, nunca determinístico, sempre citado), não o formato exato da saída.

---

## 3. Conflitos entre níveis estratégicos

**Não é uma responsabilidade formal do Advisor.** Comparar a declaração de um nível contra a declaração de outro nível (`Portfolio.strategic_objective` vs. `Program.objective`, por exemplo) nunca é uma chamada, regra de código ou instrução obrigatória de prompt — o Domain Blueprint já havia estabelecido que "a comparação nunca cruza unidades" (execução vs. estratégia da própria unidade); esta revisão confirma que essa mesma restrição vale também para comparações estratégia-vs-estratégia entre níveis.

Como o `StrategyEvidenceAssembler` entrega, na mesma chamada, as evidências de estratégia declarada de Portfolio, Program e Project de uma mesma cadeia (quando comparáveis), o LLM tecnicamente **pode** observar textualmente uma divergência aparente entre elas ao formular sua resposta — isso é permitido como leitura factual das declarações reais fornecidas, nunca proibido por completo, mas:

- nunca é uma responsabilidade obrigatória do Advisor (o Advisor não precisa procurar conflitos entre níveis);
- o Advisor **nunca decide qual nível prevalece** — isso seria decidir estratégia, proibição permanente reafirmada;
- nenhum cálculo estrutural de "conflito entre níveis" existe em código — se mencionado, é sempre prosa do LLM fundamentada nas declarações reais entregues.

---

## 4. Ausência em níveis intermediários

**Confirmado: não afeta os níveis vizinhos.** A agregação de evidência de execução de cada nível é sempre feita **diretamente sobre os Projects** (Domain Blueprint §5.2, passos 5-6):

- Portfolio-level: soma a execução de todos os Projects sob **todos** os seus Programs, tenham eles `objective` declarado ou não;
- Program-level: soma a execução dos Projects daquele Program especificamente;
- Project-level: usa apenas a evidência direta daquele Project.

Nenhuma dessas três agregações depende de uma etapa intermediária ter sua própria declaração — um Program sem `objective` simplesmente **não é comparável nesse nível** (contado estruturalmente como tal, per Domain Blueprint §7), mas isso nunca bloqueia, reduz ou de qualquer forma afeta a comparação de Portfolio acima ou de Project abaixo. Ausência em um nível é sempre local a esse nível, nunca propagada.

---

## 5. Precedência entre unidades

**Não existe precedência — Portfolio, Program e Project são observações independentes e paralelas.**

Diferente do Governance Advisor (AR-10), cuja hierarquia documental — Decision Log sempre a fonte mais alta — resolve **qual fonte prevalece quando duas fontes conflitam sobre o mesmo fato**, o Strategy Advisor nunca enfrenta esse problema estruturalmente: Portfolio, Program e Project nunca competem pela mesma verdade, porque cada unidade responde a uma pergunta diferente (a organização como um todo está alinhada? este programa está alinhado? este projeto está alinhado?) sobre uma evidência de execução diferente (agregada de forma diferente, per §4).

Consequência direta: todas as unidades comparáveis entram no mesmo conjunto de evidências, cada uma explicitamente rotulada por seu próprio nível (`level`) e identidade (`entity_id`/`entity_name`, ver §6) — a resposta do Advisor apresenta as observações de cada unidade lado a lado, nunca fundidas em um veredito único de "a organização está alinhada" que exigiria um desempate entre níveis divergentes.

---

## 6. Modelo definitivo de citações

### 6.1 Achado crítico — colisão de espaço de identificadores

Por leitura direta de `src/services/ai_foundation/recommendation_engine.py`:

```python
def build(answer, cited_ids, evidence):
    by_id = {item.source_id: item for item in evidence}
    cited = [by_id[cited_id] for cited_id in cited_ids if cited_id in by_id]
    return Recommendation(answer=answer, cited_evidence=cited)
```

O agrupamento é feito **exclusivamente por `Evidence.source_id`**, sem nenhuma consideração de `source_type`/`kind`. Isso já era um risco nomeado (AR-8 §7, item 1 — nomenclatura acoplada a `AnalysisRecord`, cosmético, referente a `Chunk.id` do Document Advisor), mas nunca um risco de **colisão real**, porque nenhum Advisor até hoje combinava, no mesmo array de evidência de uma única chamada a `framework.run()`, dois espaços de identificador (`AnalysisRecord.id` e um segundo tipo de id) simultaneamente — Document/Governance Advisor usam exclusivamente `Chunk.id`; Portfolio/PMO/Executive Advisor usam exclusivamente `AnalysisRecord.id`.

**O Strategy Advisor é o primeiro a combinar dois espaços de identificador na mesma chamada**: `AnalysisRecord.id` (evidência de execução) e `Portfolio.id`/`Program.id`/`Project.id` (evidência de estratégia declarada). Como ambos são inteiros gerados por sequência própria de cada tabela, uma colisão numérica (ex.: `Portfolio.id = 42` e `AnalysisRecord.id = 42` presentes na mesma resposta) resolveria `by_id[42]` para apenas um dos dois — silenciosamente atribuindo a citação errada, um risco de correção, não apenas de nomenclatura.

### 6.2 Resolução — sem nenhuma mudança a `Evidence`/`RecommendationEngine`

O `StrategyEvidenceAssembler`, ao montar evidência de estratégia declarada, usa um **`source_id` sintético e estruturalmente disjunto de qualquer `AnalysisRecord.id`** (sempre positivo, per `SERIAL`/`IDENTITY`):

- valores sintéticos sempre **negativos** — nunca colidem com `AnalysisRecord.id`;
- namespaced por nível com faixas amplas, garantindo que os três níveis também nunca colidam entre si (ex.: Portfolio em uma faixa, Program em outra, Project — apenas para sua evidência de estratégia declarada, nunca para sua evidência de execução, que continua usando o `AnalysisRecord.id` real — em uma terceira faixa); valores exatos de offset são decisão do Technical Design, o princípio (disjunção garantida, nunca dependente de coincidência estatística) é decidido aqui.

O id real da entidade (`Portfolio.id`/`Program.id`/`Project.id`) **permanece preservado em `Evidence.metadata`** (ex.: `metadata["entity_id"]`), nunca perdido — o `source_id` sintético serve exclusivamente ao mecanismo interno de `RecommendationEngine.build()`/`AdvisorFramework.run()`, **nunca é exposto na resposta HTTP**: o mapeamento de `explanation.recommendation.cited_evidence` para `StrategyCitedEvidence` sempre lê o id real de `metadata["entity_id"]`, nunca o `source_id` sintético.

Evidência de execução (`kind="status"`/`"risk"`) nunca precisa dessa técnica — continua usando `AnalysisRecord.id` real diretamente, como todo Advisor anterior.

### 6.3 Modelo de citação (`StrategyCitedEvidence`, novo e isolado)

| Campo | Tipo | Origem |
|---|---|---|
| `level` | `str` — `"portfolio"`\|`"program"`\|`"project"` | Qual unidade esta citação pertence |
| `entity_id` | `int` | Id real do Portfolio/Program/Project (nunca o `source_id` sintético) |
| `entity_name` | `str` | Nome real da entidade |
| `kind` | `str` — `"status"`\|`"risk"`\|`"declared_strategy"` | Extensão do mesmo campo `kind` já usado por todo Advisor Classe B — terceiro valor introduzido aqui pela primeira vez |
| `source_id` | `int` | `AnalysisRecord.id` real (execução) ou o id real da entidade (estratégia declarada — nunca o sintético) |
| `created_at` | `datetime \| None` | `AnalysisRecord.created_at` real (execução); `None` para estratégia declarada — Portfolio/Program/Project não têm um timestamp de "declaração" próprio hoje |

**Nunca reaproveita `CitedProject` nem `ExecutiveCitedEvidence`** — nenhum dos dois consegue expressar `level` (múltiplos tipos de unidade, não apenas Project) nem o terceiro valor de `kind` (`"declared_strategy"`, que não é uma execução). Confirmação exigida: nenhuma mudança a `CitedProject`/`ExecutiveCitedEvidence`, ambos continuam servindo Portfolio/PMO/Executive Advisor sem nenhuma alteração.

---

## 7. Limites reafirmados (item 6 da Founder Decision, D-125/D-126)

- Nunca cria, escreve, decide ou altera `strategic_objective`/`objective`.
- Nunca infere objetivo entre níveis (§2.2 do Domain Blueprint, reafirmado por esta revisão em §3/§4).
- Nunca decide qual nível prevalece em caso de divergência aparente entre declarações (§3, §5).
- Nunca calcula alinhamento/desvio deterministicamente em código (§2).
- Nunca consome `Recommendation`/`Explanation`/resposta de outro Advisor.

---

## 8. Preservação de infraestrutura — confirmação

Nenhuma das cinco resoluções desta etapa exige mudança de assinatura ou comportamento em `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline — inclusive a resolução do achado crítico (§6), que é inteiramente uma técnica de composição dentro do próprio `StrategyEvidenceAssembler` (namespacing de `source_id`), nunca uma mudança ao mecanismo de agrupamento por id do `RecommendationEngine.build()` em si.

---

## 9. Riscos residuais

| Risco | Natureza | Mitigação registrada |
|---|---|---|
| Colisão de `source_id` entre `AnalysisRecord.id` e ids de domínio | Comprovado, encontrado nesta revisão | Resolvido via namespacing sintético disjunto (§6.2), sem mudança de infraestrutura compartilhada |
| Taxonomia de saída do julgamento de alinhamento ainda não definida | Não é risco — decisão explicitamente reservada ao Technical Design (§2.3) | N/A |
| Volume de faixas de namespacing (offsets exatos) ainda não fixado | Decisão de Technical Design | Princípio (disjunção garantida) já decidido, valores exatos reservados |

Nenhum risco listado é bloqueante para o Technical Design.

---

## 10. Critérios de sucesso

- Toda citação rastreável a uma unidade real (`level`+`entity_id`) e a uma evidência real (`AnalysisRecord` ou o próprio campo de objetivo) — nunca ambígua por colisão de `source_id`.
- Nenhum julgamento de alinhamento calculado deterministicamente em código.
- Nenhuma comparação estratégia-vs-estratégia entre níveis tratada como responsabilidade obrigatória ou geradora de decisão de precedência.
- Ausência em um nível nunca propaga para nem afeta os níveis vizinhos.
- `CitedProject`/`ExecutiveCitedEvidence` confirmados inalterados por `git diff` vazio, quando implementado.
- Nenhuma mudança de assinatura em `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline exigida por esta revisão.

---

## 11. Recomendação

**GO para o Technical Design do Strategy Advisor.**

Resolvido nesta etapa: regra conceitual de alinhamento (sempre semântica, nunca determinística); conflitos entre níveis estratégicos (não é responsabilidade formal, observação textual permitida, decisão de precedência nunca tomada); ausência em níveis intermediários (nunca propaga); precedência entre unidades (não existe — observações paralelas); modelo definitivo de citações (`StrategyCitedEvidence`, novo e isolado, resolvendo o achado crítico de colisão de `source_id` via namespacing sintético, sem tocar infraestrutura compartilhada).

Retorno obrigatório para Executive Review do Founder. Nenhum Technical Design será iniciado sem nova aprovação explícita.
