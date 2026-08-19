# Advisor Specification — Executive Advisor

**Etapa 1 de 6** do ciclo institucional do Executive Advisor (sétimo Advisor da Wave 5). Produzida sob autorização da Founder Decision "Abertura do ciclo institucional do Executive Advisor", que segue a Founder Decision anterior — "PMO Advisor" (D-118) — que encerrou oficialmente o PMO Advisor, registrou `PMOEvidenceAssembler` como o segundo padrão consolidado Classe B, e encerrou a validação do padrão Classe B em si (próximos Advisors dessa classe reutilizam o padrão sem nova validação arquitetural). Missão exclusivamente documental — nenhum código escrito, nenhum Technical Design, nenhuma implementação, nenhuma mudança arquitetural proposta.

---

## 0. Base institucional já permanente, não redecidida aqui

Antes de definir a identidade do Executive Advisor, é necessário registrar o que já é fato de código e decisão permanente, porque toda a Specification se apoia nisso:

- **Classificação já registrada em AR-8 §4 (D-085), nunca decidida nesta Specification**: a tabela oficial de classificação dos 7 Enterprise Advisors já lista o Executive Advisor na **Classe B — Analysis-Record Intelligence (agregada)**, ao lado de PMO Advisor e Portfolio Advisor, com a nota explícita "`AnalysisRecord`, múltiplos projetos **e/ou múltiplos `kind`**". Este documento não inventa a classificação — apenas a confirma e a aplica.
- **Restrição permanente de "nunca delegação entre Advisors"** (`framework.py`, Fase 3, já citada para fundamentar a Advisor Specification do PMO Advisor): `AdvisorFramework.run()` executa exatamente um Advisor por chamada, nunca compõe a saída de um Advisor a partir da saída de outro.
- **Padrão Classe B consolidado (D-118)**: dois componentes de composição já existem e coexistem — `PortfolioEvidenceAssembler` (um `Evidence` por Project, escopo de um Portfolio) e `PMOEvidenceAssembler` (histórico limitado por Project, escopo organizacional, único `kind="status"`). Nenhum dos dois é generalizado automaticamente para o Executive Advisor — o gatilho de generalização (terceiro consumidor estruturalmente equivalente) só se aplica se a composição do Executive Advisor for **idêntica** a um dos dois já existentes, o que — adiantando a conclusão da §3 — não é o caso.

---

## 1. Identidade do Executive Advisor

### 1.1 Problema executivo que resolve

Hoje, um executivo (C-level, sponsor, board) que precisa entender "como está a organização agora, sob a ótica que importa para uma decisão de alta gestão" precisa navegar múltiplas superfícies isoladas — o Executive Dashboard (V1, `web/app/dashboard/page.tsx`), o Decision Center (`web/lib/decision-center/decision-queue.ts`), e, se quisesse uma leitura em linguagem natural, teria que perguntar individualmente ao Risk Advisor sobre um projeto, ao Portfolio Advisor sobre um portfólio, ou ao PMO Advisor sobre conformidade de processo — nenhum deles produz uma síntese única que atravesse execução, risco e processo ao mesmo tempo, na altitude de uma decisão executiva.

O Executive Advisor resolve exatamente essa lacuna: uma síntese executiva única, em linguagem natural, rastreável a evidência primária real, que responde "o que a liderança sênior precisa saber agora, e onde precisa decidir" — sem recalcular nada que os Advisors operacionais/táticos já não tenham como evidência bruta disponível.

### 1.2 Decisão executiva que apoia

Não uma decisão específica de projeto (isso é o Delivery Advisor), nem de composição de portfólio (Portfolio Advisor), nem de conformidade de processo (PMO Advisor) — o Executive Advisor apoia a decisão **de para onde a atenção executiva deve ir**: quais sinais, hoje espalhados por dados primários reais, justificam uma intervenção, uma pergunta ao time responsável, ou uma escalada — nunca a decisão final em si (mesmo limite permanente de todo Enterprise Advisor: evidencia, nunca decide).

### 1.3 Valor entregue à alta gestão

Redução do custo de síntese: em vez de a liderança (ou alguém em seu nome) agregar manualmente sinais de múltiplos projetos/portfólios/riscos para formar um quadro executivo, o Executive Advisor entrega essa síntese pronta, sempre rastreável, nunca inventada — mesma disciplina de citação já provada em produção pelos 6 Advisors anteriores.

### 1.4 Por que ele não duplica nenhum Advisor já existente

| Advisor existente | O que já resolve | Por que o Executive Advisor não duplica |
|---|---|---|
| **Risk Advisor** | Narrativa de risco de **um projeto/portfólio específico**, recomendação de mitigação | Executive Advisor nunca narra um projeto isolado — sintetiza o **padrão de risco na organização** (concentração, não detalhe de mitigação) |
| **Document Advisor** | Perguntas ad-hoc sobre **documentos institucionais genéricos** já ingeridos | Executive Advisor não faz Q&A documental — não é uma interface de busca |
| **Governance Advisor** | Conformidade da **própria governança da STRATECH** (Decision Log, Technical Debt Register) contra um estado declarado | Executive Advisor não classifica conformidade de governança — se algum sinal de governança entrar em sua síntese, é um achado a resolver explicitamente no Domain Blueprint (§8), nunca presumido aqui |
| **Delivery Advisor** | Trajetória temporal de **um único projeto** (melhora/deterioração) | Executive Advisor nunca narra a trajetória de um projeto isolado |
| **Portfolio Advisor** | Composição/equilíbrio de **um portfólio específico**, snapshot atual por projeto | Executive Advisor não avalia balanceamento de um portfólio específico — opera na organização como um todo, através de múltiplos `kind`s de evidência, não apenas `kind="status"` |
| **PMO Advisor** | Conformidade de processo (staleness, padrões recorrentes) **em toda a organização**, exclusivamente `kind="status"` | Executive Advisor difere em **amplitude de fonte** (múltiplos `kind`s — status **e** risco, no mínimo, per AR-8 §4) e em **altitude da pergunta** (não é "os processos estão em dia?", é "o que precisa da atenção da liderança agora?") |

Nenhum Advisor existente combina múltiplos tipos de evidência primária (`kind`s) para produzir uma síntese de decisão executiva — essa é a lacuna real, confirmada por leitura de código (nenhum dos 6 Advisors chama `gather_context()` com mais de um `kind` distinto), não uma lacuna presumida.

---

## 2. Papel institucional

O Executive Advisor representa a visão executiva da organização. Sua responsabilidade é produzir uma síntese executiva para tomada de decisão da alta gestão, construída **exclusivamente** a partir de evidências primárias da plataforma.

**É expressamente proibido, permanentemente:**
- consumir `Recommendation` de outro Advisor;
- consumir `Explanation` de outro Advisor;
- atuar como orquestrador de Advisors;
- consolidar respostas previamente produzidas por outro Advisor;
- executar regras de negócio;
- interpretar políticas corporativas além da evidência disponível.

Toda conclusão é construída diretamente a partir das evidências primárias disponíveis — mesma disciplina já reafirmada para o PMO Advisor, fundamentada na restrição permanente de `AdvisorFramework.run()` desde a Fase 3 ("nunca delegação de um Advisor para outro"). Este princípio é permanente, não específico desta Epic.

---

## 3. Classificação arquitetural

**Classe B**, confirmada — não decidida nesta etapa, apenas aplicada. AR-8 §4 (D-085) já registra o Executive Advisor na Classe B — "Analysis-Record Intelligence (agregada)" — com a nota "`AnalysisRecord`, múltiplos projetos **e/ou múltiplos `kind`**", distinta explicitamente de PMO/Portfolio (múltiplos projetos, um único `kind`).

Confirmado também pela definição institucional permanente de Classe A/B (D-104, AR-8 §4.2): a fronteira é a **cardinalidade de fontes primárias de evidência** — uma única chamada estrutural (Classe A) vs. duas ou mais (Classe B). O Executive Advisor exige, no mínimo, duas fontes primárias independentes — `AnalysisRecord`/`kind="status"` e `AnalysisRecord`/`kind="risk"` (ver §4) — o que já satisfaz a definição de Classe B por si só, independentemente de quantos projetos ou portfólios estejam envolvidos.

### 3.1 Fontes primárias que participarão da composição (identificação, não implementação)

Confirmadas nesta etapa como participantes: `AnalysisRecord`/`kind="status"` e `AnalysisRecord`/`kind="risk"` (ver §4.1/§4.2). Candidatas identificadas mas **não decididas** nesta etapa (reservadas ao Domain Blueprint, ver §8): `AnalysisRecord`/`kind="meeting"`, Knowledge Platform/RAG. Nenhum mecanismo de composição (nome de componente, assinatura, local no código) é decidido aqui — apenas a lista de fontes candidatas e sua justificativa.

---

## 4. Fontes primárias de evidência (reais, hoje, no código)

| Fonte | Onde existe hoje | Justificativa para o Executive Advisor |
|---|---|---|
| **`AnalysisRecord`/`kind="status"`** | `AIContextEngine.gather(organization_id, project_name, "status")`, já usado por Delivery/Portfolio/PMO Advisor | Estado de execução é o primeiro insumo de qualquer síntese executiva — sem ele não há como falar de "saúde da execução" |
| **`AnalysisRecord`/`kind="risk"`** | Mesmo `gather()`, já usado pelo Risk Advisor | Sem esta fonte, o Executive Advisor não poderia falar de "principais riscos executivos" com evidência real — teria que inventar ou pedir emprestado ao Risk Advisor, ambos proibidos |
| **`AnalysisRecord`/`kind="meeting"`** (candidata, não decidida) | Já existe (`meeting_intelligence`), já consumido estruturalmente por `ProjectSummaryService.list_action_items()` | Poderia sustentar "capacidade de entrega" (itens de ação pendentes) — mas o mesmo problema já identificado na Advisor Specification do PMO Advisor permanece: o schema de `action_items` não tem campo de conclusão, então seu valor real como evidência executiva não está confirmado; decisão explicitamente reservada ao Domain Blueprint |
| **Knowledge Platform / RAG** (candidata, não decidida) | `KnowledgeRepository`/`RagPipeline`, já usado por Document/Governance Advisor (Classe D) | O catálogo (`ENTERPRISE-ADVISOR-CATALOG.md` §2) já registra RAG como "opcional, não obrigatório" para este Advisor; se algum sinal de governança precisar entrar na síntese executiva, usar RAG diretamente (nunca a classificação já produzida pelo Governance Advisor) seria a única forma compatível com §2 — mas o risco real de sobreposição de altitude com Document/Governance Advisor exige análise própria, não decidida aqui (ver §8) |
| **`DomainService` (Portfolio/Program/Project)** | Já usado por Portfolio/PMO Advisor para **resolver o escopo** (quais Projects existem), nunca como conteúdo citado | Papel permanece o mesmo aqui: resolução de escopo (quantos Portfolios/Programs/Projects existem na organização), nunca evidência citável em si — a mesma distinção já estabelecida para PMO Advisor entre "infraestrutura de escopo" e "evidência" |

**Nunca**: `Recommendation`, `Explanation`, resposta de outro Advisor — confirmado, nenhuma dessas três aparece na tabela acima, porque nenhuma é uma fonte primária real.

---

## 5. Escopo de atuação

O Executive Advisor deverá responder perguntas executivas como (exemplos que caracterizam o domínio, não uma lista de funcionalidades a implementar):

- situação geral da organização;
- saúde da execução;
- principais riscos executivos;
- capacidade de entrega;
- tendências organizacionais;
- equilíbrio entre execução, governança e risco;
- pontos que exigem decisão da alta gestão.

Cada uma dessas perguntas, quando respondida, deve permanecer rastreável a `AnalysisRecord`s reais (e, se aplicável após decisão do Domain Blueprint, a chunks de RAG) — nunca a uma métrica inventada, nunca a uma extrapolação sem evidência de múltiplos registros reais (mesmo critério já aplicado a PMO/Portfolio Advisor).

---

## 6. Relação com os demais Advisors

| Advisor | Visão | Altitude | Como o Executive Advisor complementa, sem sobrepor |
|---|---|---|---|
| **Risk Advisor** | Um projeto/portfólio | Operacional/tático | Executive Advisor não narra o risco de um projeto — observa o **padrão** de risco através de múltiplos `AnalysisRecord`s de `kind="risk"`, na organização inteira |
| **Document Advisor** | Um documento por vez, sob demanda | Consulta pontual | Executive Advisor não responde perguntas documentais — nunca substitui a função de busca |
| **Governance Advisor** | Conformidade da própria governança STRATECH | Meta-institucional | Executive Advisor não avalia essa conformidade — se um sinal de governança aparecer em sua síntese (aberto, §8), seria sobre a organização cliente, nunca sobre a governança da própria plataforma |
| **Delivery Advisor** | Um projeto | Operacional | Executive Advisor nunca narra um projeto isoladamente |
| **Portfolio Advisor** | Um portfólio | Tático | Executive Advisor não avalia composição/equilíbrio de um portfólio específico |
| **PMO Advisor** | Toda a organização, processo (staleness, padrões), único `kind="status"` | Operacional-organizacional | Executive Advisor difere em amplitude (múltiplos `kind`s) e em altitude (decisão executiva, não conformidade de processo) |

**Separação explícita de altitude:**
- **Visão operacional** — Delivery Advisor (um projeto), Risk Advisor (um projeto/portfólio), Document Advisor (um documento) — o "chão" da execução.
- **Visão tática** — Portfolio Advisor (um portfólio) — composição e equilíbrio de um conjunto delimitado.
- **Visão executiva** — PMO Advisor (organização, processo) e Executive Advisor (organização, decisão) — a diferença entre os dois últimos não é o escopo organizacional (ambos são), é a **pergunta**: PMO Advisor pergunta "os processos estão em dia?"; Executive Advisor pergunta "o que precisa da atenção da liderança agora, através de execução, risco e (se decidido) governança combinados?".

Nenhuma sobreposição de responsabilidade — cada Advisor responde a uma pergunta estruturalmente diferente, mesmo quando consome a mesma fonte bruta (`kind="status"`), assim como Delivery/Portfolio/PMO já convivem hoje sem sobreposição consumindo o mesmo `kind`.

---

## 7. Limites de atuação

### 7.1 Limites permanentes de todo Enterprise Advisor (reafirmados, não específicos desta Epic)

- Nunca decide — apenas recomenda/evidencia, para quem decide.
- Nunca escreve no domínio (sem `create`/`update`/`delete` em nenhuma entidade).
- Sempre escopado por `organization_id` da sessão autenticada — nunca um parâmetro cross-tenant.
- Portão anti-alucinação (`RecommendationEngine.build()`/`no_evidence()`) — nenhuma citação sem `Evidence` real por trás.
- Nunca invocado por Workflow Runtime nem registrado como handler de Event Pipeline.
- `AdvisorFramework.run()` executa exatamente um Advisor por chamada — nunca delegação entre Advisors (§2).

### 7.2 Limites específicos do Executive Advisor

- Nunca substitui o Executive Dashboard já existente (V1, `web/app/dashboard/page.tsx`) nem o Decision Center (`web/lib/decision-center/decision-queue.ts`) — consome fontes primárias equivalentes, apresenta em linguagem natural, nunca inventa uma métrica que essas superfícies não exibem estruturalmente.
- Nunca avalia um único projeto/portfólio isoladamente com a profundidade de um Delivery/Risk/Portfolio Advisor — sua unidade de síntese é sempre a organização.
- Nunca classifica conformidade de governança (isso permanece exclusivo do Governance Advisor) — se vier a citar um sinal relacionado a governança, é sobre dados primários da organização cliente, nunca sobre a própria governança institucional da STRATECH.
- Nunca compõe sua resposta a partir de `ProjectSummaryService`/`Recommendation`/`Explanation` de forma que oculte a origem primária real da evidência (se `ProjectSummaryService` vier a ser reaproveitado — decisão aberta, §8 — a rastreabilidade até o `AnalysisRecord` de origem permanece obrigatória, mesma disciplina já provada em Portfolio/PMO Advisor).

---

## 8. Questões arquiteturais abertas (reservadas ao Domain Blueprint, não decididas aqui)

1. **Conjunto definitivo de `kind`s** — `kind="status"` e `kind="risk"` estão confirmados como fontes; `kind="meeting"` permanece candidato não decidido (mesmo achado já registrado na Specification do PMO Advisor, ainda sem uma necessidade real comprovada).
2. **Participação de RAG/Knowledge Platform** — se e como o Executive Advisor consultaria documentos institucionais sem sobrepor Document/Governance Advisor; não presumido nem a favor nem contra.
3. **Reaproveitamento de `ProjectSummaryService` vs. novo componente de composição** — `ProjectSummaryService` já agrega estruturalmente `open_risks`/`pending_action_items`/`latest_health_status` a partir de `AnalysisRecord`s reais (nunca de `Recommendation`/`Explanation`); avaliar se reaproveitá-lo evita duplicação de lógica de agregação já existente, ou se um componente próprio (mesmo padrão de `PortfolioEvidenceAssembler`/`PMOEvidenceAssembler`) é mais correto — decisão de composição, não de arquitetura de evidência.
4. **Escopo de resolução** — sempre organizacional (como PMO Advisor), ou também aceitar um escopo de Portfolio específico (como Portfolio Advisor) para relatórios executivos direcionados a uma iniciativa? Não presumido.
5. **Controle de volume** — com dois ou mais `kind`s multiplicando o número de chamadas `gather_context()` por projeto na organização inteira, o gatilho de performance já aprovado (20+ chamadas sequenciais ou p95 > 3s) provavelmente será atingido mais cedo que em PMO Advisor; avaliação reservada, nenhuma otimização antecipada aqui.
6. **Necessidade real de `gather_context_many()`** — AR-8 §3 já registrou esta possibilidade como extensão futura do `AdvisorFramework`/`AIContextEngine`, condicionada a "um Advisor real da Classe B demonstrar essa necessidade" — o Executive Advisor, sendo o primeiro Classe B a combinar múltiplos `kind`s (não apenas múltiplos projetos do mesmo `kind`), é o primeiro candidato genuíno a essa avaliação; **não decidido nesta etapa**, e mesmo se necessário seria uma extensão aditiva ao Framework, nunca uma reescrita.

Nenhuma dessas seis questões é resolvida aqui — cada uma exige leitura de código adicional e ponderação própria, própria do Domain Blueprint.

---

## 9. Critérios de sucesso

- Toda afirmação executiva é rastreável a um `AnalysisRecord` real (e, se decidido, a um chunk de RAG real) — nenhuma métrica inventada.
- Nenhuma citação de `Recommendation`/`Explanation`/resposta de outro Advisor como evidência, em nenhuma circunstância.
- Nenhuma generalização de padrão organizacional sem evidência de múltiplos registros reais, através de múltiplos `kind`s quando aplicável.
- Cobertura (quantos projetos/portfólios têm evidência de cada fonte usada) sempre estrutural, nunca calculada pelo LLM — mesmo padrão já provado em Portfolio/PMO Advisor.
- Nenhuma chamada ao LLM quando não há evidência primária suficiente para sintetizar (mesmo portão anti-alucinação).
- Nenhuma mudança de assinatura ou comportamento em `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline exigida por esta Specification.

---

## 10. Riscos

### 10.1 Comprovados (fato de código, confirmado nesta etapa)

- `AIContextEngine.gather()` aceita exatamente um `kind` por chamada — combinar `status` + `risk` (e possivelmente outros) exige múltiplas chamadas independentes, exatamente como Portfolio/PMO Advisor já fazem para múltiplos projetos do mesmo `kind`. Nenhuma mudança de Framework é necessária para isso funcionar hoje.
- Volume de chamadas cresce multiplicativamente (número de `kind`s × número de projetos da organização) — mais alto que o já registrado para PMO Advisor.

### 10.2 Hipóteses (plausíveis, não confirmadas — a resolver no Domain Blueprint)

- Inclusão de RAG poderia criar sobreposição de altitude com Document/Governance Advisor — hipótese registrada, não assumida como verdadeira nem falsa.
- Reaproveitar `ProjectSummaryService` pode ser mais correto que construir um novo componente de composição — ou pode não ser, dependendo de como sua agregação atual (dedupe por projeto, contagens) se encaixa ou não com a necessidade de citação por `AnalysisRecord` individual que a disciplina de rastreabilidade desta Epic exige (mesmo padrão do PMO Advisor).

### 10.3 Riscos futuros (fora do escopo desta Epic, registrados por transparência)

- A Wave 6 — Executive Intelligence (`WAVE-3-INTEGRATION-BLUEPRINT.md` §5/§11, já destacada formalmente em D-071) consumirá os 8 Enterprise Advisors, incluindo o Executive Advisor — a classificação e os limites definidos aqui devem permanecer estáveis o suficiente para servirem de insumo a essa Wave futura, mas nenhuma decisão da Wave 6 é antecipada ou presumida nesta Specification.

---

## 11. Visão arquitetural — posicionamento do Executive Advisor

A progressão arquitetural já consolidada pelos Advisors anteriores desta Wave:

```
Delivery Advisor   → visão do projeto           (Classe A, kind="status", um projeto)
Portfolio Advisor  → visão do portfólio          (Classe B, kind="status", evidence[0] por Project, um Portfolio)
PMO Advisor        → visão operacional da org.   (Classe B, kind="status", histórico limitado por Project, toda a organização)
Executive Advisor  → visão executiva para decisão (Classe B, múltiplos kind, toda a organização)
```

Cada degrau amplia o escopo (projeto → portfólio → organização) e/ou a amplitude de fonte (um `kind` → múltiplos `kind`s), **nunca** trocando evidência primária por interpretação de outro Advisor. O Executive Advisor é o primeiro a ampliar ambas as dimensões simultaneamente (organização inteira **e** múltiplos `kind`s) — por isso é Classe B como PMO/Portfolio, mas estruturalmente mais amplo que os dois, exatamente como AR-8 §4 já havia previsto ao registrar "múltiplos projetos **e/ou** múltiplos `kind`" como a definição da própria Classe B.

Esta evolução é construída inteiramente sobre evidências primárias (`AnalysisRecord`s reais, possivelmente RAG se decidido), nunca sobre interpretações já produzidas por outro Advisor — o mesmo princípio permanente que distingue toda a Wave 5 de um simples "chatbot que resume outros chatbots".

---

## 12. Regras permanentes — confirmação de aderência

Esta Specification usa exclusivamente arquitetura, código e componentes reais já citados (§0, §4, §6, §11) — nenhuma abstração nova proposta, nenhuma mudança a `AdvisorFramework`/`AIContextEngine`/Workflow Runtime/Event Pipeline/`RecommendationEngine`/`ExplanationEngine`, nenhuma infraestrutura nova criada, nenhuma generalização de componente existente. As únicas menções a extensões futuras possíveis (`gather_context_many()`, §8.6) são citações do que a própria AR-8 já havia registrado como possibilidade condicional — não uma proposta desta Specification.

---

## 13. Recomendação

**GO para o Domain Blueprint.**

Identidade, classificação (Classe B, confirmada via AR-8/D-104), domínio de responsabilidade, fontes primárias candidatas e confirmadas, limites, relação com os 6 Advisors existentes, e riscos residuais estão todos definidos. Seis questões arquiteturais permanecem explicitamente reservadas ao Domain Blueprint (§8), nenhuma decidida ou presumida nesta etapa.

Retorno obrigatório para Executive Review do Founder. Nenhum trabalho da Etapa 2 (Domain Blueprint) será iniciado sem nova aprovação explícita.
