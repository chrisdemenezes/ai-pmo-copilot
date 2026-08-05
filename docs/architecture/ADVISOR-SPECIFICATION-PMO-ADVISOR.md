# Advisor Specification — PMO Advisor (sexto uso do padrão institucional, segundo Classe B)

**Autorização:** "Founder Decision — Encerramento do Portfolio Advisor e abertura do PMO Advisor" — Founder declarou o Portfolio Advisor oficialmente encerrado, reconhecendo: `PortfolioEvidenceAssembler` permaneceu exclusivo do pacote do Advisor; cada Project contribui com somente seu status mais recente; contagens de cobertura estruturais, independentes do LLM; `cited_projects` contém apenas Projects efetivamente citados; cobertura completa/parcial/zero comprovadas; isolamento organizacional preservado; toda a infraestrutura compartilhada (`AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, Workflow Runtime, Event Pipeline, `DomainService`, `DomainRepository`, `Evidence`) permaneceu inalterada; suíte verde. **5 de 8 Advisors da Wave 5 concluídos.** Autorizada a abertura do ciclo institucional do **PMO Advisor**, iniciando exclusivamente pela Advisor Specification (etapa 1 de 6, D-092). Nenhum código deverá ser escrito. Exigência explícita: avaliar primeiro se o PMO Advisor deve consumir fontes primárias diretamente ou compor resultados estruturados já produzidos pelos Advisors existentes — nenhuma decisão sobre essa composição tomada silenciosamente.

---

## Executive Summary

O PMO Advisor é o sexto Advisor a passar pelo padrão institucional e o **segundo Advisor Classe B** (D-104), após o Portfolio Advisor — primeira validação real do padrão de composição que AR-8 §7.3 previu que precisaria de um segundo consumidor para se confirmar como referência. Diferente do Portfolio Advisor (composição/equilíbrio de projetos dentro de **um** portfólio), o objetivo do PMO Advisor é identificar **padrões de processo** — atrasos recorrentes, ausência de atualização, lacunas de conformidade — através de **múltiplos projetos de uma organização**, potencialmente atravessando portfólios. A questão arquitetural central que esta Specification resolve, per exigência explícita do Founder (não decidida silenciosamente): **o PMO Advisor deve consumir fontes primárias diretamente (`AnalysisRecord` via `AIContextEngine.gather()`), nunca compor `Recommendation`/`Explanation` já produzidos por outros Advisors** — esta não é uma escolha de estilo, é a aplicação direta de uma restrição já permanente e documentada no próprio `AdvisorFramework` desde a Fase 3: "`run()` executa exatamente um Advisor por chamada... nunca delegação de um Advisor para outro" (`framework.py`, docstring, Founder's explicit restriction, Fase 3). Recomendação ao final: **GO para o Domain Blueprint.**

---

## 1. Objetivo e usuário-alvo (per `ENTERPRISE-ADVISOR-CATALOG.md` §4, reafirmado)

**Objetivo:** apoiar a função de PMO (Project Management Office) com visão consolidada de conformidade e saúde de processo entre projetos.

**Usuário-alvo:** o PMO da organização (não um sponsor de projeto individual, não a liderança executiva sênior) — quem precisa identificar, através de muitos projetos, se o processo de gestão (atualização regular, conformidade de acompanhamento) está sendo seguido, não o conteúdo específico de risco ou o estado de entrega de um projeto isolado.

**Responsabilidade (catálogo, reafirmada):** identificar padrões de processo (atrasos recorrentes, ausência de atualização, lacunas de governança) através de múltiplos projetos de uma organização.

---

## 2. Classificação — Classe B, com justificativa

**Classe B**, per a definição institucional permanente (D-104/AR-8 §4.2): "Advisor baseado na composição de duas ou mais fontes independentes de evidência." O objetivo do PMO Advisor — identificar **padrões** — é estruturalmente impossível com uma única fonte primária: um padrão de "atraso recorrente" ou "ausência de atualização" só existe quando comparado através de múltiplos projetos independentes. Isso é exatamente a mesma natureza de composição já provada pelo Portfolio Advisor: N chamadas a `gather_context()`, uma por projeto, compostas fora do Framework (§4).

**Diferença de escopo em relação ao Portfolio Advisor, ambos Classe B:** o Portfolio Advisor compõe evidência de projetos **dentro de um Portfolio identificado** (`portfolio_id` obrigatório); o PMO Advisor compõe evidência de projetos em **escopo organizacional**, potencialmente todos os projetos da organização, atravessando portfólios — per catálogo, "Entradas: `organization_id` + escopo organizacional/portfólio" (o escopo de portfólio é opcional, não obrigatório).

---

## 3. Fontes reais de evidência — decisão arquitetural central desta etapa

### 3.1 A pergunta exigida pelo Founder: fontes primárias ou resultados de outros Advisors?

**Decisão: fontes primárias diretamente — nunca compor `Recommendation`/`Explanation` de outro Advisor.**

**Fundamentação, não uma preferência de estilo:** `AdvisorFramework.run()` já declara, desde sua Technical Design de Fase 3 (docstring do próprio `framework.py`, citada literalmente): *"`run()` executa exatamente um Advisor por chamada, escolhido pelo chamador — nunca um motor de workflow, nunca roteamento autônomo entre Advisors, nunca delegação de um Advisor para outro (restrições explícitas do Founder, Fase 3)."* Consumir o `answer`/`cited_evidence` de, por exemplo, o Delivery Advisor como "evidência" de entrada do PMO Advisor seria, na prática, uma forma de delegação entre Advisors — exatamente o que essa restrição, já permanente, proíbe. Esta Advisor Specification não está decidindo uma preferência nova; está aplicando uma regra arquitetural que já existe e que nenhuma Epic desde a Fase 3 tentou contornar.

**Consequência prática:** o PMO Advisor consome exclusivamente `AnalysisRecord` via `AIContextEngine.gather()` (o mesmo mecanismo já usado por Risk/Delivery/Portfolio Advisor) — nunca chama `POST /delivery-advisor/ask`, `POST /portfolio-advisor/ask`, ou qualquer outra rota/objeto de outro Advisor internamente.

### 3.2 `kind` proposto (achado grounded, não decisão final — reservado ao Domain Blueprint)

Por analogia direta ao Delivery Advisor (D-104/D-106) e ao Portfolio Advisor (D-109/D-111), a proposta é `AnalysisRecord`/`kind="status"` como fonte primária — cada projeto contribui seu registro de status mais recente (mesma regra de recência já permanente). O que distingue o PMO Advisor não é uma fonte diferente, é uma **leitura diferente** dos mesmos dados: além do conteúdo (`health_status`/`key_findings`/`recommendations`, já usados por Delivery/Portfolio Advisor), o PMO Advisor precisa do **timestamp de cada registro** (`Evidence.metadata["created_at"]`, campo já existente, nenhuma extensão) para detectar "ausência de atualização" — um projeto cujo `AnalysisRecord` de status mais recente é antigo é, em si, o sinal de processo que este Advisor deve reportar. Nenhum campo novo, nenhum método novo — apenas uma leitura de domínio adicional sobre dados que já chegam ao Advisor.

**Não decidido aqui:** se um segundo `kind` (ex.: `"meeting"`, para detectar atraso de ação recorrente) é necessário — o catálogo menciona "atrasos recorrentes" que poderiam, em princípio, vir de `action_items` (hoje só existentes em `AnalysisRecord`s de `kind="meeting"`, per achado já registrado na Advisor Specification do Delivery Advisor, D-103). Se confirmado necessário, isso seria uma segunda fonte independente (ainda Classe B, apenas com mais fontes) — decisão reservada ao Domain Blueprint, não a esta Specification.

### 3.3 Explicitamente fora de alcance: RAG/Knowledge Platform

O PMO Advisor **não consulta RAG** — "lacunas de governança" no sentido deste Advisor refere-se a lacunas de **processo evidenciadas dentro dos próprios `AnalysisRecord`s** (ex.: uma análise de status que não menciona acompanhamento esperado), nunca aos documentos institucionais (Decision Log/Technical Debt Register) que são domínio exclusivo do Governance Advisor (§4). Nenhuma ambiguidade de nomenclatura entre "lacunas de governança" (PMO Advisor, processo) e "governança institucional" (Governance Advisor, documentos) deve ser permitida a se infiltrar na implementação — reafirmado aqui para o Domain Blueprint.

---

## 4. Relação com Delivery, Portfolio e Governance Advisors

| Advisor | Escopo de evidência | Pergunta que responde | Sobreposição com o PMO Advisor |
|---|---|---|---|
| **Delivery Advisor** | Um projeto, histórico completo de status | Qual a trajetória de entrega deste projeto? | Nenhuma — Delivery Advisor narra um projeto; PMO Advisor nunca narra um projeto individual, apenas padrões através de muitos. |
| **Portfolio Advisor** | Projetos de **um** Portfolio, apenas o status atual de cada um | Como este portfólio está balanceado/composto agora? | Nenhuma — Portfolio Advisor responde sobre composição/prioridade de portfólio; PMO Advisor nunca decide composição de portfólio, apenas relata se o processo de acompanhamento está sendo seguido (§8). |
| **Governance Advisor** | Documentos institucionais (Decision Log, Technical Debt Register) via RAG | Esta decisão/débito segue o processo de governança documentado? | Nenhuma — Governance Advisor opera sobre documentos institucionais; PMO Advisor nunca consulta RAG, opera exclusivamente sobre `AnalysisRecord` (§3.3). |
| **PMO Advisor (este)** | Múltiplos projetos da organização (potencialmente todos, atravessando portfólios), apenas o status atual de cada um | Os processos de PMO (atualização regular, acompanhamento) estão sendo seguidos através dos projetos? | — |

**Reafirmado, per restrição já permanente (§3.1):** nenhum dos quatro Advisors acima consome a saída de outro como evidência de entrada — cada um monta sua própria evidência a partir de fontes primárias, sempre via `AdvisorFramework`.

---

## 5. Responsabilidades próprias

- Identificar projetos cujo `AnalysisRecord` de status mais recente está desatualizado além de um limiar de recência (achado grounded — o limiar exato é decisão de Technical Design, não desta Specification).
- Identificar padrões que se repetem através de múltiplos projetos (ex.: vários projetos reportando o mesmo tipo de bloqueio ou atraso em `key_findings`) — sempre citando os projetos reais envolvidos, nunca uma generalização sem evidência de múltiplos projetos (critério de sucesso já definido no catálogo).
- Sinalizar lacunas de processo evidenciadas no conteúdo das próprias análises de status — nunca inventadas, nunca inferidas além do texto presente.

---

## 6. Decisões que pode sugerir

- Recomendar que um PMO revise projetos com ausência de atualização recente.
- Recomendar atenção a um padrão de atraso recorrente identificado através de múltiplos projetos, citando-os.
- Recomendar que uma lacuna de processo evidenciada (ex.: análise sem acompanhamento esperado) seja endereçada.

Todas como **evidência para quem decide** — nunca como decisão em si, mesma disciplina de todo Advisor (`AR-8` §8).

---

## 7. Decisões que nunca poderá tomar

- Nunca decide realocação de recursos, orçamento, ou prioridade (isso permanece limite do Portfolio Advisor, reafirmado, não deste Advisor).
- Nunca avalia conteúdo de risco de um projeto individual (catálogo, reafirmado — isso é o Risk Advisor).
- Nunca decide política de governança institucional nem aplica a hierarquia documental (isso é o Governance Advisor, RAG, fora de alcance per §3.3).
- Nunca executa uma ação corretiva, nunca altera um `AnalysisRecord`/Project/Program/Portfolio — produz exclusivamente `Recommendation`/`Explanation` (mesmo limite estrutural de todo Advisor).
- Nunca invocado por `WorkflowRuntime`, nunca registrado como handler de `EventDispatcher` (mesmo limite estrutural de todo Advisor).

---

## 8. Limites para evitar sobreposição com Portfolio Advisor e Executive Advisor

**Contra o Portfolio Advisor:** o PMO Advisor nunca responde sobre equilíbrio, composição, ou priorização de um portfólio específico — essas perguntas permanecem exclusivas do Portfolio Advisor. O PMO Advisor responde exclusivamente sobre **conformidade de processo** (atualização, acompanhamento), nunca sobre a **composição** dos projetos entre si. Se uma pergunta pedir "quais projetos deste portfólio estão em risco de atraso e como isso afeta o equilíbrio do portfólio" — a segunda metade é Portfolio Advisor, não PMO Advisor; esta Specification não resolve esse roteamento (é uma decisão de produto/UX, não arquitetural, fora de alcance aqui).

**Contra o Executive Advisor (ainda não implementado, catálogo §2):** o Executive Advisor sintetiza um resumo executivo a partir de **sinais já existentes** (Portfolio Intelligence, Decision Center, riscos, ações) para liderança sênior — nunca recalcula esses sinais. O PMO Advisor, ao contrário, **calcula** o próprio sinal de padrão de processo a partir de `AnalysisRecord`s brutos — ele é uma fonte primária de síntese, não um consumidor de sínteses já prontas. Quando o Executive Advisor for especificado, ele poderá vir a consumir uma saída do PMO Advisor como um dos "sinais já existentes" que sintetiza — mas essa é uma decisão da Advisor Specification do Executive Advisor, quando sua vez chegar, não desta.

---

## 9. Critérios de sucesso (per catálogo §4, reafirmado)

Padrões identificados sempre referenciam projetos/dados reais; nenhuma generalização sem evidência de múltiplos projetos.

---

## 10. Riscos arquiteturais

| Risco | Bloqueante? | Onde resolver |
|---|---|---|
| Escopo organizacional (não apenas um Portfolio) pode exigir muitas chamadas a `gather_context()` — mais que o Portfolio Advisor, que já tem um gatilho de performance registrado (>20 chamadas ou p95 > 3s, D-111) | Não | Domain Blueprint deve avaliar se o mesmo gatilho se aplica ou se um limiar diferente é necessário para escopo organizacional |
| Segundo `kind` (`"meeting"`, para `action_items`) pode ser necessário para "atrasos recorrentes" — não decidido aqui (§3.2) | Não | Domain Blueprint |
| Reutilização/generalização do padrão de composição do `PortfolioEvidenceAssembler` — este é o segundo consumidor real de um componente de composição Classe B, o gatilho que AR-8 §7.3 previu para avaliar se um padrão compartilhado deve ser extraído | Não | Domain Blueprint deve avaliar explicitamente esta questão, não presumir nem a favor nem contra a extração |
| Limiar de "ausência de atualização" (quantos dias/semanas sem novo `AnalysisRecord` de status caracteriza uma lacuna) — nenhum dado real de uso ainda | Não | Technical Design |
| Ambiguidade de nomenclatura "lacunas de governança" (processo, PMO Advisor) vs. "governança institucional" (documentos, Governance Advisor) — mitigado nesta Specification (§3.3/§4), deve permanecer explícito no Domain Blueprint | Não | Domain Blueprint reafirma |

Nenhum risco listado bloqueia a abertura do Domain Blueprint.

---

## 11. Recomendação GO/NO-GO para o Domain Blueprint

**GO.** A questão arquitetural central exigida pelo Founder — fontes primárias vs. composição de resultados de outros Advisors — foi resolvida com fundamentação em uma restrição já permanente do `AdvisorFramework` (Fase 3, "nunca delegação de um Advisor para outro"), não uma preferência nova: o PMO Advisor consome exclusivamente `AnalysisRecord` via `AIContextEngine.gather()`, mesma fonte primária já usada por Delivery/Portfolio Advisor, apenas com uma leitura de domínio adicional sobre o timestamp já existente (`created_at`) para detectar ausência de atualização. Nenhuma infraestrutura nova é esperada — o padrão de composição Classe B já provado pelo Portfolio Advisor se aplica, com escopo organizacional em vez de um único portfólio. Os pontos em aberto (segundo `kind`, limiar de atualização, avaliação de generalização do componente de composição) são decisões de domínio reservadas ao Domain Blueprint, não lacunas arquiteturais.

Per instrução do Founder: nenhuma implementação iniciada; retorno obrigatório para Executive Review antes de prosseguir ao Domain Blueprint (etapa 2).
