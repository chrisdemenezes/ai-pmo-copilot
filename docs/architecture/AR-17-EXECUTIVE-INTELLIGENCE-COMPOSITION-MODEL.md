# AR-17 — Executive Intelligence Composition Model

Produzida sob autorização da "Founder Decision" que aprovou o Domain Blueprint do Executive Orchestrator (D-138) sem ressalvas, confirmando que os conceitos `Advisor Identity` e `Selection Rule` estabelecem a arquitetura permanente da seleção determinística, e mandatando, antes do primeiro Technical Design da Wave 6, a consolidação da arquitetura da própria Executive Intelligence: como ela produz seus diferentes tipos de saída. **Nenhum Domain Blueprint. Nenhum Technical Design. Nenhuma implementação.** Nenhum código escrito nesta etapa.

**Precondição:** `WAVE-6-EXECUTIVE-INTELLIGENCE-KICKOFF.md` (D-133), `WAVE-6-EXECUTIVE-INTELLIGENCE-VISION.md` (D-134/D-135/D-137, 12 princípios permanentes), `AR-16-EXECUTIVE-ORCHESTRATOR-ARCHITECTURE-REVIEW.md` (D-136/D-137) e `DOMAIN-BLUEPRINT-EXECUTIVE-ORCHESTRATOR.md` (D-138) aprovados sem ressalvas.

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
| **Advisor Identity** — a identidade institucional já declarada de cada um dos 8 Advisors (problema que resolve, fronteira que nunca cruza), nunca um novo dado inventado | Domain Blueprint §2.1 (D-138) |
| **Selection Rule** — correspondência determinística entre sinais estruturados e Advisor Identities relevantes | Domain Blueprint §2.2 (D-138) |
| **Orchestration Result** — dois estados exaustivos: coleção com proveniência preservada, ou base insuficiente | Domain Blueprint §2.3 (D-138) |
| "Base insuficiente" — dois gatilhos exaustivos: seleção vazia, ou coleta vazia (todos os selecionados sem evidência própria) | Domain Blueprint §4 (D-138) |
| Ciclo de vida do Orchestrator: request-scoped | Domain Blueprint §5 (D-138) |

Este documento nunca reabre nenhuma destas decisões — resolve exclusivamente como os conceitos já oficiais (`Advisor Identity`, `Selection Rule`, `Orchestration Result`) se compõem em produtos de inteligência distintos.

---

## 1. Quais produtos de inteligência existirão?

Seis produtos, exatamente os nomeados pelo Founder — consolidando as sete capacidades já caracterizadas conceitualmente no Kickoff §4 (Executive Briefing, Cross-Advisor Correlation, Conflict Detection, Recommendation Prioritization, Executive Narrative, Decision Support, Organizational Intelligence) em uma taxonomia definitiva e permanente:

| Produto | Definição | Mapeamento ao Kickoff §4 |
|---|---|---|
| **Executive Briefing** | Síntese ampla, periódica ou sob demanda, do estado de uma ou mais unidades organizacionais, cruzando múltiplos Advisors | Executive Briefing; absorve Organizational Intelligence quando o escopo do briefing atravessa múltiplas unidades |
| **Executive Narrative** | Síntese em prosa coerente, sob demanda, respondendo a uma pergunta executiva específica que exige mais de um Advisor | Executive Narrative |
| **Cross Advisor Correlation** | Identificação de que dois ou mais Advisors falam sobre a mesma unidade organizacional, apresentada como achado estrutural — nunca prosa sintetizada | Cross-Advisor Correlation |
| **Conflict Analysis** | Identificação de que dois ou mais Advisors produzem afirmações aparentemente divergentes sobre a mesma unidade, sempre exposta, nunca resolvida | Conflict Detection |
| **Recommendation Package** | Organização não-ranqueada de achados de múltiplos Advisors relevantes a uma decisão, apresentados lado a lado | Recommendation Prioritization — renomeado para evitar a palavra "Priorização", que sugere ranking, permanentemente proibido (Princípio 9) |
| **Decision Support** | O produto mais abrangente — combina Correlation, Conflict Analysis e evidência de múltiplos Advisors para apoiar (nunca decidir) uma decisão executiva específica | Decision Support |

**Nenhum produto além destes seis é decidido nesta etapa.** Organizational Intelligence, nomeada isoladamente no Kickoff, não se torna um sétimo produto — é tratada como uma característica de escopo (múltiplas unidades organizacionais simultâneas) que Executive Briefing e Decision Support podem assumir, nunca uma capacidade de composição distinta com mecânica própria.

---

## 2. Cada produto será gerado por qual Capability?

Cada produto é gerado por exatamente uma **Capability** homônima — mas nenhuma Capability inventa mecânica própria: todas são composições da mesma sequência de até quatro **operações estruturais**, já nomeadas ou implícitas nos documentos anteriores desta Wave, nunca um pipeline novo por produto:

1. **Seleção** — aplica a `Selection Rule` (D-138 §2.2/§3) sobre a pergunta/escopo, produzindo o subconjunto relevante de `Advisor Identity`s. Sempre presente, sempre a primeira operação.
2. **Execução** — invoca `AdvisorFramework.run()` uma vez por Advisor selecionado (AR-16 §5, inalterado). Sempre presente, sempre a segunda operação.
3. **Correlação** — relaciona as `Explanation`s coletadas entre si, identificando sobreposição de unidade organizacional e divergência textual (Vision §6, Kickoff Epic W6-2). Presente quando o produto exige comparar Advisors entre si, nunca quando um único Advisor já responde isoladamente.
4. **Síntese** — compõe a apresentação final (narrativa em prosa, ou pacote estruturado), sempre informativa, nunca uma decisão automática (Vision, Princípio 6). Presente apenas nos produtos cujo resultado final é uma composição apresentável, nunca um achado bruto de correlação.

| Capability | Produto | Seleção | Execução | Correlação | Síntese |
|---|---|:---:|:---:|:---:|:---:|
| Executive Briefing Capability | Executive Briefing | ✓ | ✓ | ✓ | ✓ |
| Executive Narrative Capability | Executive Narrative | ✓ | ✓ | ✓ | ✓ |
| Cross Advisor Correlation Capability | Cross Advisor Correlation | ✓ | ✓ | ✓ | — |
| Conflict Analysis Capability | Conflict Analysis | ✓ | ✓ | ✓ | — |
| Recommendation Package Capability | Recommendation Package | ✓ | ✓ | ✓ | ✓ |
| Decision Support Capability | Decision Support | ✓ | ✓ | ✓ | ✓ |

Cross Advisor Correlation e Conflict Analysis terminam na Correlação — seu produto final **é** o achado estrutural da correlação, nunca uma narrativa sobre ele. Os demais quatro produtos exigem uma etapa adicional de Síntese sobre o resultado já correlacionado.

**Nenhuma Capability pula a Seleção ou a Execução.** Isso garante que todo produto, sem exceção, seja rastreável até uma decisão de seleção determinística e até chamadas reais e auditadas a `AdvisorFramework.run()` — nunca um atalho que gere um produto sem ter de fato consultado nenhum Advisor.

---

## 3. Quais Advisor Identities normalmente participam de cada Capability?

**Ilustrativo, nunca prescritivo — a participação real é sempre computada pela `Selection Rule` para a pergunta/escopo específico, nunca uma lista fixa embutida em nenhuma Capability** (isso violaria o Princípio 12: a mesma Capability, para perguntas diferentes, seleciona conjuntos de Advisors diferentes; nenhuma Capability pode ter uma composição de Advisors hardcoded).

| Capability | Participação tipicamente esperada (ilustrativa) |
|---|---|
| Executive Briefing | Amplitude ampla — tipicamente Executive, Portfolio, PMO, Strategy; potencialmente qualquer subconjunto dos 8, dependendo do escopo do briefing |
| Executive Narrative | Determinada inteiramente pela pergunta — tipicamente 2-3 Advisors cuja Identity corresponde aos sinais extraídos da pergunta |
| Cross Advisor Correlation | Pares de Advisors cuja Identity declara evidência sobre a mesma unidade — tipicamente Delivery + Risk (mesmo Project), ou Strategy + Executive (mesmo Portfolio/Program) |
| Conflict Analysis | Pares cuja Identity declara perspectivas estruturalmente distintas sobre a mesma unidade — tipicamente Strategy + Risk (alinhamento declarado vs. risco não mitigado), ou Governance + Delivery (conformidade vs. execução real) |
| Recommendation Package | Tipicamente Executive, PMO, Portfolio — Advisors cuja Identity já trata de "o que precisa de atenção" em algum nível |
| Decision Support | O mais amplo e variável — qualquer combinação, tipicamente incluindo Strategy e/ou Risk quando a decisão tem componente de risco estratégico |

Esta tabela existe exclusivamente para grounding intuitivo — **nenhuma Capability deve, na implementação futura, consultar esta tabela como fonte de verdade de seleção.** A única fonte de verdade de seleção é a `Selection Rule` avaliada em tempo real contra os sinais da pergunta (D-138 §3).

---

## 4. Como preservar rastreabilidade completa da composição?

Toda saída de qualquer Capability carrega, permanentemente, um **Composition Trace** — não um novo modelo de dado decidido nesta etapa, mas um requisito arquitetural permanente que qualquer forma futura de implementação precisa satisfazer:

1. **Qual `Selection Rule` foi aplicada e por quê** — a decisão de seleção em si precisa ser auditável (Princípio 12), nunca apenas o resultado final sem o raciocínio que levou a ele.
2. **Quais Advisors foram efetivamente invocados**, cada um com sua `Explanation` completa e sua citação real, nunca resumida ou reescrita (Princípio 4).
3. **Qual Correlação foi identificada**, se aplicável — quais Advisors foram comparados e por qual critério (mesma unidade organizacional).
4. **Qual Síntese foi produzida**, se aplicável, e a partir de quais `Explanation`s especificamente — nunca uma frase que não possa ser rastreada de volta a pelo menos um Advisor de origem (Princípio 11: nenhum conhecimento novo).

Isso estende, ao nível de produto completo, exatamente o mesmo princípio que já rege cada Advisor individual desde a Wave 5: nenhuma afirmação sem citação real, nenhuma citação sem identidade de origem preservada.

---

## 5. Como preservar determinismo da seleção?

**Toda Capability, sem exceção, consome a mesma e única `Selection Rule`** definida pelo Executive Orchestrator (D-138 §2.2) — nenhuma Capability implementa sua própria lógica de seleção paralela, nem mesmo uma variação "otimizada" ou "especializada" para seu produto específico.

Isso garante uma propriedade permanente: para a mesma pergunta e a mesma configuração organizacional, **duas Capabilities diferentes que recebam a mesma pergunta selecionam exatamente o mesmo conjunto de Advisors** — a única diferença entre Capabilities está no que fazem com esse conjunto depois de selecionado (se correlacionam, se sintetizam), nunca em como o selecionam.

Consequência arquitetural permanente: se, no futuro, uma necessidade real demonstrar que uma Capability precisa de uma seleção estruturalmente diferente (ex.: um subconjunto mais restrito de sinais), isso é uma evolução da própria `Selection Rule` compartilhada — nunca a criação de uma segunda regra de seleção paralela. O mesmo princípio de reuso e de "gatilho por demanda real" (D-104, D-118) que já rege a generalização de padrões Classe B entre Advisors se aplica aqui.

---

## 6. Como evitar que um produto de inteligência se torne um novo Advisor?

Um produto/Capability se tornaria, de fato, um nono Advisor, exatamente quando violasse qualquer uma das seguintes fronteiras — cada uma já permanente desde a Vision, reafirmada aqui explicitamente como o tripwire arquitetural definitivo:

- **Se uma Capability chamar `AIContextEngine.gather()`, `gather_rag_context()`, `DomainService`, ou qualquer repositório diretamente** — isso seria adquirir evidência primária própria, violando o Princípio 1/3/11. Nenhuma Capability tem, ou terá, esse caminho de acesso.
- **Se uma Capability implementar `AdvisorContract`** — isso a tornaria invocável via `AdvisorFramework.run()` como se fosse um Advisor comum, violando o Princípio 8. Uma Capability nunca é invocada dessa forma; ela é o componente que invoca Advisors, nunca o inverso.
- **Se uma Capability interpretar o conteúdo de uma evidência de domínio** (ex.: julgar se um `health_status` é preocupante) em vez de apenas relacionar o que os Advisors já interpretaram — isso duplicaria a responsabilidade de domínio que pertence exclusivamente ao Advisor (Princípio 3).
- **Se uma Capability inventar uma afirmação que nenhum Advisor consultado sustentou** — violação direta e inequívoca do Princípio 11.

Nenhuma das seis Capabilities definidas em §2 cruza qualquer uma dessas quatro linhas, por construção: cada uma é estritamente uma composição das quatro operações estruturais (Seleção, Execução, Correlação, Síntese), e nenhuma dessas quatro operações, por definição, exige acesso a fonte primária, implementação de `AdvisorContract`, interpretação de domínio, ou invenção de fato.

---

## 7. Como manter o Executive Orchestrator completamente agnóstico ao domínio?

O Orchestrator — e, por extensão, toda Capability construída sobre ele — opera exclusivamente sobre dois tipos de conhecimento, ambos estruturais e nunca de domínio:

1. **O catálogo fechado de `Advisor Identity`s** — um conjunto pequeno, fixo e institucional (hoje, exatamente oito), cada uma descrita em termos do problema que resolve e da fronteira que nunca cruza (D-138 §2.1). O Orchestrator conhece que "o Strategy Advisor responde sobre alinhamento entre execução e estratégia declarada" — mas nunca conhece o conteúdo de nenhum objetivo estratégico real de nenhuma organização específica.
2. **Os sinais estruturados extraídos de uma pergunta** (mecanismo exato ainda não decidido, D-138 §8.1/§8.2) — categorização/classificação da pergunta em si, nunca uma consulta ao conteúdo de nenhum `Portfolio`/`Program`/`Project` real.

**O que o Orchestrator nunca conhece, em nenhuma circunstância:** o conteúdo de nenhum objetivo declarado, nenhum status de execução, nenhum risco identificado, nenhum documento indexado — todo esse conhecimento de domínio permanece exclusivamente dentro dos Advisors que o produzem, nunca vazando para a camada de seleção/correlação/síntese estrutural.

Isso é o que torna a arquitetura permanentemente estável mesmo se um nono Advisor viesse a ser adicionado no futuro (hipótese não decidida, apenas ilustrativa): o Orchestrator precisaria apenas de uma nova `Advisor Identity` no seu catálogo fechado — nunca de nenhuma mudança à sua lógica de seleção, correlação ou síntese, que permanecem inteiramente agnósticas a qual domínio específico cada Advisor cobre.

---

## Taxonomia Permanente da Executive Intelligence

Consolidação definitiva desta revisão — três camadas, permanentes desde já:

### Camada 1 — Operações Estruturais (4, fechadas)

1. **Seleção** — `Selection Rule` sobre `Advisor Identity`s.
2. **Execução** — `AdvisorFramework.run()`, uma chamada por Advisor selecionado.
3. **Correlação** — relação entre `Explanation`s por unidade organizacional compartilhada.
4. **Síntese** — composição informativa final, nunca decisória.

### Camada 2 — Capabilities (6, permanentes, cada uma uma composição fixa das operações da Camada 1)

| Capability | Composição |
|---|---|
| Executive Briefing | Seleção → Execução → Correlação → Síntese |
| Executive Narrative | Seleção → Execução → Correlação → Síntese |
| Cross Advisor Correlation | Seleção → Execução → Correlação |
| Conflict Analysis | Seleção → Execução → Correlação |
| Recommendation Package | Seleção → Execução → Correlação → Síntese |
| Decision Support | Seleção → Execução → Correlação → Síntese |

### Camada 3 — Composition Trace (obrigatório, permanente, acompanha toda saída de qualquer Capability)

Registro auditável de: qual `Selection Rule` decidiu qual conjunto de Advisors e por quê; quais `Explanation`s reais foram coletadas; qual Correlação (se houver) relacionou quais Advisors; qual Síntese (se houver) foi produzida a partir de quais `Explanation`s especificamente.

**Nenhuma Capability nova pode ser adicionada a esta taxonomia sem demonstrar necessidade real** (mesmo gatilho "Grounded before Generalized" já permanente desde a Wave 4) — e, quando adicionada, deve ser expressável inteiramente como uma composição das mesmas quatro operações estruturais da Camada 1, nunca uma mecânica nova e paralela.

### Camada 4 — Executive Intelligence Result / Orchestration Result (registrado após a aprovação original desta AR)

O produto lógico de qualquer Capability, sempre contendo: a Capability executada; a `Selection Rule` aplicada; o conjunto de `Advisor Identity`s participantes; as `Explanation`s consumidas, com proveniência preservada; o Composition Trace (Camada 3); e a síntese produzida, quando a Capability incluir a operação de Síntese. Assume sempre um de dois estados exaustivos — coleção completa, ou base insuficiente (Princípio 11; Domain Blueprint §2.3/§4, D-138) — nunca um terceiro estado.

**Explicitamente não é**: um novo Advisor; uma nova fonte de evidência; um contrato HTTP; um modelo de banco de dados; um tipo de domínio. É exclusivamente a representação arquitetural do resultado — nenhuma forma de serialização ou código é decidida aqui, matéria exclusiva do Technical Design. Definição completa em `WAVE-6-EXECUTIVE-INTELLIGENCE-VISION.md`, seção "Conceito Permanente — Executive Intelligence Result (Orchestration Result)".

---

## Recomendação

**GO para o primeiro Technical Design da Wave 6**, sujeito a nova autorização explícita do Founder.

Este documento respondeu, em nível institucional e arquitetural, as sete perguntas mandatadas: os seis produtos de inteligência (§1); a Capability que gera cada um, sempre uma composição das mesmas quatro operações estruturais (§2); a participação ilustrativa — nunca prescritiva — de Advisor Identities por Capability (§3); a rastreabilidade completa via Composition Trace (§4); a preservação de determinismo através de uma única `Selection Rule` compartilhada por todas as Capabilities (§5); os quatro tripwires que impedem qualquer Capability de se tornar um nono Advisor (§6); e a natureza estritamente estrutural — nunca de domínio — do conhecimento que mantém o Orchestrator agnóstico (§7). A Taxonomia Permanente consolida quatro camadas fechadas: quatro Operações Estruturais, seis Capabilities, o Composition Trace obrigatório, e o conceito de Executive Intelligence Result/Orchestration Result que os reúne. Nenhuma inconsistência arquitetural foi encontrada entre esta revisão e nenhuma decisão já registrada na Vision, na AR-16, ou no Domain Blueprint. Nenhum trabalho posterior deverá ser iniciado automaticamente — aguarda nova autorização explícita do Founder.
