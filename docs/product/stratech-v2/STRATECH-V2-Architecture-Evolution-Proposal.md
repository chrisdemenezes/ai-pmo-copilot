# STRATECH V2 — Architecture Evolution Proposal

| | |
|---|---|
| **Documento** | Proposta arquitetural — não implementação |
| **Autor** | Claude (atuando como Principal Software Architect, conforme solicitado) |
| **Status** | Proposta — aguardando aprovação do Founder antes de qualquer codificação |
| **Natureza** | Este documento **não substitui** `Enterprise-Architecture-Blueprint-v2.0.html`, o Domain Map, o `Release-Roadmap-0.1-to-0.5.html` ou o `Release-0.1-Macro-Backlog.html` — todos já aprovados. Ele **reconcilia** a visão de produto apresentada nesta Engineering Order com o que já está aprovado, aponta onde a visão já está coberta, onde exige extensão formal (via ADR ou Capability Blueprint futura), e onde há lacuna real de implementação. Nenhuma decisão arquitetural já aprovada é reaberta ou contradita aqui. |

> **Princípio de leitura deste documento:** em cada seção, distingo três coisas — (a) **o que já está aprovado e implementado**, (b) **o que já está aprovado mas não implementado**, (c) **o que a visão desta Engineering Order traz de novo e ainda não tem decisão arquitetural formal**. Categoria (c) não é decidida unilateralmente aqui — é apontada como pendência para uma ADR ou Capability Blueprint futura, conforme o Product Engineering Framework (EO-021).

---

## 1. Diagnóstico da RC-1 (V1)

### O que existe e funciona hoje, verificado no código real

| Camada | Estado real |
|---|---|
| **Backend** (`src/`) | FastAPI. `src/api/routes/intelligence.py` expõe 9 endpoints: `POST /meetings/analyze`, `POST /risks/analyze`, `POST /projects/analyze`, `GET /analyses`, `GET /analyses/{id}`, `GET /action-items`, `GET /risks/latest`, `GET /projects/summary`, `GET /portfolio/summary`. Todos operam hoje sobre `analysis_records.project_name` (texto livre), não sobre a entidade `Project` real (que já existe no schema desde o Épico 1, mas ainda não é usada por estes endpoints). |
| **AI Agents** (`src/agents/`) | 3 agentes reais: `project_status`, `risk_review`, `meeting_intelligence`, cada um com `agent.py` próprio + `output_parser.py` compartilhado (`src/agents/shared/`). |
| **LLM Provider** (`src/llm/providers/`) | `factory.py` + `base.py` (contrato) + `mock_provider.py`/`production_provider.py` — os 3 agentes já são agnósticos ao provedor de IA concreto. |
| **Prompts** (`src/prompts/registry.py`) | **Um único** `PromptRegistry`, resolvendo `src/agents/<agent>/prompts/<prompt>.md`. Não há (e não deve haver) um segundo registry. |
| **Orquestração** (`src/workflows/pmo_workflow.py`) | Existe como stub deliberado (`PMOWorkflow`), documentado no próprio código como "reservado para a próxima fase... ainda não conectado ao MVP atual" — não é código órfão, é uma reserva arquitetural consciente para orquestração multi-agente futura (Release 0.5). |
| **Identity Layer** (`src/services/identity/`) | Único módulo de domínio de negócio já extraído para `src/services/`, com `interfaces.py` (Protocols), `models.py` (dataclasses imutáveis), `auth_service.py` — este é o **padrão de módulo** que a Seção 3 desta proposta generaliza para os próximos domínios. |
| **Schema** (`src/database/models.py`) | `organizations`, `users` (`identity_type`, `UNIQUE(organization_id, email)`), `roles`, `permissions`, `role_permissions`, `user_roles`, `projects` (`UNIQUE(organization_id, name)`), `user_project_memberships`. Multi-tenant desde o primeiro commit de schema (Épico 1), mesmo operando hoje com 1 organização principal + 1 organização Demo. |
| **Frontend** (`web/app/`) | Next.js 16 App Router: `/entrar`, `/dashboard`, `/portfolio`, `/projects`, `/workspace/[projectName]`, `/actions`, `/decisions`, `/aprendizados`. Padrão BFF (`web/app/api/bff/`) isola `X-API-Key`/`SESSION_SECRET` do navegador. |
| **Autenticação** | Individual, escopada por organização (Épico 2, `POST /api/auth/login` com `{organization, email, password}`), Argon2id, cookie assinado `stratech_session`. |
| **Autorização** | Papéis (`roles`/`permissions`) existem no schema, **nenhum motor de autorização os aplica ainda** — RBAC funcional é o Épico 3, não iniciado. |
| **Integrações externas** | **Nenhuma existe hoje.** Nenhum conector com Jira, Azure DevOps, MS Project, SAP, Oracle, Power BI, Teams, SharePoint, GitHub, Google Workspace ou Outlook está implementado. |
| **Gestão documental** | **Não existe hoje.** Nenhum módulo de documento, metadado, versão ou extração. |
| **Portfólio/Programa como agregação** | **Não existe hoje.** A página `/portfolio` lista projetos (via `project_name` livre); não há entidade `Portfolio` ou `Program`. |

### O que já está aprovado, mas ainda não implementado (referência: Blueprint v2.0, Release Roadmap)

O Enterprise Architecture Blueprint v2.0 (já aprovado) já define um **Domain Map de 8 domínios** e uma **Target Architecture em 6 camadas + 2 transversais**, cobrindo — em nível de arquitetura, não de código — praticamente toda a visão descrita nesta Engineering Order: Enterprise Foundation, Portfolio/Program/Project Intelligence, Document Intelligence, Process Intelligence, Integration Hub, AI Intelligence Layer, Event & Orchestration, Executive Intelligence. O `Release-Roadmap-0.1-to-0.5.html` já sequencia a entrega desses domínios em 5 releases. Isso é detalhado na Seção 4.

---

## 2. Pontos fortes da RC-1 (a preservar, não a reescrever)

1. **Separação de camadas já é real, não apenas nominal**: `agents/` (lógica de IA) nunca importa `database/` diretamente; `services/` orquestra; `api/` só expõe HTTP. Isso já é uma base compatível com Clean Architecture — não precisa ser reconstruída, precisa ser **generalizada** para novos domínios (Seção 3).
2. **Padrão BFF já protege segredos** (`X-API-Key`, `SESSION_SECRET`) do navegador — postura de segurança Enterprise já presente desde o Sprint 1 do frontend.
3. **Multi-tenancy estrutural desde o primeiro commit de schema** (Épico 1) — `organization_id` presente em toda tabela relevante, mesmo antes de o produto operar com múltiplas organizações de fato. Isso evita a dívida mais cara de se corrigir tardiamente em produtos Enterprise (retrofitting multi-tenancy).
4. **Provider de IA já é plugável** (`src/llm/providers/factory.py`) — trocar ou adicionar um provedor de LLM não exige tocar em nenhum agente.
5. **Um único `PromptRegistry`, um único ponto de resolução de prompt** — a regra do CLAUDE.md ("nunca criar novo registry") já é estruturalmente garantida, não apenas prometida.
6. **`PMOWorkflow` reservado, não construído prematuramente** — evita o erro comum de Enterprise de construir um motor de orquestração antes de ter agentes suficientes para justificá-lo (YAGNI respeitado).
7. **Disciplina de governança já institucionalizada** (EO→TDS→Architecture Review→PR→Merge, Product Engineering Framework EO-021) — rara em produtos deste estágio, e diretamente relevante para um produto Enterprise de PMO/Governança, cujo próprio domínio de negócio é governança.
8. **Identity Layer (`src/services/identity/`) já prova o padrão de módulo de domínio** que todo domínio futuro deve seguir (Seção 3) — não é um caso isolado, é o primeiro exemplar de uma convenção repetível.

## 3. Pontos de melhoria (gaps reais, verificados, não hipotéticos)

1. **Os 3 Accelerators de IA ainda operam sobre `project_name` livre**, não sobre a entidade `Project` real — a Release 0.3 (já aprovada) existe exatamente para fechar isso.
2. **RBAC não é aplicado** — papéis existem, nenhuma rota os verifica. Épico 3.
3. **Nenhum Integration Hub existe** — este é o maior gap relativo à visão desta Engineering Order. Nenhum conector (Jira, Azure DevOps, MS Project, SAP, Oracle, Power BI, Teams, SharePoint, GitHub, Google Workspace, Outlook) está implementado. Release 0.4, não iniciada.
4. **Nenhuma Gestão Documental existe** — TAP, Atas, Business Case, Contratos, Normativos, Lições Aprendidas como fonte de inteligência de IA: 0% implementado. Release 0.4/0.5.
5. **Portfólio e Programa não são entidades reais** — hoje é uma lista de projetos. Release 0.2.
6. **"Issues" e "Mudanças" (Change Requests) não aparecem no Domain Map aprovado** (domínio 2 lista Portfolio/Program/Project/Phase/Milestone/Deliverable/Task/Cost/Risk/Decision/Action — Issue e Change Request **não estão nomeados**). Isto é uma lacuna real entre a visão desta Engineering Order e o Domain Map já aprovado — **não decido unilateralmente adicioná-los**; aponto como pendência de ADR (Seção 8).
7. **"Recursos" (gestão de recursos/capacidade) também não aparece no Domain Map** — mesma observação do item 6.
8. **TD-001/TD-002 (FK não aplicada pelo SQLite, política de exclusão indefinida)** seguem abertos — tornam-se relevantes assim que qualquer tela administrativa de exclusão for construída (Épico 5).
9. **Nenhum Event Bus/Orquestração existe** — `PMOWorkflow` é só um stub. Release 0.5.
10. **Inconsistência cosmética de nomenclatura de rotas** (`/aprendizados`, `/entrar` em português; `/dashboard`, `/actions` em inglês) — não urgente, mas vale registrar para uma futura Capability Blueprint de IA de navegação, não corrigida aqui (fora do escopo desta proposta, que é só arquitetural).

---

## 4. Arquitetura proposta

### 4.1 Organização da solução

Nenhuma reestruturação de `src/`/`web/`. A árvore oficial do CLAUDE.md (`api/`, `agents/`, `database/`, `llm/`, `prompts/`, `services/`, `workflows/`) já comporta todos os domínios futuros. **Regra proposta:** toda nova lógica de negócio de um domínio vive em `src/services/<domínio>/`, seguindo exatamente a forma já provada por `src/services/identity/`:

```
src/services/<domínio>/
  __init__.py
  models.py       # dataclasses imutáveis do domínio
  interfaces.py   # Protocols para estratégias substituíveis (ex.: conectores, verificadores)
  <domínio>_service.py  # orquestração, injeção de dependência via construtor
```

### 4.2 Separação por domínios

Reutiliza integralmente o **Domain Map de 8 domínios já aprovado** (Blueprint, Seção 6) como fronteira canônica — nenhuma segunda taxonomia é criada:

| Domínio (já aprovado) | Mapeamento para a visão desta EO |
|---|---|
| Enterprise Foundation | Organização, usuário, papel, permissão, sessão, auditoria — Épicos 1-2 já entregues |
| Portfolio, Program & Project Intelligence | Portfólio, Programas, Projetos, Cronogramas (Phase/Milestone/Task), Custos, Riscos, Decisões, Ações — cobre a maior parte da lista "Portfólio/Programas/Projetos/Demandas¹/Cronogramas/Custos/Riscos/Decisões" |
| Document Intelligence | Gestão Documental como fonte de conhecimento de IA (TAP, Atas, Business Case, Contratos, Normativos, Lições Aprendidas) |
| Process Intelligence | Referência a processos formais (ex.: metodologia de PMO), sem ser um BPM nativo |
| Integration Hub | Jira, Azure DevOps, MS Project, SAP, Oracle, Power BI, Teams, SharePoint, GitHub, Google Workspace, Outlook, APIs de clientes |
| AI Intelligence Layer | Os 3 Accelerators atuais + os 9 adicionais do AI-Accelerators-Map, incluindo Knowledge Intelligence sobre documentos |
| Event & Orchestration | Futuro `PMOWorkflow` real, auditoria de mudanças, Governança de eventos |
| Executive Intelligence | Dashboards, KPIs, Executive Reports, Cockpit por perfil (CEO/CIO/PMO/Gerentes/Analistas) |

¹ "Demandas" (intake de solicitações) **não tem mapeamento explícito** no Domain Map atual — mesma observação da Seção 2, item 6/7: pendência de ADR, não decidida aqui.

### 4.3 Estrutura de módulos

Um módulo = um domínio × uma capacidade delimitada. Cada módulo:
- Expõe apenas sua interface pública (`interfaces.py`); nenhum outro módulo importa seus internals.
- Tem seus próprios testes, no mesmo padrão já usado por `tests/test_identity_*.py`.
- É registrado no container de DI (padrão `build_*()` + `@lru_cache` já usado em `src/api/routes/auth.py`) — nunca instanciado diretamente pela rota.

Exemplos futuros, mesma forma de `identity/`: `src/services/portfolio/`, `src/services/documents/`, `src/services/integrations/<connector>/`.

### 4.4 Arquitetura de navegação

Nenhuma URL existente muda. Para organizar visualmente a árvore por domínio sem quebrar rotas, usar **Route Groups** do Next.js App Router (pastas entre parênteses, não aparecem na URL): `(portfolio)/`, `(documents)/`, `(admin)/`, `(ai)/`. O Cockpit-Views-Matrix já aprovado (8 perfis: Acionista/Conselho, C-Level, Diretoria, PMO, Gestor de Portfólio, Gerente de Programa/Projeto, Analista/Contribuinte, Externo autorizado) já cobre a lista de público-alvo desta EO (CEO, CIO, PMO, Gerentes de Programa, Gerentes de Projeto, Coordenadores, Analistas) quase integralmente — **"Coordenadores" não é um perfil nomeado à parte** hoje; mapeia naturalmente sob "Gerente de Programa/Projeto" ou "Analista/Contribuinte", mas essa equivalência não foi formalmente decidida e fica registrada como pendência (Seção 8).

### 4.5 Estrutura de integrações (Integration Hub)

Um `IntegrationConnector` Protocol (mesmo padrão de `CredentialVerifier` em `identity/interfaces.py`):

```python
class IntegrationConnector(Protocol):
    def authenticate(self, credentials: ConnectorCredentials) -> None: ...
    def fetch(self, since: datetime | None) -> Iterable[ExternalRecord]: ...
    def map_to_domain(self, record: ExternalRecord) -> DomainEntity: ...
```

Cada conector (Jira, Azure DevOps, MS Project, SAP, Oracle, Power BI, Teams, SharePoint, GitHub, Google Workspace, Outlook) implementa este contrato uma vez; credenciais sempre por organização (mesma disciplina multi-tenant do Épico 1). O Systems-Responsibility-Matrix já aprovado define, para cada sistema externo, o que ele continua possuindo (execução) versus o que a STRATECH assume (inteligência/governança) — as integrações **enriquecem**, nunca substituem, o dado nativo do PMO (Data-Ownership-Matrix já aprovado: Nativo/Sincronizado/Referenciado/Derivado/Calculado/Enriquecido-por-IA).

### 4.6 Estrutura administrativa

Telas mínimas do Épico 5 (Org/User/Role/Project) evoluem para: gestão de credenciais de conectores, log de auditoria, gestão de papéis — sempre atrás do motor de RBAC do Épico 3, nunca um sistema de permissão paralelo.

### 4.7 Arquitetura para IA

Formaliza o que os 3 agentes atuais já provam informalmente: `src/agents/<accelerator>/agent.py` + `prompts/` + `output_parser.py` compartilhado, sobre o `LLMProviderFactory` e o `PromptRegistry` já existentes — **nunca um segundo provider, nunca um segundo registry** (regra CLAUDE.md). Todo novo Accelerator (12 ao todo, per AI-Accelerators-Map já aprovado) segue essa forma. Contrato formal de evidência/confiança/validação humana (ADR-V2-007, já aprovado) passa a ser explícito em `output_parser.py`, não apenas implícito. `PMOWorkflow` evolui de stub para orquestrador real somente quando a Release 0.5 (Event & Orchestration) for autorizada — não antes.

### 4.8 Arquitetura documental

Document Intelligence como **camada de referência** (ADR-V2-005 já aprovado — não GED nativo): documentos (TAP, Atas, Business Case, Contratos, Normativos, Lições Aprendidas) residem no sistema de origem (SharePoint/Google Workspace/anexo do cliente) ou como upload direto; STRATECH armazena metadado + ponteiro de versão + extração de texto + vínculo com o Projeto/Programa/Decisão a que o documento serve de evidência. A IA indexa o texto extraído para consulta — isso é exatamente o Accelerator "Knowledge Intelligence" já mapeado (Release 0.5) — fechando o gap descrito na Seção 3, item 4.

### 4.9 Estratégia de evolução incremental

Reafirma ADR-V2-001 (evolução incremental por release, nunca reescrita total) e acrescenta o Product Engineering Framework recém-institucionalizado (EO-021, PR #43): todo domínio/módulo novo passa primeiro por uma **Capability Blueprint** aprovada pelo Founder — as regras de negócio que esta própria Engineering Order descreveu em prosa (Cronogramas, Custos, Riscos, etc.) passam a ser capturadas formalmente por capacidade, não apenas narrativamente em uma mensagem.

### 4.10 Roadmap técnico da V2

Reafirma o `Release-Roadmap-0.1-to-0.5.html` já aprovado — nenhum novo roadmap é proposto:

| Release | Cobre da visão desta EO |
|---|---|
| 0.1 — Enterprise Foundation (em andamento, Épicos 1-2 concluídos) | Organização, identidade, RBAC inicial |
| 0.2 — Portfolio & Governance Foundation | Portfólio, Programa, convites, papéis expandidos |
| 0.3 — AI Foundation | Portar os 3 Accelerators para `Project` real, contrato formal de evidência |
| 0.4 — Integration Hub | Jira/Azure DevOps/MS Project/SAP/Oracle/Power BI/Teams/SharePoint/GitHub/Google Workspace/Outlook + Document Intelligence |
| 0.5 — Event Orchestration | `PMOWorkflow` real, Knowledge Intelligence sobre documentos |

---

## 5. Estratégia de migração

- **Sem reescrita.** Strangler pattern já em curso: o Épico 1 introduziu o schema multi-tenant ao lado do `analysis_records.project_name` livre; o Épico 4 (já planejado) completa o corte para a entidade `Project` real.
- **Sem quebra de compatibilidade.** Todo endpoint novo é aditivo; nenhum contrato de API existente muda sem necessidade (regra explícita desta EO, já seguida desde o Épico 1).
- **Multi-tenant desde o primeiro dia** — já verdadeiro, nada a migrar retroativamente.
- Document Intelligence e Integration Hub nascem como módulos novos em `src/services/`, com risco zero para os 3 agentes existentes até que a Release 0.3 explicitamente os porte.

## 6. Épicos técnicos e ordem de implementação

**Nenhum épico novo é inventado aqui** — a ordem abaixo reafirma o que já está aprovado no Macro Backlog da Release 0.1 e no Release Roadmap 0.1-0.5, para responder objetivamente ao pedido de "ordem de implementação" desta Engineering Order:

1. **Épico 3 — Organização e RBAC inicial** (próximo, não iniciado): motor de permissões, segregação cross-tenant em CI.
2. **Épico 4 — Projeto como entidade real**: `Project` com ciclo de vida completo, ligação dos Accelerators existentes.
3. **Épico 5 — Auditoria e administração mínima**: log de auditoria, telas administrativas.
4. **Épico 6 — Validação e documentação**: contínuo.
5. **Release 0.2 — Portfolio & Governance Foundation**: Portfólio/Programa reais, convites, papéis expandidos.
6. **Release 0.3 — AI Foundation**: contrato formal de Accelerator, portar os 3 existentes.
7. **Release 0.4 — Integration Hub + Document Intelligence**: primeiro conector de referência, gestão documental.
8. **Release 0.5 — Event Orchestration**: `PMOWorkflow` real, Knowledge Intelligence.

## 7. Aderência aos princípios exigidos

| Princípio exigido | Como já é/será satisfeito |
|---|---|
| SOLID | Injeção de dependência via construtor já usada em `AuthService`/rotas; `interfaces.py` como Protocols garante Dependency Inversion e Open/Closed (novo conector = nova implementação, zero mudança no consumidor) |
| Clean Architecture | Camadas já separadas (`agents` → `services` → `database`/`llm`, `api` só HTTP); regra explícita de "módulo só expõe interface pública" (Seção 4.3) |
| DDD (quando fizer sentido) | Cada domínio do Domain Map já aprovado vira um módulo com sua própria linguagem ubíqua (`models.py`); não aplicado onde não agrega valor (ex.: CRUD simples de admin) |
| API First | Contratos de API já vêm antes da implementação (Pydantic models em `routes/auth.py`); mantido para todo domínio novo |
| Multiempresa | Já estrutural desde o Épico 1 |
| RBAC | Papéis já no schema; motor de aplicação é o próximo épico (não iniciado nesta proposta) |
| Observabilidade | Não avaliado em profundidade nesta proposta — gap a tratar em uma ADR dedicada (não decidido aqui) |
| Segurança | Argon2id, BFF, segregação cross-tenant já comprovados por teste real |

## 8. Pendências que exigem decisão do Founder (não decididas unilateralmente)

1. **"Issues" e "Mudanças" (Change Requests)** não estão no Domain Map aprovado — precisa de ADR para decidir se entram no domínio 2 ou merecem domínio próprio.
2. **"Recursos" (gestão de recursos/capacidade)** — mesma situação.
3. **"Demandas" (intake)** — mesma situação.
4. **Equivalência "Coordenadores" → perfil do Cockpit-Views-Matrix** — não formalizada.
5. **Observabilidade como pilar arquitetural formal** — ainda sem ADR ou épico dedicado (Master Roadmap já registra isso como pilar de maturidade em 0%).

Nenhuma implementação, Capability Blueprint ou Engineering Order de codificação será iniciada a partir desta proposta sem sua aprovação explícita.

---

## Revisão 2 — Product Charter (não substitui as Seções 1-8, incorpora clareza nova)

> Adicionada em resposta ao "STRATECH V2 — Product Charter + Engineering Order", que redefine o processo de desenvolvimento e explicita o domínio de negócio com granularidade maior que a Engineering Order anterior. As Seções 1-8 acima permanecem válidas e não são reescritas — esta revisão aponta o que mudou e o que exige decisão explícita antes de qualquer implementação.

### R2.1 — Resolução parcial das Pendências da Seção 8

O Product Charter lista explicitamente **Gestão de Demandas, Gestão de Recursos, Gestão de Issues, Gestão de Mudanças** como domínios centrais — isso confirma a intenção do Founder para as pendências 1-3 da Seção 8 (que hoje **não existem** no Domain Map aprovado do Blueprint v2.0). Isso ainda não é uma extensão formal do Domain Map — é a evidência de que ela deve acontecer. Proponho formalizá-la como **ADR-V2-008** (próximo ID livre — não decidido nem executado aqui), estendendo o domínio "Portfolio, Program & Project Intelligence" com 4 novas entidades de primeira classe: `Demand` (intake, anterior à aprovação como Project/Program), `Resource` (alocação/capacidade), `Issue` (distinto de Risk — já realizado, não potencial), `Change Request` (mudança formal de escopo/prazo/custo, com fluxo de aprovação próprio). **Não implemento essas entidades nesta resposta** — aguardo aprovação do ADR.

### R2.2 — Inteligência Artificial: especialista em PMO, não chatbot genérico

O Product Charter lista 9 capacidades de IA: Análise de Projetos, Análise de Riscos, Executive Brief, Status Report, Resumo Executivo, Análise Documental, Pesquisa Semântica, Consolidação de Indicadores, Apoio à Tomada de Decisão. Mapeamento contra o já aprovado:

| Capacidade pedida | Já existe? |
|---|---|
| Análise de Projetos | **Sim** — `project_status` agent |
| Análise de Riscos | **Sim** — `risk_review` agent |
| Status Report | **Sim** — mesmo agent de Análise de Projetos, reaproveitado |
| Executive Brief / Resumo Executivo | **Parcial** — já existe na V1 (Executive Brief no Workspace/Dashboard); não é um Accelerator próprio, é uma composição dos 3 agents existentes |
| Análise Documental | **Não** — depende do módulo de Gestão Documental (Seção 4.8), inexistente |
| Pesquisa Semântica | **Não** — depende de indexação de texto extraído de documentos; mesmo pré-requisito da linha acima |
| Consolidação de Indicadores | **Parcial** — Dashboard/Portfolio Summary já consolidam indicadores hoje, mas apenas sobre os 3 agents atuais, não sobre dado de integrações externas |
| Apoio à Tomada de Decisão | **Sim** — Decision Center (`/decisions`) já existe na V1 |

**Nenhuma capacidade pedida exige um novo provider de IA ou um novo registry** — todas cabem na arquitetura já proposta na Seção 4.7 (um Accelerator = `agent.py` + prompts + `output_parser.py`, sobre o `LLMProviderFactory`/`PromptRegistry` já existentes).

### R2.3 — Modelo de negócio SaaS (elementos novos, ainda sem decisão arquitetural)

O Product Charter introduz requisitos de plataforma SaaS ainda não tratados nas Seções 1-8: **Licenciamento**, **Feature Flags**, **APIs Públicas**, **Escalabilidade Horizontal**. Nenhum desses tem hoje uma decisão arquitetural — ficam registrados como pendências adicionais (ver R2.5), não implementados nem decididos unilateralmente aqui. Multi-Tenant, RBAC, Auditoria, Observabilidade e Segurança já estão cobertos (Seções 4 e 7).

### R2.4 — Processo de desenvolvimento: pergunta para o Founder antes de prosseguir

O Product Charter define um novo fluxo: **ChatGPT (Chief Product Officer)** define visão/regras/backlog/especificações → **Claude (Principal Software Architect)** analisa impacto, propõe arquitetura, implementa, testa, entrega versão navegável → **Founder** valida executando a aplicação. Isso é uma evolução real do modelo de 3 papéis já formalizado em `docs/governance/GOVERNANCE_MODEL.md` (Seção 1) e `LESSONS_LEARNED.md` (LL-002), onde o ChatGPT é hoje descrito como **"Architecture & Product Advisor"** (revisão arquitetural independente, não definição de backlog/regras de negócio). **Não atualizei `GOVERNANCE_MODEL.md` para refletir isso** — é uma mudança de papel real, não apenas uma nota de rodapé, e o próprio `GOVERNANCE_MODEL.md` (Seção 3, regra 6) exige que mudanças de governança nunca sejam silenciosas. Preciso de confirmação explícita: o papel do ChatGPT passa de revisor de arquitetura para definidor de produto/backlog (substituindo, não somando), ou os dois papéis coexistem?

### R2.5 — Pendências adicionais registradas (somam-se às 5 da Seção 8, não as substituem)

6. Licenciamento (planos, limites por organização) — sem decisão arquitetural.
7. Feature Flags — sem decisão arquitetural (nenhum mecanismo de flag existe hoje no código).
8. APIs Públicas (fora do server-to-server atual, que exige `X-API-Key` interno) — exigiria um modelo de autenticação de API externa novo, ainda não especificado.
9. Escalabilidade Horizontal — sem avaliação de infraestrutura feita (fora do escopo de código-fonte revisado nesta proposta).
10. Papel do ChatGPT como CPO vs. Architecture & Product Advisor (R2.4) — requer confirmação antes de eu atualizar `GOVERNANCE_MODEL.md`.

### R2.6 — Sobre "iniciar imediatamente a implementação" e o modelo de Sprints

O Product Charter pede que, após aprovação, a implementação comece imediatamente, e que toda Sprint termine com produto navegável/executável. Concordo com o modelo de entrega incremental — é consistente com a disciplina de regressão completa já seguida em todo este engajamento. **Ainda não proponho um escopo de Sprint 1 nesta resposta**, porque isso exigiria decidir, antes de você, qual das 4 novas entidades (Demanda/Recurso/Issue/Mudança) ou qual capacidade de IA vem primeiro — uma decisão de produto, não de arquitetura. Pelo próprio Product Engineering Framework que você institucionalizou (EO-021), essa priorização deveria vir de uma Capability Blueprint aprovada, não de mim escolhendo por conta própria.

**Recomendação concreta para destravar a Sprint 1**, sujeita à sua aprovação: começar pelo Épico 3 (RBAC funcional) já aprovado no Macro Backlog — é o único próximo passo que não depende de nenhuma das pendências acima (ADR-V2-008, papel do ChatGPT, licenciamento/feature flags), tem escopo já definido, e entrega uma diferença navegável real (permissões de fato aplicadas, não apenas armazenadas). Alternativa: se você preferir priorizar algo do Product Charter diretamente (ex.: Gestão de Demandas), preciso primeiro do ADR-V2-008 aprovado e de uma Capability Blueprint para essa entidade, conforme o próprio framework que você aprovou.

**Nada foi implementado.** Aguardando sua decisão sobre: (a) ADR-V2-008 (Demanda/Recurso/Issue/Mudança), (b) papel do ChatGPT (R2.4), (c) qual Sprint 1 priorizar.
