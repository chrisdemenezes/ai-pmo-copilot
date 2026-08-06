# AR-16 — Architecture Review do Executive Orchestrator

**Primeira Architecture Review da Wave 6 — Executive Intelligence.** Produzida sob autorização da "Founder Decision" que aprovou `WAVE-6-EXECUTIVE-INTELLIGENCE-VISION.md` sem ressalvas, registrou o décimo primeiro princípio permanente (D-135 — "Executive Intelligence nunca produz conhecimento novo") e autorizou **exclusivamente** esta revisão, com objeto arquitetural único e exclusivo: o **Executive Orchestrator**. Nenhum Domain Blueprint. Nenhum Technical Design. Nenhuma implementação. Nenhum código escrito nesta etapa.

**Precondição:** `WAVE-6-EXECUTIVE-INTELLIGENCE-KICKOFF.md` (D-133) e `WAVE-6-EXECUTIVE-INTELLIGENCE-VISION.md` (D-134/D-135) aprovados sem ressalvas — ambos grounded exclusivamente na arquitetura real, nunca no Blueprint conceitual pré-D-071.

---

## 0. O que já é oficial (não reaberto aqui)

| Decisão | Origem |
|---|---|
| Executive Intelligence nunca é uma nova fonte primária de evidência — consome exclusivamente `Explanation`s já produzidas por Advisors | Vision, Princípio 1 |
| `AdvisorFramework.run()` continua a executar exatamente um Advisor por chamada, sem exceção — cooperação acontece via múltiplas chamadas independentes, orquestradas acima do Framework | Vision, Princípio 2 |
| Interpretação de evidência de domínio permanece exclusiva do Advisor dono daquele domínio | Vision, Princípio 3 |
| Toda citação em uma resposta executiva permanece atribuível a exatamente um Advisor de origem, usando a citação real já produzida | Vision, Princípio 4 |
| Conflitos entre Advisors são sempre expostos explicitamente, nunca resolvidos, nunca ranqueados | Vision, Princípio 5 |
| Síntese executiva permanece informativa, nunca uma decisão automática | Vision, Princípio 6 |
| Nenhum componente compartilhado pode ser alterado destrutivamente para acomodar Executive Intelligence | Vision, Princípio 7 |
| O Executive Orchestrator nunca se torna um nono Advisor, nunca implementa `AdvisorContract` como se tivesse evidência primária própria | Vision, Princípio 8 |
| Nenhum ranking/score decide o que é mais importante para o executivo | Vision, Princípio 9 |
| Workflow Runtime permanece exclusivamente orientado a evento, nunca invocado por uma pergunta de usuário | Vision, Princípio 10 |
| **Executive Intelligence nunca produz conhecimento novo** — toda síntese integralmente derivada das respostas dos Advisors; declara explicitamente ausência de base suficiente quando nenhuma combinação sustenta uma conclusão; nunca consulta Domain/Knowledge Platform/Workflow Runtime/banco de dados diretamente | D-135, Vision Princípio 11 |

Esta revisão nunca reabre nenhum destes onze princípios — aprofunda exclusivamente o papel do Executive Orchestrator dentro dos limites que eles já impõem.

---

## 1. Responsabilidades

O Executive Orchestrator é o único componente da Wave 6 cuja responsabilidade é **coordenar** — nunca interpretar, nunca decidir, nunca persistir.

**É responsável por:**
- Receber a pergunta executiva do usuário.
- Determinar quais Advisors, dentre os oito existentes, são relevantes para respondê-la com integridade (mecanismo de seleção não decidido nesta etapa — matéria de Domain Blueprint).
- Invocar cada Advisor selecionado através do caminho já existente e inalterado — uma chamada independente a `AdvisorFramework.run()` por Advisor.
- Coletar as `Explanation`s resultantes, cada uma já completa, já auditada, já com seu próprio `rationale` (`ExplanationEngine.explain()`, inalterado).
- Reconhecer quando a coleta resultante é insuficiente para sustentar qualquer síntese, e declarar essa insuficiência explicitamente — nunca preencher a lacuna com inferência própria (Princípio 11, D-135).
- Entregar o conjunto coletado a uma etapa de correlação/síntese (se um componente distinto ou o próprio Orchestrator — não decidido aqui, matéria de Technical Design).

**Não é responsável por, em nenhuma circunstância:**
- Interpretar evidência de domínio diretamente — essa responsabilidade permanece exclusiva do Advisor que a produziu (Princípio 3).
- Resolver conflitos entre Advisors ou decidir qual está certo (Princípio 5).
- Consultar `Enterprise Domain`, Knowledge Platform, Workflow Runtime, banco de dados, ou qualquer outra fonte primária de evidência (Princípio 11).
- Produzir uma recomendação de ação ou decisão automática (Princípio 6; Princípio 1 da Product Constitution).
- Persistir qualquer novo dado — nenhuma responsabilidade de escrita foi identificada para este componente em nenhum documento desta Wave até aqui.

## 2. Fronteiras

O Executive Orchestrator é o ponto de entrada da camada Executive Intelligence no fluxo conceitual já definido (Kickoff §5/§6): recebe a pergunta, e é a única superfície entre o usuário e os Advisors.

**Fronteira estrutural superior:** nunca é invocado pelo Workflow Runtime como parte de um workflow orientado a evento (§6) — sua invocação, nesta etapa, é sempre síncrona, em resposta direta a uma pergunta.

**Fronteira estrutural inferior:** sua única via de acesso a qualquer fato sobre a organização é através de uma ou mais chamadas a `AdvisorFramework.run()`, cada uma retornando exatamente uma `Explanation` de exatamente um Advisor. Nunca há um caminho alternativo, mais curto ou mais direto, para qualquer dado — mesmo que tecnicamente disponível em `AIContextEngine`/`DomainService`/`KnowledgeRepository`.

**Fronteira lateral:** não compartilha estado com nenhum Advisor individual. Cada Advisor permanece, como hoje, inteiramente inconsciente da existência do Orchestrator ou de qualquer outro Advisor (confirmado em todos os oito `agent.py` — nenhum referencia outro Advisor).

## 3. Contrato

Nomeado aqui em nível conceitual — nenhuma assinatura de método, nome de classe ou shape de retorno é decidido nesta etapa; isso é trabalho do Domain Blueprint e do Technical Design subsequentes.

O contrato precisa garantir, no mínimo:

- **Entrada:** uma pergunta executiva (mesma forma já usada por todo Advisor — uma `question: str`) e, implicitamente ou explicitamente, o contexto de sessão/organização já usado por `SessionContext` em toda a plataforma.
- **Seleção:** um mecanismo — não decidido — para determinar quais Advisors participam desta pergunta.
- **Execução:** para cada Advisor selecionado, uma chamada íntegra e independente a `AdvisorFramework.run(advisor, session, question, evidence, ...)` — exatamente a mesma assinatura já usada por toda rota `ask_*_advisor` hoje, sem parâmetro novo, sem variante.
- **Saída:** um conjunto de `Explanation`s, cada uma preservando integralmente sua proveniência (qual Advisor a produziu) — nunca uma lista anônima e achatada (Princípio 4).
- **Estado terminal de insuficiência:** uma forma de expressar "nenhuma base suficiente para sintetizar" (Princípio 11) como resultado legítimo e esperado — o mesmo espírito institucional de `RecommendationEngine.no_evidence()`, aplicado um nível acima, sem que isso implique reutilizar `RecommendationEngine` diretamente (ele continua servindo exclusivamente cada Advisor individual, nunca o Orchestrator).

## 4. Ciclo de Vida

Nenhum Advisor, nenhuma parte do `AdvisorFramework`, mantém estado entre chamadas — `AdvisorFramework` é instanciado de novo a cada requisição HTTP, em cada rota (`framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)`, padrão idêntico nas oito rotas `ask_*_advisor`). Por consistência estrutural com esse padrão já universal na plataforma, o Executive Orchestrator, se seguir a mesma disciplina, seria igualmente **request-scoped** — construído para responder a uma pergunta, descartado ao final, sem memória entre perguntas.

Isso é distinto, e nunca deve ser confundido, com o `EnterpriseMemoryService` (Kickoff §2.2) — uma capacidade deliberadamente persistente, com seu próprio ciclo de vida orientado a dados, hoje sem consumidor. Se o Orchestrator vier a consultar memória organizacional persistida, isso seria sempre através de um Advisor (via `AdvisorFramework.run()`), nunca por acesso direto — reafirmando, mais uma vez, o Princípio 11.

Este é um ponto de continuidade observado, não uma decisão — a forma definitiva do ciclo de vida do Orchestrator é matéria de Technical Design.

## 5. Relação com `AdvisorFramework`

A relação é de **consumidor externo e repetido**, nunca de extensão interna. O Orchestrator chama `AdvisorFramework.run()` uma vez por Advisor selecionado — exatamente como qualquer rota `ask_*_advisor` já faz hoje para um único Advisor — nunca de forma diferente, nunca com um parâmetro que aceite mais de um `AdvisorContract` por chamada.

`AdvisorFramework` permanece inteiramente inconsciente da existência do Orchestrator: nenhuma nova responsabilidade, nenhum novo método, nenhuma alteração de assinatura em `gather_context()`/`gather_rag_context()`/`normalize_rag_evidence()`/`render_prompt()`/`call_llm()`/`run()`. Esta é a fronteira mais rigorosamente protegida de toda a Wave 6 — o próprio motivo de existir do princípio "uma chamada, um Advisor" (Vision §4) é que ele nunca dependeu, e nunca deverá depender, de o Framework saber que está sendo chamado múltiplas vezes para a mesma pergunta.

## 6. Relação com Workflow Runtime

**Nenhuma relação direta, no caminho síncrono de resposta a uma pergunta.** `WorkflowRuntime.run()` é estruturalmente disparado por um evento já publicado (`triggering_event: DomainEvent`), nunca por uma pergunta de usuário — confirmado pelo próprio docstring de `src/workflows/runtime.py`: *"Never substitutes `AdvisorFramework.run()`"*. O Orchestrator nunca invoca `WorkflowRuntime`, e `WorkflowRuntime` nunca invoca o Orchestrator para responder a uma pergunta síncrona.

A única relação hipotética e ainda não decidida (Kickoff §8.10, Epic W6-4 — Executive Briefing) seria **inversa**: um workflow futuro, disparado por um evento (ex.: um agendamento periódico), poderia ter como um de seus passos **invocar** o Orchestrator para produzir um briefing — nunca o contrário. Mesmo essa relação hipotética permanece fora do escopo desta revisão, que trata exclusivamente do caminho síncrono de pergunta-resposta.

## 7. Relação com Enterprise Advisors

O Orchestrator trata todo `AdvisorContract` já implementado — os oito Advisors da Wave 5 — de forma **uniforme e sem privilégio especial**, através da mesma superfície pública (`AdvisorFramework.run()`) que qualquer rota HTTP já usa hoje. Nenhum Advisor precisa mudar para se tornar "orquestrável" — a uniformidade do contrato já existente (`AdvisorContract.advise(session, question, evidence, rag_context)`) é, por si só, suficiente.

O Orchestrator nunca acessa a composição interna de evidência de nenhum Advisor (nenhum `EvidenceAssembler` é chamado diretamente) — ele só enxerga o resultado final, a `Explanation` que `AdvisorFramework.run()` já produz. Isso preserva integralmente o isolamento entre Advisors que toda a Wave 5 construiu: nenhum deles sabe que o outro existe, e essa ignorância mútua nunca precisa ser quebrada para que o Orchestrator funcione.

## 8. Riscos Arquiteturais

| Risco | Fundamentação | Mitigação conceitual (não implementação) |
|---|---|---|
| O Orchestrator adquirir, por conveniência de implementação, sua própria via de acesso a evidência (ex.: uma consulta direta a `AIContextEngine` "só para enriquecer o contexto") | Violaria diretamente os Princípios 1/3/8/11 — o risco mais grave nomeado nesta revisão | Nenhum Technical Design futuro pode introduzir um caminho de leitura de evidência que não passe por `AdvisorFramework.run()` de um Advisor real |
| O mecanismo de seleção de Advisors (Kickoff §8.2) tornar-se uma decisão implícita de código (ex.: um `if`/`else` hardcoded) em vez de uma decisão arquitetural explícita | Nenhuma decisão de seleção foi tomada até aqui — permanece aberta desde o Kickoff | O Domain Blueprint do Orchestrator precisa nomear e decidir esse mecanismo explicitamente, nunca deixá-lo emergir implicitamente durante a implementação |
| Estado (cache, memória de sessão) surgir no Orchestrator sem decisão explícita, contradizendo o padrão request-scoped observado em toda a plataforma (§4) | Nenhum Advisor ou componente do `AdvisorFramework` mantém estado hoje — introduzir estado seria uma primeira vez estrutural | Qualquer necessidade de estado deve ser nomeada e decidida explicitamente em Technical Design, nunca introduzida silenciosamente |
| Custo/latência não avaliado — N chamadas independentes a `AdvisorFramework.run()`, cada uma já contendo sua própria chamada ao LLM | Já nomeado no Kickoff §10; nenhum Advisor da Wave 5 precisou considerar esse cenário | Nenhuma mitigação de código decidida aqui — nomeado como questão a resolver antes de qualquer implementação real |
| Ambiguidade na declaração de "base insuficiente" (Princípio 11) — sem uma definição precisa de quando essa condição se aplica (zero Advisors selecionados? todos retornaram `no_evidence()`? um julgamento mais fino?), o comportamento pode variar de forma inconsistente entre implementações futuras | Nenhuma definição operacional foi decidida por este Founder Decision, apenas o princípio | O Domain Blueprint do Orchestrator precisa definir esse critério explicitamente, nunca deixá-lo implícito |

Nenhum risco listado é bloqueante para a produção do primeiro Domain Blueprint da Wave 6 — todos são endereçáveis nessa etapa subsequente.

---

## Recomendação

**GO para o primeiro Domain Blueprint da Wave 6, com objeto o Executive Orchestrator.**

Esta revisão respondeu, em nível institucional e arquitetural, exatamente as oito dimensões mandatadas: responsabilidades, fronteiras, contrato, ciclo de vida, relação com `AdvisorFramework`, relação com Workflow Runtime, relação com Enterprise Advisors, e riscos arquiteturais. Nenhuma decisão de implementação foi tomada — cada seção nomeia explicitamente o que permanece em aberto para o Domain Blueprint (mecanismo de seleção de Advisors, forma exata do contrato, definição operacional de "base insuficiente", modelo de estado/ciclo de vida definitivo). Nenhuma inconsistência arquitetural foi encontrada entre esta revisão e os onze princípios já registrados na Vision. Nenhum trabalho posterior deverá ser iniciado automaticamente — aguarda nova autorização explícita do Founder.
