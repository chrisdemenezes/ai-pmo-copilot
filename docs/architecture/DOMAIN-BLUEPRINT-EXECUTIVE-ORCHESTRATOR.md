# Domain Blueprint — Executive Orchestrator

Primeiro Domain Blueprint da Wave 6 — Executive Intelligence. Produzido sob autorização da "Founder Decision" que aprovou a AR-16 (`AR-16-EXECUTIVE-ORCHESTRATOR-ARCHITECTURE-REVIEW.md`) sem ressalvas, registrou o décimo segundo princípio permanente (D-137 — "Deterministic Orchestration") e autorizou a abertura deste Domain Blueprint com objeto exclusivamente o **Executive Orchestrator**. **Nenhum Technical Design. Nenhuma implementação.** Nenhum código escrito nesta etapa.

**Precondição:** `WAVE-6-EXECUTIVE-INTELLIGENCE-KICKOFF.md` (D-133), `WAVE-6-EXECUTIVE-INTELLIGENCE-VISION.md` (D-134/D-135/D-137, 12 princípios permanentes) e `AR-16-EXECUTIVE-ORCHESTRATOR-ARCHITECTURE-REVIEW.md` (D-136/D-137) aprovados sem ressalvas.

**Nota de sequenciamento:** ao contrário de todo Advisor da Wave 5 (Advisor Specification → Domain Blueprint → Architecture Review → Technical Design → Implementação), o Founder decidiu, para o Executive Orchestrator, produzir a Architecture Review (AR-16) **antes** deste Domain Blueprint. Este documento aprofunda, em nível de modelo de domínio, exatamente as questões que a AR-16 nomeou explicitamente como abertas — nunca reabre o que a AR-16 já decidiu.

---

## 0. O que já é oficial (não reaberto aqui)

| Decisão | Origem |
|---|---|
| Executive Intelligence nunca é uma nova fonte primária de evidência — consome exclusivamente `Explanation`s já produzidas por Advisors | Vision, Princípio 1 |
| `AdvisorFramework.run()` continua a executar exatamente um Advisor por chamada, sem exceção | Vision, Princípio 2 |
| Interpretação de evidência de domínio permanece exclusiva do Advisor dono daquele domínio | Vision, Princípio 3 |
| Toda citação permanece atribuível a exatamente um Advisor de origem, usando a citação real já produzida | Vision, Princípio 4 |
| Conflitos entre Advisors são sempre expostos explicitamente, nunca resolvidos, nunca ranqueados | Vision, Princípio 5 |
| Síntese executiva permanece informativa, nunca uma decisão automática | Vision, Princípio 6 |
| Nenhum componente compartilhado pode ser alterado destrutivamente | Vision, Princípio 7 |
| O Executive Orchestrator nunca se torna um nono Advisor | Vision, Princípio 8 |
| Nenhum ranking/score decide o que é mais importante para o executivo | Vision, Princípio 9 |
| Workflow Runtime permanece exclusivamente orientado a evento | Vision, Princípio 10 |
| Executive Intelligence nunca produz conhecimento novo; declara explicitamente ausência de base suficiente quando aplicável; nunca consulta fonte primária diretamente | Vision, Princípio 11 |
| **Deterministic Orchestration** — a seleção de Advisors nunca é responsabilidade do LLM; regras explícitas, reproduzíveis, auditáveis; determinística para a mesma entrada e configuração; LLM participa apenas da síntese | Vision, Princípio 12 (D-137) |
| Responsabilidades/fronteiras/contrato conceitual/ciclo de vida observado/relação com `AdvisorFramework`/relação com Workflow Runtime/relação com Enterprise Advisors do Orchestrator | AR-16 |

Este Domain Blueprint resolve, em nível de modelo de domínio (nunca de código), exatamente três questões que a AR-16 nomeou explicitamente como abertas: a forma conceitual da regra determinística de seleção (§3); a definição operacional precisa de "base insuficiente" (§4); e a confirmação do ciclo de vida (§5).

---

## 1. Executive Summary

O Executive Orchestrator não é um Advisor — não tem evidência primária própria, não implementa `AdvisorContract`, não interpreta domínio. Seu domínio de responsabilidade é inteiramente **relacional e regulatório**: decidir, de forma determinística, quais dos oito Advisors participam de uma pergunta, invocá-los através do caminho já existente, e reconhecer quando o resultado coletado não sustenta síntese alguma.

**Modelo de domínio central proposto**: cada um dos oito Advisors já possui, desde sua própria Advisor Specification institucional, uma identidade declarada e pública — o problema que resolve, o que não resolve, os limites que nunca cruza (ex.: a Advisor Specification do Strategy Advisor declara literalmente que ele responde "a execução continua alinhada com a estratégia declarada?"; a do Executive Advisor declara "o que exige atenção da liderança agora?"). Essa identidade já registrada, nunca inventada nesta etapa, é o material bruto sobre o qual uma regra determinística de seleção pode operar — sem que o LLM precise, ou possa, julgar relevância.

**Regra de seleção**: proposta conceitual, não código — mapeamento determinístico entre sinais estruturados extraídos da pergunta (não decidido nesta etapa como esses sinais são extraídos) e o conjunto de identidades declaradas dos Advisors. O que é permanentemente decidido aqui: essa correspondência nunca pode ser um julgamento livre de um LLM; deve ser expressável como regra auditável, reproduzível para a mesma entrada.

**Base insuficiente**: definida operacionalmente com dois gatilhos precisos (§4) — nenhum Advisor selecionado, ou todos os Advisors selecionados retornando sem evidência própria (o equivalente, em cada Advisor individual, ao seu próprio `no_evidence()`).

**Ciclo de vida**: confirmado como request-scoped — mesma disciplina já universal em toda a plataforma, nunca uma exceção.

**Recomendação: GO para a próxima etapa institucional (Technical Design), sujeita a nova autorização explícita do Founder.**

---

## 2. Modelo de Domínio

Três conceitos novos, nomeados aqui pela primeira vez, exclusivamente em nível de domínio — nenhum shape de dado, nenhuma classe, nenhum método:

### 2.1 Advisor Identity (conceito, não novo dado)

Cada Advisor já declara, desde sua Advisor Specification (etapa 1 do seu próprio ciclo institucional), o problema estratégico que resolve e a fronteira que nunca cruza — informação já pública, já registrada em `docs/architecture/ADVISOR-SPECIFICATION-*.md` para todos os oito. Este Domain Blueprint não cria um novo dado — nomeia esse corpo de identidade já existente como o material sobre o qual a regra de seleção (§3) opera. Nenhuma nova fonte de verdade é introduzida; a identidade de cada Advisor permanece exatamente onde já está documentada institucionalmente.

### 2.2 Selection Rule (conceito, mecanismo não decidido)

Uma correspondência determinística entre sinais derivados da pergunta e o subconjunto de Advisor Identities relevante. Propriedades exigidas pelo Princípio 12, permanentes desde já:

- **Determinística**: a mesma pergunta, na mesma configuração organizacional, produz sempre o mesmo conjunto de Advisors selecionados.
- **Explícita**: a regra é nomeável e inspecionável — nunca um comportamento emergente de um modelo de linguagem.
- **Reproduzível**: executável novamente, produzindo o mesmo resultado, sem depender de estado externo variável (ex.: nunca depende de uma resposta de LLM não determinística).
- **Auditável**: dado um resultado de seleção, é possível explicar exatamente por que aqueles Advisors, e não outros, foram escolhidos.

**O que esta etapa não decide**: o mecanismo exato de extração de sinais da pergunta (análise lexical, tags explícitas fornecidas pelo usuário, categorização estrutural, ou qualquer outro método determinístico) — isso é matéria de Technical Design, desde que a etapa de decisão final (qual Advisor participa) nunca seja, ela mesma, um julgamento de LLM.

### 2.3 Orchestration Result (conceito, não novo modelo de resposta)

O resultado de uma execução do Orchestrator é, conceitualmente, um dos dois estados seguintes — nunca um terceiro:

- **Coleção com proveniência preservada**: um conjunto de `Explanation`s, cada uma permanecendo identificável por qual Advisor a produziu (Princípio 4) — nunca um resultado achatado ou anônimo.
- **Base insuficiente**: um estado terminal explícito (§4), nunca uma coleção vazia silenciosa.

Nenhuma forma de serialização, nenhum nome de classe, nenhum shape de resposta HTTP é decidido aqui — isso é Technical Design.

---

## 3. Regra de Seleção Determinística — Resolução Conceitual do Princípio 12

A AR-16 (§1/§3) deixou o mecanismo de seleção explicitamente em aberto. O Princípio 12 (D-137) já fixou que esse mecanismo **nunca pode ser o LLM** — esta seção resolve o que resta em nível de domínio, sem decidir implementação:

1. A regra de seleção opera sobre **sinais estruturados**, nunca sobre uma interpretação semântica livre da pergunta inteira. Qual forma exatamente esses sinais assumem (palavras-chave, categorias explícitas, entidades nomeadas na pergunta) é uma decisão de Technical Design — mas a exigência de que sejam estruturados, e não uma inferência de LLM, é permanente desde já.
2. A regra de seleção é avaliada contra as **Advisor Identities** já declaradas (§2.1) — nunca contra o conteúdo de evidência já produzida por nenhum Advisor (isso seria circular: precisaria já ter executado o Advisor para decidir se deveria executá-lo).
3. **Nenhuma seleção parcial silenciosa**: se a regra determinística identificar zero Advisors relevantes, isso é, por si só, uma forma de base insuficiente (§4) — nunca um erro, nunca uma seleção arbitrária de fallback.
4. A regra pode legitimamente selecionar um único Advisor — Executive Intelligence não exige, por definição, mais de um Advisor por pergunta; exige apenas que a decisão de quantos e quais seja sempre determinística.

**Risco residual explicitamente nomeado, não resolvido nesta etapa**: a granularidade exata da taxonomia de sinais (§3.1) pode se revelar insuficiente ou excessivamente rígida na prática — isso é esperado ser descoberto e ajustado no Technical Design, nunca decidido especulativamente aqui.

---

## 4. Definição Operacional de "Base Insuficiente" (Princípio 11)

A AR-16 nomeou esta ambiguidade explicitamente como risco (§8, tabela de riscos). Resolvida aqui com dois gatilhos precisos e mutuamente exaustivos:

| Gatilho | Condição | Resultado |
|---|---|---|
| **Seleção vazia** | A regra determinística (§3) não identifica nenhum Advisor relevante para a pergunta | Base insuficiente declarada imediatamente — nenhum Advisor é invocado |
| **Coleta vazia de evidência** | Um ou mais Advisors foram selecionados e invocados, mas **todos** retornaram sem evidência própria (o equivalente, em cada um, ao seu próprio portão `no_evidence()`) | Base insuficiente declarada após a coleta — mesmo que a seleção não tenha sido vazia |

**Caso intermediário, explicitamente não insuficiente**: se ao menos um Advisor selecionado retornar evidência real (mesmo que outros não retornem), a síntese é permitida — mesma disciplina de cobertura parcial já usada por todo Advisor Classe B da Wave 5 (ex.: Strategy Advisor, Domain Blueprint §7.3). A declaração de limitação (quais Advisors não contribuíram) permanece obrigatória na resposta final, nunca omitida silenciosamente.

Este critério é definido em nível de domínio — a forma exata de como o Orchestrator representa e comunica esse estado terminal permanece matéria de Technical Design.

---

## 5. Ciclo de Vida — Confirmação

A AR-16 (§4) observou, sem decidir formalmente, que o padrão já universal na plataforma (`AdvisorFramework` instanciado a cada requisição, em toda rota `ask_*_advisor`) sugere um Executive Orchestrator igualmente **request-scoped**. Este Domain Blueprint eleva essa observação a decisão de domínio: o Orchestrator não mantém memória entre perguntas, não mantém estado de sessão próprio, não faz cache de seleções anteriores.

Isso permanece distinto e nunca confundido com `EnterpriseMemoryService` (capacidade deliberadamente persistente, hoje sem consumidor) — se o Orchestrator vier a consultar memória organizacional persistida no futuro, isso acontece exclusivamente através de um Advisor (via `AdvisorFramework.run()`), nunca por acesso direto (Princípio 11 reafirmado).

---

## 6. Rastreabilidade e Citação — Modelo Conceitual

Reafirmação, em nível de domínio, do Princípio 4: cada item do Orchestration Result (§2.3) preserva integralmente o modelo de citação que o Advisor de origem já produziu — `CitedProject`, `ExecutiveCitedEvidence`, `StrategyCitedEvidence`, ou qualquer outro dos oito modelos já em produção, nunca substituídos, nunca achatados. Nenhum esquema global e unificado de numeração de citações é introduzido nesta etapa — isso seria uma nova abstração especulativa sem consumidor real demonstrado ainda, exatamente o tipo de decisão que a disciplina desta plataforma sempre reservou para quando a necessidade real se comprova (mesmo princípio "Grounded before Generalized" já aplicado em toda a Wave 4/5).

---

## 7. Fronteiras Reafirmadas

Nenhuma fronteira da AR-16 é reaberta. Reafirmadas explicitamente, sem alteração:

- Nenhuma consulta direta a `Enterprise Domain`/Knowledge Platform/Workflow Runtime/banco de dados (Princípio 11).
- `AdvisorFramework.run()` permanece inalterado, chamado uma vez por Advisor selecionado (Princípio 2).
- Nenhuma relação com Workflow Runtime no caminho síncrono de resposta a uma pergunta (AR-16 §6).
- Nenhum Advisor precisa mudar para ser selecionável — a uniformidade de `AdvisorContract` já é suficiente (AR-16 §7).

---

## 8. Questões Remanescentes para o Technical Design

Nomeadas explicitamente, não resolvidas nesta etapa:

1. Mecanismo exato de extração de sinais estruturados da pergunta (§3.1).
2. Taxonomia exata de sinais/categorias contra a qual a Advisor Identity de cada um dos oito Advisors é comparada.
3. Forma exata de representação de código do Orchestration Result e do estado de base insuficiente (§2.3/§4).
4. Se a etapa de correlação/síntese (Kickoff §6) é responsabilidade do próprio Orchestrator ou de um componente subsequente e distinto — a AR-16 (§1) já deixou isso não decidido, e este Domain Blueprint não o resolve, por permanecer fora do objeto exclusivo desta etapa (o próprio Executive Orchestrator, não a síntese).
5. Controle de custo/latência de N chamadas independentes a `AdvisorFramework.run()` (já nomeado como risco no Kickoff §10 e na AR-16 §8).
6. Estratégia de paralelismo vs. sequencialidade na execução das chamadas selecionadas (Kickoff §8.3).

---

## 9. Riscos

Nenhum risco novo além dos já nomeados na AR-16 (§8) e no Kickoff (§10) foi identificado nesta etapa. Um risco é refinado:

| Risco | Refinamento nesta etapa |
|---|---|
| Ambiguidade na declaração de "base insuficiente" (AR-16 §8) | **Resolvido em nível de domínio** por esta etapa (§4) — os dois gatilhos precisos eliminam a ambiguidade anteriormente nomeada; a forma de código permanece aberta para o Technical Design |

---

## Recomendação

**GO para a próxima etapa institucional (Technical Design do Executive Orchestrator)**, sujeita a nova autorização explícita do Founder.

Este Domain Blueprint resolveu, em nível de modelo de domínio — nunca de código —, as três questões que a AR-16 nomeou explicitamente como abertas: a forma conceitual da regra determinística de seleção (§3, nunca o LLM, sempre sinais estruturados contra Advisor Identities já declaradas), a definição operacional precisa de "base insuficiente" (§4, dois gatilhos exaustivos), e a confirmação do ciclo de vida request-scoped (§5). Nenhuma inconsistência arquitetural foi encontrada entre este Blueprint e os doze princípios já registrados na Vision, nem com nenhuma decisão já tomada na AR-16. Seis questões permanecem explicitamente nomeadas e não resolvidas para o Technical Design (§8). Nenhum trabalho posterior deverá ser iniciado automaticamente — aguarda nova autorização explícita do Founder.
