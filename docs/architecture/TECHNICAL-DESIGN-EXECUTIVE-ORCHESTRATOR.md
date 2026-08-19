# Technical Design — Executive Orchestrator

Primeiro Technical Design da Wave 6 — Executive Intelligence. Produzido sob autorização da "Founder Decision" que declarou toda a arquitetura conceitual da Wave 6 oficialmente concluída — `WAVE-6-EXECUTIVE-INTELLIGENCE-KICKOFF.md` (D-133), `WAVE-6-EXECUTIVE-INTELLIGENCE-VISION.md` (D-134/D-135/D-137/D-140, doze princípios permanentes + o conceito permanente de Executive Intelligence Result), `AR-16-EXECUTIVE-ORCHESTRATOR-ARCHITECTURE-REVIEW.md` (D-136/D-137), `DOMAIN-BLUEPRINT-EXECUTIVE-ORCHESTRATOR.md` (D-138) e `AR-17-EXECUTIVE-INTELLIGENCE-COMPOSITION-MODEL.md` (D-139/D-140) como única fonte de verdade — e mandatando exclusivamente este Technical Design. **Nenhum código. Nenhuma implementação. Nenhum pseudocódigo. Nenhuma alteração em `src/`, `tests/` ou `web/`. Nenhuma alteração em contrato compartilhado.**

**Precondição:** os cinco documentos acima, aprovados sem ressalvas, mais D-140 (Executive Intelligence Result registrado). Este documento nunca reabre nenhuma decisão já tomada neles — resolve exclusivamente **como** o Executive Orchestrator será implementado, dentro dos limites que eles já impõem.

**Forma desta etapa:** por mandato explícito do Founder, este Technical Design decide contratos, estados, transições e estratégia de composição inteiramente em nível conceitual — tabelas e prosa, nunca uma assinatura de método, nunca uma classe, nunca uma rota HTTP, nunca um schema de banco. Onde etapas anteriores da plataforma (ex.: `TECHNICAL-DESIGN-STRATEGY-ADVISOR.md`) fecham contrato em fórmula e assinatura, esta etapa fecha contrato em modelo conceitual — a tradução para código é trabalho de uma etapa de implementação futura, não desta.

---

## 0. O que já é oficial (não reaberto aqui)

| Decisão | Origem |
|---|---|
| Executive Intelligence nunca é uma nova fonte primária de evidência; consome exclusivamente `Explanation`s já produzidas por Advisors | Vision, Princípio 1 |
| `AdvisorFramework.run()` continua a executar exatamente um Advisor por chamada, sem exceção | Vision, Princípio 2 |
| Interpretação de evidência de domínio permanece exclusiva do Advisor dono daquele domínio | Vision, Princípio 3 |
| Toda citação permanece atribuível a exatamente um Advisor de origem, usando a citação real já produzida | Vision, Princípio 4 |
| Conflitos entre Advisors são sempre expostos explicitamente, nunca resolvidos, nunca ranqueados | Vision, Princípio 5 |
| Síntese executiva permanece informativa, nunca uma decisão automática | Vision, Princípio 6 |
| Nenhum componente compartilhado pode ser alterado destrutivamente | Vision, Princípio 7 |
| O Executive Orchestrator nunca se torna um nono Advisor | Vision, Princípio 8 |
| Nenhum ranking/score decide o que é mais importante para o executivo | Vision, Princípio 9 |
| Workflow Runtime permanece exclusivamente orientado a evento | Vision, Princípio 10 |
| Executive Intelligence nunca produz conhecimento novo; declara base insuficiente explicitamente; nunca consulta fonte primária diretamente | Vision, Princípio 11 |
| **Deterministic Orchestration** — seleção nunca é responsabilidade do LLM; regras explícitas, reproduzíveis, auditáveis | Vision, Princípio 12 (D-137) |
| **Advisor Identity** — identidade institucional já declarada de cada um dos 8 Advisors, nunca um novo dado inventado | Domain Blueprint §2.1 (D-138) |
| **Selection Rule** — correspondência determinística entre sinais estruturados e Advisor Identities | Domain Blueprint §2.2 (D-138) |
| Base insuficiente — dois gatilhos exaustivos: seleção vazia, ou coleta vazia | Domain Blueprint §4 (D-138) |
| Ciclo de vida do Orchestrator: request-scoped | Domain Blueprint §5 (D-138) |
| Seis produtos permanentes (Executive Briefing, Executive Narrative, Cross Advisor Correlation, Conflict Analysis, Recommendation Package, Decision Support), cada um gerado por uma Capability homônima composta de até 4 Operações Estruturais (Seleção/Execução/Correlação/Síntese) | AR-17 §1/§2 (D-139) |
| Participação de Advisor Identities por Capability é sempre ilustrativa, nunca prescritiva — a `Selection Rule` é a única fonte de verdade | AR-17 §3 (D-139) |
| Composition Trace obrigatório em toda saída | AR-17 §4/Camada 3 (D-139) |
| Uma única `Selection Rule` compartilhada por todas as 6 Capabilities | AR-17 §5 (D-139) |
| Quatro tripwires contra virar nono Advisor: nunca fonte primária direta, nunca `AdvisorContract`, nunca interpretação de domínio, nunca invenção de afirmação | AR-17 §6 (D-139) |
| Orchestrator agnóstico ao domínio — conhece exclusivamente o catálogo fechado de Advisor Identities e sinais estruturados da pergunta | AR-17 §7 (D-139) |
| **Executive Intelligence Result / Orchestration Result** — produto lógico de qualquer Capability, contendo sempre Capability/Selection Rule/Advisor Identities/Explanations/Composition Trace/síntese (quando aplicável); dois estados exaustivos — coleção completa ou base insuficiente | Vision "Conceito Permanente" + AR-17 Camada 4 (D-140) |

Este documento resolve, em nível de Technical Design, exatamente as questões que o Domain Blueprint (§8) e a AR-17 nomearam explicitamente como remanescentes: mecanismo de extração de sinais e taxonomia (§8.1/§8.2 do Domain Blueprint); forma conceitual de representação do Orchestration Result e da base insuficiente (§8.3); se a correlação/síntese é responsabilidade do próprio Orchestrator (§8.4); controle de custo/latência (§8.5); estratégia de paralelismo vs. sequencialidade (§8.6).

---

## 1. Contrato Interno do Executive Orchestrator

Caracterizado inteiramente em nível conceitual — nenhuma API HTTP, nenhum schema de banco é decidido aqui.

### 1.1 Entrada

| Campo conceitual | Natureza | Observação |
|---|---|---|
| Capability solicitada | uma das seis já permanentes (AR-17 §1) | decide qual composição de Operações Estruturais (§3 abaixo) será executada; nunca inferida implicitamente — sempre declarada explicitamente por quem chama o Orchestrator |
| Pergunta ou escopo | texto livre (mesma forma já usada por todo Advisor, `question: str`) e/ou um escopo organizacional explícito (ex.: um Portfolio, quando a Capability for de amplitude ampla como Executive Briefing) | a forma exata de "escopo" para Capabilities de amplitude ampla é uma decisão de implementação futura sobre a mesma base conceitual aqui fixada — nunca uma segunda via de acesso a dado de domínio |
| Contexto de sessão/organização | reaproveita integralmente o `SessionContext` já existente na Foundation (`organization_id`, `user_id`, `session_id`, `project_name` opcional) | nenhum tipo novo é exigido por este contrato; reaproveitar `SessionContext` diretamente ou definir um tipo estruturalmente equivalente é decisão de implementação, nunca uma nova identidade paralela |

### 1.2 Estado interno (durante uma execução)

Estritamente **efêmero e cumulativo** — nunca persistido, nunca compartilhado entre execuções (§8). Durante uma única execução, o Orchestrator acumula, na ordem em que cada Operação Estrutural (§3) completa:

1. O conjunto de `Advisor Identity`s selecionadas (saída da Seleção).
2. A coleção de `Explanation`s obtidas, cada uma com sua proveniência preservada (saída da Execução).
3. Os achados de Correlação, quando a Capability os exigir (saída da Correlação).
4. A síntese produzida, quando a Capability a exigir (saída da Síntese).
5. O Composition Trace sendo construído incrementalmente (§5) — nunca reconstruído retroativamente ao final.

### 1.3 Transições

```
Recebida
   │  (Capability + pergunta/escopo + sessão validados estruturalmente)
   ▼
Selecionando  ──[seleção vazia]──▶  Base Insuficiente (terminal)
   │  [seleção não vazia]
   ▼
Executando  (uma chamada AdvisorFramework.run() por Advisor Identity selecionada)
   │
   ▼
Coletada  ──[todos retornaram sem evidência própria]──▶  Base Insuficiente (terminal)
   │  [ao menos um Advisor retornou evidência real]
   ▼
Correlacionando   (apenas se a Capability incluir Correlação — AR-17 §2)
   │
   ▼
Sintetizando      (apenas se a Capability incluir Síntese — AR-17 §2)
   │
   ▼
Completa (terminal)
```

Este diagrama é uma representação conceitual de fluxo — não uma máquina de estados de código, nenhuma classe ou enum é decidida aqui.

### 1.4 Saídas

Sempre e exatamente **um Executive Intelligence Result** (Vision "Conceito Permanente"; AR-17 Camada 4) — nunca uma lista, nunca um resultado parcial silencioso, nunca uma exceção como via normal de "não encontrei nada" (o estado de base insuficiente é sempre um resultado legítimo, nunca um erro).

### 1.5 Estado terminal

Exatamente dois, mutuamente exclusivos, já decididos em nível de domínio (Domain Blueprint §2.3/§4) e reafirmados aqui sem alteração: **Completa** (Executive Intelligence Result com todos os campos aplicáveis à Capability preenchidos) ou **Base Insuficiente** (Executive Intelligence Result no estado terminal do Princípio 11, com Composition Trace preservado até o ponto em que a insuficiência foi declarada — mesmo uma seleção vazia produz um Composition Trace mínimo, nunca ausente).

---

## 2. Selection Rules

### 2.1 Representação

A `Selection Rule` (Domain Blueprint §2.2) é representada como uma **tabela de correspondência estática e versionada** entre sinais estruturados e `Advisor Identity`s — nunca uma função de julgamento livre, nunca um modelo de linguagem. Dois tipos de sinal são reconhecidos, em ordem de precedência determinística:

1. **Sinais explícitos** — categorias nomeadas fornecidas junto com a pergunta/escopo (ex.: "estratégia", "risco", "execução", "governança", "portfólio", "pmo", "documento") por quem quer que invoque o Orchestrator (a superfície concreta que produz esses sinais — `web/` ou qualquer outra — está fora do escopo arquitetural desta Wave, per Kickoff §5). Um sinal explícito é, por construção, determinístico: a mesma categoria produz sempre a mesma correspondência.
2. **Sinais implícitos** — usados apenas na ausência de sinais explícitos suficientes: correspondência lexical determinística (nunca semântica, nunca embedding, nunca LLM) entre termos da pergunta e um vocabulário fixo e versionado associado a cada `Advisor Identity`, derivado do problema que cada Advisor já declara resolver (Domain Blueprint §2.1) — ex.: o vocabulário do Strategy Advisor inclui termos como "alinhamento"/"estratégia"/"objetivo declarado"; o do Risk Advisor inclui "risco"/"mitigação"/"ameaça". Esse vocabulário é metadado do catálogo fechado de Advisor Identities (AR-17 §7) — nunca inferido em tempo de execução a partir de conteúdo de domínio.

### 2.2 Avaliação

A `Selection Rule` é avaliada como uma função pura de **(sinais extraídos da entrada, versão vigente da tabela de correspondência)** para **um subconjunto do catálogo fechado de 8 `Advisor Identity`s** — nunca depende de nenhum dado de domínio, nenhuma evidência já coletada, nenhum resultado de execução anterior (Domain Blueprint §3.2: avaliar contra evidência já produzida seria circular). A avaliação é a mesma para as seis Capabilities (AR-17 §5) — nenhuma Capability implementa uma variação própria.

### 2.3 Garantias

| Propriedade exigida (Princípio 12) | Como esta representação garante |
|---|---|
| **Determinismo** | Tabela estática — a mesma entrada (mesmos sinais, mesma versão da tabela) produz sempre a mesma seleção; nenhuma dependência de resposta de LLM ou de qualquer estado externo variável |
| **Auditabilidade** | Cada entrada de seleção no Composition Trace (§5) registra exatamente quais sinais casaram com quais entradas do vocabulário de qual `Advisor Identity` — nunca apenas o resultado final sem o raciocínio |
| **Reprodutibilidade** | A tabela de correspondência é versionada como qualquer decisão arquitetural permanente desta plataforma — alterá-la é um evento de governança explícito (mesma disciplina do Decision Log: "não editado retroativamente, uma correção é uma nova entrada"), nunca um ajuste silencioso de comportamento em produção |
| **Nunca decisão do LLM** | O LLM não participa em nenhum ponto da extração de sinais ou da correspondência sinal→Advisor Identity — sua única participação em toda a orquestração é na Síntese (§7), nunca antes |

**Risco residual, explicitamente nomeado, não resolvido nesta etapa** (herdado do Domain Blueprint §3, "granularidade exata da taxonomia de sinais"): o vocabulário fixo por Advisor Identity proposto em §2.1.2 pode se revelar insuficientemente expressivo ou excessivamente amplo na prática real — isso é esperado ser observado e ajustado por etapas de implementação futuras (§11), sempre por decisão explícita de governança sobre a tabela, nunca por um ajuste heurístico silencioso em código.

---

## 3. Ciclo Completo da Orquestração

Cada etapa do fluxo mandatado, documentada com o que já existe, o que é novo, e o que permanece preservado:

| Etapa | Entrada | O que acontece | Saída | Preservação |
|---|---|---|---|---|
| **Pergunta** | pergunta/escopo + Capability + sessão (§1.1) | validação estrutural apenas — nenhuma interpretação de domínio | pergunta/escopo normalizados | nenhum componente existente tocado |
| **Selection Rule** | pergunta/escopo normalizados | avaliação da tabela de correspondência (§2) contra o catálogo fechado de 8 `Advisor Identity`s | subconjunto de `Advisor Identity`s (possivelmente vazio) | `AdvisorFramework`/Advisors não invocados ainda nesta etapa |
| **Advisor Identities** | subconjunto selecionado | se vazio: Base Insuficiente declarada imediatamente, nenhum Advisor invocado (Domain Blueprint §4) | conjunto de Advisors a executar, ou estado terminal | — |
| **`AdvisorFramework.run()`** | uma `Advisor Identity` selecionada por chamada | uma chamada íntegra e independente, exatamente a mesma assinatura já usada por toda rota `ask_*_advisor` hoje (`framework.run(agent, session, question, evidence, rag_context=..., no_evidence_answer=...)`), incluindo a montagem de evidência (`gather_context`/`gather_rag_context`) que hoje já precede cada chamada em cada rota | uma `Explanation` por Advisor invocado | `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine` inteiramente inalterados — mesmo padrão de instanciação por requisição já usado em toda rota `ask_*_advisor` |
| **Explanations** | N `Explanation`s coletadas (uma por Advisor invocado) | se todas vieram do portão de ausência de evidência (equivalente ao `no_evidence()` de cada Advisor): Base Insuficiente declarada (Domain Blueprint §4). Caso contrário, cobertura parcial é permitida — mesma disciplina já usada por todo Advisor Classe B | coleção de Explanations com proveniência preservada, ou estado terminal | citação original de cada Advisor preservada integralmente (Princípio 4) |
| **Correlation** | coleção de Explanations (quando a Capability inclui Correlação — AR-17 §2) | agrupamento por escopo organizacional comum de invocação + pareamento estrutural do catálogo de Advisor Identities (§6 abaixo) — nunca interpretação de conteúdo | achados de correlação (sobreposição de unidade, pares estruturalmente divergentes) | nenhuma consulta a `DomainService`/evidência bruta |
| **Synthesis** | achados de correlação + Explanations (quando a Capability inclui Síntese — AR-17 §2) | um mecanismo de composição informativa (§7 abaixo) | prosa ou pacote estruturado, sempre rastreável a Explanations reais | `RecommendationEngine`/`ExplanationEngine` não reaproveitados diretamente — a Síntese é uma etapa nova e aditiva, nunca uma substituição |
| **Composition Trace** | todo o histórico da execução até este ponto | registro incremental construído a cada etapa concluída (§5), nunca reconstruído retroativamente | Composition Trace completo | — |
| **Executive Intelligence Result** | Capability + Selection Rule aplicada + Advisor Identities + Explanations + Composition Trace + síntese (se houver) | composição final, um dos dois estados exaustivos | o produto entregue por esta execução (§4) | — |

---

## 4. Executive Intelligence Result

### 4.1 O que contém

Exatamente os seis elementos já permanentes (Vision "Conceito Permanente"; AR-17 Camada 4) — este Technical Design não adiciona nem remove nenhum: Capability executada; Selection Rule aplicada; conjunto de Advisor Identities participantes; Explanations consumidas com proveniência preservada; Composition Trace; síntese produzida (quando a Capability incluir Síntese).

### 4.2 Como nasce

No início de cada execução do Orchestrator (etapa "Recebida", §1.3), como uma estrutura conceitualmente vazia associada apenas à Capability solicitada — nenhum dos seis campos preenchido ainda.

### 4.3 Como evolui

Populado incrementalmente, um campo por vez, exatamente na ordem das transições de estado (§1.3): a Selection Rule aplicada e o conjunto de Advisor Identities assim que a Seleção completa; as Explanations assim que a Execução completa; os achados de Correlação, se aplicável, assim que a Correlação completa; a síntese, se aplicável, assim que a Síntese completa. O Composition Trace acompanha cada uma dessas evoluções em paralelo (§5) — nunca definido depois, como uma auditoria a posteriori.

### 4.4 Quando é considerado completo

Exatamente quando a última Operação Estrutural que a Capability exige (Correlação, para Cross Advisor Correlation/Conflict Analysis; Síntese, para as demais quatro — AR-17 §2) produziu seu resultado **e** o Composition Trace contabiliza integralmente todas as etapas efetivamente executadas — ou quando a Base Insuficiente é declarada (também um estado completo, apenas no outro dos dois estados exaustivos). Nunca "completo" enquanto qualquer etapa obrigatória da Capability ainda está pendente.

### 4.5 O que permanece explicitamente fora de escopo

Reafirmado sem alteração (D-140): nunca um contrato HTTP, nunca uma entidade persistente, nunca um tipo de domínio, nunca um novo Advisor, nunca uma nova fonte de evidência. Qualquer forma concreta de serialização, nome de classe, tabela ou rota permanece matéria de uma etapa de implementação futura, nunca decidida por este Technical Design.

---

## 5. Composition Trace

### 5.1 O que registra

Exatamente os quatro elementos já permanentes (AR-17 §4/Camada 3): qual Selection Rule foi aplicada e por quê (quais sinais casaram com qual entrada de vocabulário de qual Advisor Identity); quais Advisors foram efetivamente invocados, cada um com sua Explanation completa e citação real; qual Correlação foi identificada, quando aplicável, e por qual critério; qual Síntese foi produzida, quando aplicável, e a partir de quais Explanations especificamente.

### 5.2 Quando registra

**Incrementalmente, ao término de cada Operação Estrutural** (§3) — nunca reconstruído retroativamente a partir do resultado final. Uma execução interrompida por Base Insuficiente (seleção vazia ou coleta vazia) ainda produz um Composition Trace real, apenas mais curto — nunca um trace ausente ou um trace fabricado após o fato para justificar o resultado.

### 5.3 Como permanece rastreável

Cada entrada do Composition Trace referencia a identidade real dos objetos envolvidos — nunca uma cópia resumida ou parafraseada. Uma entrada de Seleção referencia os sinais e a Advisor Identity real; uma entrada de Execução referencia a Advisor Identity invocada e a Explanation real resultante (com sua citação original intacta); uma entrada de Correlação referencia o par ou grupo de Advisor Identities relacionadas e o critério estrutural que motivou a relação; uma entrada de Síntese referencia exatamente quais Explanations (por Advisor Identity) sustentam cada trecho da composição final — nunca uma afirmação sem origem rastreável (Princípio 11).

### 5.4 Como relaciona Selection Rule, Advisor Identity, Explanation e Executive Intelligence Result

```
Selection Rule (aplicada uma vez por execução)
   │  produz
   ▼
Advisor Identity(s) selecionada(s)  ──┐
   │  cada uma invocada via            │  cada elo preservado
   │  AdvisorFramework.run()           │  explicitamente no
   ▼                                   │  Composition Trace
Explanation(s), uma por Advisor  ──────┘
   │  (mais achados de Correlação/Síntese, quando aplicável)
   ▼
Executive Intelligence Result
   (Capability + Selection Rule + Advisor Identities + Explanations
    + Composition Trace + síntese, quando aplicável)
```

---

## 6. Correlação

### 6.1 Mecanismo

A Correlação opera exclusivamente sobre **dois sinais estruturais**, nunca sobre o conteúdo semântico de nenhuma Explanation:

1. **Escopo organizacional comum de invocação** — quando duas ou mais Advisor Identities selecionadas foram invocadas com o mesmo identificador de unidade organizacional (o mesmo `project_name`/escopo já passado como parte da entrada de cada chamada a `AdvisorFramework.run()`, exatamente o mesmo campo que `SessionContext.project_name` já carrega hoje para cada Advisor individualmente) — isso é, por construção, já conhecido antes de qualquer evidência ser interpretada, nunca inferido a partir do conteúdo das Explanations.
2. **Relação estrutural pré-declarada entre Advisor Identities** — um metadado estático do catálogo fechado (AR-17 §3, "participação tipicamente esperada" generalizada em pares/grupos estruturalmente relevantes, ex.: Delivery+Risk sobre o mesmo Project, Strategy+Risk como perspectivas estruturalmente contrastantes sobre a mesma unidade) — parte do mesmo catálogo fechado e versionado que já governa a Selection Rule (§2), nunca inferido em tempo de execução a partir de texto.

### 6.2 Sem decidir domínio, sem ranking, sem inferência

A Correlação **nunca julga se duas Explanations realmente divergem em conteúdo** — isso seria interpretação de domínio, vedada pelo Princípio 3 e pelo tripwire correspondente (AR-17 §6). O que a Correlação produz, quando dois Advisors compartilham escopo e possuem uma relação estrutural pré-declarada, é a apresentação de ambas as Explanations **lado a lado, verbatim, com suas citações originais intactas** — a rotulagem de "potencial divergência" vem inteiramente do metadado estático do par (§6.1.2), nunca de uma leitura do texto. Nenhum score de similaridade, nenhuma comparação lexical, nenhum julgamento de "quem está certo" é produzido — o julgamento permanece exclusivamente humano (Vision §6, Princípio 5).

Isso resolve, de forma consistente e sem introduzir mecanismo novo, tanto **Cross Advisor Correlation** (a Capability que termina exatamente aqui, apresentando a sobreposição de escopo como achado estrutural) quanto **Conflict Analysis** (a Capability que também termina na Correlação — AR-17 §2 — apresentando os pares estruturalmente contrastantes lado a lado, sem síntese adicional).

---

## 7. Síntese

### 7.1 Mecanismo, e apenas o mecanismo

A Síntese é uma chamada ao LLM que recebe **exclusivamente** as Explanations já coletadas (nunca a evidência bruta subjacente a elas) mais o contexto já registrado no Composition Trace (quais Advisor Identities contribuíram e com qual escopo/correlação) — nunca qualquer outro dado. Arquiteturalmente, propõe-se que esta chamada reaproveite o mesmo padrão institucional já usado por todo Advisor individual — composição de prompt via um preâmbulo institucional compartilhado (o mesmo espírito de `render_analyst_prompt()`) e registro de observabilidade auditável (o mesmo espírito de `ObservabilityRecorder.record_call()`) — nunca um mecanismo de chamada a LLM paralelo, não auditado, ou fora do padrão já validado em oito ciclos institucionais da Wave 5. A forma exata de reaproveitamento (extensão aditiva vs. novo componente que segue o mesmo padrão) é decisão de implementação futura, nunca decidida por este Technical Design.

### 7.2 O que a Síntese nunca pode fazer

- **Nunca introduzir evidência nova**: a chamada ao LLM não tem acesso a `AIContextEngine`, `DomainService`, `KnowledgeRepository` ou qualquer fonte primária — apenas às Explanations já coletadas (Princípio 1/3/11).
- **Nunca produzir nova interpretação de domínio**: o papel da Síntese é relacionar e organizar o que os Advisors já afirmaram, nunca julgar se um `health_status` é preocupante ou se um risco é grave — esse julgamento já foi feito, com exclusividade, pelo Advisor que o produziu (Princípio 3).
- **Nunca produzir decisão automática**: a saída permanece informativa (ADR-V2-007, Princípio 6) — nunca a recomendação de uma única ação correta, nunca um ranking (Princípio 9).

---

## 8. Estado Request-Scoped

Reafirmação e demonstração, em nível de contrato, da decisão já oficial do Domain Blueprint (§5):

- **Ausência de memória**: cada execução do Orchestrator constrói seu Executive Intelligence Result inteiramente a partir de zero (§4.2) — nenhuma informação de uma pergunta anterior, mesmo da mesma sessão/usuário, é reaproveitada ou influencia a Seleção, Execução, Correlação ou Síntese seguintes.
- **Ausência de cache obrigatório**: nenhuma etapa do ciclo (§3) depende estruturalmente de um resultado previamente calculado para completar. A mesma pergunta, repetida, sempre re-executa integralmente Seleção → Execução → (Correlação) → (Síntese) — um cache, se algum dia introduzido, seria uma camada de otimização estritamente aditiva sobre este contrato, nunca um requisito dele.
- **Ausência de estado compartilhado**: nenhuma estrutura em memória ou persistida é lida ou escrita entre duas execuções concorrentes do Orchestrator, mesmo para a mesma organização — exatamente a mesma garantia que `AdvisorFramework` já oferece hoje ao ser instanciado a cada requisição, em cada rota `ask_*_advisor` (AR-16 §4/§5).

Isso permanece distinto, e nunca confundido, com `EnterpriseMemoryService` (deliberadamente persistente, hoje sem consumidor) — se o Orchestrator vier a consultar memória organizacional persistida no futuro, isso acontece exclusivamente através de um Advisor via `AdvisorFramework.run()`, nunca por acesso direto (Princípio 11, Domain Blueprint §5, reafirmados sem alteração).

---

## 9. Preservações Obrigatórias

Confirmação explícita, componente a componente, de que nenhum é alterado por este Technical Design:

| Componente | Confirmação |
|---|---|
| **`AdvisorFramework`** | Invocado exclusivamente via `run()`, exatamente uma vez por Advisor Identity selecionada, com a mesma assinatura já em produção hoje (`run(advisor, session, question, evidence, rag_context=None, no_evidence_answer=None)`) — nenhum parâmetro novo, nenhuma variante, nenhuma alteração interna |
| **`AIContextEngine`** | Nunca chamado diretamente pelo Orchestrator — alcançado exclusivamente de forma indireta, dentro do caminho de execução de um Advisor real, exatamente como acontece hoje em cada rota `ask_*_advisor` |
| **`RecommendationEngine`** | Continua a servir exclusivamente cada `AdvisorFramework.run()` individual — o Orchestrator nunca o invoca diretamente, nunca constrói sua própria `Recommendation` fora desse caminho |
| **`ExplanationEngine`** | Continua a envolver exclusivamente a `Recommendation` de cada Advisor individual — a Síntese (§7) é uma etapa nova e aditiva que opera sobre Explanations já produzidas por `ExplanationEngine`, nunca uma substituição ou uma segunda implementação dele |
| **Workflow Runtime** | Nenhuma relação no caminho síncrono de resposta a uma pergunta (AR-16 §6, reafirmado sem alteração) — `WorkflowRuntime.run()` permanece exclusivamente disparado por `triggering_event: DomainEvent`, nunca por uma pergunta de usuário |
| **Enterprise Advisors (os 8)** | Nenhum muda — mesmo `AdvisorContract`, mesmas rotas `ask_*_advisor`, mesmo comportamento quando consultados isoladamente hoje. Nenhum precisa ser alterado para se tornar "orquestrável" (AR-16 §7) |
| **Knowledge Platform** | Nunca consultada diretamente pelo Orchestrator — alcançada exclusivamente através do caminho RAG já existente de um Advisor individual (Risk/Document/Governance), nunca um segundo caminho |
| **Enterprise Domain** | Nunca consultado diretamente pelo Orchestrator (Princípio 11) — alcançado exclusivamente através de `DomainService`, dentro do caminho de execução de um Advisor real, exatamente como hoje |

---

## 10. Riscos Arquiteturais

Apenas riscos grounded — nenhuma hipótese nova além do que já foi nomeado no Kickoff (§10), na AR-16 (§8) e no Domain Blueprint (§9), refinados nesta etapa:

| Risco | Fundamentação | Mitigação conceitual |
|---|---|---|
| A relação estrutural pré-declarada entre Advisor Identities (§6.1.2) degradar, na prática, para uma inferência disfarçada de conteúdo | Se o metadado de pares "estruturalmente relevantes" não for mantido estritamente como parte do catálogo fechado e versionado (§2.1.2), uma implementação futura poderia, por conveniência, começar a inspecionar o texto das Explanations para decidir correlação — violação direta do Princípio 3 | Qualquer alteração ao catálogo de pares estruturais exige o mesmo rigor de governança já usado para toda decisão permanente desta Wave (Decision Log), nunca um ajuste heurístico silencioso em código de Correlação |
| Custo/latência não controlado — N chamadas independentes a `AdvisorFramework.run()`, cada uma já contendo sua própria chamada ao LLM, mais potencialmente uma chamada adicional de Síntese | Já nomeado no Kickoff §10 e na AR-16 §8; nenhum Advisor da Wave 5 precisou considerar esse cenário isoladamente | Nenhuma mitigação de código decidida nesta etapa — nomeada explicitamente como requisito da Etapa 5 do roadmap incremental (§11) antes de qualquer exposição a um consumidor de produção real |
| Paralelismo não controlado nas N chamadas a `AdvisorFramework.run()` esgotar limites de conexão/taxa do `LLMProvider` | Nenhum Advisor da Wave 5 executa mais de uma chamada ao LLM concorrente por requisição hoje — esse é um cenário estruturalmente novo | Decisão técnica desta etapa (§3, §11): execução sequencial na primeira implementação (Etapa 2), paralelismo real, se vier a ser introduzido, exige um limite explícito de concorrência documentado e testado, nunca implícito |
| Vocabulário fixo da Selection Rule (§2.1.2) tornar-se insuficiente ou desatualizado conforme a organização e o uso real evoluem | Nomeado como risco residual explícito no Domain Blueprint §3 e reafirmado em §2.3 deste documento | Qualquer ajuste ao vocabulário é um evento de governança explícito, nunca um ajuste silencioso — mesma disciplina do Decision Log |

Nenhum risco listado é bloqueante para o início da Etapa 1 do roadmap incremental (§11) — todos são endereçáveis nas etapas subsequentes, cada uma com seus próprios critérios de sucesso.

---

## 11. Estratégia Incremental de Implementação

Cinco etapas, cada uma com dependência estrita da anterior — nenhum código é escrito nesta etapa, apenas a sequência e os critérios de cada etapa futura.

### Etapa 1 — Selection Rule + catálogo de Advisor Identity

- **Objetivo:** estabelecer o catálogo fechado das 8 `Advisor Identity`s e a `Selection Rule` determinística (sinais explícitos + vocabulário fixo, §2), comprovando determinismo antes de qualquer execução real de Advisor.
- **Componentes:** um módulo novo, estruturalmente fora de `AdvisorFramework` — nenhuma alteração a nenhum componente existente.
- **Dependências:** nenhuma além dos 8 Advisors já existentes (Wave 5, concluída).
- **Critérios de sucesso:** testes automatizados demonstrando determinismo (mesma entrada → mesma seleção, múltiplas execuções); seleção vazia tratada corretamente como Base Insuficiente; nenhuma dependência de LLM confirmada por revisão de código.

### Etapa 2 — Execução multi-Advisor e coleção com proveniência

- **Objetivo:** dado um conjunto selecionado de `Advisor Identity`s (Etapa 1), invocar `AdvisorFramework.run()` uma vez por Advisor, sequencialmente (§10), e compor a coleção de Explanations com proveniência preservada — sem Correlação, sem Síntese ainda.
- **Componentes:** o próprio Executive Orchestrator, como componente novo, estruturalmente acima de `AdvisorFramework` — nunca dentro dele.
- **Dependências:** Etapa 1.
- **Critérios de sucesso:** dois ou mais Advisors reais invocados para a mesma pergunta, cada Explanation rastreável ao seu Advisor de origem; coleta vazia tratada corretamente como Base Insuficiente; `git diff --stat` confirmando zero alteração a `AdvisorFramework`/Advisors existentes.

### Etapa 3 — Correlação estrutural (Cross Advisor Correlation, Conflict Analysis)

- **Objetivo:** implementar a Correlação por escopo organizacional compartilhado e por pares estruturalmente pré-declarados (§6), completando as duas Capabilities que terminam na Correlação sem exigir Síntese.
- **Componentes:** módulo de Correlação, consumindo a coleção da Etapa 2; extensão do Composition Trace para registrar achados de Correlação.
- **Dependências:** Etapa 2.
- **Critérios de sucesso:** dado dois Advisors reais invocados sobre o mesmo escopo organizacional, a Correlação identifica corretamente a sobreposição e, quando o par é estruturalmente pré-declarado, apresenta as duas Explanations lado a lado sem as julgar; nenhuma interpretação de conteúdo de domínio encontrada em revisão de código.

### Etapa 4 — Síntese (Executive Briefing, Executive Narrative, Recommendation Package, Decision Support)

- **Objetivo:** implementar a Síntese informativa (§7), reaproveitando o padrão institucional de composição de prompt e observabilidade já validado pela Wave 5, completando as quatro Capabilities restantes.
- **Componentes:** módulo de Síntese, consumindo a Correlação da Etapa 3 (quando aplicável) e a coleção da Etapa 2; Composition Trace estendido para registrar a Síntese.
- **Dependências:** Etapa 3.
- **Critérios de sucesso:** pelo menos uma Capability completa, testada, produzindo um Executive Intelligence Result citando evidência real de dois ou mais Advisors distintos — o próprio Critério de Encerramento nomeado no Kickoff §11.3.

### Etapa 5 — Endurecimento, observabilidade e revisão de custo/latência

- **Objetivo:** endereçar os riscos residuais (§10) antes de qualquer exposição a um consumidor de produção real — controle explícito de concorrência (caso paralelismo venha a ser introduzido), medição de custo por Capability, revisão do vocabulário da Selection Rule à luz de uso real.
- **Componentes:** nenhum componente novo — instrumentação e configuração sobre os já construídos nas Etapas 1-4.
- **Dependências:** Etapas 1-4.
- **Critérios de sucesso:** limite de concorrência explícito documentado e testado (se aplicável); custo médio por Capability medido e registrado; suíte completa dos 8 Advisors individuais sem regressão.

---

## 12. Critérios de Encerramento

O Executive Orchestrator poderá ser considerado tecnicamente concluído quando, objetivamente:

1. As cinco etapas do roadmap incremental (§11) estiverem concluídas, cada uma com testes automatizados aprovados.
2. Pelo menos uma das seis Capabilities (AR-17 §2) estiver funcional em produção, citando evidência real de dois ou mais Advisors distintos na mesma resposta (mesmo critério já nomeado no Kickoff §11.3).
3. `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, Workflow Runtime, Knowledge Platform, Enterprise Domain e os 8 Advisors da Wave 5 permanecerem preservados sem alteração destrutiva, confirmado por `git diff --stat` a cada etapa — mesma disciplina já usada em toda a Wave 5.
4. `ruff check src tests`, `tsc` e `eslint` permanecerem limpos a cada etapa.
5. O determinismo da `Selection Rule` estiver comprovado por teste automatizado (mesma entrada → mesma seleção, múltiplas execuções).
6. Todo Executive Intelligence Result produzido em teste ou produção for rastreável, via Composition Trace, a pelo menos uma Explanation real e citável — nunca uma afirmação sem origem.
7. Nenhuma pendência técnica ou arquitetural permanecer aberta, com o mesmo padrão de rigor já aplicado ao `WAVE-5-COMPLETION-REVIEW.md`.
8. O Founder aprovar explicitamente o encerramento técnico do Executive Orchestrator.

---

## Recomendação

**GO para a implementação do Executive Orchestrator**, iniciando pela Etapa 1 do roadmap incremental (§11), sujeita a nova autorização explícita do Founder antes de qualquer código ser escrito.

Este Technical Design fechou o contrato completo do Executive Orchestrator inteiramente em nível conceitual — entrada, estado interno, transições, saída e estado terminal (§1); representação e avaliação determinística da Selection Rule, com vocabulário fixo e versionado, nunca LLM (§2); o ciclo completo de orquestração documentado etapa a etapa, com o que é novo e o que é preservado explicitado em cada uma (§3); o Executive Intelligence Result caracterizado em seu nascimento, evolução e critério de completude (§4); o Composition Trace definido em o quê, quando e como relaciona seus quatro elementos (§5); a Correlação resolvida como operação estritamente estrutural — escopo compartilhado e pares pré-declarados do catálogo fechado, nunca leitura de conteúdo (§6); a Síntese limitada ao seu mecanismo, reaproveitando o padrão institucional já validado, nunca introduzindo evidência, interpretação ou decisão automática (§7); o estado request-scoped demonstrado em ausência de memória, cache obrigatório e estado compartilhado (§8); as oito preservações obrigatórias confirmadas componente a componente (§9); os riscos arquiteturais grounded, nenhum bloqueante (§10); uma estratégia incremental de cinco etapas, cada uma com objetivo, componentes, dependências e critérios de sucesso próprios (§11); e critérios de encerramento objetivos (§12).

Nenhuma inconsistência arquitetural foi encontrada entre este Technical Design e nenhuma decisão já registrada no Kickoff, na Vision, na AR-16, no Domain Blueprint ou na AR-17. As questões que essas etapas nomearam explicitamente como remanescentes para o Technical Design — mecanismo de sinais, forma conceitual do Orchestration Result, responsabilidade da correlação/síntese, controle de custo/latência, estratégia de paralelismo — foram todas resolvidas nesta etapa, em nível conceitual, sem nenhuma linha de código. Nenhum trabalho posterior deverá ser iniciado automaticamente — aguarda nova autorização explícita do Founder antes de qualquer implementação.
