# Wave 6 — Executive Intelligence: Architecture Vision

**Status:** documento complementar ao `WAVE-6-EXECUTIVE-INTELLIGENCE-KICKOFF.md` (aprovado, D-133), autorizado pelo Founder ("Founder Decision" seguinte a D-133, 2026-08-06) para consolidar a visão arquitetural da Wave 6 antes da primeira Architecture Review. **Nenhum código é escrito por este documento. Nenhum Domain Blueprint. Nenhum Technical Design. Nenhum Epic iniciado.**

**Precondição:** `WAVE-6-EXECUTIVE-INTELLIGENCE-KICKOFF.md` aprovado sem ressalvas — Executive Summary confirmou ausência de inconsistências arquiteturais impeditivas. Este documento nunca reabre o Kickoff; aprofunda-o.

**Fundamentação:** exclusivamente o Kickoff já aprovado e a arquitetura real (código de `src/`) nele grounded — nunca especulação nova, nunca o Blueprint conceitual pré-D-071.

---

## 1. O que é Executive Intelligence dentro da STRATECH?

Executive Intelligence é a camada institucional cuja única responsabilidade é **relacionar respostas já produzidas pelos Enterprise Advisors**, nunca produzir uma nova interpretação de evidência primária, nunca ser uma nova fonte de fato.

Formalmente: Executive Intelligence opera exclusivamente sobre o **produto de saída** de uma ou mais chamadas a `AdvisorFramework.run()` — a `Explanation` (`recommendation.answer` + `recommendation.cited_evidence` + `rationale`) que cada Advisor já produz hoje, sozinho, de forma completa e auditada. Ela nunca chama `AIContextEngine.gather()`, `gather_rag_context()`, ou qualquer repositório de domínio diretamente — fazer isso duplicaria a responsabilidade de interpretação que já pertence, com exclusividade, a um dos oito Advisors.

Isso posiciona Executive Intelligence estruturalmente **depois** de um ou mais Advisors terem respondido, nunca **ao lado** ou **dentro** deles. A analogia mais precisa com o que já existe na plataforma: assim como `ExplanationEngine.explain()` hoje envolve uma `Recommendation` de um único Advisor num envelope padrão (`rationale`, ADR-V2-007), Executive Intelligence envolve **múltiplas** `Explanation`s já produzidas — a mesma disciplina de nunca inventar, aplicada um nível acima.

## 2. Como Executive Intelligence difere de um Enterprise Advisor?

| | Enterprise Advisor (os 8 da Wave 5) | Executive Intelligence |
|---|---|---|
| Fonte de evidência | Consulta direta a `AnalysisRecord`/`Chunk`/campos de domínio, via `AdvisorFramework.gather_context()`/`gather_rag_context()` | Nunca consulta evidência primária diretamente — consome `Explanation`s já produzidas por Advisors |
| Fronteira de domínio | Fixa e estreita (um `kind`, uma composição fixa de `kind`s, ou RAG) | Atravessa fronteiras — pode relacionar Strategy + Risk + Executive na mesma síntese |
| Contrato | Implementa `AdvisorContract` (`name` + `advise(session, question, evidence, rag_context)`), invocado por exatamente uma chamada a `AdvisorFramework.run()` | Não implementa `AdvisorContract` — não tem evidência primária própria para compor; invoca `AdvisorFramework.run()` **múltiplas vezes**, uma por Advisor selecionado |
| Natureza da "inteligência" | Interpretação semântica de evidência de domínio (o que os dados significam) | Interpretação relacional entre respostas já interpretadas (o que a relação entre elas significa) |
| Citação | Modelo de citação próprio e isolado por Advisor (`CitedProject`, `ExecutiveCitedEvidence`, `StrategyCitedEvidence`, etc.) | Precisa preservar a citação original de cada Advisor consultado, nunca reinventar uma nova identidade de evidência (§5) |

A distinção central, já nomeada no Kickoff §3 e reafirmada aqui como definição permanente: **um Advisor responde dentro de uma fronteira; Executive Intelligence responde através de fronteiras já respondidas.**

## 3. Qual é o papel do futuro Executive Orchestrator?

Nomeado aqui apenas como **papel institucional**, nunca como componente de código decidido (isso é Technical Design, fora de escopo desta missão):

1. **Recebe** a pergunta executiva do usuário.
2. **Determina** quais Advisors, dentre os oito existentes, são relevantes para respondê-la com integridade (mecanismo de seleção não decidido — Kickoff §8.2).
3. **Invoca** cada Advisor selecionado através do caminho já existente e inalterado — uma chamada independente a `AdvisorFramework.run()` por Advisor (nunca uma chamada composta, nunca um novo método que aceite múltiplos Advisors).
4. **Coleta** as `Explanation`s resultantes, cada uma já completa, já auditada, já com seu próprio `rationale`.
5. **Entrega** o conjunto coletado a uma etapa de correlação/síntese (§6/§7) — que pode ou não ser o mesmo componente; não decidido aqui.

O Orchestrator **nunca**: interpreta evidência de domínio diretamente (isso permanece exclusivo do Advisor), decide qual Advisor está certo quando há divergência (§6), produz uma recomendação de ação (Princípio 1 da Product Constitution), ou se torna, ele mesmo, um nono Advisor com `AdvisorContract` próprio — sua inteligência é inteiramente relacional, nunca de domínio.

## 4. Como múltiplos Advisors cooperam sem violar o princípio permanente de que `AdvisorFramework.run()` executa exatamente um Advisor por chamada?

A resolução conceitual é que **o princípio nunca foi "uma pergunta, um Advisor" — sempre foi "uma chamada, um Advisor"**. Isso permanece, sem exceção, verbatim como está hoje em `src/services/advisor_framework/framework.py`.

O que muda é o **nível em que a cooperação acontece**: nunca dentro de `run()`, sempre **acima** dele. Uma pergunta executiva que precise de Strategy + Risk resulta em **duas chamadas independentes e completas** a `AdvisorFramework.run()` — uma com `StrategyAdvisorAgent`, outra com `RiskAdvisorAgent` — cada uma exatamente como acontece hoje quando um usuário pergunta a um Advisor isoladamente. `run()` nunca sabe que existe uma segunda chamada acontecendo; cada Advisor nunca sabe que outro foi consultado. A cooperação é inteiramente uma responsabilidade do Orchestrator (§3), que existe **fora** de `AdvisorFramework`, nunca dentro dele.

Isso é a mesma disciplina já usada, em miniatura, por todo Advisor Classe B da Wave 5: o `StrategyEvidenceAssembler`, por exemplo, nunca modificou `AIContextEngine.gather()` para aceitar múltiplos `kind`s numa única chamada — ele fez múltiplas chamadas independentes e compôs o resultado ele mesmo, na sua própria camada. Executive Intelligence generaliza exatamente esse padrão, um nível acima: múltiplas chamadas independentes a `AdvisorFramework.run()`, compostas por um componente que existe estruturalmente acima do Framework, nunca dentro dele.

## 5. Como preservar rastreabilidade quando uma única resposta utilizar múltiplos Advisors?

Princípio permanente: **nenhuma citação de Advisor é achatada, renomeada, ou perde a identidade do Advisor que a produziu.**

Cada um dos oito Advisors já tem seu próprio modelo de citação real e testado (`CitedProject`, `ExecutiveCitedEvidence`, `StrategyCitedEvidence`, etc.), cada um contendo a identidade real e auditável da evidência (`source_analysis_id`, `entity_id`, `chunk_id`, conforme o caso). Executive Intelligence nunca substitui esses modelos por um único modelo genérico que perderia a diferenciação entre eles — ao invés disso, o princípio é que toda citação na resposta executiva final permanece **atribuível a exatamente um Advisor de origem, usando a citação real que esse Advisor já produziu**, nunca uma citação nova inventada no nível executivo.

Isso implica, conceitualmente (sem decidir a forma exata — Technical Design): uma resposta executiva que cita achados de dois Advisors precisa expressar, para cada citação, "isto veio do Strategy Advisor, citando X" e "isto veio do Risk Advisor, citando Y" — nunca uma lista única e anônima de citações misturadas. A mesma disciplina que levou a Wave 5 a nunca reaproveitar `CitedProject` para o Strategy Advisor quando a forma de citação exigia um campo novo (`level`) se aplica aqui: um modelo de citação executivo, se vier a existir, **envolve** as citações reais dos Advisors, nunca as substitui.

## 6. Como conflitos entre Advisors deverão ser tratados conceitualmente?

O mesmo limite institucional já permanente para o Strategy Advisor — "nunca decide qual nível prevalece caso observe divergência textual, pode apenas observar" (AR-15 §3) — generaliza-se aqui para o caso entre Advisors: **Executive Intelligence pode observar e expor um conflito explicitamente, nunca resolvê-lo, nunca decidir qual Advisor está certo, nunca aplicar um score ou peso que favoreça um sobre o outro.**

Um conflito (ex.: Strategy Advisor afirma alinhamento; Risk Advisor identifica um risco crítico não mitigado que ameaça esse mesmo objetivo) é, ele mesmo, um achado executivo legítimo e valioso — a resposta correta não é escondê-lo nem sintetizar uma média entre as duas posições, é **nomear as duas afirmações lado a lado, cada uma atribuída ao seu Advisor de origem**, e deixar o julgamento humano decidir o que isso significa (Princípio 1 da Product Constitution: "não substitui o julgamento do PM/PMO... não decide, não prioriza" — aplicado aqui pela primeira vez ao nível de relação entre Advisors, não apenas dentro de um único Advisor).

## 7. Como Executive Intelligence deverá produzir uma narrativa executiva única mantendo todas as evidências originais?

O princípio permanente é o mesmo que já governa `ExplanationEngine` desde a Wave 3: **síntese informativa, nunca decisão automática** (ADR-V2-007) — estendido, sem enfraquecer, ao nível de múltiplos Advisors.

Uma narrativa única não significa perda de rastreabilidade — significa organização em prosa coerente de achados que permanecem, cada um, ligados à sua evidência real de origem (§5). Duas formas estruturais são conceitualmente possíveis para compor essa narrativa (nenhuma decidida aqui — isso é Technical Design):

- **Composição por um novo passo de síntese** (ex.: um LLM call adicional que recebe as `Explanation`s já produzidas — nunca a evidência bruta — e produz prosa unificada), preservando as citações originais de cada Advisor como anexo estrutural à resposta.
- **Composição estrutural sem novo LLM call** (ex.: template/concatenação que organiza as respostas já prontas dos Advisors, sem reinterpretá-las).

Em qualquer uma das duas formas, o princípio inegociável é: **a narrativa nunca pode afirmar algo que nenhum dos Advisors consultados afirmou primeiro** — Executive Intelligence organiza e relaciona, nunca inventa um fato novo que nenhum Advisor sustentou com sua própria evidência.

## 8. Quais princípios arquiteturais desta Wave deverão permanecer permanentes para todas as Waves futuras?

Consolidados na seção seguinte.

---

## Executive Intelligence Principles

Princípios institucionais permanentes desta camada, aplicáveis a toda a Wave 6 e a qualquer trabalho futuro que dela dependa — no mesmo espírito das definições permanentes já registradas para os Advisors (D-104, Classe A/B; AR-8 §4, Classe D):

1. **Executive Intelligence nunca é uma nova fonte primária de evidência.** Ela consome exclusivamente `Explanation`s já produzidas por Advisors — nunca consulta `AnalysisRecord`, `Chunk`, ou qualquer campo de domínio diretamente.

2. **`AdvisorFramework.run()` continua a executar exatamente um Advisor por chamada, sem exceção.** Cooperação entre Advisors acontece exclusivamente através de múltiplas chamadas independentes, orquestradas por um componente que existe estruturalmente acima do Framework — nunca por uma alteração a `run()` que o faça invocar mais de um Advisor internamente.

3. **A interpretação de evidência de domínio permanece exclusiva do Advisor dono daquele domínio.** Executive Intelligence nunca reinterpreta evidência bruta — sua inteligência é inteiramente relacional (o que a relação entre respostas já interpretadas significa), nunca de domínio.

4. **Toda citação em uma resposta executiva permanece atribuível a exatamente um Advisor de origem, usando a citação real que esse Advisor já produziu.** Nenhuma citação é achatada, anonimizada ou reinventada no nível executivo.

5. **Conflitos entre Advisors são sempre expostos explicitamente, nunca resolvidos, nunca ranqueados.** Nenhum algoritmo decide qual Advisor está certo — o julgamento permanece exclusivamente humano.

6. **Síntese executiva permanece informativa, nunca uma decisão automática, nunca a recomendação de uma única ação correta** (ADR-V2-007, estendido sem enfraquecer da Wave 3 até aqui).

7. **Nenhum componente compartilhado (`AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, Workflow Runtime, Event Pipeline, contrato `Evidence`) pode ser alterado destrutivamente para acomodar Executive Intelligence** — apenas extensões aditivas, exatamente a disciplina já comprovada nos oito ciclos institucionais da Wave 5.

8. **O Executive Orchestrator nunca se torna um nono Advisor.** Ele nunca implementa `AdvisorContract` como se tivesse evidência primária própria — sua função é exclusivamente coordenar chamadas já existentes e relacionar seus resultados.

9. **Nenhum ranking, score ou algoritmo de priorização decide o que é mais importante para o executivo.** A apresentação pode organizar; nunca decide (generalização, ao nível cross-Advisor, do princípio já permanente desde D-104/AR-8 de que nenhum Advisor calcula ranking determinístico).

10. **O Workflow Runtime permanece exclusivamente orientado a evento.** Ele nunca se torna o mecanismo de invocação síncrona de Executive Intelligence em resposta a uma pergunta de usuário — essa fronteira, já nomeada no Kickoff §5, é permanente.

---

## Recomendação

**GO para a primeira Architecture Review da Wave 6**, fundamentada neste documento em conjunto com o Kickoff já aprovado (D-133).

Nenhuma decisão de implementação foi tomada aqui — as oito perguntas foram respondidas em nível institucional e arquitetural, e os dez princípios permanentes acima consolidam o que a Wave 6 nunca poderá violar, independentemente de qual Domain Blueprint, Technical Design ou Epic vier a decidir a forma exata do Executive Orchestrator, do modelo de citação executivo, ou do mecanismo de síntese. Nenhum trabalho posterior deverá ser iniciado automaticamente — aguarda nova autorização explícita do Founder.
