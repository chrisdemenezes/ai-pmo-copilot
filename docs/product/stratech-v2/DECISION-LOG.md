# STRATECH V2 — Product Decision Log

Registro leve e cronológico de decisões de produto/técnicas tomadas durante a execução de Sprints — distinto dos ADRs (`docs/architecture/adr/`), que registram decisões arquiteturais formais e passam por Architecture Review. Aqui ficam decisões de menor porte, tomadas dentro da autonomia técnica já concedida pelo Founder, mas que vale registrar para rastreabilidade.

---

### D-001 — Marca visível renomeada para "STRATECH"

- **Contexto:** produto ainda exibia "AI PMO Copilot" (V1) em sidebar/metadata/style guide.
- **Decisão:** renomear para "STRATECH" em toda a superfície visível, consistente com a visão de produto já usada em toda a documentação da V2.
- **Sprint:** 1, Dia 1.

### D-002 — Novos primitivos de Design System seguem o padrão V1, não um novo

- **Contexto:** Sprint 1 pedia consolidar um Design System; um já existia (RFC-001).
- **Decisão:** estender (Table, Progress, Tooltip, Avatar), nunca recriar. Nenhuma nova convenção visual introduzida.
- **Sprint:** 1, Dia 1.

### D-003 — Dado mock do Executive Cockpit centralizado em um único arquivo

- **Contexto:** Portfolio/Program não são entidades reais ainda (Release 0.2); a Sprint pede mock.
- **Decisão:** todo dado simulado do Cockpit vive em `web/lib/mock/cockpit-data.ts` — quando a Release 0.2/0.3 wire dado real, só esse arquivo (e seus consumidores diretos) muda, não cada componente.
- **Sprint:** 1, Entrega 2.1.

### D-004 — Situação do Portfólio/Programa como grids novos, não retrofit do grid real de Projetos

- **Contexto:** poderia ter reaproveitado `ProjectHealthGrid` genericamente para as 3 entidades.
- **Decisão:** dois componentes novos (`PortfolioSituationGrid`, `ProgramSituationGrid`), mesma forma visual, mas sem generalizar prematuramente uma abstração comum entre 3 formatos de dado ainda em fluxo (2 mock, 1 real) — evita uma abstração errada agora que teria que ser desfeita quando o dado real chegar.
- **Sprint:** 1, Entrega 2.2.

### D-005 — "Riscos" do inventário de portfólio é distinto do Risk Intelligence de IA

- **Contexto:** a Entrega 2.3 pediu "Riscos" como uma das 4 categorias (Demandas/Riscos/Issues/Mudanças); a V1 já tem um "Risk Intelligence" real (análise de IA sobre reuniões/riscos).
- **Decisão:** manter os dois conceitos explicitamente separados — o "Riscos" do Mission Control/Cockpit é um item de trabalho formal de portfólio (com mitigação, dono, status), não a mesma coisa que a saída do agente `risk_review`. Documentado no componente para não confundir o próximo engenheiro.
- **Sprint:** 1, Entrega 2.3.

### D-006 — Mission Control usa dado real estático, não mock

- **Contexto:** diferente do Executive Cockpit (Portfolio/Program simulados, porque não existem), o Mission Control mostra o estado real da governança (Épicos, PRs, débito técnico) — que já existe, só não está exposto via API.
- **Decisão:** popular `mission-control-data.ts` com os fatos reais atuais (lidos manualmente dos artefatos de governança e do GitHub), não dado fictício — deixando claro no código que uma versão futura pode ler isso ao vivo (arquivo ou API), sem mudar a forma dos componentes.
- **Sprint:** 1, Mission Control.

### D-007 — Mission Control atrás da sessão, mas sem RBAC de Founder ainda

- **Contexto:** a diretriz pede um painel "exclusivo do Founder"; RBAC funcional não existe (Épico 3 não iniciado).
- **Decisão:** adicionar a rota ao gate de sessão existente (`proxy.ts`) — exige login, mas não distingue papel. Limitação documentada explicitamente na página, no código e neste log, não ocultada.
- **Sprint:** 1, Mission Control.

### D-008 — Executive Focus calculado a partir de dado real, não mock

- **Contexto:** Executive Focus precisa responder "onde devo concentrar atenção hoje?" de forma confiável para um executivo real.
- **Decisão:** reaproveitar `rankByRisk()` (já usado pelo Risk Concentration Ranking real) em vez de criar um novo cálculo ou usar dado simulado — o painel mais visualmente proeminente do Cockpit é o único, além do Mission Control, que não é mock.
- **Sprint:** 1.4, Entrega 2.4.

### D-009 — "Riscos" do inventário permanece distinto do Risk Intelligence de IA (reforço de D-005)

- **Contexto:** Actions Center/AI Recommendations citam "Multilift" e riscos, criando risco de confundir com o Risk Concentration real.
- **Decisão:** manter a separação de conceitos já registrada em D-005; nenhum texto novo combina os dois modelos de dado.
- **Sprint:** 1.4, Entrega 2.4.

### D-010 — Numeração "2.N" será substituída por Capabilities de produto

- **Contexto:** o Founder recomendou abandonar a sequência "2.4/2.5" e passar a organizar o trabalho por Capability de negócio (Capability 01 — Executive Decision, 02 — Portfolio Intelligence, 03 — Governance, 04 — AI Copilot, 05 — Knowledge Intelligence).
- **Decisão:** registrado como direção aprovada para a próxima Sprint — não aplicado retroativamente a esta Sprint 1 (que mantém "Dia N"/"2.N"/"Sprint 1.4" como já documentado, por não reescrever histórico).
- **Sprint:** 1.4 (decisão para vigorar a partir da Sprint seguinte).

### D-011 — Portfolio real, mas ainda sem persistência em banco

- **Contexto:** Capability 01 pede Portfolio como "entidade real de domínio", mas o Founder também instrui manter o backend mockado nesta fase e preservar a arquitetura RC-1 — sem migração/model/provider novo (CLAUDE.md).
- **Decisão:** implementar `web/lib/domain/portfolio.ts` como a primeira camada de domínio explícita do frontend — uma interface `Portfolio` completa (Identificação/Gestão/Indicadores/Governança) e um acessor assíncrono `listPortfolios()` com a mesma forma de um repositório real, resolvendo hoje a partir de dado semeado em memória. Nenhuma tabela/migração criada em `src/database`. Quando a Release 0.2 wireener um endpoint real, apenas o corpo de `listPortfolios()` muda — nenhum consumidor (`usePortfolios()`, `PortfolioSituationGrid`, Dashboard) é afetado.
- **Sprint:** Release 0.2, Capability 01.

### D-012 — Entidade Portfolio (V2) é distinta de "Portfolio Intelligence" (V1)

- **Contexto:** `lib/portfolio-intelligence/portfolio-view.ts` já existe e é uma feature real do V1 (priorização executiva por projeto, via `buildExecutivePortfolioView`) — nome próximo ao da nova entidade `Portfolio` da Capability 01.
- **Decisão:** manter os dois conceitos explicitamente separados, mesmo padrão de D-005/D-009 — a entidade `Portfolio` (`lib/domain/portfolio.ts`) representa um agrupamento estratégico real; "Portfolio Intelligence" continua sendo a visão de priorização por projeto do V1. Nenhum novo código combina os dois.
- **Sprint:** Release 0.2, Capability 01.

### D-013 — Definição de Pronto por Capability: 4 dimensões (Domínio, Experiência, Engenharia, Governança)

- **Contexto:** o Founder recomendou uma "regra de ouro" — toda Capability só é considerada concluída quando a entidade existe corretamente (Domínio), está integrada ao Executive Cockpit com boa experiência (Experiência), arquitetura/testes permanecem íntegros (Engenharia) e os artefatos vivos foram atualizados (Governança).
- **Decisão:** adotar essa regra como o padrão de Definition of Done para todas as Capabilities a partir da Release 0.2, registrado aqui como a fonte formal (não é um ADR, é uma norma de processo leve).
- **Sprint:** Release 0.2 (decisão para vigorar a partir da Capability 01, em diante).

### D-014 — Program implementado como classe DDD; Portfolio permanece como estava

- **Contexto:** a partir da Capability 02, o Founder instituiu uma Diretriz Arquitetural Permanente contra modelos anêmicos — cada entidade deve encapsular seu próprio comportamento.
- **Decisão:** `Program` (`web/lib/domain/program.ts`) nasce como classe, com invariante de construção (`Program.create()` recusa um Program sem `portfolioId`) e comportamento próprio (`belongsToPortfolio()`, `isAtRisk()`, `isOverdue()`). `Portfolio` (Capability 01) permanece `interface` + array — a diretriz vale a partir desta Capability; retrofitá-la agora seria refatoração desnecessária, sem requisito que a exija (Domain Blueprint CB-002 §1).
- **Sprint:** Release 0.2, Capability 02.

### D-015 — Vocabulário de domínio compartilhado (`shared.ts`)

- **Contexto:** `Program` precisava dos mesmos três vocabulários já existentes em `Portfolio` (saúde/status/prioridade) — declará-los de novo seria duplicar código (CLAUDE.md).
- **Decisão:** criado `web/lib/domain/shared.ts` (`DomainHealth`/`DomainStatus`/`DomainPriority`/`worstHealth`), reaproveitado por `Portfolio` e `Program`. `worstHealth()` é a regra de consolidação (vermelho vence amarelo vence verde) usada por `consolidatePortfolios()` e reaproveitável quando Program também precisar consolidar a partir de Projects.
- **Sprint:** Release 0.2, Capability 02.

### D-016 — Recomendação de substituir "Release 0.x" por Épicos de Produto, a partir da Capability 03

- **Contexto:** o Founder recomendou, a partir da Capability 03, organizar a comunicação externa (clientes/parceiros/investidores) por Épicos de Produto (ex.: Epic 1 — Strategic Portfolio Management) em vez de "Release 0.x", sem perder o controle técnico das Capabilities.
- **Decisão:** registrado como direção aprovada para vigorar a partir da Capability 03 — não aplicado retroativamente às Capabilities 01/02 ou à numeração "Release 0.2" já em uso nesta entrega, mesmo padrão de D-010 (Capability numbering).
- **Sprint:** Release 0.2 (decisão para vigorar a partir da Capability 03).

### D-017 — Mission Control ganha `layout.tsx` (AppShell), corrigindo lacuna pré-existente da Sprint 1

- **Contexto:** ao criar `app/program-management/layout.tsx` (padrão de toda rota real: `<AppShell>` com Sidebar), notou-se que `app/mission-control/` nunca teve o seu — desde a Sprint 1, Mission Control renderizava sem Sidebar/navegação, embora já estivesse em `NAV_ITEMS`.
- **Decisão:** corrigir por igualdade de padrão (mesmo `layout.tsx` de uma linha usado por Dashboard/Projects/Actions/Decisions/Portfolio/Aprendizados), não uma refatoração — Mission Control passa a ter Sidebar como as demais rotas reais.
- **Sprint:** Release 0.2, Capability 02 (correção incidental, não solicitada, mas mesma disciplina de consistência do Design System).

### D-018 — Project implementado como classe DDD, com Saúde/Progresso encapsulados por método

- **Contexto:** o Founder listou `health()` e `completionPercentage()` entre os comportamentos exigidos de Project, mesmo esses dados aparecendo também como "Indicadores" na estrutura mínima — uma aparente tensão entre campo de dado e método de comportamento.
- **Decisão:** resolver a favor do encapsulamento explícito — `progressPercentage`/`health` são campos privados, expostos apenas via `completionPercentage()`/`health()`. Os demais campos (nome, código, sponsor etc.) permanecem `readonly` públicos, mesmo padrão de `Program` (Capability 02) — não vale a pena o boilerplate de getters para dados sem comportamento associado.
- **Sprint:** Release 0.2, Capability 03.

### D-019 — Terceiro "Project" no código: distinto do `ProjectSummary` (V1) e do `Project` real do backend

- **Contexto:** já existiam dois conceitos "Project": o model real do backend (Épico 1, `src/database/models.py`, persistido, hoje só usado para membership) e `ProjectSummary` (V1, `lib/dashboard/types.ts`, dado real do BFF, chaveado por `project_name` livre, usado pelo Cockpit "Projetos"). A Capability 03 introduz um terceiro `Project` (domínio, vinculado a Program).
- **Decisão:** documentar explicitamente a distinção dos três (nenhum compartilha ID) — mesmo padrão de D-005/D-012 — em vez de tentar unificá-los agora. A unificação real é o Épico 4, fora do escopo desta Capability.
- **Sprint:** Release 0.2, Capability 03.

### D-020 — Cadeia de consolidação passa a ser transitiva (Project → Program → Portfolio)

- **Contexto:** até a Capability 02, Portfolio derivava de Program, mas Program ainda carregava valores próprios semeados (sem Projects reais para derivar). Introduzir Project expôs que a consolidação precisava encadear, não apenas existir em cada par isolado.
- **Decisão:** no Dashboard, `consolidatePrograms()` roda primeiro (Program deriva de Project), e o resultado alimenta `consolidatePortfolios()` (Portfolio deriva do Program já consolidado) — nunca mais o valor semeado de um nível intermediário.
- **Sprint:** Release 0.2, Capability 03.

### D-021 — ADR-V2-009 usa o número 009, não 008, para não colidir com uma reserva pendente

- **Contexto:** o próximo ID sequencial de ADR seria 008, mas esse número já foi mencionado em prosa (Architecture Evolution Proposal, Revisão 2) para uma proposta de extensão do Domain Map (Demand/Resource/Issue/Change Request) nunca formalmente autorizada.
- **Decisão:** usar `ADR-V2-009` para a decisão desta Capability (frontend domain layer), evitando reivindicar um número já reservado em prosa para outra decisão pendente — mesma disciplina de transparência de `NORMALIZATION-PLAN.md` sobre a colisão existente em `ADR-V2-004`.
- **Sprint:** Release 0.2, Capability 03.

### D-022 — Founder recomenda uma Architecture Review (AR-1) antes da Capability 04

- **Contexto:** após a Capability 03 (terceira entidade real do domínio), o Founder recomendou uma pausa de uma iteração para uma Architecture Review — não para refatorar, mas para validar a consistência do domínio antes de Demand/Risk/Decision/Knowledge.
- **Decisão:** registrado como recomendação aceita para o próximo passo, condicionada a nova instrução do Founder para efetivamente iniciar a AR-1 (mesmo padrão de D-010/D-016: registrar a direção, não executá-la preventivamente).
- **Sprint:** Release 0.2, Capability 03 (recomendação para o próximo passo).

### D-023 — Regra de consolidação duplicada extraída para `consolidateFromChildren()`

- **Contexto:** a Architecture Review AR-1 encontrou `consolidatePortfolios()` (program.ts) e `consolidatePrograms()` (project.ts) implementando o mesmo algoritmo duas vezes (filtrar filhos por pai, média de progresso, saúde por pior-caso), violando "nunca duplicar código" (CLAUDE.md).
- **Decisão:** extrair `consolidateFromChildren()` (`shared.ts`), parametrizada por um `rebuild` callback — a única parte que legitimamente difere entre Portfolio (objeto simples) e Program (classe, via `Program.create()`). Comportamento idêntico, comprovado pelos mesmos testes já existentes permanecendo verdes sem alteração.
- **Sprint:** Release 0.2, Architecture Review AR-1.

### D-024 — Faixa de KPIs do Executive Overview corrigida para dados reais

- **Contexto:** a AR-1 encontrou `COCKPIT_KPIS` (mock, Sprint 1) ainda em uso no Dashboard mesmo depois de Portfolio/Program/Project virarem domínio real — "Programas em Execução"/"Projetos em Andamento" mostravam 8/24 (mock) contra 4/7 reais; "Decisões Pendentes" (5) nem batia com o próprio mock de Decision Center (4 itens).
- **Decisão:** substituir por um array computado a partir de `usePortfolios()`/`usePrograms()`/`useProjects()` (filtrados por `status === "Ativo"`) e `criticalDecisionsCount` (o mesmo valor já usado pelo link `/decisions` para o qual o KPI aponta). `COCKPIT_KPIS` removido de `cockpit-data.ts` (export sem nenhum consumidor restante).
- **Sprint:** Release 0.2, Architecture Review AR-1.

### D-025 — Mock morto (`PortfolioSituation`/`ProgramSituation`) removido

- **Contexto:** a AR-1 encontrou `PortfolioSituation`/`PORTFOLIO_SITUATIONS` e `ProgramSituation`/`PROGRAM_SITUATIONS` em `cockpit-data.ts` sem nenhum consumidor — as Capabilities 01/02 já haviam migrado `PortfolioSituationGrid`/`ProgramSituationGrid` para as entidades reais, mas o mock antigo nunca foi apagado.
- **Decisão:** remover os 2 tipos + 2 arrays (e `CockpitHealth`, que só existia para eles). Nenhum comportamento muda — eram exports mortos.
- **Sprint:** Release 0.2, Architecture Review AR-1.

### D-026 — AR-1 não gerou nenhuma nova decisão arquitetural

- **Contexto:** a Architecture Review AR-1 pediu explicitamente para registrar uma ADR nova caso alguma decisão arquitetural relevante surgisse da revisão, ou declarar explicitamente que a arquitetura foi validada sem alterações, caso contrário.
- **Decisão:** nenhuma ADR nova foi necessária. As 3 correções aplicadas (D-023/024/025) são ajustes de qualidade dentro dos princípios já decididos em ADR-V2-009 — nenhuma mudou um princípio, convenção DDD ou regra de evolução. A arquitetura das Capabilities 01-03 foi certificada como consistente pela AR-1 (ver `docs/architecture/ARCHITECTURE-BASELINE-RC2.md` e o AR-1 Executive Report).
- **Sprint:** Release 0.2, Architecture Review AR-1.

### D-027 — CI encontrou um regressão real de E2E que a suíte local não pegou (`e2e/shell.spec.ts`)

- **Contexto:** RC-2 (Enterprise Release Certification) começou verificando o PR #44 e encontrou o check obrigatório "frontend" falhando no CI — `e2e/shell.spec.ts` esperava exatamente 6 itens de navegação, mas o Sprint 1 (Mission Control), a Capability 02 (Program Management) e a Capability 03 (Project Delivery) já haviam levado o total a 9. `web/components/shell/navigation.test.ts` (teste unitário) foi atualizado a cada entrega, mas a suíte E2E Playwright (`npx playwright test`) nunca foi executada localmente durante nenhuma das Capabilities — apenas `vitest run` (testes unitários/componente), que não cobre este arquivo.
- **Decisão:** corrigido `e2e/shell.spec.ts` para 9 itens, com asserções para `/program-management` e `/project-delivery`. Suíte E2E completa executada localmente (`--project=lg/md/mobile`, 67-68 testes cada) antes de reenviar ao CI — nenhuma outra quebra encontrada.
- **Processo, registrado para não se repetir:** a partir de agora, qualquer entrega que altere `NAV_ITEMS` (ou qualquer superfície coberta por `web/e2e/*.spec.ts`) deve rodar `npx playwright test` localmente, não apenas `vitest run`, antes de declarar "sem regressões".
- **Sprint:** RC-2 Enterprise Release Certification.

### D-028 — Phase 2 Foundation Architecture produzida como proposta, não como ADR aprovada

- **Contexto:** a Executive Directive de início da Phase 2 — Enterprise AI Platform pediu uma missão "Phase 2 Foundation Architecture" (API Strategy, Persistence Strategy, Organizational Scoping, RBAC Architecture, Event Architecture), explicitamente documentação/governança apenas, sem implementação.
- **Decisão:** produzido `docs/architecture/PHASE-2-FOUNDATION-ARCHITECTURE.md` como **proposta**, não como ADR já aceita — cada uma das 5 áreas reaproveita um componente já existente no código (`get_request_context`, o padrão Épico 1 de multi-tenant, o Event Map, o padrão de router de `intelligence.py`), sem inventar mecanismo novo. Nenhum ADR formal foi criado ainda — per o próprio documento (§7), ADRs virão quando a proposta for aprovada e a Technical Design existir, mesmo padrão já usado neste projeto (Blueprint → Aprovação → EO → TDS → Implementação → ADR quando necessário).
- **Observação registrada, não decidida unilateralmente:** o documento assume que a sequência Phase 2 (Foundation Architecture → AI Foundation → Knowledge Platform → Executive Copilot → Workflow Automation → Executive Intelligence) reorganiza o restante do roadmap de Releases (0.3-0.5) — sinalizado como suposição a confirmar, não uma reescrita do Master Roadmap.
- **Sprint:** Phase 2, Foundation Architecture (missão de governança, sem implementação).

### D-029 — Phase 2 Foundation Technical Design produzido, ainda sem ADR e sem implementação

- **Contexto:** a Foundation Architecture proposal (D-028) foi aprovada conceitualmente pelo Architecture Review Board. A Executive Directive seguinte pediu um Technical Design de nível de implementação para as mesmas 5 áreas (API, Persistence, Organizational Scoping, RBAC, Event Architecture), com 15 elementos por área (Objetivo, Responsabilidades, Componentes, Interfaces/Protocols, Fluxo de execução, Dependências, Estrutura de diretórios, Contratos públicos/internos, Diagrama lógico, Sequência de chamadas, Estratégia de testes, Critérios de aceite, Impactos, Riscos, Plano de migração) — explicitamente sem código, sem novo ADR, sem alteração da Baseline, sem mudança funcional.
- **Decisão:** produzido `docs/architecture/PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md`, com Protocols nomeados (`PortfolioRepository`, `ProgramRepository`, `ProjectDeliveryRepository`, `PermissionChecker`, `EventEmitter`), estrutura de diretórios concreta e planos de teste/migração, fundamentados em código real já existente (`intelligence.py`, `identity_context.py`, `enterprise_repository.py`, `identity/interfaces.py`). O risco já nomeado na proposta (D-028) sobre `projects_delivery` virar um 4º conceito de "Project" caso o Épico 4 não seja decidido antes (TD-008) foi mantido e tornado explícito como gate obrigatório antes de qualquer migração de dados reais. Nenhum ADR foi criado — permanece a mesma regra de D-028 (ADR vem quando a implementação começar).
- **Sprint:** Phase 2, Foundation Technical Design (missão de governança, sem implementação).

### D-030 — Épicos e Capabilities deixam de ser linhas paralelas de evolução; Waves passam a ser o único eixo

- **Contexto:** desde D-010 (Capabilities substituindo a numeração "2.N") existiam, de fato, duas sequências de trabalho evoluindo lado a lado — os 6 Épicos do Release 0.1 e as Capabilities do Release 0.2 — nunca formalmente unificadas em um único plano. A missão "STRATECH Enterprise Master Execution Program" pediu essa unificação.
- **Decisão:** produzido `docs/product/ENTERPRISE-MASTER-EXECUTION-PROGRAM.md`, reclassificando todo Épico e toda Capability já existente como item dentro de uma de 6 Waves (Foundation, Platform, Intelligence, Operations, Analytics, Productization). Nenhum documento aprovado (Product Constitution, Foundation Architecture, Foundation Technical Design, Decision Logs, Technical Debts) foi reescrito — apenas referenciado. Um Decision Proposal foi produzido (não decidido unilateralmente) para o único conflito de escopo real encontrado: Enterprise Administration completa (pedida pela missão) vs. "administração mínima" (Épico 5, já aprovado via EO-016). As Waves 3 (Enterprise Intelligence) e 6 (Productization) foram documentadas como **sem Blueprint/decisão de negócio hoje** — não tiveram arquitetura inventada para preencher a lacuna, por instrução explícita da própria missão.
- **Missão encerrada sem autorizar implementação ponta a ponta** (regra explícita da própria missão): pendências residuais listadas no documento (§13) e no Executive Report desta missão.
- **Sprint:** Enterprise Master Execution Program (missão de governança, sem implementação).

### D-031 — 5 Blueprints de fechamento produzidos; Architecture Freeze declarado como parcial, não total

- **Contexto:** a missão "STRATECH Architecture Closure (Fase Final)" pediu 5 Blueprints (Wave 3 Enterprise Intelligence, Enterprise Administration, RBAC, Project Domain Closure, Business Model) e, ao final, a declaração de um "STRATECH Architecture Freeze" caso nenhuma lacuna arquitetural restasse.
- **Decisão:** os 5 Blueprints foram produzidos (`docs/architecture/DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md`, `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md`, `DOMAIN-BLUEPRINT-RBAC.md`, `DOMAIN-BLUEPRINT-PROJECT.md`, `BUSINESS-MODEL-BLUEPRINT.md`), cada um com recomendação técnica fundamentada, sem preencher nenhuma lacuna com suposição. Como a verificação final (`docs/architecture/ARCHITECTURE-FREEZE.md`) encontrou respostas afirmativas em 4 das 5 perguntas de fechamento, **o Freeze foi declarado como parcial**, não como um estado binário único: Wave 1 e partes da Wave 2 (RBAC, Administration Nível 1) congeladas; Administration Níveis 2/3 e a unificação de Project aguardando ratificação do Founder (Decision Proposals, não aplicadas); Wave 3 com Blueprint mas exigindo Architecture Review antes de Technical Design; Wave 6 explicitamente fora do Freeze, por depender de uma decisão de modelo de negócio que nenhum documento aprovado jamais definiu — `BUSINESS-MODEL-BLUEPRINT.md` recusou-se deliberadamente a inventar essa estratégia.
- **Nenhum documento já aprovado foi modificado** (Product Constitution, Foundation Architecture, Foundation Technical Design, Enterprise Master Execution Program, Decision Logs anteriores, Technical Debt Register, Mission Control, Product Pulse) — apenas esta entrada foi acrescentada, per a convenção append-only já em uso.
- **Sprint:** STRATECH Architecture Closure (Fase Final) — missão de governança, sem implementação.

### D-032 — Wave 2 Sprint 1: persistência do Enterprise Domain implementada; sequenciamento ajustado (Wave 1 antes de Wave 2)

- **Contexto:** a Executive Directive "STRATECH Product Development Program" pediu início imediato da Wave 2 (Enterprise Platform) como prioridade absoluta. Verificação técnica mostrou que a Wave 1 (Enterprise Foundation) tinha Technical Design completo mas 0% implementado — e o próprio Foundation Technical Design (§6) já sequenciava Persistence → Organizational Scoping → RBAC → API → Event, ordem que a Wave 2 (Enterprise Domain, RBAC) depende de respeitar tecnicamente, não uma preferência.
- **Decisão:** implementada a Persistence Foundation (Wave 1) simultaneamente como o primeiro passo real da Wave 2 (Enterprise Domain), não como um adiamento — `Portfolio`/`Program` como tabelas novas, `Project` estendido (não uma tabela `projects_delivery` separada, per `DOMAIN-BLUEPRINT-PROJECT.md` Opção A). Migração `0005_domain_persistence` + `DomainRepository` (`src/database/domain_repository.py`), 16 novos testes, 179 testes totais passando, 98% de cobertura, `ruff` limpo. TD-007 resolvido; TD-008 avança para Fase 1 de 3.
- **Não incluído nesta Sprint, registrado para a próxima:** API/rotas (Foundation Technical Design §1), RBAC enforcement (`DOMAIN-BLUEPRINT-RBAC.md`), migração do frontend (`web/lib/domain/*.ts`) para consumir a API real em vez do array semeado.
- **Nenhum Blueprint, Domain Model aprovado ou documento de arquitetura foi alterado** — a única mudança de plano foi de sequenciamento de Sprint (Wave 1 antes de Wave 2), tecnicamente forçada pela própria dependência já documentada, não uma nova decisão arquitetural.
- **Sprint:** Wave 2, Sprint 1 — Enterprise Domain persistence.

### D-033 — Wave 2 Sprint 2: Enterprise API Layer entregue sem RBAC fino (por desenho, per diretriz do Founder)

- **Contexto:** Sprint 2 aprovada com escopo explícito: API completa para Portfolio/Program/Project, protegida por uma estrutura de autenticação "preparada para receber RBAC" (não o enforcement fino em si), documentada em OpenAPI/Swagger, 100% dos testes passando, sem alterar o frontend.
- **Decisão:** implementadas 9 rotas (`GET`/`GET by id`/`POST` para as 3 entidades) sobre `verify_api_key` + `enforce_rate_limit` + `get_request_context` — primeiro uso real de `get_request_context` desde o Épico 2. Escopo por organização resolvido do header institucional, nunca de um parâmetro de query (nenhuma organização pode escolher ver os dados de outra só trocando um id). 404, nunca 403, para qualquer id de outra organização (padrão consistente entre Portfolio/Program/Project). `DomainService` novo (`src/services/domain_service.py`) mantém essa regra em um único lugar. 33 testes novos, 201 totais passando, 98% de cobertura, `ruff` limpo, `/docs` e `/openapi.json` funcionais.
- **Não incluído, registrado para a próxima Sprint:** `require_permission(...)` (RBAC fino, `DOMAIN-BLUEPRINT-RBAC.md`) e a migração do frontend para consumir esta API.
- **Nenhum conflito arquitetural real encontrado** — nenhuma Decision Proposal necessária nesta Sprint.
- **Sprint:** Wave 2, Sprint 2 — Enterprise API Layer.

### D-034 — Wave 2 Sprint 3: RBAC fine-grained enforcement aplicado; premissa de schema do RBAC Blueprint corrigida

- **Contexto:** Sprint 3, identificada automaticamente como a próxima Sprint elegível per o Enterprise Master Execution Program (Wave 2, Epic Enterprise Identity, adiada explicitamente pela Sprint 2). Objetivo: aplicar `require_permission(...)` às 9 rotas da Enterprise Domain API, per `DOMAIN-BLUEPRINT-RBAC.md`.
- **Decisão:** migração `0006_rbac_permission_catalog` semeia 6 permissões (`portfolio`/`program`/`project_delivery` × `read`/`write`) e as atribui aos 4 papéis já existentes desde o Épico 1. `src/services/authorization/` (`PermissionChecker` Protocol + `SqlPermissionChecker`) e `src/api/authorization.py` (`require_permission`) implementados per o desenho já existente (`PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §4). Todas as 9 rotas ganham o `Depends(...)` adicional. 18 testes novos/reescritos, 211 totais, 98% de cobertura.
- **Correção de premissa (não uma mudança de Blueprint):** `DOMAIN-BLUEPRINT-RBAC.md` §1 recomendava estender `user_roles` com `organization_id`, presumindo que um usuário pudesse pertencer a mais de uma organização. Na implementação, confirmou-se que isso não é verdade no schema atual — `users.organization_id` é uma FK única e obrigatória desde o Épico 1, então um usuário nunca tem papéis em mais de uma organização hoje. A extensão de schema não foi aplicada; o Blueprint em si não foi editado (per a regra desta missão de não alterar Blueprints) — a correção fica registrada aqui.
- **Nenhum conflito arquitetural real** — correção de premissa técnica, não uma Decision Proposal.
- **Sprint:** Wave 2, Sprint 3 — RBAC fine-grained enforcement.

### D-035 — Wave 2 Sprint 4: Enterprise Administration (Nível 1+2) implementado; premissa de "Sessões" corrigida

- **Contexto:** o Founder ratificou o Nível 1 (já era o Épico 5 aprovado) e o Nível 2 (extensão de baixo risco) de `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md`, autorizando a implementação.
- **Decisão:** migração `0007` (tabela `audit_logs` + permissões `administration.read`/`administration.write`), `AdministrationRepository`/`AdministrationService`/`src/api/routes/administration.py` (8 endpoints). Auditoria aplicada retroativamente às mutações já existentes de Portfolio/Program/Project (Sprint 1-3), não apenas às novas rotas de Administration. "Logs" reaproveita a mesma tabela de "Auditoria" — nenhum sistema de logging duplicado. "Segurança" ficou com um endpoint mínimo, somente leitura.
- **Correção de premissa, não uma mudança de Blueprint:** `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §2 assumiu que "Sessões" seria uma extensão de baixo risco ("painel é só leitura+revogação sobre o que já existe"). A implementação confirmou que isso é falso — não existe armazenamento server-side de sessões (a sessão é um cookie HMAC stateless, `auth_service.py` já documentava "No server-side session store exists yet"). Um painel de Sessões real exigiria um componente de arquitetura novo, fora do escopo de extensão de baixo risco. **Não implementado.** O Blueprint não foi editado (regra da missão anterior contra alterar Blueprints) — a correção fica registrada aqui, mesmo padrão de D-034.
- **Bug encontrado e corrigido durante a implementação:** `AdministrationRepository.assign_role()` retornava um objeto SQLAlchemy expirado após `commit()` sem `session.refresh()`, causando `DetachedInstanceError` ao serializar a resposta da API — corrigido antes do commit, coberto por teste.
- **Nenhum conflito arquitetural novo** — a correção de premissa acima não é uma Decision Proposal, é um fato técnico verificado.
- **Sprint:** Wave 2, Sprint 4 — Enterprise Administration.

### D-036 — Wave 2 Sprint 5: frontend migrado para a API real; seed muda de casa (frontend → banco); demo user ganha papel viewer

- **Contexto:** o Founder aprovou a migração do frontend para a Enterprise Domain API. Pré-condição descoberta na análise: as tabelas do backend estavam vazias — trocar o frontend sem semear o banco apagaria visualmente todas as páginas; e o demo user não tinha papel algum, então o Demo Mode receberia 403 em toda a API protegida por RBAC.
- **Decisão:** (1) migração `0008_domain_seed` move os dados semeados do frontend para o banco, nas duas organizações por desenho, executando a unificação Fase 2 (`DOMAIN-BLUEPRINT-PROJECT.md`) para nomes colidentes com Projects legados ("Multilift"/"Aurora" — atualizados in-place, nunca duplicados); (2) `bootstrap_demo_user` passa a garantir o papel `viewer` a cada boot (inclusive para instalações existentes), com `assign_role_in_session` tornado idempotente; (3) 3 BFF routes novos sobre um helper compartilhado resolvem os headers institucionais server-side a partir do cookie de sessão; (4) os corpos de `listPortfolios()`/`listPrograms()`/`listProjects()` viram `fetch()` real e os arrays semeados são deletados — nenhum hook/página/componente tocado, exatamente o seam prometido em D-011.
- **Verificação:** 245 testes backend + 436 unitários frontend + suíte E2E completa nos 3 projetos (203 testes) — disciplina D-027 cumprida; mock backend do Playwright estendido com os 3 endpoints reais.
- **TD-008 avança para a Fase 2 executada nos nomes do seed** (unificação in-place); Fase 3 (reconciliar `analysis_records.project_name` → `project_id` e aposentar `ProjectSummary`) permanece para a Wave 3.
- **Sprint:** Wave 2, Sprint 5 — Frontend migration to real Enterprise Domain API.

### D-037 — Wave 2 RC-2: PostgreSQL torna-se o banco oficial; suíte de testes migrada de SQLite para PostgreSQL efêmero

- **Contexto:** com a Wave 2 substancialmente completa (Sprints 1-5) e a Wave 3 congelada pelo Architecture Freeze, o Founder abriu a missão RC-2 (Release Engineer/QA Lead/DevOps Lead) para preparar a primeira homologação completa em ambiente local com PostgreSQL — sem novas funcionalidades, sem reabrir Wave 3, sem alterar domínio ou arquitetura.
- **Decisão:** `DATABASE_URL` e a configuração de pool (`src/database/engine.py`, novo — `resolve_database_url`/`build_engine`, reutilizado por `AnalysisRepository` e `alembic/env.py`, eliminando a duplicação de fallback que existia antes) tornam PostgreSQL o ambiente oficial; SQLite permanece apenas como fallback de zero-dependência quando `DATABASE_URL` não é definida — nunca um alvo de deploy. Pipeline de vida do banco criado via `Makefile` + `scripts/rc2-db.sh`/`.ps1` (`make setup db-create migrate seed reset-db dev test-*`), com auto-detecção de peer-auth vs. password-auth Postgres. `demo/start-demo.sh` ganhou uma chamada a `alembic upgrade head` antes do boot do backend (idempotente) — antes, migrations não rodavam automaticamente por esse caminho, um gap de correção pré-existente exposto pela nova seed baseada em migration.
- **Mudança de infraestrutura de testes (não uma mudança de domínio ou arquitetura de produto):** toda a suíte pytest — 22 arquivos, ~35 ocorrências de `sqlite:///` — foi convertida para usar `tests/db.py::temp_database_url`, que cria/derruba um banco Postgres efêmero por teste, preservando o mesmo isolamento um-banco-por-teste que os arquivos SQLite temporários davam. Nenhum teste de negócio foi reescrito — apenas a fixture de conexão.
- **Achado técnico corrigido durante a implementação:** um papel Postgres não-superusuário (o role `aipmo` da aplicação) não pode `pg_terminate_backend` em processos de autovacuum (que rodam sob o contexto do superusuário do servidor), mesmo sendo dono do banco — corrigido filtrando `backend_type = 'client backend'` na query de terminação, tanto em `tests/db.py` quanto em `scripts/rc2-db.sh`/`.ps1`.
- **Exceção justificada (não uma limitação nova):** a suíte Playwright E2E continua usando `web/e2e/mock-backend.mjs` em vez do backend Python real — decisão de arquitetura de teste pré-existente (E2E de frontend rápido e determinístico, desacoplado da disponibilidade de Python/Postgres em CI), não alterada por esta missão. A cobertura contra o Postgres real vem da suíte pytest (245 testes) e da validação manual completa (login, CRUD Portfolio/Program/Project, RBAC, audit log, dashboard) registrada no Release Validation Checklist.
- **Nenhum conflito arquitetural encontrado** — nenhuma Decision Proposal necessária. Nenhum Bounded Context novo, nenhum Blueprint alterado, nenhuma decisão de negócio antecipada.
- **Verificação:** `alembic upgrade head`/`downgrade base`/`upgrade head` round trip limpo em Postgres real; 245 testes backend (98% cobertura) + 436 testes frontend + 203 testes E2E (3 projetos) passando; `ruff check src tests` limpo; `make dev` validado de ponta a ponta (clone→setup→postgres→migration→seed→backend→frontend→login→CRUD→RBAC→dashboard).
- **Missão:** Wave 2 RC-2 — Release Candidate (PostgreSQL homologation readiness), não uma Sprint do Enterprise Master Execution Program.

### D-038 — Wave 2 encerrada: Capability User Management implementada; Épico Enterprise Administration completo para o escopo mínimo aprovado

- **Contexto:** a revisão de fechamento da Wave 2 (missão anterior) encontrou o Épico Enterprise Administration incompleto por ausência da Capability User Management. O Founder aprovou o Domain Blueprint condicionado a 8 critérios técnicos obrigatórios (governança, cadastro/integridade, auditoria, frontend, escopo explicitamente excluído, PostgreSQL, testes obrigatórios, critério de encerramento) e autorizou seguir direto de Technical Design para implementação, sem nova autorização, na ausência de conflito arquitetural.
- **Decisão:** implementado exatamente o escopo mínimo pedido — listagem, cadastro, edição, ativação/inativação, associação à organização, associação/remoção de roles, RBAC aplicado, auditoria, integração Backend → BFF → Frontend. Migração `0009_user_management` adiciona `users.is_active` e substitui a constraint de e-mail case-sensitive por um índice único funcional case-insensitive `(organization_id, lower(email))`. Mecanismo de credencial inicial resolvido sem Decision Proposal: o admin define a senha diretamente no cadastro, reaproveitando o padrão já existente desde o Épico 2 (`create_user_in_session`), evitando por completo a necessidade de convite/reset. Proteções de governança (auto-inativação, último admin ativo) implementadas com `SELECT ... FOR UPDATE` para fechar corridas entre requisições concorrentes. `AdministrationRepository` passa a compor `EnterpriseRepository` em vez de duplicar lógica de criação de usuário.
- **Bug de UI encontrado e corrigido durante a implementação:** o bottom-nav mobile (`sidebar.tsx`) tinha itens `flex` sem `min-w-0`, recusando encolher abaixo da largura intrínseca do rótulo — o 10º item de navegação (Administração) excedeu o viewport de 375px e empurrou itens para fora da área visível. Corrigido com `min-w-0` + truncamento; risco de fragilidade já latente antes desta mudança (rótulos longos pré-existentes), apenas exposto por ela.
- **Escopo explicitamente excluído, confirmado sem necessidade de Decision Proposal:** convites, SSO, MFA, session store, recuperação/reset de senha, stakeholders, configurações gerais de organização — pertencem a outro Épico/Wave ou permanecem em aberto no Decision Proposal de escopo completo (`ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §9), não bloqueando este fechamento.
- **Verificação:** 281 testes backend (245 pré-existentes + 36 novos) contra PostgreSQL efêmero real; 437 testes frontend unitários; suíte E2E completa nos 3 projetos (`lg`/`md`/`mobile`, 81 testes cada) passando; `ruff`/`tsc`/`eslint` limpos.
- **Nenhum Blueprint, Domain Model ou ADR aprovado foi alterado** — mudança aditiva em todas as camadas, nenhuma arquitetura paralela.
- **Wave 2 (Enterprise Platform) declarada 100% completa** para os 3 Épicos que a compõem (Identity, Administration, Domain) — ver `USER-MANAGEMENT-EXECUTIVE-REPORT.md`. Homologação funcional completa permanece explicitamente adiada para depois da Wave 3, por instrução do Founder.
- **Sprint:** Wave 2, encerramento — Capability User Management.

### D-039 — Wave 3 aberta: Architecture Review AR-2 concluída, Epic Ledger definido, 2 sub-áreas bloqueadas por decisão do Founder

- **Contexto:** o Founder aprovou o encerramento formal da Wave 2 e autorizou a abertura da Wave 3 (Enterprise Intelligence), sob o fluxo Architecture Review → Domain Blueprint → Technical Design → Implementation → Testing → Executive Report por Epic, sem nova autorização entre Epics salvo 5 gatilhos explícitos (alteração arquitetural significativa, ampliação de escopo, novo Bounded Context, mudança do Product Constitution, decisão estratégica do Founder). A própria `ARCHITECTURE-FREEZE.md` já exigia que a Wave 3 passasse por uma Architecture Review dedicada antes de qualquer Technical Design.
- **Decisão:** AR-2 (`docs/architecture/AR-2-WAVE-3-ARCHITECTURE-REVIEW.md`) auditou código (nenhum desvio de CLAUDE.md, nenhuma duplicação nova, grounding do `DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md` §0 revalidado linha a linha), governança (nenhuma divergência) e engenharia (281 testes backend + 437 frontend + 243 E2E, todos verdes, reaproveitados da verificação de encerramento da Wave 2 — nenhuma mudança de código no intervalo). Organizou a Wave 3 em um Epic Ledger: **Epic W3-1** (Project Identity Unification — TD-008 Fase 3, reconciliar `analysis_records.project_name`→`project_id`, aposentar `ProjectSummary`) e **Epic W3-2** (AI Platform Foundation — extensão do `LLMProvider`/`factory.py` para múltiplos providers, Model Registry, Prompt Versioning aditivo ao `PromptRegistry`) liberados para início imediato, sem depender de nenhuma decisão do Founder. **Epic W3-3** (Risk Advisor, prova de conceito de um único Enterprise Agent, per a recomendação já existente no Blueprint da Wave 3) liberado condicionalmente — sua própria Technical Design deve provar que nenhum framework de orquestração multi-agente está sendo introduzido.
- **Correção de premissa (não uma mudança de Blueprint ou do Freeze):** `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §11 listava TD-008 como bloqueado por "migrar dados reais de `projects_delivery`" — tabela que nunca chegou a existir separadamente (a unificação Fase 1 já colocou os campos de domínio na própria tabela `projects`). O gatilho real e atual de TD-008 Fase 3 é apenas "a Wave 3 começar", já cumprido por esta decisão. Nenhum documento foi reescrito — a correção fica registrada aqui, mesmo padrão de D-034/D-035.
- **2 sub-áreas da Wave 3 permanecem bloqueadas, registradas como Decision Proposal, não decididas silenciosamente** (`ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §15, nova seção aditiva): **Knowledge Platform** (Vector Store/RAG/Embeddings — decisão de infraestrutura nova, pertence ao Founder) e **Enterprise Agents além do Risk Advisor** (framework de orquestração multi-agente para os demais 7 Advisors — alteração arquitetural significativa sem precedente). Nenhum código, Blueprint ou Technical Design foi produzido para estas 2 sub-áreas.
- **`ARCHITECTURE-FREEZE.md` não foi editado retroativamente**, per sua própria regra ("este veredito não é reaberto... deve ser registrado como uma nova entrada de Decision Log") — a pendência "Wave 3 aguardando Architecture Review" que ele registrava fica resolvida por esta entrada, não por uma edição daquele documento.
- **Nenhum Blueprint, Domain Model ou ADR aprovado foi alterado.** Nenhuma implementação ainda — esta é a Architecture Review que precede o primeiro Domain Blueprint de Epic da Wave 3.
- **Missão:** Wave 3, Architecture Review (AR-2) — abertura da Wave.

### D-040 — Wave 3, Epic W3-1 concluído: Project Identity Unification (TD-008, Fase 3a)

- **Contexto:** AR-2 liberou o Epic W3-1 (Project Identity Unification) para início imediato, como o primeiro Epic da Wave 3, por já ser um item de dívida técnica conhecido (TD-008) com gatilho de resolução ("a Wave 3 começar") já cumprido.
- **Decisão:** `ProjectSummaryService.summarize_portfolio()` passa a agrupar por `project_id` (já populado em toda escrita desde o Épico 1) em vez de `project_name` bruto — corrige um bug real: análises salvas com nomes que diferem só por espaço em branco resolvem ao mesmo `project_id` (`get_or_create_project_for_name` normaliza), mas apareciam como 2 entradas separadas no portfólio agregado antes desta correção. `ProjectSummaryResponse`/`ProjectSummary` ganham `project_id` como campo aditivo (opcional no frontend, para não exigir nenhuma atualização de fixture de teste existente). Nenhuma rota, parâmetro de URL ou contrato existente foi alterado.
- **Escopo deliberadamente faseado (Fase 3a apenas):** migrar toda a superfície de Dashboard/Portfólio/Decision Center/Executive Focus/Workspace de `project_name` para `project_id` como chave primária de fato, aposentando `ProjectSummary` por completo (Fase 3b), permanece documentado e **não implementado** — o levantamento feito no Domain Blueprint deste Epic (`DOMAIN-BLUEPRINT-PROJECT-IDENTITY-UNIFICATION.md`) mostrou que essa Fase sozinha teria um raio de impacto maior que o resto da Wave 3 inteira. Não decidido silenciosamente: registrado como trabalho futuro explícito, candidato a um Epic dedicado dentro da própria Wave 3.
- **Verificação:** 282 testes backend (281 pré-existentes + 1 novo cobrindo o bug corrigido); `ruff`/`tsc`/`eslint` limpos; 437 testes frontend inalterados (campo opcional); spot-check E2E (`dashboard.spec.ts`+`portfolio.spec.ts`, `lg`) 20/20 passando — justificado por esta mudança não tocar nenhum comportamento de frontend nem o mock E2E.
- **Nenhum Blueprint, Domain Model ou ADR aprovado foi alterado.**
- **Sprint:** Wave 3, Epic W3-1.

### D-041 — Wave 3, Epic W3-2 avaliado e adiado: AI Platform Foundation não tem consumidor real hoje

- **Contexto:** AR-2 havia liberado o Epic W3-2 (AI Platform Foundation) para início imediato, seguindo o sequenciamento já recomendado pelo `DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md` §1 (Provider Strategy → Model Registry → Model Routing → Cost/Token → Observability → Evaluation Framework).
- **Decisão:** o Domain Blueprint deste Epic (`DOMAIN-BLUEPRINT-AI-PLATFORM-FOUNDATION.md`) auditou cada sub-área contra a pergunta "existe um consumidor real hoje?", não apenas "é seguro construir?". Resultado: **nenhuma das 7 sub-áreas tem um caso de uso concreto hoje** — os 3 Accelerators reais sempre usam o mesmo `LLMProvider` (nenhuma seleção por caso de uso é pedida); nenhum prompt jamais precisou de versionamento; nenhum problema de custo/token foi relatado (apesar de um gap real e concreto: `ProductionLLMProvider.generate()` descarta o `message.usage`/tokens que a API da Anthropic já devolve). Construir Model Registry, Model Routing, Prompt Versioning ou instrumentação de custo sem nenhum consumidor real seria exatamente a arquitetura especulativa que este projeto evita em toda a sua história (CLAUDE.md: "não fazer mais do que o necessário", "não projetar para requisitos hipotéticos futuros").
- **Nenhum código foi produzido por este Epic.** Epic W3-2 marcado como **adiado, não cancelado** — gatilhos explícitos de reabertura documentados (Epic W3-3 ou um Advisor futuro precisar de um modelo diferente; um problema real de custo/latência surgir; o Founder pedir visibilidade de custo de IA explicitamente).
- **A Wave 3 avança para o Epic W3-3 (Risk Advisor)**, que tem um entregável concreto e nomeado, em vez de permanecer bloqueada por um Epic sem trabalho real a fazer.
- **Nenhum Blueprint, Domain Model ou ADR aprovado foi alterado.** Nenhuma decisão de que a STRATECH nunca terá múltiplos providers — apenas que não há hoje nenhum caso de uso que justifique construir isso agora.
- **Sprint:** Wave 3, Epic W3-2 (Architecture/Blueprint apenas, sem implementação).

### D-042 — Repository Audit Wave 3: Go with Conditions; 2 achados críticos de segurança pré-existentes registrados como Decision Proposal

- **Contexto:** o Founder autorizou uma Auditoria Técnica completa do repositório (`docs/product/governance/REPOSITORY-AUDIT-WAVE-3.md`) antes de atualizar a `main` e iniciar o Epic W3-3, cobrindo estrutura, código/dependências, banco de dados/PostgreSQL, testes/qualidade, segurança e coerência de documentação.
- **Achados críticos (C-1, C-2), ambos pré-existentes desde o V1, não introduzidos por nenhum trabalho da Wave 2/3:** `src/api/routes/intelligence.py` não aplica RBAC nem contexto organizacional em nenhuma de suas 8 rotas (ao contrário de todo outro módulo de rota); `AnalysisRecord` não tem `organization_id`, causando vazamento real de dados entre as duas organizações reais que já coexistem na base ("Default Organization", "Demo Organization"). **Nenhuma correção de código aplicada** — registrado como Decision Proposal (`ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §16), não decidido silenciosamente, per instrução explícita do Founder.
- **Correções de baixo risco aplicadas durante a auditoria:** `mission-control-data.ts::EPIC_STATUS`/`RELEASE_STATUS` corrigidos (Épicos 3-5 estavam "Not Started" já concluídos; Releases 0.1/0.2 estavam "In Progress" já 100% concluídas); nota de `DOMAIN_EVOLUTION` sobre TD-008 atualizada; `README.md` status corrigido de "Wave 2 RC-2" para "Wave 3 em progresso".
- **Incidente de ambiente registrado por transparência:** o serviço PostgreSQL do ambiente parou durante a auditoria (confirmado via `pg_isready`), causando 171 falhas de conexão em uma execução de `pytest --cov` — não um defeito de código. Reiniciado e revalidado limpo (282/282 testes, 97% cobertura).
- **E2E:** suíte completa (241 testes, 3 projetos) — 230 passed, 11 failed; re-execução isolada confirma que apenas 6 falhas são deterministicamente reproduzíveis, todas já rastreadas como TD-004/005/006 (Baseline Defects conhecidos); as demais 5 não reproduziram isoladamente (transitórias, atribuídas à contenção de recursos do ambiente).
- **Recomendação: GO WITH CONDITIONS.** Atualização da `main` autorizada (nenhuma mudança desta sessão piora C-1/C-2). Implementação do Epic W3-3 (Risk Advisor) **não deve prosseguir** até o Founder decidir a Decision Proposal — o Advisor construiria diretamente sobre a rota vulnerável (C-1). Blueprint/Technical Design do W3-3 podem prosseguir em paralelo, nomeando esta dependência explicitamente.
- **Nenhum Blueprint, Domain Model ou ADR aprovado foi alterado.**
- **Missão:** Repository Audit Wave 3 (pré-requisito Founder para main update + Epic W3-3).

### D-043 — Epic W3-3: Enterprise Domain Blueprint do Risk Advisor concluído; Implementação bloqueada até C-1/C-2 serem decididos

- **Contexto:** o Founder autorizou o início do Epic W3-3 (Risk Advisor) condicionado à conclusão da auditoria + atualização da `main`, exigindo um Enterprise Domain Blueprint (não apenas Technical Design) cobrindo propósito executivo, atores, modelo de domínio, fluxo decisório, integração LLM, explainability, nível de confiança, RBAC, organization scope, auditoria, interface conversacional, critérios de aceite, riscos, dependências e não-escopo.
- **Decisão:** `DOMAIN-BLUEPRINT-RISK-ADVISOR.md` produzido cobrindo todos os pontos exigidos. Desenho: nenhuma entidade de domínio nova (reaproveita `Project` e `AnalysisRecord` já existentes), nenhuma extensão de `LLMProvider`/`PromptRegistry` necessária, somente leitura (nunca dispara nova análise), explainability obrigatória (cita `source_analysis_id`), auditoria de toda pergunta feita. Confirma o guarda-corpo da AR-2: nenhum framework de orquestração multi-agente, vector store, RAG ou memória de longo prazo é introduzido — exatamente os itens explicitamente fora de escopo pelo Founder.
- **Implementação bloqueada, não decidida silenciosamente:** o Blueprint identifica que o Risk Advisor herdaria diretamente as 2 lacunas críticas de segurança do Repository Audit (C-1: `intelligence.py` sem RBAC; C-2: `AnalysisRecord` sem `organization_id`) se implementado antes delas serem resolvidas — construir uma interface conversacional sobre uma rota sem controle de acesso agravaria o problema. Nenhum código produzido. Aguardando: (1) decisão do Founder sobre C-1/C-2 (Decision Proposal, `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §16), (2) conclusão do merge da `main` (PR #45).
- **Nenhum Blueprint, Domain Model ou ADR aprovado foi alterado.**
- **Missão:** Wave 3, Epic W3-3 (Blueprint apenas, Implementação pendente).

### D-044 — Baseline oficial consolidada: PR #45 mergeado na `main`, todos os checks essenciais revalidados

- **Contexto:** o Founder autorizou o merge imediato da PR #45 (Wave 2 closure + abertura da Wave 3, Phase 2 Foundation → Repository Audit) e exigiu revalidação completa sobre a `main` após o merge.
- **Merge:** PR #45 mergeado via `merge` commit — hash final da `main`: **`d8ff04d5db3999a3defafdc8ee9362e0ab7308b3`** (branch origem: `claude/stratech-permanent-principles-yjnm74` @ `2362688`; branch destino: `main`, anterior em `3eb9f18`). Árvore do merge commit confirmada idêntica (`git diff` vazio) ao HEAD da branch de origem — nenhuma surpresa introduzida pelo merge. Branch remota `origin/main` confirmada sincronizada com o local (`git fetch` + `git log` no mesmo hash).
- **Checks essenciais revalidados sobre a `main` (não a branch de origem) após o merge:**

| Check | Resultado |
|---|---|
| Backend (`pytest`) | 282 passed |
| `ruff check src tests` | Limpo |
| Frontend `tsc --noEmit` | Limpo |
| Frontend `eslint .` | Limpo |
| Frontend `vitest run` | 437 passed |
| Integração PostgreSQL | Confirmada — toda a suíte de integração já roda sobre Postgres real (`tests/db.py`) |
| Migrations (upgrade → downgrade → re-upgrade, `0001`→`0009`→`base`→`0009`) | Round-trip completo validado em banco descartável, limpo em todas as 3 direções |

- **Achado incidental durante a validação de PR #45:** a falha de CI real reportada pelo GitHub (`check_run` 89228306744, job `validate`) revelou que `.github/workflows/ci.yml` nunca provisionava um serviço PostgreSQL — o job falhava deterministicamente (não uma flakiness) desde que a RC-2 tornou Postgres obrigatório para a suíte de integração. Corrigido durante a mesma sessão (serviço `postgres:16`, `aipmo`/`aipmo`, healthcheck `pg_isready`) — ambos os checks obrigatórios (`validate`, `frontend`) ficaram verdes na `PR #45` antes do merge ser autorizado.
- **Governança atualizada:** Mission Control, CHANGELOG (esta entrada).
- **Confirmação:** a `main` representa a baseline oficial da Wave 3 em progresso (Epics W3-1 concluído, W3-2 adiado, W3-3 com Blueprint concluído e Implementação bloqueada). Per a própria autorização do Founder, **a implementação do Risk Advisor não foi iniciada** — próximo passo autorizado é o Security Hardening Gate (C-1/C-2).
- **Missão:** Repository Audit Wave 3, Etapa 2 (consolidação da `main`).

### D-045 — Security Hardening Gate concluído: C-1 (RBAC em intelligence.py) e C-2 (Tenant Isolation em AnalysisRecord) fechados

- **Contexto:** o Repository Audit Wave 3 (D-042) havia registrado 2 achados críticos pré-existentes desde o V1 como Decision Proposal, não corrigidos naquele momento: `src/api/routes/intelligence.py` sem RBAC/escopo organizacional em nenhuma de suas 8 rotas; `AnalysisRecord` sem `organization_id`, causando vazamento real de dados entre organizações. Após a consolidação da `main` (D-044), o Founder autorizou o Security Hardening Gate, exigindo primeiro um Technical Design consolidado das 2 correções e, não havendo impacto arquitetural fora do escopo aprovado, prosseguir diretamente para implementação, testes e Executive Report.
- **Decisão:** `docs/architecture/TECHNICAL-DESIGN-SECURITY-HARDENING-GATE.md` confirmou nenhum impacto arquitetural fora do escopo aprovado — implementação prosseguiu diretamente. **C-1:** as 8 rotas de `intelligence.py` passam a exigir `Depends(get_request_context)` + `Depends(require_permission("intelligence.read"|"intelligence.write"))`, mesmo padrão já adotado em `portfolio.py`/`program.py`/`project_delivery.py`/`administration.py`; novas permissões `intelligence.read` (todos os 4 papéis seed) e `intelligence.write` (todos exceto viewer) seedadas via migração `0010`. **C-2:** `AnalysisRecord` ganha `organization_id` (migração `0010`: coluna nullable → backfill via join com `projects.organization_id` → `NOT NULL` → FK → índice, com `RuntimeError` explícito se alguma linha ficasse sem backfill); `save_analysis`/`list_analyses`/`get_analysis` passam a filtrar/exigir `organization_id`. **Causa raiz mais profunda encontrada durante o Technical Design** (não apenas o sintoma reportado pela auditoria): `get_or_create_project_for_name` sempre resolvia para uma única "Default Organization" hardcoded, independente do chamador real — corrigido para usar o `organization_id` real do contexto da requisição.
- **Refatoração mínima incidental:** `build_repository` extraído de `intelligence.py` para um novo módulo compartilhado `src/api/dependencies.py`, para evitar um import circular (`authorization.py` → `intelligence.py` → `authorization.py`) que surgiria assim que `intelligence.py` passasse a depender de `require_permission`.
- **BFF (Next.js):** as 9 rotas do BFF que proxiam para `intelligence.py` (Dashboard, Ações, Riscos, e as 6 rotas do Workspace) passam a resolver a identidade da sessão (`readSessionIdentity`) e encaminhar os headers institucionais (`X-Stratech-User-Id`/`Organization-Id`/`Session-Id`) — nenhuma delas exigia isso antes, porque as rotas de backend também não exigiam. `domain-proxy.ts` ganhou `institutionalHeaders()`/`readSessionIdentity()` exportados para reuso por essas rotas bespoke (timeouts/mapeamento de erro/renomeação de campo próprios, que não se encaixam no `forwardDomainRequest()` genérico).
- **Verificação:** auditoria de segurança C-1/C-2 confirmada por teste, não apenas por inspeção — `test_intelligence_api.py` reescrito na convenção Postgres+RBAC real (`test_portfolio_api.py`), incluindo `test_meeting_analyzed_by_org_a_is_invisible_to_org_b` (prova ponta-a-ponta de que o vazamento real encontrado pela auditoria não pode mais ocorrer) e 403 parametrizado para as 8 rotas. Migração `0010` validada por round-trip manual completo (upgrade → downgrade → re-upgrade) em banco descartável, incluindo um registro no formato legado (sem `organization_id`) para provar o backfill. **305 testes backend** (282 pré-existentes + 23 novos/reescritos), **452 testes frontend** (437 pré-existentes + 15 novos, incluindo os 401 sem sessão), `ruff`/`tsc`/`eslint` limpos, suíte E2E completa (3 projetos) — as 6 falhas observadas foram isoladas e confirmadas pré-existentes ao Gate (reproduzem de forma idêntica na baseline anterior a esta mudança, via comparação A/B com `git stash`), nenhuma delas nova.
- **Nenhum Blueprint, Domain Model ou ADR aprovado foi alterado.** Nenhuma arquitetura paralela, nenhum novo provider, nenhum novo registry — reaproveitamento total do padrão RBAC e do `AdministrationRepository.record_audit` já existentes.
- **Todos os critérios de aceite do Founder confirmados:** nenhuma rota de `intelligence.py` acessível sem autorização; nenhum `AnalysisRecord` acessível entre organizações; PostgreSQL como banco oficial; migração validada (upgrade/downgrade/re-upgrade); regressão completa aprovada; testes específicos de isolamento multi-tenant; trilha de auditoria atualizada (3 novas ações `analysis.*_created`); nenhuma exposição de dado histórico durante o backfill (constraint `NOT NULL` só aplicada após backfill confirmado, com `RuntimeError` de segurança).
- **Próximo passo autorizado:** retomar o Epic W3-3 (Risk Advisor PoC) com o Blueprint já aprovado (`DOMAIN-BLUEPRINT-RISK-ADVISOR.md`), per o fluxo oficial da Wave 3 — a dependência que bloqueava sua Implementação (D-043) está resolvida.
- **Missão:** Security Hardening Gate (C-1 + C-2).

---

## Convenção

Cada decisão ganha um ID sequencial `D-NNN`, contexto, decisão e a Sprint/Entrega em que foi tomada. Não editado retroativamente — uma correção é uma nova entrada.
