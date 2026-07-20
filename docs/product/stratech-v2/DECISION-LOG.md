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

---

## Convenção

Cada decisão ganha um ID sequencial `D-NNN`, contexto, decisão e a Sprint/Entrega em que foi tomada. Não editado retroativamente — uma correção é uma nova entrada.
