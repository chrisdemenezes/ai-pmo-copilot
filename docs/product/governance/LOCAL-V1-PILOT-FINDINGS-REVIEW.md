# Local V1 Pilot Findings Review — Triagem Executiva

- **Missão:** FOUNDER DECISION — LOCAL V1 PILOT FINDINGS REVIEW (Triagem Executiva da Primeira Validação Humana)
- **Data:** 2026-08-20
- **Natureza:** Product Review + Findings Triage + Decision Proposal. **Nenhuma implementação foi feita nesta missão.**
- **Fonte primária:** `docs/product/governance/LOCAL-V1-HUMAN-USER-SESSION-EVIDENCE.md` (D-216)

## 1. Executive Summary

Esta missão triou os 10 achados/áreas da primeira sessão humana (D-216) contra o comportamento real do código, a Product Constitution e os blueprints arquiteturais existentes — não apenas contra a interpretação inicial dada durante a própria sessão. O resultado corrige uma classificação: a **atribuição de papéis a usuários já existe no produto** (`UserRolesDialog`, testada em E2E) — o usuário não a encontrou, não é um Product Gap real. A **criação de novas Organizações**, por outro lado, é confirmada como um gap real: já aprovada institucionalmente (`DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md`), nunca implementada. A Priorização (Task 2, FAIL) tem causa raiz identificada com precisão: o mecanismo de ranking é real e determinístico (`buildExecutivePortfolioView`), mas totalmente invisível na UI — nenhum cabeçalho de camada, nenhuma explicação da regra. O delta mínimo de correção é pequeno (composição de UI, sem mudança de backend). **Nenhum P0 (bloqueador literal de Session #2) foi identificado** — o ambiente já foi corrigido pelo próprio Founder. Dois itens compõem o **Controlled Pilot Gate**: comunicar a regra de Priorização, e distinguir visualmente os widgets mock/demo do Dashboard antes de expor a usuários externos reais.

## 2. Session Evidence Reviewed

- `docs/product/governance/LOCAL-V1-HUMAN-USER-SESSION-EVIDENCE.md` (D-216) — integral.
- `docs/product/governance/LOCAL-V1-USER-SESSION-PROTOCOL.md` — fronteira de IA e metodologia.
- `docs/product/governance/LOCAL-V1-WINDOWS-REVALIDATION-EXECUTIVE-EVIDENCE.md`, `LOCAL-V1-PILOT-MAIN-INTEGRATION-EXECUTIVE-EVIDENCE.md` — estado técnico validado.
- Decision Log D-200 até D-216.
- `docs/product/stratech-constitution/STRATECH-Product-Constitution.html` — Product Philosophy, os 10 Princípios Permanentes, Executive Frameworks.
- Código real: `web/app/portfolio/`, `web/app/dashboard/`, `web/app/projects/`, `web/app/program-management/`, `web/app/project-delivery/`, `web/app/administracao/`, `web/app/actions/`, `web/app/decisions/`, `web/app/aprendizados/`, `src/database/models.py`, `src/api/routes/administration.py`, `src/services/executive_orchestrator/catalog.py`, `web/lib/*`, `web/components/shell/navigation.ts`, `web/app/globals.css`, `docs/architecture/DOMAIN-MODEL.md`, `docs/architecture/DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md`, `docs/product/rfc-001/RFC-001-frontend-architecture.html`.

**Nota metodológica importante:** a Product Constitution lida (`STRATECH-Product-Constitution.html`, 2026-07-16) antecede o pivô Enterprise/V2 (Waves 3-7) — sua tabela das "8 Capabilities" (Decision Center, Portfolio Intelligence, Action Intelligence, Organizational Intelligence etc.) não corresponde 1:1 à navegação real de hoje (Priorização, Projetos, Program Management, Project Delivery, Ações, Decisões, Aprendizados, Administração). Essa tabela está **superada**. Seus **princípios** (guardrail de não substituir o julgamento do PM/PMO, Princípio da Atenção, Transparent Prioritization, System Integrity, Silent Intelligence, regra de entrada na navegação) permanecem a referência institucional mais próxima disponível e foram aplicados por extensão nesta triagem — não por mapeamento literal de nomes de tela.

## 3. Value Validation

1. **A proposta de valor foi compreendida?** SIM — o usuário descreveu a STRATECH, com suas próprias palavras, como "um assessor, um analista de projetos... vai operar o escritório de projetos e trazer insights importantes pra tomada de decisão" — muito próximo do posicionamento pretendido (Executive Decision Operating System). A hierarquia Portfolio→Program→Project foi inferida corretamente sem qualquer explicação.
2. **O posicionamento atual funcionou?** Majoritariamente sim — Ações, Logout e o conceito de Aprendizados (conectado espontaneamente a alimentar IA) geraram percepção de valor forte.
3. **Há risco de a plataforma ser percebida apenas como PM tool?** Risco moderado e real — os pedidos de board/Kanban e de maior granularidade em Project Delivery puxam nessa direção. Isso contraria diretamente o guardrail fundacional da Constitution ("não decide, não prioriza, não é fonte de verdade sobre o que realmente aconteceu no projeto") e deve ser resistido deliberadamente nesta triagem (ver Seções 9 e 11).
4. **Capabilities que sustentaram maior valor:** Ações (PASS limpo), hierarquia Portfolio/Program/Project (compreendida sem ajuda), Aprendizados (conexão espontânea com IA), Logout (confiança/polimento).
5. **Capabilities que prejudicaram a percepção:** Priorização (FAIL — mina diretamente a promessa central "ajudar a decidir onde focar"), Dashboard ("poluído" — mina o posicionamento executivo/curado), Administração (gaps percebidos, parcialmente reais).

**PRODUCT VALUE PROPOSITION: PARTIALLY VALIDATED.** O modelo mental central foi corretamente absorvido pelo usuário; a tela mais central para entregar essa promessa (Priorização) falhou em comunicá-la visivelmente — esse é o achado de maior consequência para o posicionamento do produto.

## 4. Findings Inventory

| ID | Fonte | Categoria inicial (sessão) | Categoria confirmada (triagem) |
|---|---|---|---|
| F01 | Task 2 | HIGH / TASK BLOCKED | Confirmado — causa raiz identificada, delta pequeno |
| F02a | Task 1 | MEDIUM (densidade) | Confirmado — 13 seções, 4 explicitamente mock |
| F02b | Task 1 | MEDIUM (financeiro) | Reclassificado — exige nova modelagem de dados, decisão arquitetural |
| F02c | Task 1 | MEDIUM (prazo) | Reclassificado — dado já existe, delta pequeno |
| F03 | Task 3 | MEDIUM (navegação) | Confirmado — hierarquia real não refletida na nav |
| F04a | Task 9 (papéis) | Product Gap | **Corrigido — NÃO é gap, UI já existe (discoverability)** |
| F04b | Task 9 (organizações) | Product Gap | Confirmado — aprovado institucionalmente, nunca implementado |
| F05 | Task 4 | MEDIUM | Reclassificado — provável gap de cross-link para Workspace, não de granularidade nova |
| F06 | Task 8 ("chunks") | LOW | Confirmado — jargão técnico interno vazando para UI |
| F07 | Task 8 ("Ações") | LOW | Confirmado — coluna vazia na maioria dos casos |
| F08 | Task 7 (Aprendizados) | LOW | Confirmado — conceito correto, síntese ausente por escopo V1 deliberado; NÃO alimenta IA hoje (aspiracional) |
| F09 | Seção 18 | Feature Request | Confirmado — realocação de baixo custo |
| F10 | Tasks 5/6 | Feature Request (recorrente 3x) | **Rejeitado para Ações; cosmético para Decisões; evidência insuficiente para Priorização** |
| F11 | Seção 19 | Feature Request | Confirmado, mas parcialmente já especificado (RFC-001) e não implementado |
| F12 | Task 8 | Feature Request | Confirmado — requer decisão arquitetural |
| F13 | Task 2 | Business Insight | Transformado em proposta de pesquisa escopada, não executada |

## 5. Prioritization Analysis (Finding 01)

**ROOT CAUSE:** o item de menu "Priorização" (`web/components/shell/navigation.ts:18`) aponta para `/portfolio`, cujo `h1` diz "Portfólio" — nunca "Priorização" ou "prioridade" em nenhum lugar da própria tela. A página renderiza uma lista vertical plana de cards, um por projeto, sem cabeçalhos de seção, sem legenda, sem explicação da regra de ordenação em nenhum ponto do DOM.

Existe, porém, uma regra real e determinística de 4 camadas (`web/lib/portfolio-intelligence/portfolio-view.ts:79-146`, `buildExecutivePortfolioView`): `decision_today` → `decision_this_week` → `risk_to_monitor` → `no_signal`, com critério de risco reaproveitado do Dashboard. Cada card já carrega um rótulo `whyAttention` (ex. "Decisão pendente hoje") — mas nada na página comunica o **sistema** de camadas como um todo.

Isso é exatamente o que a própria Constitution nomeia como o princípio **Transparent Prioritization**: "cada camada é a justificativa" — a regra existe, mas não é comunicada.

**Respostas às 10 perguntas do mandato:**
1. Propósito visível? Não — o h1 diz "Portfólio", não "Priorização".
2. Usuário identifica "o que priorizar"? Não, confirmado pelo FAIL real.
3. Existe indicação explícita do porquê um item está acima do outro? Existe por card (`whyAttention`), não como sistema.
4. Ranking, status, score, ou só dados? Ranking real (4 camadas), apresentado como dados planos.
5. Existe ação/decisão esperada? Implícita (abrir o projeto), nunca explicitada.
6. O nome "Priorização" corresponde ao comportamento? Parcialmente — a função existe, o nome/rótulo da tela não a reflete.
7. O problema está em: informação (não), layout (parcialmente), terminologia (sim — h1 errado), visualização (sim — sem agrupamento), modelo conceitual (não — o modelo é correto), ausência de explicação (sim, principal causa) — **combinação, com peso maior em terminologia + ausência de explicação**.
8. Lista é o formato adequado? Sim, com agrupamento por camada.
9. Board/Kanban resolveria? Não — seria reformatação cosmética do mesmo dado, sem resolver a causa raiz (a regra continuaria invisível).
10. Existe delta menor? Sim.

**MINIMUM PRODUCT DELTA:** (a) cabeçalhos de seção visíveis por camada ("Hoje", "Esta semana", "Risco a monitorar", "Sem sinal"); (b) uma linha explicativa da regra de ordenação; (c) reforçar `whyAttention` estruturalmente, não apenas por card. Nenhuma mudança de backend/dado — `portfolio-view.ts` já computa tudo que é necessário.

**ALTERNATIVES:** redesenho completo em board/Kanban — rejeitado (Seção 11). Renomear a rota/h1 para "Priorização" — complementar, de baixíssimo custo.

**TEST REQUIRED:** E2E atualizado (`web/e2e/portfolio.spec.ts`) afirmando visibilidade dos cabeçalhos de camada e do texto explicativo; revalidação humana (Session #2, Seção 20).

**PILOT IMPACT:** ALTO — esta foi a única tarefa que falhou (FAIL) na sessão real, numa tela central para a proposta de valor do produto.

## 6. Dashboard Analysis (Finding 02)

Tratado como 3 achados distintos, conforme mandato.

### A. Densidade / poluição visual
- **CURRENT STATE:** ~13 seções (`web/app/dashboard/page.tsx:105-273`), incluindo 4 explicitamente rotuladas "demonstração — dados simulados" (`WorkItemsOverview`, `DecisionCenterPanel`, `ActionsCenterTable`, `AIRecommendationsPanel`) sem nenhuma distinção visual das seções reais.
- **USER EXPECTATION:** visão executiva curada, não uma pilha extensa.
- **PRODUCT STRATEGY FIT:** contraria o Princípio da Atenção ("a plataforma não deve preencher a interface") ao misturar 4 painéis de dado simulado sem distinção visual.
- **PILOT NECESSITY:** alta — widgets rotulados "dados simulados" apresentados a um usuário externo real do piloto controlado passam credibilidade errada.
- **ENTERPRISE VALUE:** baixo como está hoje.
- **IMPLEMENTATION COMPLEXITY:** S.
- **ARCHITECTURAL IMPACT:** NONE.
- **DEPENDENCY ON DATA MODEL:** nenhuma.

### B. Financial Indicators
- **CURRENT STATE:** nenhum campo de custo/orçamento existe em `src/database/models.py` (busca completa, zero ocorrências reais de domínio).
- **USER EXPECTATION:** previsto vs. realizado, desvio de custo.
- **PRODUCT STRATEGY FIT:** incerto — exige avaliar se rastrear dado financeiro é uma expansão de domínio compatível com o guardrail "não é fonte de verdade sobre o que realmente aconteceu no projeto".
- **PILOT NECESSITY:** baixa — o piloto usa dado sintético, sem expectativa de dado financeiro real.
- **ENTERPRISE VALUE:** potencialmente alto a longo prazo.
- **IMPLEMENTATION COMPLEXITY:** L/XL.
- **ARCHITECTURAL IMPACT:** ALTO — exige novo modelo de dados/migration.
- **DEPENDENCY ON DATA MODEL:** SIM, bloqueante.
- **Não adicionar indicador fictício.** Classificado explicitamente como item que **exige decisão arquitetural** (Seção 9 do mandato) — não aprovado por esta triagem.

### C. Schedule Variance / Traffic Light
- **CURRENT STATE:** `start_date`, `planned_end_date`, `actual_end_date` já existem em Portfolio/Program/Project (`src/database/models.py:147-149,183-185,232-234`) — nenhuma migration necessária.
- **USER EXPECTATION:** saber se um item está atrasado ou no prazo.
- **PRODUCT STRATEGY FIT:** bom — endereça diretamente "não consegui visualizar se estão em atraso" (Task 1), usando dado real, sem fabricação.
- **PILOT NECESSITY:** alta.
- **ENTERPRISE VALUE:** alto.
- **IMPLEMENTATION COMPLEXITY:** S/M — indicador derivado, mesmo padrão já usado para `UrgencyBucket`/`ExecutiveFocus`.
- **ARCHITECTURAL IMPACT:** BAIXO.
- **DEPENDENCY ON DATA MODEL:** nenhuma — dado já existe.

## 7. Information Architecture (Finding 03)

`web/components/shell/navigation.ts:14-61`: Projetos (`/projects`), Program Management (`/program-management`), Project Delivery (`/project-delivery`) — 3 itens irmãos, planos, sem relação visual.

**Respostas:**
1. Destinos realmente distintos? Sim, com sobreposição real de entidade (Project Delivery e Projetos listam os mesmos Projects, em formatos diferentes).
2. O que cada um mostra: Projetos = diretório plano pesquisável de todos os projetos; Program Management = Programas agrupados por Portfólio pai; Project Delivery = Projetos agrupados por Programa pai.
3. Nomenclatura adequada? Os nomes técnicos (`Program Management`, `Project Delivery`) mapeiam 1:1 à cadeia de domínio real (`DOMAIN-MODEL.md:12-14`: Portfolio→Program→Project), mas a navegação não expõe essa relação.
4. A arquitetura reflete o domínio? Sim, no backend; não, na apresentação da navegação — os 3 itens são irmãos sem indicação de hierarquia.
5. Deveria haver agrupamento de navegação? Sim.
6. Existe conceito superior possível ("Execução")? Sim, plausível — os 3 já compartilham a mesma camada de domínio/hooks.
7. Exige mudança arquitetural ou só IA? **Apenas Information Architecture** — as 3 páginas já consomem a mesma camada de domínio; a mudança necessária é em `NAV_ITEMS`/`Sidebar`, que hoje não suporta agrupamento aninhado (precisaria de um pequeno reforço de componente, não um refactor de domínio/backend).

**Confirmado:** esta fragmentação foi uma decisão deliberada de entrega incremental ("Controlled Pilot Browser Baseline"), não um descuido — mas isso não significa que deva permanecer definitiva.

## 8. Organization Administration (Finding 04)

**Correção importante desta triagem:** o achado original da sessão combinava dois problemas distintos que, investigados, têm naturezas completamente diferentes.

### 8a. Atribuição de papéis — NÃO é um Product Gap
A UI já existe: `UserRolesDialog` (`web/app/administracao/usuarios/user-roles-dialog.tsx:25-59`), acionada por um botão "Papéis" na linha de cada usuário (`web/app/administracao/usuarios/page.tsx:171-173`), com cobertura E2E real (`web/e2e/users-admin.spec.ts:259-281`). O usuário da sessão não a encontrou — um botão pequeno, ao lado de outras ações, é plausivelmente perdido, mas isso é um achado de **discoverability/UX**, não de produto ausente. Reclassificado de "PRODUCT GAP" para "UX finding" — evita transformar um comentário do usuário em requisito indevido.

### 8b. Criação de novas Organizações — Product Gap real, confirmado
- Backend: `src/api/routes/administration.py:172-198` só expõe `GET`/`PATCH /admin/organization`, escopados à organização atual — nenhum `POST` de criação em lugar algum.
- `docs/architecture/DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md:99-102` classifica "Organizações" como **Nível 1 — já aprovado** ("Incluir no Épico 5 como estava aprovado") — mas nenhuma rota `/administracao/organizacoes` foi enviada. Isso é uma lacuna entre escopo aprovado e código entregue, diferente de Workspaces/API Keys/Tenant Settings, que o mesmo documento marca explicitamente "Não implementar"/"Não recomendado agora".
- Provisionamento hoje: exclusivamente via migration Alembic/SQL bruto (`alembic/versions/0002_enterprise_foundation.py`, `0008_domain_seed.py`) — só um desenvolvedor consegue criar uma organização nova.

**Respostas ao framework de 2 cenários do mandato:**
1. O gap bloqueia o produto sendo usado? **Não** — organizações pré-provisionadas funcionam normalmente.
2. Bloqueia apenas self-service onboarding? **Sim.**
3. Existe mecanismo backend/seed confiável para o piloto? **Sim** — migration/script, confiável, mas exclusivo de desenvolvedor.
4. O piloto externo pode operar com tenant pré-provisionado? **Sim.**
5. Riscos: escalar o piloto para várias organizações externas simultâneas exigiria um desenvolvedor a cada nova organização; também impede demonstrar ao vivo um fluxo de "criar organização" a um prospect.
6. Quando passa a ser obrigatório? Quando o piloto precisar de self-service real (múltiplas empresas externas sem envolvimento de engenharia) ou na Enterprise Production.
7. Responsabilidade: bounded context de Platform/Organization Administration, conforme o próprio blueprint já classifica.

**DECISÃO RECOMENDADA:** `BLOCKS SESSION #2 = NO`. `BLOCKS CONTROLLED PILOT = NO` (desde que o piloto opere com tenants pré-provisionados — Cenário A, operacionalmente viável hoje). `BLOCKS ENTERPRISE PRODUCTION = YES`. Classificação: **DEFERRED PRODUCT GAP** (P3).

## 9. Project Delivery (Finding 05)

Achado do usuário: falta de granularidade ao entrar num projeto específico dentro de Project Delivery (análises, riscos, ações não claramente listados em detalhe).

Aplicando o princípio explícito **"STRATECH NÃO é software de tarefas"**: o pedido não deve ser interpretado como "adicionar edição/gestão de tarefas a Project Delivery" — isso contrariaria diretamente o guardrail da Constitution. A hipótese mais provável, dado que `Projetos` já linka cada linha para `/workspace/[projectName]` (que tem abas reais de Riscos/Comunicação/Ações/Briefs, construídas em Waves anteriores), é que **o detalhe que o usuário procurava já existe no Workspace** — o gap real é de **cross-link/descoberta** entre Project Delivery e Workspace, não de funcionalidade ausente.

**Não confirmado com 100% de certeza nesta triagem** (não foi verificado explicitamente se cada linha de Project Delivery já linka para o Workspace correspondente) — **TEST REQUIRED:** confirmar isso antes de qualquer decisão de implementação. Se a confirmação for positiva, o delta é apenas reforçar visualmente esse link existente (badge/preview de riscos ativos, por exemplo) — nunca adicionar gestão de tarefas nova.

## 10. Documents (Findings 06/07)

### "chunks" (F06)
Confirmado jargão técnico interno: `src/database/models.py:411-435` define `Chunk` como unidade de recuperação para RAG/embeddings — nunca documentado como conceito voltado ao usuário. Hoje exposto como coluna "Chunks" com contagem crua (`web/app/administracao/documentos/page.tsx:90,104`). **Requer uma decisão de nomenclatura do Founder** — os termos óbvios (Trechos/Fragmentos/Seções indexadas/Conteúdo processado) são explicitamente não pré-aprovados pelo mandato. Registrado como Decision Proposal (Seção 22), não implementado.

### Coluna "Ações" (F07)
A única ação existente é "Reindexar", renderizada só quando `status !== "indexed"` (`page.tsx:108-110`). Para um documento já indexado (o caso comum, inclusive o testado na sessão), a célula é um `<div>` vazio — lê como quebrado, não como "sem ação necessária". **MINIMUM DELTA:** ocultar a coluna quando nenhum documento tem ação pendente, ou usar um placeholder neutro explícito.

## 11. Learnings (Finding 08)

- **PRODUCT CONCEPT:** correto — o usuário conectou espontaneamente Aprendizados a alimentar as IAs do produto.
- **CURRENT UX:** intencionalmente mínima — `organizational-learnings.ts` agrupa por igualdade textual exata (`MIN_OCCURRENCES=3`), sem clusterização semântica, com comentário explícito no código confirmando que nenhuma síntese é gerada além do template fixo. Isso é **escopo V1 deliberado**, não um defeito.
- **Achado real e novo desta triagem:** hoje, Aprendizados **não alimenta nenhum Advisor/IA real** — busca completa no backend não encontrou nenhuma referência a "organizational_learning" fora do frontend. A expectativa do usuário é **aspiracional, ainda não construída** — vale comunicar essa distinção com precisão em qualquer resposta futura ao Founder ou a usuários (não apresentar como já implementado).
- Separação: **PRODUCT CONCEPT = validado. CURRENT UX = correta para o escopo V1, mas o gap para "alimentar IA" é real e não trivial** (exigiria desenho de integração com AdvisorFramework).

## 12. Executive Intelligence IA (Finding 09)

`DecisionSupportPanel`/`ExecutiveNarrativePanel` embutidos no Dashboard por restrição explícita do Founder à época ("não criar dashboard novo" / "não criar página nova" — comentários no próprio código, `decision-support-panel.tsx:14-19`, `executive-narrative-panel.tsx:16-24`).

**Respostas:**
1. Executive Intelligence merece entrada própria? Sim, dado seu peso na percepção de valor.
2. São a mesma função ou distintas? Mesmo motor (`ExecutiveOrchestrator` + catálogo dos 8 Advisors), modos de interação funcionalmente distintos (Q&A dirigida vs. síntese de escopo completo) — o próprio código afirma explicitamente que "nunca podem parecer aliases da mesma funcionalidade".
3. Um menu dedicado seria coerente? Sim.
4. Melhoraria discoverability? Sim — hoje estão enterrados no meio de 13 seções do Dashboard.
5. Criaria duplicação? Não — é realocação, não duplicação.
6. Relação com os 8 Advisors? Direta — mesmo catálogo, sem necessidade de nova integração.
7. Impacto no posicionamento (Executive Decision Operating System)? Positivo — torna a IA um cidadão de primeira classe e descobrível, reforçando o posicionamento, em vez de escondê-la.

**Custo de implementação:** BAIXO — a camada BFF já é agnóstica de rota (`web/app/api/bff/decision-support/route.ts`, `.../executive-narrative/route.ts` dependem só de sessão, não da rota `/dashboard`); os componentes já são autocontidos. Seria realocação de 2 componentes + 1 rota nova + 1 entrada em `navigation.ts`.

## 13. Board/Kanban Request (Finding 10)

Pedido recorrente (3 ocorrências independentes), depois refinado pelo próprio usuário para "alternância de visualização", não substituição fixa.

| Capability | Estado real | Veredito |
|---|---|---|
| **Ações** | Sem campo de status real; comentário no próprio código: "Nunca um gerenciador de tarefas: nenhum filtro ou view configurável" (`web/app/actions/page.tsx:15-17`). Agrupamento por urgência já existe e é testado. | **CONFLICTS WITH PRODUCT STRATEGY** — um board aqui violaria a diretriz de design já registrada da Capability. |
| **Decisões** | `window` tem só 2-4 combinações, tratado como ordenação, não workflow. | **COSMETIC** — reformatação sem ganho funcional real. |
| **Priorização** | `PortfolioLayer` tem 4 estados discretos reais — o único caso genuinamente "Kanban-plausível". Mas a correção da Seção 5 (cabeçalhos de camada) já resolve a causa raiz com risco/esforço menor. | **NEEDS MORE USER EVIDENCE** — revisitar após o resultado da correção de lista+cabeçalho na Session #2; não implementar board agora. |

**Nenhuma das três recebe HIGH VALUE.** Este é um caso concreto de "não transformar todo comentário do usuário em requisito" — a evidência de código não sustenta a preferência declarada.

## 14. Visual Design (Finding 11)

1. **Tema:** hoje o app segue **somente `prefers-color-scheme` do SO** — não existe alternância manual no app (`web/app/globals.css:10-76`, nenhum `[data-theme]`/toggle encontrado). **Achado importante:** `docs/product/rfc-001/RFC-001-frontend-architecture.html` já **especifica** um `data-theme="dark"/"light"` manual — nunca implementado. Isso significa: a reclamação "muito escuro" pode ser resolvida implementando algo **já projetado e aprovado**, sem nova decisão de design.
2. **Densidade de menu:** 14 itens de nível superior, todos planos, sem agrupamento (`navigation.ts:13-62`). Resolvido pela mesma correção proposta na Seção 7.
3. **Tipografia/paleta:** `RFC-001` documenta contraste WCAG calculado explicitamente (AA/AAA) e `docs/architecture/ARCHITECTURE-BASELINE-RC2.md` exige que o Design System seja "preservado integralmente a cada entrega" — mudanças de tipografia/paleta **não são um ajuste livre de CSS**, exigem Design Review formal.

**CLASSIFICAÇÃO:**
- Toggle manual de tema: `IMMEDIATE PILOT FIX` (já especificado, não implementado, resolve a queixa do usuário diretamente).
- Agrupamento de menu: resolvido junto com a Seção 7 (`DESIGN REVIEW` leve).
- Tipografia/paleta: `DESIGN REVIEW` formal, não decidir aqui.

## 15. External Document Storage + AI (Finding 12)

Pedido: integração com OneDrive/Google Drive/rede interna + IA buscando documentos automaticamente (atas, requisitos, cronogramas).

Classificado como **STRATEGIC PRODUCT REQUEST**, relacionado ao Knowledge Platform/RAG/`EnterpriseMemoryService` já existentes, mas exigindo: novo mecanismo de conector/integração (não existe hoje nenhuma integração com storage externo), decisão sobre superfície de autenticação (OAuth com provedores externos), e possivelmente um novo bounded context de "Connectors/Integrations". **Não é um V1 requirement** (o piloto usa upload manual, já funcional e testado). Classificação: **V1.x evolution / future platform capability**, dependendo do apetite do Founder — requer decisão arquitetural explícita antes de qualquer design técnico.

## 16. Research Requests (Finding 13)

Transformado em proposta de pesquisa escopada, não executada nesta missão:

> **PRODUCT BENCHMARK RESEARCH:** comparar o modelo executivo atual da STRATECH com práticas contemporâneas de PMO/VMO, e identificar indicadores que realmente apoiem decisão — sem transformar a plataforma em BI genérico.

Registrada como recomendação de próxima missão, condicionada a nova Founder Decision.

## 17. P0/P1 Gate

**P0 — BLOCKS USER SESSION #2: NENHUM.** O único bloqueador operacional real (conflito de porta 5432 nativo/Docker) já foi resolvido pelo próprio Founder fora desta missão. Nenhum achado de produto impede tecnicamente a repetição da sessão.

**P1 — BLOCKS CONTROLLED EXTERNAL PILOT:**
1. Priorização não comunica sua regra de ranking (Seção 5) — mina a promessa central do produto para um usuário externo menos familiarizado que o Founder.
2. Dashboard mistura, sem distinção visual, 4 widgets explicitamente "dados simulados" com dados reais (Seção 6A) — risco de credibilidade perante um usuário externo real.

## 18. V1 Improvement Backlog (P2)

1. Indicador de prazo (atrasado/no prazo) usando `start_date`/`planned_end_date`/`actual_end_date` já existentes (Seção 6C).
2. Realocar Decision Support/Narrativa Executiva para item de menu dedicado (Seção 12).
3. Implementar o toggle manual de tema claro/escuro já especificado em RFC-001 (Seção 14).
4. Ocultar/tratar a coluna "Ações" vazia em Documentos (Seção 10).
5. Melhorar a descoberta do botão "Papéis" em Usuários (Seção 8a) — polimento de UX, não gap de produto.

## 19. V1.x / Future Backlog (P3/P4)

**P3:**
1. Agrupamento de navegação para Projetos/Program Management/Project Delivery, refletindo a hierarquia real (Seção 7).
2. Organization Administration — UI de criação de organização (já aprovada, nunca implementada) (Seção 8b).
3. Decisão de nomenclatura para "chunks" + relabel (Seção 10).
4. Design Review de tipografia/paleta/densidade (Seção 14).

**P4:**
1. Indicadores financeiros — exige novo modelo de dados e decisão arquitetural explícita (Seção 6B).
2. Integração com armazenamento externo + IA buscando documentos automaticamente (Seção 15).
3. Wiring de Aprendizados no contexto real do AdvisorFramework (Seção 11).
4. Síntese/categorização mais rica para Aprendizados, além da lista agrupada crua (Seção 11).

## 20. Session #2 Proposal

**OBJECTIVES:** revalidar se a correção de Priorização (cabeçalhos de camada) resolve o FAIL; confirmar que o Cenário A de Organization Administration (tenant pré-provisionado) é suficiente na prática; coletar mais sinal sobre a percepção de densidade do Dashboard.

**TASKS (não repetir as 10 obrigatoriamente):** Task 1 (Executive Orientation, curta) → Task 2 (Prioritization, revalidação direta do fix) → passagem leve por Ações/Decisões/Aprendizados (confirmar que resultados positivos se mantêm) → Task 9 (Administration, revalidando especificamente se o botão "Papéis" é encontrado sem assistência desta vez).

**SUCCESS CRITERIA:** Prioritization alcança PASS (não FAIL); usuário localiza atribuição de papéis com NENHUMA ou BAIXA assistência; sentimento de "poluído" no Dashboard não piora (idealmente melhora).

**USER PROFILE RECOMMENDED:** **Opção C — em sequência.** Founder novamente primeiro (ciclo rápido, confirma se as correções realmente resolveram o que ele mesmo apontou), seguido de um usuário PMO externo real numa sessão separada — a validação apenas com o Founder carrega viés de proximidade com o produto, já registrado como limitação metodológica em D-216.

## 21. Controlled Pilot Gate

Reavaliação do atual `CONTROLLED USER PILOT = NO-GO` (D-216). Gate pequeno, objetivo e mensurável — não "fechar todos os achados":

1. **Priorização comunica sua regra de ranking** (delta mínimo da Seção 5 implementado e reverificado).
2. **Provisionamento de organização para o piloto documentado e ensaiado** (Cenário A — script/migration confiável, sem necessidade de UI nova; apenas formalizar isso no Runbook).
3. **Widgets mock/demo do Dashboard visualmente distinguidos ou ocultos** para sessões com participantes externos reais.

Quando os 3 itens acima estiverem fechados e reverificados (não é necessário fechar todo o P2/P3/P4), `CONTROLLED USER PILOT PROGRESSION` pode ser reavaliado para GO.

## 22. Decision Proposals

| ID | Proposta | Prioridade | Requer decisão do Founder sobre |
|---|---|---|---|
| DP-1 | Implementar delta mínimo de Priorização (cabeçalhos de camada + explicação) | P1 | Aprovação de escopo/prosa exata |
| DP-2 | Definir termo substituto de "chunks" voltado ao usuário | P3 | Nomenclatura (termos sugeridos não pré-aprovados) |
| DP-3 | Ocultar/tratar coluna "Ações" vazia em Documentos | P2 | Aprovação de escopo |
| DP-4 | Implementar toggle de tema já especificado em RFC-001 | P2 | Aprovação de escopo |
| DP-5 | Realocar Decision Support/Narrativa para menu dedicado + nome do menu | P2 | Nome do novo item de menu |
| DP-6 | Agrupamento de navegação Projetos/Program Management/Project Delivery | P3 | Aprovação de escopo + reforço de `Sidebar` |
| DP-7 | Timing de implementação da criação de Organizações | P3 | Priorização no roadmap |
| DP-8 | Se/quando perseguir indicadores financeiros (novo modelo de dados) | P4 | Decisão arquitetural explícita |
| DP-9 | Comissionar pesquisa de benchmark PMO/VMO | Research | Autorização de nova missão de pesquisa |
| DP-10 | Confirmar escopo/perfil de usuário da Session #2 (Seção 20) | — | Aprovação direta |

## 23. Risks

- Ceder aos pedidos recorrentes de board/Kanban sem evidência suficiente arrastaria a STRATECH em direção a "ferramenta de tarefas", violando o guardrail fundacional da Constitution.
- Widgets "dados simulados" no Dashboard, se não tratados antes de um piloto externo real, podem comprometer a confiança do primeiro contato de um usuário não-Founder.
- O gap real de Organization Administration (criação), se o piloto crescer além de poucos tenants pré-provisionados manualmente, se torna um gargalo operacional real.
- Interpretar demais os comentários do usuário como requisitos (ex.: granularidade em Project Delivery) sem confirmar primeiro se a informação já existe em outro lugar (Workspace) arrisca duplicar funcionalidade já construída.

## 24. GO/NO-GO Recommendations

- **GO FOR USER SESSION #2** — sem bloqueadores reais; recomendado priorizar DP-1 (Priorização) antes de repetir a sessão, para que o novo teste seja informativo em vez de repetir o mesmo FAIL já conhecido.
- **NO-GO FOR CONTROLLED EXTERNAL PILOT PROGRESSION**, até o gate de 3 itens da Seção 21 ser fechado — gate pequeno e objetivo, não a lista completa de achados.
