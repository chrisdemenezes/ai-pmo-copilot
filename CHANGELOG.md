# Changelog

Formato leve, cronológico, por Sprint — não substitui o Decision Log (decisões) nem o Technical Debt Register (débitos). Cada entrada lista apenas o que mudou de fato no produto.

## Wave 2 — Sprint 1 (2026-07-19): Enterprise Domain persistence

**Adicionado**
- `Portfolio` e `Program` como tabelas reais persistidas (`portfolios`, `programs`), org-escopadas: `Portfolio.organization_id` direto, `Program` escopado transitivamente via `portfolio_id` (Foundation Technical Design §3.10).
- Campos de domínio de `Project` (`program_id`, `code`, `description`, `objective`, `sponsor`, `project_manager`, `status`, `health`, `priority`, datas, `progress_percentage`, `owner_json`, `milestones_json`, `team_json`) adicionados à tabela `projects` já existente (Épico 1) — **sem criar uma tabela `projects_delivery` separada**, per `DOMAIN-BLUEPRINT-PROJECT.md` (Opção A, Fase 1). Todas as colunas novas são nullable; nenhuma linha legada é afetada.
- Migração `0005_domain_persistence` (upgrade/downgrade completos, testados).
- `DomainRepository` (`src/database/domain_repository.py`): criação e leitura org-escopada de Portfolio/Program/Project, com guarda de cross-tenant (`CrossTenantViolationError`, reaproveitado do Épico 1) e o caminho de unificação de um Project legado (`attach_project_to_program`).

**Testes**
- `tests/test_migration_0005_domain_persistence.py` (4 testes: criação de tabelas, ausência de `projects_delivery`, nulidade em linhas legadas, round-trip completo de downgrade/upgrade).
- `tests/test_domain_repository.py` (12 testes: segregação de Portfolio/Program/Project por organização, criação e vínculo de Project, guardas de cross-tenant).
- Suíte completa: 179 testes passando (100% no novo módulo `domain_repository.py`, 98% de cobertura total do backend). `ruff check src tests`: sem apontamentos.

**Não incluído nesta Sprint (próxima Sprint recomendada)**
- API/rotas para Portfolio/Program/Project (Foundation Technical Design §1) — persistência ainda não é lida pelo frontend.
- RBAC enforcement (Foundation Technical Design §4 / `DOMAIN-BLUEPRINT-RBAC.md`).
- Frontend (`web/lib/domain/*.ts`) continua lendo dos arrays semeados em memória — a troca para a API real é a próxima Sprint, não esta.

## Wave 2 — Sprint 2 (2026-07-20): Enterprise API Layer

**Adicionado**
- API REST completa (GET list, GET by id, POST create) para Portfolio (`/api/portfolios`), Program (`/api/programs`) e Project Delivery (`/api/projects-delivery`) — `src/api/routes/{portfolio,program,project_delivery}.py`.
- `DomainService` (`src/services/domain_service.py`): camada de aplicação entre rotas e `DomainRepository`, com a regra "não encontrado" e "não é seu" sempre mapeadas para o mesmo 404 (nunca um 403 que confirme a existência do id em outra organização).
- Toda rota protegida por `verify_api_key` + `enforce_rate_limit` (mesmo padrão de `intelligence.py`) + `get_request_context` — **primeiro consumidor real** dessa dependência desde que foi construída no Épico 2. Escopo por organização é resolvido do header institucional (`X-Stratech-Organization-Id`), nunca de um parâmetro de query informado pelo cliente.
- **RBAC ainda não aplicado nesta Sprint** (por desenho, per diretriz do Founder): a estrutura de autenticação/escopo está pronta para receber `require_permission(...)` (`DOMAIN-BLUEPRINT-RBAC.md`) como mais um `Depends(...)` por rota, na próxima Sprint, sem alterar nenhuma assinatura de rota.
- OpenAPI/Swagger: `/docs` e `/openapi.json` documentam as 9 novas rotas (tags `portfolio`/`program`/`project-delivery`, descrições por endpoint). Versão da API elevada para `0.2.0` (`src/main.py`), com nota de escopo/RBAC na descrição do app.

**Testes**
- `tests/test_portfolio_api.py`, `test_program_api.py`, `test_project_delivery_api.py` (33 testes novos): CRUD básico, escopo por organização (inclusive listagem/`GET by id` cross-tenant retornando 404), 401 sem API key, 400 sem headers institucionais, exclusão de Projects legados sem Program da listagem.
- Suíte completa: 201 testes passando, 98% de cobertura total (100% em `domain_service.py`, `program.py`, `project_delivery.py`; 99% em `portfolio.py`, único gap é a função de wiring de DI nunca exercida sem override, mesmo padrão já aceito em `intelligence.py`). `ruff check src tests`: sem apontamentos.

**Não incluído nesta Sprint (próxima Sprint recomendada)**
- RBAC enforcement fino (`require_permission`) — `DOMAIN-BLUEPRINT-RBAC.md`.
- Migração do frontend (`web/lib/domain/*.ts`) para consumir esta API em vez do array semeado — explicitamente adiada até a API estar estável (diretriz do Founder).
- `PATCH`/`DELETE` — não implementados (delete policy TD-001/002 ainda indefinida; nenhuma Capability hoje precisa de update).

## Wave 2 — Sprint 3 (2026-07-20): RBAC fine-grained enforcement

**Adicionado**
- Migração `0006_rbac_permission_catalog`: catálogo de 6 permissões (`portfolio`/`program`/`project_delivery` × `read`/`write`) + atribuição aos 4 papéis seed do Épico 1 (`organization_admin`/`pmo`: acesso total; `project_manager`: leitura de Portfolio, leitura+escrita de Program/Project; `viewer`: somente leitura).
- `src/services/authorization/` (`interfaces.py`: `PermissionChecker` Protocol; `checker.py`: `SqlPermissionChecker`) + `src/api/authorization.py` (`require_permission(...)` dependency).
- As 9 rotas da Wave 2 Sprint 2 ganham `Depends(require_permission("recurso.ação"))`, inserido após `get_request_context`, sem alterar nenhuma assinatura de rota além disso.
- **Correção de premissa registrada, não uma mudança de Blueprint:** `DOMAIN-BLUEPRINT-RBAC.md` §1 recomendava adicionar `organization_id` a `user_roles` para suportar um usuário com papéis diferentes por organização — na implementação, confirmou-se que `users.organization_id` já é uma FK única (NOT NULL, Épico 1): um usuário nunca pertence a mais de uma organização hoje, então essa extensão de schema não é necessária. Documentado no Decision Log (D-034), não uma edição retroativa do Blueprint.

**Testes**
- `tests/test_authorization.py` (5 testes: `SqlPermissionChecker` contra o catálogo real da migração 0006, por papel).
- `test_portfolio_api.py`/`test_program_api.py`/`test_project_delivery_api.py` reescritos para usar usuários reais com papéis reais (antes usavam um `user_id` sem nenhum papel) + 5 testes novos de enforcement (403 para `viewer` tentando escrever, 403 para usuário sem papel).
- Suíte completa: 211 testes passando, 98% de cobertura (100% em `authorization/checker.py`, `program.py`, `project_delivery.py`; gaps residuais são funções de wiring de DI nunca exercidas sem override, mesmo padrão já aceito em `intelligence.py`). `ruff check src tests`: sem apontamentos.

**Não incluído nesta Sprint (próxima Sprint recomendada)**
- Migração do frontend (`web/lib/domain/*.ts`) para a API real — agora protegida por RBAC de fato, não apenas por autenticação.
- Enterprise Administration (Épico 5 / `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md`) — aguardando ratificação do Founder sobre o nível de escopo (Decision Proposal ainda aberta).

## Wave 2 — Sprint 4 (2026-07-20): Enterprise Administration (Nível 1 + Nível 2 ratificados)

**Ratificação do Founder:** Nível 1 (Usuários, Organizações, Papéis, Auditoria — já era o Épico 5 aprovado) + Nível 2 (Sessões, Segurança, Logs, Health, Configurações — extensão de baixo risco), per `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md`.

**Adicionado**
- Migração `0007_enterprise_administration`: tabela `audit_logs` + permissões `administration.read`/`administration.write` (organization_admin/pmo leem; só organization_admin escreve).
- `AdministrationRepository` + `AdministrationService` + `src/api/routes/administration.py`: 8 endpoints — `GET`/`PATCH /admin/organization`, `GET /admin/users`, `GET /admin/roles`, `GET /admin/roles/{id}/permissions`, `POST /admin/users/{id}/roles`, `GET /admin/audit-log`, `GET /admin/security`.
- **Auditoria retroativa:** `DomainService.create_portfolio/create_program/create_project` (Sprint 1-3) agora registram uma entrada de auditoria a cada mutação — não é uma feature nova isolada, é o Épico 5 aplicado ao que já existia.
- **"Logs" (Nível 2) não é um sistema de logging novo** — reaproveita a mesma tabela `audit_logs` de "Auditoria" (Nível 1), um único store estruturado.
- **"Segurança" (Nível 2)** — endpoint mínimo, somente leitura (`GET /admin/security`): expõe apenas o que já existe (algoritmo de hash Argon2, ausência de MFA). Nenhuma configuração de política nova foi inventada.

**Correção de premissa registrada, não uma mudança de Blueprint:** `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §2 descreveu "Sessões" como "painel é só leitura+revogação sobre o que já existe" — na implementação, confirmou-se que **não existe** armazenamento server-side de sessões (`auth_service.py`: "No server-side session store exists yet", cookie HMAC stateless). Um painel real de Sessões exigiria um componente de arquitetura novo (session store), fora do escopo de "extensão de baixo risco" assumido pelo Blueprint. **Não implementado** — registrado no Decision Log (D-035), não construído como uma lista falsa. "Configurações" também não implementado, per o próprio adiamento do Blueprint (precisa de definição de produto antes de Technical Design).

**Testes**
- `tests/test_administration_repository.py` (13 testes) + `tests/test_administration_api.py` (17 testes, incluindo um teste end-to-end que cria um Portfolio via API e confirma que aparece no audit log).
- Bug encontrado e corrigido durante o desenvolvimento: `AdministrationRepository.assign_role()` retornava um objeto SQLAlchemy expirado após `commit()` sem `refresh()`, causando `DetachedInstanceError` na serialização da resposta — mesmo padrão já usado em `create_organization`/`create_user`, só que esquecido aqui; corrigido antes do commit.
- Suíte completa: 241 testes passando, 98% de cobertura, `ruff check src tests` sem apontamentos.

**Não incluído nesta Sprint (aguardando decisão futura)**
- Sessões (requer session store — não existe hoje, decisão de arquitetura nova).
- Configurações (requer definição de produto — Blueprint já adiou isso).
- Migração do frontend para a API real (Sprint 5, aprovada e em andamento).

## Wave 2 — Sprint 5 (2026-07-20): Frontend migrado para a API real (fim do mock de domínio)

**Aprovação do Founder:** migração do frontend para a Enterprise Domain API, condicionada à API estar estável e versionada (0.3.0, RBAC aplicado) — condição satisfeita.

**Mudado**
- `web/lib/domain/{portfolio,program,project}.ts`: os corpos de `listPortfolios()`/`listPrograms()`/`listProjects()` agora fazem `fetch()` real via BFF — **os arrays semeados foram deletados do frontend** (sem período de dupla fonte de verdade, per Foundation Technical Design §2.16 passo 3). Nenhum hook, página ou componente mudou — o seam prometido desde a Capability 01 (D-011) pagou exatamente como desenhado.
- Migração `0008_domain_seed`: os dados semeados mudam de casa (frontend → banco), nas duas organizações por desenho ("Organização Principal" e "Demo Organization"), preservando o que toda página exibia. **Unificação Fase 2 executada para nomes colidentes:** um Project legado com o mesmo nome de um seed ("Multilift", "Aurora") é atualizado in-place com os campos de domínio — nunca duplicado (testado, inclusive no downgrade, que preserva linhas legadas).
- Demo user agora recebe o papel `viewer` no bootstrap (novo E existente — reassegurado a cada boot, idempotente): sem isso, o Demo Mode receberia 403 em toda a Domain API. `assign_role_in_session` tornou-se idempotente para suportar isso.
- Novos BFF routes `web/app/api/bff/{portfolio,program,project-delivery}/route.ts` sobre um helper compartilhado (`web/lib/bff/domain-proxy.ts`): sessão → headers institucionais `X-Stratech-*` resolvidos server-side (nunca do browser), 401 sem sessão, mesmo contrato de timeout/erro do BFF do dashboard.
- E2E mock backend (`web/e2e/mock-backend.mjs`) ganhou os 3 endpoints de domínio com os mesmos dados do seed real — a cadeia página → hook → fetch → BFF → backend é exercitada de ponta a ponta pela suíte Playwright.

**Testes**
- Backend: 245 passando (4 novos: migração 0008 × 3, papel do demo user × 1; 2 testes de migração pré-existentes ajustados por afirmarem contagens que o seed 0008 legitimamente muda). `ruff` limpo.
- Frontend: `tsc` limpo, `eslint` limpo, 436 testes unitários passando.
- **E2E completo executado localmente: 3 projetos (lg/md/mobile), 203 testes passando** — a disciplina D-027 aplicada; a cadeia real de fetch validada em navegador de verdade.

## Wave 2 — RC-2 (2026-07-23): PostgreSQL oficial + suíte de testes em PostgreSQL

**Missão de Release Engineering (não uma Sprint) — sem novas funcionalidades, sem tocar domínio/arquitetura.**

**Adicionado**
- `src/database/engine.py` — `resolve_database_url()`/`build_engine()`, seam único reutilizado por `AnalysisRepository` e `alembic/env.py`; pool de conexões (`DB_POOL_SIZE`/`DB_MAX_OVERFLOW`/`DB_POOL_TIMEOUT_SECONDS`/`DB_POOL_RECYCLE_SECONDS`/`DB_POOL_PRE_PING`) totalmente configurável por variável de ambiente.
- `Makefile` + `scripts/rc2-db.sh`/`.ps1` + `scripts/prepare-env.sh`: pipeline completo `setup → db-create → migrate → seed → dev/test`, idempotente, com fallback automático de peer-auth para `sudo -u postgres` em instalações Linux nativas.
- `tests/db.py::temp_database_url` — banco Postgres efêmero por teste (cria/derruba), substituindo os arquivos SQLite temporários em 22 arquivos de teste (~35 ocorrências).
- `docs/product/release-candidate/RC-2/Quick-Start.md` e `Release-Validation-Checklist.md` (novos).
- `docker-compose.yml`: healthcheck no serviço `database` + passthrough das variáveis de pool.

**Mudado**
- `demo/start-demo.sh` roda `alembic upgrade head` antes de iniciar o backend (idempotente) — antes, migrations não rodavam automaticamente por esse caminho.
- `docs/technical/03-development-environment.md` e `docs/technical/05-database-model.md` atualizados para refletir PostgreSQL como banco oficial e a suíte de testes real.
- `.env.example`, `README.md` atualizados.

**Testes**
- Backend: 245 passando, 98% cobertura — cada teste contra seu próprio banco Postgres efêmero.
- Frontend: 436 passando (sem dependência de banco).
- E2E: 203 passando nos 3 projetos (`lg`/`md`/`mobile`) — mock backend mantido por decisão de arquitetura de teste pré-existente (ver D-037).
- `ruff check src tests`: limpo.
- Validação manual completa contra PostgreSQL real: login, CRUD Portfolio/Program/Project, RBAC (403 para viewer), audit log, dashboard, health check — ver Release Validation Checklist.

**Decision Log:** D-037.

## Wave 2 — Encerramento (2026-07-23): Capability User Management (Enterprise Administration)

**Aprovação condicionada do Founder** com 8 critérios técnicos obrigatórios (`DOMAIN-BLUEPRINT-USER-MANAGEMENT.md`, `TECHNICAL-DESIGN-USER-MANAGEMENT.md`), para fechar a lacuna encontrada na revisão de fechamento da Wave 2: o Épico Enterprise Administration estava incompleto por ausência desta Capability.

**Adicionado**
- Migração `0009_user_management`: `users.is_active` (default `true`) + índice único funcional case-insensitive `uq_users_org_email_lower` sobre `(organization_id, lower(email))`, substituindo a constraint case-sensitive anterior.
- `src/services/identity/email_normalization.py` — `normalize_email()`, reutilizado no cadastro, na edição de e-mail e no login.
- 6 novos endpoints REST (`POST/GET/PATCH /admin/users`, status, roles) + 8 novas rotas BFF sob `web/app/api/bff/admin/`.
- Página `/administracao/usuarios` (10º item de navegação): listar, pesquisar, filtrar por status/papel, cadastrar, editar, ativar/inativar (com confirmação), atribuir/remover papel.

**Mudado**
- `AdministrationRepository` passa a compor `EnterpriseRepository` (reuso de `create_user_in_session`/`assign_role_in_session`) em vez de duplicar lógica de criação de usuário.
- `SqlPermissionChecker.has_permission` e `AuthService.authenticate` passam a rejeitar usuários inativos (dois pontos de enforcement, não um filtro espalhado).
- `web/lib/bff/domain-proxy.ts::forwardDomainRequest` generalizado de GET-only para forwarding completo de método/corpo/status.
- `sidebar.tsx`: corrigido um bug latente de overflow no bottom-nav mobile (itens `flex` sem `min-w-0`, exposto pelo 10º item de navegação).

**Governança**
- Auto-inativação do próprio admin e inativação/despromoção do último admin ativo de uma organização bloqueadas com `SELECT ... FOR UPDATE` (fecha corridas entre requisições concorrentes).
- Auditoria: `user.created`, `user.updated`, `user.activated`, `user.deactivated`, `role.assigned`, `role.removed` — nunca com senha/hash.
- Fora de escopo, por decisão explícita do Founder: convites, SSO, MFA, session store, recuperação/reset de senha, stakeholders, configurações gerais de organização.

**Testes**
- Backend: 281 passando (245 pré-existentes + 36 novos), contra PostgreSQL efêmero real. `ruff` limpo.
- Frontend: `tsc`/`eslint` limpos, 437 testes unitários passando.
- E2E completo nos 3 projetos (`lg`/`md`/`mobile`, 81 testes cada) — disciplina D-027 cumprida.

**Wave 2 (Enterprise Platform) declarada 100% completa** para os 3 Épicos que a compõem. Homologação funcional completa permanece adiada para depois da Wave 3, por instrução do Founder.

**Decision Log:** D-038. Ver `docs/product/governance/USER-MANAGEMENT-EXECUTIVE-REPORT.md`.

## Wave 3 — Abertura (2026-07-23): Architecture Review AR-2 + Epic Ledger

**Autorização do Founder** para abrir a Wave 3 (Enterprise Intelligence), sob o fluxo Architecture Review → Domain Blueprint → Technical Design → Implementation → Testing → Executive Report por Epic, sem nova autorização entre Epics salvo 5 gatilhos explícitos.

**Adicionado**
- `docs/architecture/AR-2-WAVE-3-ARCHITECTURE-REVIEW.md`: auditoria de código (nenhum desvio, grounding do Blueprint da Wave 3 revalidado), auditoria de governança e verificação de engenharia (todas as suítes verdes, reaproveitadas da verificação de encerramento da Wave 2 -- nenhuma mudança de código no intervalo).
- Epic Ledger da Wave 3: **W3-1** Project Identity Unification (TD-008 Fase 3), **W3-2** AI Platform Foundation, **W3-3** Risk Advisor (prova de conceito) liberados; Knowledge Platform e os demais 7 Enterprise Agents bloqueados por Decision Proposal ao Founder (`ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §15, nova seção aditiva).
- `docs/product/governance/AR-2-EXECUTIVE-REPORT.md`.

**Mudado**
- Nenhum código de produção alterado nesta etapa -- apenas documentação/governança. `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §11 corrigido (não reescrito): o gatilho de TD-008 Fase 3 nunca dependeu de uma tabela `projects_delivery` separada (que nunca chegou a existir), apenas do início da Wave 3.

**Decision Log:** D-039.

## Wave 3 — Epic W3-1 (2026-07-23): Project Identity Unification (TD-008, Fase 3a)

**Adicionado**
- `docs/architecture/DOMAIN-BLUEPRINT-PROJECT-IDENTITY-UNIFICATION.md` e `TECHNICAL-DESIGN-PROJECT-IDENTITY-UNIFICATION.md`.
- `tests/test_project_summary_service.py`: teste novo cobrindo o bug de agrupamento por variação de espaço em branco.

**Mudado**
- `src/services/project_summary_service.py`: `summarize()`/`summarize_portfolio()` agrupam por `project_id` (já populado em toda escrita desde o Épico 1) em vez de `project_name` bruto -- corrige duplicidade real no portfólio agregado quando o mesmo projeto é referenciado com variação de espaço em branco.
- `src/api/routes/intelligence.py`: `ProjectSummaryResponse` ganha `project_id: int | None` (aditivo).
- `web/lib/dashboard/types.ts`: `ProjectSummary` ganha `project_id?: number` (opcional -- nenhuma fixture de teste existente precisou mudar).

**Testes**
- Backend: 282 passando (281 + 1 novo). `ruff` limpo.
- Frontend: `tsc`/`eslint` limpos, 437 testes inalterados. Spot-check E2E (`dashboard.spec.ts`+`portfolio.spec.ts`, `lg`) 20/20 -- mudança não toca comportamento de frontend nem o mock E2E.

**Escopo explicitamente não incluído:** migrar toda a superfície de Dashboard/Portfólio/Decision Center/Executive Focus/Workspace de `project_name` para `project_id`, aposentando `ProjectSummary` (TD-008 Fase 3b) -- documentado como trabalho futuro de escopo muito maior, não decidido silenciosamente.

**Decision Log:** D-040. Ver `docs/product/governance/W3-1-EXECUTIVE-REPORT.md`.

## Wave 3 — Epic W3-2 (2026-07-23): AI Platform Foundation avaliado e adiado

**Nenhum código produzido.** O Domain Blueprint deste Epic (`docs/architecture/DOMAIN-BLUEPRINT-AI-PLATFORM-FOUNDATION.md`) auditou as 7 sub-áreas propostas (Provider Strategy, Model Registry, Model Routing, Prompt Versioning, Cost/Token Governance, AI Observability, Evaluation Framework) e encontrou zero consumidor real hoje para 6 delas, e nenhum requisito ativo para a sétima (Cost/Token, apesar de um gap real: `ProductionLLMProvider` descarta o `usage`/tokens que a Anthropic já devolve). Construir qualquer uma delas agora seria arquitetura especulativa sem caso de uso -- contra a disciplina "não fazer mais do que o necessário".

Epic marcado como **adiado, não cancelado**, com gatilhos explícitos de reabertura documentados. A Wave 3 avança para o Epic W3-3 (Risk Advisor), que tem um entregável concreto.

**Decision Log:** D-041.

## Repository Audit — Wave 3 Gate (2026-07-23)

Full repository audit (structure, code/dependencies, database/PostgreSQL, tests/quality, security, docs/governance coherence) required by the Founder before updating `main` and starting Epic W3-3. Full report: `docs/product/governance/REPOSITORY-AUDIT-WAVE-3.md`.

**Found (Critical, pre-existing since V1, not introduced by any Wave 2/3 work)**: `src/api/routes/intelligence.py` applies no RBAC or organization scoping on any of its 8 routes; `AnalysisRecord` has no `organization_id`, causing a real cross-tenant data leak now that two real organizations coexist in the same database. **No code fix applied** -- registered as a Decision Proposal (`ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §16) per the Founder's explicit instruction not to decide architectural-impact fixes silently.

**Fixed (low-risk, no product/architecture impact)**:
- `web/lib/mock/mission-control-data.ts`: `EPIC_STATUS`/`RELEASE_STATUS` were stale (Épicos 3-5 "Not Started" despite being done since Wave 2; Releases 0.1/0.2 "In Progress" despite being 100% done); `DOMAIN_EVOLUTION` note on TD-008 updated.
- `README.md`: status line updated from "Wave 2 RC-2" to "Wave 3 in progress."

**Tests**: backend 282 passed, 97% coverage; frontend tsc/eslint clean, 437 vitest passed; full E2E suite (241 tests, 3 projects) 230 passed / 11 failed -- isolated re-run confirmed only 6 failures reproduce deterministically, all already tracked as TD-004/005/006; the rest were transient (environment resource contention, not a regression). A PostgreSQL service outage during the audit (environment issue, confirmed via `pg_isready`) caused one contaminated test run, resolved by restarting the service and revalidating clean.

**Recommendation: GO WITH CONDITIONS.** `main` update authorized (this session's changes don't touch the vulnerable files). Epic W3-3 (Risk Advisor) implementation is held pending the Founder's decision on the security Decision Proposal -- it would build directly on the unprotected route.

**Decision Log:** D-042.

## Wave 3 — Epic W3-3 (2026-07-23): Risk Advisor Enterprise Domain Blueprint

`docs/architecture/DOMAIN-BLUEPRINT-RISK-ADVISOR.md` -- covers purpose, actors, domain model (no new entities: reuses `Project`/`AnalysisRecord`), decision flow, LLM integration (no `LLMProvider`/`PromptRegistry` extension needed), explainability (every answer cites its source `AnalysisRecord`), confidence, RBAC, organization scope, audit, conversational interface, acceptance criteria, risks/dependencies, and explicit non-scope (no multi-agent framework, vector store, RAG, long-term memory, orchestration engine, model registry, new prompt registry, or provider router -- confirming the AR-2 guardrail holds).

**No code produced.** Implementation is explicitly held pending two dependencies outside this Epic's control: the Founder's decision on the C-1/C-2 security Decision Proposal (the Risk Advisor would otherwise inherit intelligence.py's missing RBAC/org-scoping), and the main branch merge (PR #45).

**Decision Log:** D-043.

## Baseline consolidation — PR #45 merged to main (2026-07-23)

Per the Founder's authorization, PR #45 (Wave 2 closure + Wave 3 opening, Phase 2 Foundation through the Repository Audit) merged into `main`. Final `main` hash: **`d8ff04d5db3999a3defafdc8ee9362e0ab7308b3`**. Merge commit tree confirmed identical to the source branch (`git diff` empty) -- no surprises introduced. `origin/main` confirmed synchronized.

**Essential checks re-validated directly on `main`:**
- Backend (`pytest`): 282 passed
- `ruff check src tests`: clean
- Frontend `tsc --noEmit`: clean
- Frontend `eslint .`: clean
- Frontend `vitest run`: 437 passed
- PostgreSQL integration: confirmed (entire integration suite already runs on real Postgres)
- Migrations: full upgrade (0001→0009) → downgrade (base) → re-upgrade round trip validated clean on a disposable database

**Incidental finding while validating PR #45**: the real CI failure GitHub reported on the PR revealed `.github/workflows/ci.yml`'s `validate` job never provisioned a PostgreSQL service -- a deterministic failure (not flakiness) since RC-2 made Postgres required for the integration suite. Fixed in the same session (`postgres:16` service, `aipmo`/`aipmo`, `pg_isready` healthcheck) -- both required checks were green before the merge was authorized.

**Per the Founder's explicit instruction, Risk Advisor implementation has not started.** Next: Security Hardening Gate (C-1/C-2).

**Decision Log:** D-044.

## Security Hardening Gate (2026-07-23): C-1 (RBAC in intelligence.py) and C-2 (AnalysisRecord tenant isolation) closed

Closes the 2 critical, pre-existing-since-V1 findings the Repository Audit (D-042) registered as a Decision Proposal. Technical Design (`docs/architecture/TECHNICAL-DESIGN-SECURITY-HARDENING-GATE.md`) confirmed no architectural impact outside the approved scope, so implementation proceeded directly.

**C-1 -- RBAC**: all 8 routes in `src/api/routes/intelligence.py` now require `Depends(get_request_context)` + `Depends(require_permission("intelligence.read"|"intelligence.write"))` -- the same pattern already used by `portfolio.py`/`program.py`/`project_delivery.py`/`administration.py`. New `intelligence.read` (all 4 seed roles) and `intelligence.write` (all except viewer) permissions seeded via migration `0010`.

**C-2 -- Tenant isolation**: `AnalysisRecord` gains `organization_id` (migration `0010`: nullable column -> backfill via a join with `projects.organization_id` -> `NOT NULL` -> FK -> index, with a loud `RuntimeError` if any row can't be backfilled). `save_analysis`/`list_analyses`/`get_analysis` now filter/require `organization_id`. **Deeper root cause found during the Technical Design**: `get_or_create_project_for_name` always resolved to a single hardcoded "Default Organization" regardless of the real caller -- fixed to use the request's actual `organization_id`.

**Added**
- `alembic/versions/0010_security_hardening.py` -- permissions + `organization_id` + backfill + constraints + index.
- `src/api/dependencies.py` -- `build_repository` extracted from `intelligence.py` to break a circular import (`authorization.py` -> `intelligence.py` -> `authorization.py`) once `intelligence.py` needed `require_permission`.
- `docs/architecture/TECHNICAL-DESIGN-SECURITY-HARDENING-GATE.md`.

**Changed**
- `web/lib/bff/domain-proxy.ts`: exported `readSessionIdentity`/`institutionalHeaders` for the 9 BFF routes (Dashboard, Ações, Riscos, and the 6 Workspace routes) that proxy to `intelligence.py` but have bespoke timeout/error-mapping/field-renaming logic that doesn't fit the generic `forwardDomainRequest()` helper. All 9 now resolve the session cookie and forward institutional headers, 401ing without one -- a real, necessary consequence of C-1 that had no coverage before, since the backend routes didn't require it either.
- Audit trail: the 3 analyze routes now record `analysis.meeting_created`/`analysis.risk_created`/`analysis.status_created` via the existing `AdministrationRepository.record_audit`, not a new mechanism.

**Tests**
- `tests/test_intelligence_api.py` rewritten onto the real-Postgres + real-RBAC convention (`test_portfolio_api.py`'s pattern): RBAC 403s parametrized across all 8 routes, `test_meeting_analyzed_by_org_a_is_invisible_to_org_b` (end-to-end proof the audit's live leak can't recur), and audit-trail assertions.
- Migration `0010` validated by a full manual round-trip (upgrade -> downgrade -> re-upgrade) on a disposable database, including a legacy-shape row to prove the backfill.
- **305 backend tests** (282 existing + 23 new/rewritten), **452 frontend tests** (437 existing + 15 new, including the new 401-without-session cases), `ruff`/`tsc`/`eslint` clean.
- Full E2E suite (3 projects) run twice; the 6 observed failures were isolated and confirmed pre-existing to this Gate via an A/B comparison (`git stash`) against the pre-Gate baseline -- none are new regressions.

**Every Founder acceptance criterion confirmed**: no intelligence route accessible without authorization; no `AnalysisRecord` accessible across organizations; PostgreSQL as the official database; migration upgrade/downgrade/re-upgrade validated; full regression approved; multi-tenant isolation tests in place; audit trail updated; no historical-data exposure during the backfill (the `NOT NULL` constraint only applies after the backfill is confirmed complete, with a loud `RuntimeError` otherwise).

**Next, per the Founder's explicit sequencing**: resume Epic W3-3 (Risk Advisor PoC) with the already-approved Blueprint (`DOMAIN-BLUEPRINT-RISK-ADVISOR.md`) -- the dependency that blocked its Implementation (D-043) is now resolved.

**Decision Log:** D-045.

## Wave 3 — Epic W3-2 (2026-07-23): Digital PMO Intelligence Foundation

Per a new permanent strategic decision from the Founder ("STRATECH is an Executive Decision Operating System... the AI operates, executives decide"), Epic W3-2 is redefined from the previously deferred "AI Platform Foundation" (D-041) into the **Digital PMO Intelligence Foundation** -- shared infrastructure every Enterprise Analyst (the Risk Advisor today; any future specialist) must reuse instead of reimplementing.

Full institutional flow followed: `DOMAIN-BLUEPRINT-W3-2-Digital-PMO-Intelligence-Foundation.md` -> `AR-3-W3-2-DIGITAL-PMO-FOUNDATION-REVIEW.md` (approved without reservations) -> `TECHNICAL-DESIGN-W3-2-DIGITAL-PMO-FOUNDATION.md` -> implementation.

**Added**
- `src/services/ai_foundation/` -- 6 shared components: `AIContextEngine` (resolves already-persisted evidence via `AnalysisRepository`, no new query), `RecommendationEngine` (normalizes model output, discards any evidence citation the model invented), `ExplanationEngine` (every recommendation carries a standard rationale, per ADR-V2-007), `render_analyst_prompt` (composes one shared institutional preamble over the existing `PromptRegistry` -- no new registry), `AIFoundationAudit` (delegates to `AdministrationRepository.record_audit`, never logs the model's answer), `ObservabilityRecorder` (latency + token logging via the project's existing structured `logging`, closing the real gap D-041 flagged: `ProductionLLMProvider` discarding `message.usage`).
- `ProductionLLMProvider.last_usage` -- aditive, optional attribute; `LLMProvider` Protocol unchanged.

**Changed**
- Risk Advisor (`ask_risk_advisor`, `RiskAdvisorAgent`) migrated to consume the Foundation -- proof of real reuse, not just a theoretical design. **HTTP contract unchanged** (`RiskAdvisorRequest`/`RiskAdvisorResponse` identical), no BFF/frontend migration needed.
- **Deliberate, registered behavior change** (not a silent regression): the Risk Advisor now synthesizes over the project's **entire risk-analysis history**, not just the latest one -- a genuine improvement for a conversational advisor (historical questions like "has this risk happened before?" now have data to answer), without violating any acceptance criterion.

**No item from the Founder's prohibition list was introduced**: Vector Store, pgvector, embeddings, RAG, Knowledge Platform, permanent Executive Memory, Multi-Agent Framework, autonomous planning/reflection/self-execution, collaborative agents -- none appear in any component. `SessionContext` is explicitly ephemeral (never persisted).

**Tests**
- **335 backend tests** (314 existing + 21 new: 20 Foundation unit tests + 1 for the migrated agent), **468 frontend tests** unchanged (no HTTP contract change), `ruff`/`tsc`/`eslint` clean, Risk Advisor E2E test confirmed passing across all 3 breakpoints after the migration.

**Decision Log:** D-047.

## Wave 3 — Epic W3-3 (2026-07-23): Risk Advisor implemented

Both dependencies blocking the Blueprint's Implementation (D-043) are resolved: C-1/C-2 closed by the Security Hardening Gate (D-045), `main` consolidated (D-044). Technical Design (`docs/architecture/TECHNICAL-DESIGN-RISK-ADVISOR.md`) confirmed no architectural impact outside the Blueprint's approved scope.

**Added**
- `src/agents/risk_advisor/` -- new agent, same convention as the 3 existing Accelerators. `advise(question, risks)` (not `analyze()`: this agent never creates a new analysis, only synthesizes over risks already identified).
- `POST /api/risk-advisor/ask` in `src/api/routes/intelligence.py` -- protected by `intelligence.read` (the same permission already protecting `GET /risks/latest`, its data source; no new permission introduced). Returns a canned "no risks yet" answer without calling the LLM when the project has none. Every question is audited (`risk_advisor.question_asked`), never the model's answer.
- `web/app/api/bff/workspace/[projectName]/risk-advisor/route.ts` -- same bespoke BFF pattern as the 3 `.../analyze/*` routes (session resolution, 60s timeout, error mapping).
- `web/components/workspace/risk-advisor-section.tsx` -- new Workspace section: question field, answer with source-analysis citation, no persisted conversation history.

**No new entity, no migration, no `LLMProvider`/`PromptRegistry` extension** -- confirms the AR-2 guardrail and the Blueprint's own non-scope (no multi-agent framework, vector store, RAG, or long-term memory).

**Tests**
- `tests/test_risk_advisor_agent.py` (3 new) + `tests/test_intelligence_api.py::TestRiskAdvisor` (6 new): RBAC, organization isolation (a risk from another organization is never synthesized over), audit trail without the LLM's answer, and the no-LLM-call fast path when a project has no risks yet.
- **314 backend tests** (305 existing + 9 new), **468 frontend tests** (452 existing + 16 new), `ruff`/`tsc`/`eslint` clean.
- New end-to-end Playwright test (mock backend -> BFF -> hook -> component) passing across all 3 breakpoints; Workspace suite spot-checked (60/63 -- the 3 failures already confirmed pre-existing and unrelated during the Security Hardening Gate's own verification).

**Decision Log:** D-046.

## Superseding Decision (2026-07-23): official Wave Completion Policy; retrospective Wave Completion Review (Waves 1-3) opened

The Founder issued a superseding decision revoking every prior decision that allowed deferring an originally-planned Epic, Capability, or Enterprise Analyst, treating built infrastructure as sufficient to close a Wave, carrying planned scope forward as an open Decision Proposal, or closing a Wave with remaining functional backlog.

**New permanent Wave Completion Policy**: a Wave can only be declared CONCLUÍDA when, simultaneously: 100% of technical and functional scope is implemented; 100% of originally-planned Epics, Capabilities, and Enterprise Analysts are implemented and functional; 100% of Domain Blueprints and Technical Designs have matching implementation; 100% of Executive Reports are published; all unit/integration/E2E tests pass; and zero placeholder/TODO/stub/partial implementation remains in the Wave's scope.

**Substantive change, not just a stricter checklist**: the permanent prohibition on speculative architecture now applies only to work outside a Wave's official plan. Anything that was already part of an approved Wave plan (e.g., Knowledge Platform and the 7 Enterprise Advisors beyond Risk Advisor, both named in `DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md`) stops being speculative and becomes mandatory -- reversing the reasoning D-039/D-041/the Repository Audit (D-042) and the initial `WAVE-3-COMPLETION-REVIEW.md` used to treat them as blocked Decision Proposals that didn't gate Wave 3's closure.

**Immediate action mandated**: a full retrospective Wave Completion Review across Waves 1, 2, and 3 -- comparing original planning, Decision Logs, Mission Control, Domain Blueprints, Technical Designs, Executive Reports, implemented code, and the running application -- to surface and then close every remaining gap.

**No Wave is declared complete by this entry.** This entry records the policy change itself; the retrospective audit and the implementation of whatever gaps it finds are tracked in subsequent Decision Log entries as each is resolved.

**Decision Log:** D-048.

## Wave Completion Review retrospective, item 1 (2026-07-23): Event Foundation implemented

The retrospective Wave Completion Review (D-048) audited Wave 1 against `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §5 and found the Event Foundation 0% implemented despite being fully specified since the Technical Design Sprint. Sequenced as item 1 of the closure plan (`WAVE-COMPLETION-REVIEW-RETROSPECTIVE.md` §6) -- no pending design decision, only implementation of already-approved scope.

**Added**
- `src/services/events/` -- `EventEmitter` (Protocol: `emit(event_name, payload, organization_id) -> None`), `NoOpEventEmitter` (logs only, no other effect -- "the seam exists, the bus doesn't yet"). Wired via `src/api/dependencies.py::build_event_emitter`.
- `DomainService.__init__` now requires an `emitter: EventEmitter` (no default). Its 3 mutating methods emit the 5 events already named in the Technical Design after the repository write and audit record both succeed: `portfolio.created`; `program.created` + `program.linked_to_portfolio`; `project_delivery.created` + `project_delivery.linked_to_program`.
- Design note: since `create_program`/`create_project` always create an entity already linked to its parent atomically (no separate re-parenting API is exposed), the `.created` event and its matching `.linked_to_*` event are emitted together from the same creation call rather than inventing a new "link" operation.

**No item from the Founder's permanent prohibition list was introduced.** No Event Bus, Workflow Engine, or real consumer was built -- `NoOpEventEmitter` is deliberately log-only, exactly as the Technical Design describes for this phase.

**Tests**
- `tests/test_domain_service.py` (5 new, using a `RecordingEventEmitter` fake) + `tests/test_events_noop_emitter.py` (1 new).
- 4 existing API test files updated for `DomainService`'s new constructor signature.
- **341 backend tests** (335 existing + 6 new), `ruff check src tests` clean. No HTTP contract change.

**Decision Log:** D-049.

## Wave Completion Review retrospective, item 2 (2026-07-23): TD-004/005/006 fixed (React Query invalidation race)

The Riscos panel, Comunicação panel, and Executive Memory's "Mudou" insight all read the mutated data through `useWorkspaceLatestByKind`/`useRecentAnalysesByKind`. When "Analisar Projeto"'s mutation invalidated those queries while their first-mount fetch was still in flight, React Query reused the in-flight promise instead of starting a new fetch -- the invalidation was silently discarded once that stale promise resolved.

**Fixed**
- `useSubmitRiskReview`, `useSubmitMeetingIntelligence`, `useSubmitProjectStatus` now call `queryClient.cancelQueries(...)` on the relevant `workspace-latest`/`workspace-recent` keys before `invalidateQueries` in their `onSuccess` -- cancelling the in-flight fetch resets it to idle so the invalidation always starts a genuinely new one.

**Verification**
- Controlled A/B on the same running dev server (no restart between runs): baseline code fails 8/8 on a repeated isolated run of the TD-006 test; with the fix, 8/8 passes. TD-004+TD-005 together: 20/20 passing (`--repeat-each=5`).
- Full E2E suite, all 3 breakpoints: 81/81 (lg), 81/81 (md), 82/82 (mobile), 341 backend tests unchanged, `ruff`/`tsc`/`eslint`/468 frontend tests clean.
- A stale Next.js dev-server build cache (`.next`) was found to cause broad, unrelated full-suite flakiness under this session's sustained hot-reload load -- confirmed independent of this fix (`rm -rf web/.next` eliminated it); noted in `TECHNICAL_DEBT.md` so it isn't mistaken for a regression later.

**Decision Log:** D-050.

## Wave Completion Review retrospective, item 3 (2026-07-24): API Keys implemented -- architectural correction, not a new dependency

The Founder issued a permanent decision: an architectural dependency never authorizes leaving a planned Epic pending -- when one is found, the correct response is to review and remove it if artificial, not wait on a future decision. Specifically for API Keys, the prior Blueprint classified it as depending on a future Integration Hub (Wave 4); auditing that dependency found it was never real -- just the result of an earlier architectural decision. Corrected: **no foundational component may depend on a future component; the reverse is always allowed.** API Keys is reclassified from "depends on Integration Hub" to foundational (same tier as Users/Organizations/Roles/Audit).

**Added**
- `ApiKey` model + migration `0011` (table + `api_keys.manage` permission, `organization_admin` only).
- `AdministrationRepository`/`AdministrationService`: CRUD (create/list/revoke) + `authenticate_api_key` (narrows candidates by non-secret `key_prefix`, then verifies via the same `Argon2PasswordHasher` already used for passwords -- no new hashing infrastructure).
- A second, additive authentication path in `get_request_context`: header `X-Stratech-Api-Key`, alternative to the existing 3 session headers. **Every existing permission-protected route gains API Key auth automatically, with zero changes to its own route wiring** -- a key authenticates as the user who created it, inheriting that user's RBAC exactly as a session would.
- Routes `GET/POST /api/admin/api-keys`, `DELETE /api/admin/api-keys/{id}` (revoke returns `200` with the resource, not `204` -- `forwardDomainRequest`, the shared BFF proxy helper, can't represent a body-less 204; same convention as `remove_role`).
- Frontend: `/administracao/api-keys` page (new "Chaves de API" nav entry), two-step creation dialog (form -> one-time plaintext reveal, does not auto-close), revoke button with confirmation.

**Fixed (pre-existing gaps found during implementation, corrected in-scope, not deferred)**
- `web/proxy.ts::config.matcher` never included `/administracao`/`/administracao/:path*` -- an unauthenticated visitor could load the Administração page shell (BFF calls still 401'd). Affected `/administracao/usuarios` too, not just the new page.
- `app.dependency_overrides` leaked in 3 tests across `tests/test_api_security.py` and `tests/test_rate_limit_api.py` -- exposed only because the new end-to-end auth-path test was the first to exercise the real (non-overridden) `build_repository` path in the full suite.

**Design note (DI):** `AdministrationService` is constructed via a plain function call inside the `X-Stratech-Api-Key` branch, not a declared `Depends(...)` parameter -- a declared dependency on a widely-shared function like `get_request_context` would force FastAPI to eagerly build a real repository on every request, across every existing test file, even when no API key is sent.

**Fixed (E2E infra, found while adding the API Keys nav entry)**
- Adding an 11th nav item exposed the same known Next.js dev-overlay (`nextjs-portal`) click-interception artifact already documented in `workspace.spec.ts`, this time on `portfolio.spec.ts`'s mobile "Priorização" nav-click test (confirmed via controlled A/B: 2/2 pass on baseline, 5/5 fail with the change). Since this test must click the nav bar link itself, it hides the overlay via `page.addStyleTag` before clicking, rather than using `workspace.spec.ts`'s in-page-link workaround.

**Tests**
- New: `tests/test_migration_0011_api_keys.py`, `tests/test_administration_service.py`, `tests/test_identity_context_api_key_auth.py`, `web/e2e/api-keys-admin.spec.ts`.
- Extended: `tests/test_administration_repository.py`, `tests/test_administration_api.py`, `web/components/shell/navigation.test.ts`, `web/e2e/shell.spec.ts` (nav count 10 -> 11).

**Decision Log:** D-051.

## Wave Completion Review retrospective, item 4 (2026-07-24): Configurações da Organização / Tenant System Settings separated and reclassified -- Governance Concluded, not Implemented

Sequencing item 4 ("Tenant/System Settings") initially considered per-organization rate limiting as the buildable scope for "Configurações da Organização." The Founder corrected this: making rate limiting organization-aware is a platform infrastructure improvement, not an Organização Settings feature, and using it to close the Epic would violate the explicit rule against "using infrastructure improvements just to justify closing an Epic." A mandatory repository-wide audit followed: does any official document (Blueprints, Technical Designs, Business Model Blueprint, Mission Control, Decision Log, backlog, roadmap) specify any concrete content for "Configurações da Organização"?

**Result: no.** Every occurrence of the term across the repository is either a bare label in a list of admin sub-areas, or an explicit statement that scope is still undefined -- no field (language, timezone, branding, notifications, default role, feature flags) is named anywhere. `Organization` (`src/database/models.py`) has no settings column.

**Reclassified (`DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` new §0.1), two distinct concepts, two distinct statuses:**
- **Configurações da Organização** (functional preferences) -> **No Defined Functional Scope.** Not an architectural or business-model block -- a genuine absence of a product requirement. Stays out of scope until the Founder defines concrete content; must not be filled with invented behavior or a repurposed infrastructure improvement.
- **Tenant/System Settings** (SaaS commercial model -- plans, billing, per-paying-tenant isolated config) -> **Pending Business Decision (Wave 6 -- `BUSINESS-MODEL-BLUEPRINT.md`).** Depends entirely on that document's 7 unanswered questions -- a real, never-answered business decision, not an eliminable architectural dependency under D-051's permanent principle.

**No code produced.** This item closes as Governance Concluded: the audit is complete, both concepts are formally separated and documented in a non-ambiguous, trackable state, but there is no functional requirement to implement until the Founder changes either status.

**Decision Log:** D-052.

## Wave Completion Review retrospective, item 5 (2026-07-24): server-side sessions -- real session revocation (resolves TD-010)

The STRATECH login cookie was always a stateless HMAC token with no server-side record, so "logout" only discarded the client cookie (the token stayed valid until its 12h expiry) and no session could be listed or revoked early. The Administration Blueprint wrongly assumed Sessões was "just read + revoke over what already exists"; TD-010 recorded that no store existed. Item 5 builds it.

**Added**
- `sessions` table + migration `0012` (+ `sessions.manage` permission, `organization_admin` only). The `session_id` is now minted by the backend at login (`AuthService.create_session`) instead of by the BFF's `crypto.randomUUID()`, so both sides track one id the table can revoke.
- `AuthService.logout()` stops being a no-op and revokes the session row (idempotent). `LoginResponse` gains `session_id`; `web/lib/session.ts` signs that backend-issued id into its cookie instead of generating its own.
- Revocation enforcement in `require_permission` via a new, overridable `build_session_revocation_checker` dependency -- a revoked session is rejected (401) on its next request, not in up to 12h. **Fail-open:** only an id with an explicit `revoked_at` row is rejected; an unknown id (predating the store, or a test fixture) is treated as active, so no existing session breaks. `api-key:` sessions are skipped (already revocable via the key).
- Routes `GET /api/admin/sessions`, `DELETE /api/admin/sessions/{id}` (200 with the resource, not 204). Tenant isolation enforced in `AdministrationService` (checks `organization_id` before revoking, since `session_id` is globally unique). Each revocation is audited (`session.revoked`).
- Frontend: `/administracao/sessoes` page (new "Sessões" nav entry, 12th item), list + revoke-with-confirmation, no creation (sessions are born from login).

**Design note (DI):** the revocation check is a dedicated overridable dependency defaulted to "never revoked" by conftest's autouse fixture (same pattern as `verify_api_key`/`enforce_rate_limit`), so the ~12 existing API test modules -- which use fabricated session ids -- are untouched, while production (never overridden) runs the real DB-backed check.

**Tests**
- New: `tests/test_migration_0012_sessions.py`, `tests/test_session_revocation_enforcement.py`, `web/e2e/sessions-admin.spec.ts`.
- Extended: `test_administration_repository.py`, `test_administration_service.py`, `test_administration_api.py` (all gained a `TestSessions` class), `test_auth_api.py` (login now returns/creates a session), `web/lib/session.test.ts`, `web/components/shell/navigation.test.ts`, `web/e2e/shell.spec.ts` (nav count 11 -> 12).

**Decision Log:** D-053.

## Wave Completion Review retrospective, item 6 (2026-07-24): Invitations (Convites) -- domain decoupled from email infrastructure

The closure plan flagged Convites as blocked on "email sending -- an SMTP/SES provider decision is a prerequisite". A mandatory repository-wide audit separated domain from infrastructure: "Convites e Stakeholders" is approved scope (Master Roadmap §3.2, Release 0.2, Planned/0%) -- so mandatory under D-048 -- but no document defines the invitation functionally (actors, states, expiry, RBAC, audit all UNSPECIFIED) or ties it intrinsically to email. The only email mention is the closure plan's own assumption, describing email as the *delivery mechanism*, never a constituent of the domain. So the email dependency is artificial as a domain blocker, real only as a delivery mechanism.

Implemented the full domain, with the functional spec supplied by the Founder's decision, and isolated delivery behind a `NotificationProvider` abstraction with a `NoOpNotificationProvider` default -- no concrete provider (SMTP/SES/etc.) is chosen. Same discipline as the Event Foundation's `NoOpEventEmitter` (D-049): the seam exists, the provider doesn't yet. The invitation is fully functional without email -- the token is returned once at creation for manual delivery.

**Added**
- `Invitation` model + migration `0013` (table + `invitations.manage` permission, `organization_admin` only). States (pending/accepted/expired/cancelled) are derived from timestamps, never a stored mutable flag -- "expired" needs no background job.
- `src/services/notifications/` -- `NotificationProvider` Protocol + `NoOpNotificationProvider` (logs only). Wired via `build_notification_provider`.
- `AdministrationRepository`/`AdministrationService`: create/list/cancel + token preview/accept. Acceptance is atomic (re-load FOR UPDATE, re-check pending, create user+role via the existing `create_user` path, stamp accepted). Token hashed with the same Argon2 already used for passwords/API keys; narrow-by-prefix lookup like API keys. The invitee sets their own password on accept -- the admin never sees it.
- New `src/api/routes/invitations.py`: admin routes (`POST/GET /api/admin/invitations`, `DELETE .../{id}`, 200 with body) require `invitations.manage`; public routes (`GET /api/invitations/{token}` preview, `POST /api/invitations/accept`) are token-authenticated with no session -- same session-less design as login.
- `web/proxy.ts` exempts `/api/bff/invitations/` from the session gate (like `LOGIN_ROUTE`); `forwardPublicRequest` added to the shared BFF proxy for session-less forwarding.
- Frontend: `/administracao/convites` admin page (13th nav entry, "Convites") with create (two-step link reveal) + cancel-with-confirmation; public `/convite/[token]` acceptance page (outside the session gate).

**Design note:** an invitation's 7-day expiry is an implementation default (documented in `TECHNICAL-DESIGN-INVITATIONS.md`), not an invented product behavior -- the "expired" state the Founder named requires that a validity exist; the concrete duration is a sensible default, same nature as a session's 12h TTL.

**Not chosen, deliberately:** any concrete notification provider (SMTP/SES/etc.). That remains a pending business decision (communication model) that does not block the domain -- a future provider consumes this capability, never the reverse.

**Tests**
- New: `tests/test_migration_0013_invitations.py`, `tests/test_invitations.py` (repository + service + NoOp provider), `tests/test_invitations_api.py` (admin RBAC + public no-session flow), `web/e2e/convites-admin.spec.ts` (incl. public end-to-end acceptance with no login).
- Extended: `web/components/shell/navigation.test.ts`, `web/e2e/shell.spec.ts` (nav count 12 -> 13).

**Decision Log:** D-054.

## Wave Completion Review retrospective, item 7 (2026-07-24): Workspace reclassified as View/UI -- not a domain entity (Governance Concluded)

Item 7 ("Workspaces como entidade") was flagged "A esclarecer" -- the term collides with the existing `/workspace/:projectName` UI route, needing its own Domain Blueprint before any code. A mandatory architectural audit of the whole repository (docs + code) established the true nature of the concept before writing anything.

**Finding:** "workspace" has three senses, only two of which exist, and none is a new domain entity:
- (a) the `/workspace/:projectName` **View/UI** -- a project's analysis page, explicitly "não representa uma entidade persistida", the presentation layer over Portfolio/Project Intelligence + AI Intelligence Layer;
- (b) the **"workspace session"** -- an inherited RFC-001 synonym for the Nível-1 auth session, already realized by the `Session` entity (D-053);
- (c) a proposed administrable **"Workspaces" entity** that does not exist -- no id, lifecycle, invariants, permissions, relationships, or persistence anywhere (`src/database/models.py` has no `workspaces` table; a prior Visual Fidelity Gate already flagged a "Workspaces" selector as design fiction with no FS and no code).

**Classification (Founder's matrix): (A) View/UI.** DDD validation of sense (c) fails on every required element (identity, invariants, lifecycle, relationships, domain responsibility, consistency boundaries). Per the Founder's principle ("not every screen is a domain entity") and CLAUDE.md ("never create parallel architecture / duplicate code"), it must not be promoted: creating a "Workspace" entity would duplicate what Program/Portfolio already do, or the RBAC Organization Scope already provides.

**Decision: not implemented; formally reclassified.** No code produced. "Workspace" is reserved as a presentation-layer term, recorded in the Ubiquitous Language (`DOMAIN-MODEL.md` §1) and formalized in `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §0.2. Any future need to group users/projects under an organizational sub-unit is to be evaluated as an extension of Program/Portfolio or Organization Scope, with a name that does not collide with the product View -- never as a "Workspace" entity built to satisfy a roadmap item.

**Decision Log:** D-055.

## Wave Completion Review retrospective, item 8 — Etapa 1 (2026-07-24): TD-008 Phase 3b -- additive introduction of `project_id` with a dual-key contract

Item 8 is the last technical gap of the retrospective: TD-008 Phase 3b, migrating Project's access key from `project_name` to `project_id`. Per the Founder, this runs as a controlled, auditable migration -- an Impact Assessment (`docs/architecture/TD-008-PHASE-3B-IMPACT-ASSESSMENT.md`) was produced and approved first, and execution proceeds in 5 stages, each concluded/tested/documented/committed separately. This entry is **Etapa 1 (additive, zero removal)**.

**Adicionado**
- `EnterpriseRepository.resolve_project_reference(organization_id, project_id?, project_name?)` -- org-scoped dual-key resolution returning the `Project` (or `None` when neither key is given). Typed exceptions `ProjectNotFoundError`, `AmbiguousProjectNameError`, `ProjectReferenceMismatchError` (`src/database/enterprise_repository.py`).
- Intelligence read routes (`/api/analyses`, `/api/action-items`, `/api/risks/latest`, `/api/projects/summary`) now accept **`project_id` in addition to `project_name`**. A boundary helper `resolve_project_scope` maps the resolution: nonexistent/cross-org id → **404** (never confirms another org's id), id≠name divergence → **409**, ambiguous name → **409** (`src/api/routes/intelligence.py`).
- `project_id` filter threaded through `AnalysisRepository.list_analyses` and `ProjectSummaryService` (`summarize`, `list_action_items`, `list_latest_risks`).
- Migration `0014_analysis_project_id_backfill` -- defensive, idempotent, non-destructive re-backfill of `analysis_records.project_id` from the matching `Project`; **no NOT NULL** (that is Etapa 4). Downgrade is a documented no-op.

**Additividade estrita (nada quebra):** when `project_id` is supplied it is the exact key (`AnalysisRecord.project_id`); a name that resolves uniquely now filters by that id (identical result, now exact); a **never-analyzed name keeps its legacy behavior (empty list, never 404)**. No frontend consumer migrated yet (Etapas 2-3).

**Achado (reduz risco do Impact Assessment):** the `uq_projects_org_name` UNIQUE constraint on `projects(organization_id, name)` already makes two same-named projects in one organization impossible -- so **name ambiguity is structurally impossible today**. The resolver's ambiguity branch is retained as future-proof defensive code; the "duplicate name" risk drops from Medium to ~nil.

**Testes**
- `tests/test_project_resolver.py` (12): the 5 Founder-mandated scenarios (nonexistent name, duplicate name, nonexistent id, id≠name divergence, cross-org access) + whitespace normalization + the constraint invariant.
- `tests/test_intelligence_dual_key_api.py` (9): id-exact filtering, dual-key 404/409 through the real routes, cross-org 404, name-only additivity.
- `tests/test_migration_0014_backfill.py` (2): idempotent backfill + downgrade no-op.
- Suíte backend completa: 449 testes passando (inclui a atualização dos test doubles `FakeService` de `/action-items`, `/risks/latest` e `/projects/summary`, que agora aceitam `project_id` e injetam um repositório stub org-escopado). E2E (lg/md/mobile): 292 testes passando. `ruff check src tests`: sem apontamentos.

## Wave Completion Review retrospective, item 8 — Etapa 2 (2026-07-25): TD-008 Phase 3b -- frontend consumers become dual-key

Etapa 2 of the 5-stage migration: making the **frontend consumers** dual-key capable, coexisting `project_name` and `project_id` throughout. Frontend-only, additive, zero removal -- no `src/` (backend) change. Migrated consumer group by consumer group, each validated.

**G1 -- BFF forwards `project_id`.** The 4 intelligence BFF routes (`/api/bff/workspace/[projectName]/summary`, `/api/bff/workspace/[projectName]/analyses`, `/api/bff/risks/latest`, `/api/bff/action-items`) now forward an optional `project_id` alongside `project_name`. Absent → byte-for-byte the previous behaviour.

**G2 -- types + hooks carry `project_id`.** `WorkspaceSummary` gains `project_id` (the resolver output `/api/projects/summary` already returns since Etapa 1). The scoped hooks (`use-workspace-summary`, `use-latest-risks`, `use-action-items`, `use-workspace-latest`, `use-recent-analyses`, `use-workspace-timeline`) gain an optional `projectId`, forwarded as `project_id` and folded into the React Query key; `project_name` encoding preserved exactly (`%20`, not `+`).

**G3 -- real end-to-end wiring, no new dependency.** In `executive-brief.tsx` (which already co-locates the summary read with the analysis reads), the resolved `project_id` from the summary is reused as the exact key on the sibling reads. While the summary is pending, or the project has no analyses (id null), the reads fall back to name -- panel independence and additivity preserved.

**Arquitetura:** the Workspace stays name-keyed in the URL (UX preserved); `/projects/summary` is the name→id resolution and the resolved id is the key used downstream -- the ratified end-state ("resolve the name to a project_id before any domain operation", never forcing the user to type IDs). No new provider/registry/parallel architecture; 100% reuse of existing hooks/BFF/types.

**Testes**
- New dual-key forwarding tests across the 4 BFF route `.test.ts` files and the hook `.test.tsx` files; new `components/workspace/executive-brief.test.tsx` (2: id threaded when resolved; name-only fallback while pending).
- `tsc` clean, `eslint` clean, `vitest`: 483 testes passando. E2E (lg/md/mobile): 292 testes passando (contra build de produção). Backend inalterado nesta etapa.

**Gate destrutivo (Etapa 4):** removing `project_name` as a key + `DROP COLUMN` still needs **new explicit Founder approval**.

**Decision Log:** D-057.

**Gate destrutivo (Etapa 4):** removing `project_name` as a key and `DROP COLUMN` will only happen once no behavior consumer uses the column as a key, a repository-wide search proves absence, the whole suite is green, backup+downgrade are tested, and **new explicit Founder approval is requested again**.

## Wave Completion Review retrospective, item 8 — Etapa 3 (2026-07-25): TD-008 Phase 3b -- consumers use `project_id` as the primary key

Etapa 3 of the 5-stage migration: the remaining workspace consumers now use `project_id` as their **primary access key**, keeping `Project.name` purely as a display attribute. Frontend-only, additive, zero removal (no `src/` change). `project_name` and `ProjectSummary` are **not** removed here (that is Etapa 4/5).

**Adicionado**
- `lib/hooks/use-resolved-project-id.ts` -- `useResolvedProjectId(projectName)`: reads `useWorkspaceSummary` (the single name→id resolution, **deduplicated by React Query**) and projects the resolved `project_id`. Every consumer reuses the already-resolved id -- no redundant resolution, no extra request.

**Migrado**
- The remaining scoped consumers resolve via that hook and send `project_id` as the exact key: `RisksPanel` + `CommunicationBrief` (`useWorkspaceLatestByKind`), `IntelligenceTimeline` + `AnalysisHistory` (`useWorkspaceTimeline`), `ActionsSection` + `ActionsContextLine` (`useActionItems`). `ExecutiveBrief` already did so in Etapa 2.
- `placeholderData: keepPreviousData` on the 5 scoped hooks (`use-workspace-latest`, `use-recent-analyses`, `use-workspace-timeline`, `use-latest-risks`, `use-action-items`): the name→id key switch keeps the (identical) displayed data with no loading flash -- functional behaviour unchanged.

**Independência dos painéis preservada:** each section renders/fetches by name immediately; the id refines the key once the (deduplicated) summary resolves; nothing blocks anything. Post-mutation invalidations (`useSubmit*`) match by **key prefix** (`["workspace-latest", projectName, kind]` etc.), so they still hit the now id-suffixed queries -- post-analysis reflection unchanged.

**Trade-off (registrado):** preserving panel independence means the id-refinement triggers a second read (deduplicated per summary, smoothed by `keepPreviousData`, same data). Absolute single-request would couple panel latency to the resolver (`enabled` gating) or need fragile cache seeding; the "avoid duplicate requests" directive was met best-effort ("sempre que possível") without sacrificing independence or correctness.

**Testes**
- New `lib/hooks/use-resolved-project-id.test.tsx` (3: resolved id, pending fallback, null-id fallback); updated the workspace component tests to mock the shared resolver.
- `tsc` clean, `eslint` clean, `vitest`: 486 testes passando. E2E (lg/md/mobile): 292 testes passando (contra build de produção; suíte isolada `workspace.spec.ts` 19/19, suíte completa verde em servidor limpo -- o container é propenso a OOM sob carga acumulada). Backend inalterado.

**Gate destrutivo (Etapa 4):** removing `project_name` as a key + `DROP COLUMN` still needs **new explicit Founder approval**.

**Decision Log:** D-058.

## Wave Completion Review retrospective, item 8 — Etapa 5 (2026-07-26): TD-008 Phase 3b -- `ProjectSummary` eliminated, intelligence consolidated on the Project entity

Founder reordered the sequence: run **Etapa 5 before the destructive Etapa 4**, with a **Gate Final de Migração** in between, to further de-risk the only irreversible step. Frontend-only, no DB change.

**Achado:** `ProjectSummary` (`lib/dashboard/types.ts`) and `WorkspaceSummary` (`lib/workspace/types.ts`) were **two duplicated mirrors** of the same read-model — a Project's *intelligence projection* (`total_analyses`/`open_risks`/`pending_action_items`/`latest_health_status` over `AnalysisRecord`), already keyed by `project_id`. The domain `Project` (`lib/domain/project.ts`) is a **different bounded context** (the Delivery entity). Merging the intelligence read-model into the Delivery entity would conflate bounded contexts — rejected. "Consolidar sobre a entidade Project" = anchor the projection on the Project's identity (`project_id`) and remove `ProjectSummary` as a duplicated concept.

**Alterado**
- New canonical `ProjectIntelligenceSummary` (`lib/project/intelligence-summary.ts`): anchored on `project_id` (key, `number | null`) + `project_name` (display only).
- All `ProjectSummary` consumers migrated (Dashboard/Portfolio/Decision Center: `aggregate`, `executive-focus`, `portfolio-view`, `decision-queue`, `use-portfolio-summary`, BFF `dashboard`, and the 4 dashboard widgets).
- All `WorkspaceSummary` consumers migrated (`use-workspace-summary`, `use-resolved-project-id`, `workspace-header`, `executive-brief`, BFF `workspace/[projectName]/summary`).
- `ProjectSummary` and `WorkspaceSummary` type definitions **removed**; `project_id` promoted from optional (Dashboard) to present key (`number | null`).

**Backend inalterado:** `ProjectSummaryService`/`ProjectSummaryResponse` remain — the legitimate producer of the projection (already grouped by `project_id` since Fase 3a). Renaming them would touch the OpenAPI contract with no architectural gain; recorded in the Gate Final for Founder evaluation.

**Testes**
- `tsc` clean, `eslint` clean, `vitest`: 486 testes passando (fixtures updated to carry `project_id`). E2E (lg/md/mobile): 292 testes passando (contra build de produção). Backend inalterado.

**Próximo passo:** o **Gate Final de Migração** (comprovações). A Etapa 4 (destrutiva) só inicia após a aprovação do Gate Final e permanece condicionada a **nova aprovação explícita do Founder**.

**Decision Log:** D-059.

**Decision Log:** D-056.

## Wave 2 — TD-008 Fase 3b, Etapa 4a (2026-07-26): Eliminação aditiva dos consumidores residuais de `project_name` como chave

Gate Final aprovado; `project_id` passa a ser a **única chave de escopo de leitura**. Integralmente aditiva e reversível — nenhuma coluna removida (a `DROP COLUMN` é a Etapa 4b, bloqueada).

**Alterado (backend)**
- `list_analyses` id-only: removidos o parâmetro e o filtro por `project_name` (R1). Novo `AnalysisRepository.resolve_scope_id` (nome→id via `resolve_project_reference`), reutilizado pelo `ProjectSummaryService` e pelo `AIContextEngine` (Risk Advisor).
- `AnalysisRecord.project` (relacionamento `lazy="joined"`) + helper `analysis_display_name` — todo nome de exibição deriva de `Project.name`; o projeto-sentinela "(sem projeto)" mapeia para `None` (preserva a semântica de nulos). Nada lê mais a coluna `project_name` (R3).
- `list_latest_risks` deduplica por `project_id`; `summarize_portfolio` agrupa por `project_id` e exclui o sentinela por identidade (R2).
- `AnalysisSummary`/`ActionItemResponse`/`LatestRiskItemResponse` ganharam `project_id`; `/analyses` e `/analyses/{id}` constroem o display a partir de `Project.name` (R3).
- `save_analysis` deixou de gravar a coluna `project_name` — mantém o link real via `project_id`; a coluna fica `NULL` para linhas novas, sem leitor (R6).

**Alterado (frontend)**
- `decision-queue` e `portfolio-view` juntam por `project_id` (`ExecutiveDecision.project_id`, `groupLatestRisksByProject`/`groupDecisionsByProject` como `Map<number>`) (R4/R5).
- Tipos `LatestRiskItem`/`ActionItemView`/`AnalysisListItem` ganharam `project_id`; `mock-backend` devolve `project_id` e deduplica riscos por id.

**Migração 0015 (Etapa 4b, encenada)** — `alembic/versions_pending/0015_*.py` (fora do `version_locations` ativo): upgrade (`NOT NULL` em `project_id` + `DROP COLUMN project_name`) e downgrade **provados reversíveis em PostgreSQL real** por `tests/test_migration_0015_drop_project_name.py`. O head ativo permanece `0014`; a coluna é preservada até a Etapa 4b (nova aprovação do Founder).

**Nomenclatura backend** — `ProjectSummaryResponse`/`ProjectSummaryService` mantidos e classificados como projeção de leitura/serviço de composição (registrado em `docs/architecture/DOMAIN-MODEL.md`).

**Testes** — `ruff` limpo; `pytest` 449 + teste da 0015; `tsc`/`eslint` limpos; `vitest` 491; Playwright E2E (lg/md/mobile) 292 passando (2 skipped). Novos testes de join por identidade (mesmo id/nomes diferentes → juntam; nomes iguais/ids diferentes → não juntam).

**Decision Log:** D-060.

## Wave 2 — TD-008 Fase 3b, Etapa 4b (2026-07-26): remoção de `project_name`; **TD-008 RESOLVIDO**

Etapa destrutiva (autorizada pelo Founder). `project_id` é a única chave de acesso interno ao Project.

**Removido**
- Migração `0015` **ativada** (`alembic heads` = `0015`): `SET NOT NULL` em `analysis_records.project_id` + `DROP COLUMN analysis_records.project_name` + drop do índice `ix_analysis_records_project_name`.
- Campo `project_name` **removido do ORM** (`AnalysisRecord`); `project_id` passa a `nullable=False`.

**Preservado (Condição 1 do Founder — nome como apresentação)**
- `Project.name` continua sendo a fonte do nome de exibição. O campo `project_name` **permanece nas responses** de intelligence, agora derivado exclusivamente de `Project.name` — **nenhum campo removido das responses, zero regressão de frontend**. A UX de informar/selecionar por nome (resolvida para `project_id` antes de qualquer operação de domínio) é preservada.

**Downgrade íntegro (Condição 2 do Founder)**
- O downgrade da `0015` recria a coluna + índice, relaxa `project_id` para nullable e **repopula `project_name` a partir de `projects.name` via `project_id`** (`UPDATE ... FROM projects`). Provado em PostgreSQL real (`tests/test_migration_0015_drop_project_name.py`): upgrade dropa a coluna + `NOT NULL`; downgrade restaura a coluna com o nome real do Project (não vazia) — uma versão anterior da aplicação que lê a coluna opera sobre nomes de exibição reais.

**Testes** — `ruff` limpo; `pytest` **449 passando** (com a 0015 ativa + teste da 0015); `tsc`/`eslint` limpos; `vitest` **491**; Playwright E2E (lg/md/mobile) **292** passando (2 skipped). Busca global: 0 dependências comportamentais de `project_name`; a coluna não existe mais no schema nem no ORM.

**Encerramento** — todos os critérios do Founder satisfeitos: 0015 ativa; coluna removida; rollback íntegro comprovado; suíte verde; modelo de domínio e docs atualizados; sem compatibilidade temporária desnecessária. **TD-008 declarado RESOLVIDO.**

**Decision Log:** D-061.

## Wave 2 — Closure Review (2026-07-27): Wave 2 (Enterprise Platform) formalmente encerrada

Sete entregáveis produzidos, sem implementação de nenhum Epic da Wave 3.

**Adicionado**
- `docs/product/governance/WAVE-2-CLOSURE-REPORT.md` — objetivos originais, 13 itens implementados, 2 reclassificados como Governança (Configurações da Organização, Workspaces), 3 em Business Pending (Tenant/System Settings, provedor de notificação, nomenclatura backend), débitos técnicos encerrados/remanescentes, decisões arquiteturais, riscos residuais, 5 lições aprendidas e o Readiness Assessment.
- `docs/architecture/ARCHITECTURE-DELTA-WAVE-2.md` — o que mudou/permaneceu/foi simplificado/eliminado; novos padrões (migração dual-key aditiva-primeiro/destrutiva-por-último, seam-antes-de-infraestrutura).
- `docs/architecture/DOMAIN-EVOLUTION-REPORT-WAVE-2.md` — Aggregates que mudaram, entidades consolidadas (`ProjectSummary`+`WorkspaceSummary` → `ProjectIntelligenceSummary`), conceitos extintos, 5 novos princípios de domínio.
- `docs/product/governance/WAVE-2-GOVERNANCE-REVIEW.md` — validação de Decision Log/Mission Control/CHANGELOG/Domain Model/Blueprints/Architecture Documents contra o código atual.

**Corrigido**
- `docs/architecture/DOMAIN-MODEL.md` §6 — drift documental encontrado (descrevia o estado pré-persistência muito depois de a persistência real e a migração do frontend para a API real existirem desde a Sprint 1/5).
- `docs/architecture/TECHNICAL_DEBT.md` — nova seção de classificação final: todos os 8 itens ativos classificados (Resolvido/Postergado/Futuro Roadmap), nenhum sem status.
- `web/lib/mock/mission-control-data.ts` — `ENTERPRISE_PROGRAM_WAVES["Wave 2"]` atualizado de `"In Progress"` para `"Done"`.

**Readiness Assessment:** zero bloqueadores técnicos, arquiteturais, documentais ou de governança. **"Wave 3 Ready"** declarado formalmente.

**Próximo passo:** `docs/product/WAVE-3-EXECUTIVE-PLAN.md` — plano executivo da Wave 3 (objetivos, entregáveis, ordem dos Epics, dependências, riscos, critérios de conclusão), aguardando aprovação do Founder antes de qualquer implementação.

**Decision Log:** D-062.

## Wave 3 — Domain Blueprint (2026-07-27): 2 Decision Proposals resolvidas + 8 entregáveis do Blueprint mestre produzidos

Documentação de arquitetura apenas — **nenhum Epic implementado nesta missão**, conforme diretriz explícita do Founder.

**Decidido**
- **Enterprise Knowledge Platform:** adoção de Vector Store aprovada — implementação inicial `pgvector`, sempre atrás de uma abstração (`KnowledgeRepository`/`VectorRepository`); o domínio nunca depende diretamente da tecnologia.
- **Enterprise Advisor Framework:** adoção de um Framework de Orquestração Multiagente aprovada — infraestrutura de execução apenas; os Enterprise Advisors permanecem conceitos do domínio, cada um com contrato próprio.

**Adicionado**
- `docs/architecture/WAVE-3-DOMAIN-BLUEPRINT.md` — documento mestre: arquitetura em camadas unidirecionais (Advisors → Advisor Framework + Digital PMO Intelligence Foundation → Knowledge Platform → Enterprise Domain), 8 princípios arquiteturais, 6 Bounded Contexts, fluxos de informação (ingestão assíncrona + resposta síncrona estendendo o fluxo já provado por `POST /risk-advisor/ask`).
- `docs/architecture/DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` — os 13 sub-componentes mandatados (Ingestion→Parsing→Chunking→Embeddings→Indexação→Vector Store/`pgvector`→Semantic Search→RAG Pipeline→Knowledge Repository), versionamento, atualização incremental, retenção, cache.
- `docs/architecture/DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` — 5 memórias (documental/operacional/decisões/aprendizados/organizacional), com checklist obrigatória de colisão contra Executive Memory (V1) em §0 — nenhuma alteração feita ao código de Executive Memory.
- `docs/architecture/DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md` — contratos, ciclo de vida, orquestração, isolamento, observabilidade e auditoria comuns a todo Advisor, generalizando o padrão já provado pelo `RiskAdvisorAgent`.
- `docs/architecture/ENTERPRISE-ADVISOR-CATALOG.md` — os 8 Advisors (Risk — já existe — Executive, Strategy, PMO, Portfolio, Delivery, Governance, Document) catalogados; nenhum implementado.
- `docs/architecture/DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md` — pipeline, recuperação semântica, ranking, contexto, grounding (extensão do anti-hallucination guard do Risk Advisor a citações documentais), qualidade das respostas.
- `docs/architecture/WAVE-3-INTEGRATION-BLUEPRINT.md` — integração com Portfolio, Program, Project, Executive Dashboard, Decision Center, Actions, Risks, Lessons Learned, Workspace e a AI Intelligence Layer.
- `docs/product/WAVE-3-EXECUTION-PLAN.md` — supersede `WAVE-3-EXECUTIVE-PLAN.md`; ordem mandatória de Fases (Foundation → Knowledge Services → Advisor Framework → Advisors individuais), dependências, riscos, Gates de aprovação entre Fases.

**Próximo passo:** Architecture Review e aprovação explícita do Founder sobre `WAVE-3-EXECUTION-PLAN.md` antes do início da Fase 1.

**Decision Log:** D-063.

## Wave 3 — AR-6 (2026-07-27): Architecture Review do Domain Blueprint, aprovado sem ressalvas

**Adicionado**
- `docs/architecture/AR-6-WAVE-3-DOMAIN-BLUEPRINT-REVIEW.md` — auditoria dos 8 entregáveis do Blueprint contra as regras do CLAUDE.md, as diretrizes verbatim do Founder (Vector Store/Framework), consistência interna cruzada, grounding em consumidor real (Risk Advisor) e risco de sobre-engenharia.

**Corrigido**
- `docs/architecture/ENTERPRISE-ADVISOR-CATALOG.md` — referência cruzada desatualizada (PMO Advisor apontava ao plano executivo superseded) corrigida para `WAVE-3-EXECUTION-PLAN.md`.

**Veredito:** aprovado para avançar à aprovação do Founder, sem ressalvas.

**Decision Log:** D-064.

## Wave 3 — Fase 1 (2026-07-27): Enterprise Knowledge Platform (Foundation) implementada

Founder autorizou o início da implementação após a AR-6. Primeiro código real desta Wave — nenhum Advisor consome a plataforma ainda.

**Adicionado**
- `docs/product/governance/WAVE-3-SUCCESS-CRITERIA.md` — Definition of Done por Fase (1-4 + W3-8) e critérios objetivos de encerramento da Wave, publicado antes do primeiro commit de implementação (precondição do Founder).
- `docs/architecture/TECHNICAL-DESIGN-ENTERPRISE-KNOWLEDGE-PLATFORM-FASE1.md` — escopo, pré-requisito de infraestrutura (`pgvector`), modelo de dados, arquivos alterados.
- `src/services/knowledge_platform/` (`types.py`, `embedding_provider.py`, `vector_repository.py`, `knowledge_repository.py`) — `KnowledgeRepository` (fachada), `PgVectorRepository` (única classe ciente de `pgvector`), `EmbeddingProvider`/`MockEmbeddingProvider` (determinístico; backend de produção deferido à Fase 2).
- `Document`, `DocumentVersion`, `Chunk` em `src/database/models.py` — escopados por `organization_id`, `project_id` como metadado opcional (nunca chave, mesma disciplina de TD-008).
- Migração `0016` — habilita a extensão `pgvector` + cria as 3 tabelas (aditiva; downgrade remove as tabelas sem remover a extensão compartilhada).
- `pgvector>=0.5.0` (dependência Python) em `requirements.txt`.

**Infraestrutura**
- `scripts/rc2-db.sh` — novo passo idempotente instalando `pgvector` em `template1` (superusuário), para que todo banco novo (app + bancos efêmeros de teste) herde a extensão sem elevar o privilégio do papel `aipmo`.
- `docker-compose.yml` / `.github/workflows/ci.yml` — imagem do serviço Postgres trocada de `postgres:16` para `pgvector/pgvector:pg16`.

**Testes**
- `tests/test_migration_0016_knowledge_platform.py` (upgrade/downgrade/re-upgrade em PostgreSQL real).
- `tests/test_knowledge_platform.py` (14 testes: `MockEmbeddingProvider`, `PgVectorRepository` upsert + busca por similaridade + isolamento cross-tenant, `KnowledgeRepository` ingest→index→search, versionamento sem sobrescrita, escopo por organização).
- Suíte completa: `ruff check src tests` limpo, `pytest` 464 passando, 97% de cobertura total.

**Próximo passo:** Fase 2 (Knowledge Services — Semantic Search, RAG Pipeline, Enterprise Memory Model, Versionamento), per o Gate definido em `WAVE-3-EXECUTION-PLAN.md` §7.

**Decision Log:** D-065.

## Wave 3 — Fase 2 (2026-07-27): Enterprise Knowledge Platform (Knowledge Services) implementada

Founder autorizou a Fase 2 após a Fase 1. Ainda nenhum Advisor implementado — os novos serviços são infraestrutura de plataforma pura.

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-ENTERPRISE-KNOWLEDGE-PLATFORM-FASE2.md` — delimita onde a Fase 2 termina (RAG Pipeline entrega evidência, nunca compõe prompt nem chama `LLMProvider`).
- `src/services/knowledge_platform/rag_pipeline.py` — `RagPipeline`/`RagContext`: recuperação via `KnowledgeRepository.search()` + ranking determinístico (score, depois recência) + `chunk_ids` rastreáveis para grounding futuro; toda chamada logada.
- `src/services/knowledge_platform/enterprise_memory_service.py` — `EnterpriseMemoryService`/`MemoryCategory` (5 categorias): `classify()`/`list_by_category()` sobre documentos já ingeridos, sempre via `KnowledgeRepository`.
- `MemoryRecord` em `src/database/models.py`; migração `0017` (aditiva).
- `ScoredChunk` ganhou `document_version_created_at` (usado pelo ranking do RAG Pipeline).

**Governança**
- Checklist de colisão Enterprise Memory vs. Executive Memory (`DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §0) revalidada explicitamente antes do código — nenhuma sobreposição, nenhum arquivo de `web/lib/executive-memory/` tocado.
- Escopo do ciclo de vida da memória limitado a Captura+Classificação+Consulta nesta Fase — Consolidação e Expiração automática explicitamente adiadas por falta de consumidor real.

**Testes**
- `tests/test_migration_0017_enterprise_memory_model.py`, `tests/test_rag_pipeline.py`, `tests/test_enterprise_memory_service.py` (13 testes novos: migração real, determinismo e ranking do RAG Pipeline, isolamento cross-tenant, classificação e consulta de memória).
- Suíte completa: `ruff check src tests` limpo, `pytest` 477 passando, 97% de cobertura total.

**Próximo passo:** Fase 3 (Enterprise Advisor Framework — contratos, orquestração, infraestrutura comum, observabilidade, auditoria), per o Gate definido em `WAVE-3-EXECUTION-PLAN.md` §7.

**Decision Log:** D-066.

## Wave 3 — Fase 3 (2026-07-27): Enterprise Advisor Framework (Minimum Viable Framework) implementada

Founder autorizou a Fase 3 após a Fase 2, exigindo auditoria obrigatória do Risk Advisor antes de qualquer código. Nenhum Advisor migrado nesta Fase — `RiskAdvisorAgent`/`ask_risk_advisor` permanecem intocados; validação arquitetural do Framework fica para a Fase 4.

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-ENTERPRISE-ADVISOR-FRAMEWORK-FASE3.md` — auditoria linha a linha do fluxo real do Risk Advisor, mapeando o que já é compartilhado (Foundation), o boilerplate duplicável, e o que é mandato explícito do Founder sem uso hoje (RAG).
- `src/services/advisor_framework/types.py` — `AdvisorContract` (Protocol, nomeia a forma já real de `RiskAdvisorAgent.advise()`, sem `input_schema`/`output_schema` genérico) + `AdvisorExecutionError`.
- `src/services/advisor_framework/framework.py` — `AdvisorFramework`: `gather_context`/`gather_rag_context`/`render_prompt`/`call_llm`/`run` (executa exatamente um Advisor por chamada, audita incondicionalmente, retorna `no_evidence()` sem custo de LLM, levanta `AdvisorExecutionError` para saída malformada).
- `docs/product/governance/W3-FASE3-ADVISOR-FRAMEWORK-REPORT.md` — relatório de governança de 8 pontos exigido pelo Founder (artefatos, responsabilidades extraídas, contratos, abstrações não criadas, testes, riscos residuais, confirmação de ausência de acesso direto à infraestrutura).

**Testes**
- `tests/test_advisor_framework.py` (8 testes contra um `_FakeAdvisor` mínimo, nunca o `RiskAdvisorAgent` real).
- Suíte completa: `ruff check src tests` limpo, `pytest` 485 passando, 97% de cobertura total, 100% no novo pacote.

**Próximo passo:** Fase 4 (migração do Risk Advisor ao novo contrato — único ponto em que o Framework é validado arquiteturalmente, ponta a ponta com RAG e LLM reais).

**Decision Log:** D-067.

## Wave 3 — Fase 4 (2026-07-27): Risk Advisor migrado; Advisor Framework validado arquiteturalmente

Founder autorizou a Fase 4 após a Fase 3. Nenhuma capacidade nova criada — apenas validação do que já existia.

**Alterado**
- `src/agents/risk_advisor/agent.py` — `RiskAdvisorAgent` migrado: construtor passa a receber um `AdvisorFramework`; composição de prompt e chamada ao LLM passam por `framework.render_prompt`/`framework.call_llm`; retorno achatado (`{"structured", "answer", "cited_analysis_ids"}`), removendo o wrapper legado `{"agent": ..., "model_output": ...}`.
- `src/agents/risk_advisor/prompts/advise.md` — nova seção suplementar de contexto de documentos indexados (RAG), explicitamente subordinada ao guard-rail anti-alucinação já existente.
- `src/api/routes/intelligence.py` — `ask_risk_advisor` reescrita para construir `AdvisorFramework` e delegar `gather_context`/`gather_rag_context`/`run`; 2 novos DI providers (`build_knowledge_repository`, `build_rag_pipeline`). `RiskAdvisorRequest`/`RiskAdvisorResponse` **inalterados**.
- `src/services/advisor_framework/{types,framework}.py` — `AdvisorContract.advise()`/`AdvisorFramework.run()` ganham parâmetros opcionais `rag_context`/`no_evidence_answer` (default `None`, retrocompatíveis).

**Corrigido (achados detectados pela suíte de regressão já existente, rodada sem alteração)**
- `RiskAdvisorAgent.advise()` devolvia o wrapper legado em vez do dict achatado que `AdvisorContract` já exigia desde a Fase 3 — corrigido.
- `AdvisorFramework.run()` perdia a mensagem de domínio "Nenhum risco identificado ainda para este projeto." — corrigido com `no_evidence_answer`.

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-RISK-ADVISOR-MIGRATION-FASE4.md`.
- `docs/product/governance/W3-FASE4-RISK-ADVISOR-MIGRATION-REPORT.md` — evidências das 6 exigências obrigatórias (rastreabilidade de chunk_ids, no_evidence sem LLM, ausência de acesso direto à infraestrutura, preservação funcional, isolamento entre organizações, cobertura de testes) + avaliação (não declaração) do critério de encerramento da Wave 3.
- `tests/test_risk_advisor_migration.py` (6 testes, contra o Agent real).

**Testes**
- `tests/test_risk_advisor_agent.py` atualizado para a nova assinatura do construtor (+2 testes novos para RAG). Novo teste de regressão 502 em `tests/test_intelligence_api.py`.
- **A suíte pré-existente `test_intelligence_api.py::TestRiskAdvisor` (6 casos) permanece 100% verde sem nenhuma alteração de asserção.**
- Suíte completa: `ruff check src tests` limpo, `pytest` 494 passando, 97% de cobertura total.

**Próximo passo:** decisão do Founder sobre um Wave 3 Closure Review formal antes de declarar a Wave encerrada.

**Decision Log:** D-068.

## Wave 3 — Closure Review (2026-07-27): 5 elementos solicitados pelo Founder produzidos

Founder autorizou este Closure Review em "Founder Decision — Encerramento da Wave 3", após aprovar a Fase 4. Missão documental — nenhum código alterado.

**Adicionado**
- `docs/product/governance/WAVE-3-CLOSURE-REPORT.md` — comparação entre objetivos planejados e entregues (7 Fases entregues 100%; 7 Advisors restantes + Executive Intelligence/W3-8 reclassificados como deferidos por decisão explícita do Founder, não descartados silenciosamente); validação das 5 principais decisões arquiteturais (pgvector atrás de abstração, fronteira do RAG Pipeline, escopo limitado do Memory Model, contrato flat-dict do Advisor Framework, disciplina de "migração fiel"); 5 lições aprendidas; débitos técnicos remanescentes (TD-011/012/013); recomendação formal de GO para a Wave 4.
- `docs/architecture/TECHNICAL_DEBT.md` — nova seção "Classificação Final — Wave 3 Closure Review": TD-011/012/013 classificados como Postergados (gatilho explícito, sem consumidor real hoje); TD-001/002/003/009 reconfirmados sem alteração; TD-004/005/006/007/008/010 seguem Resolvidos. Nenhum item sem classificação.

**Achado registrado (não bloqueador)**
- O escopo original da Wave 3 (`WAVE-3-EXECUTION-PLAN.md` §2/§7) incluía os 7 Enterprise Advisors restantes e o Executive Intelligence (W3-8) — nenhum dos dois foi entregue. A própria decisão do Founder que abre este Closure Review reclassifica esse gap, declarando que a validação arquitetural da Fase 4 já é suficiente para encerrar a Wave. Reconciliação de nomenclatura de roadmap identificada: `mission-control-data.ts` já nomeia "Wave 4" como Enterprise Operations (escopo distinto dos Advisors restantes) — a ser resolvida pelo Founder quando decidir retomar os Advisors.

**Recomendação formal:** GO para o início da Wave 4 — nenhum débito técnico bloqueante, nenhuma decisão arquitetural invalidada, escopo remanescente já reclassificado. Encerramento formal da Wave 3 permanece com o Founder, mediante aprovação deste artefato.

**Decision Log:** D-069.

## Wave 3 — Encerramento oficial (2026-07-27): Founder aprova o Closure Review, Wave 4 autorizada

Founder aprovou formalmente o `WAVE-3-CLOSURE-REPORT.md` em "Founder Decision — Wave 3 Closure", confirmando os 5 elementos do relatório e declarando a Wave 3 oficialmente encerrada.

**Alterado**
- `web/lib/mock/mission-control-data.ts` — `ENTERPRISE_PROGRAM_WAVES["Wave 3"].status` de `"In Progress"` para `"Done"`; `RECENT_DECISIONS`/`PRODUCT_PULSE_TODAY` atualizados com a aprovação formal.

**Condição do Founder para a Wave 4 (pendente, não encerrada nesta entrada)**
- Único condicionante explícito: harmonizar a nomenclatura oficial da Wave no Mission Control e na documentação de planejamento **antes da publicação do primeiro Domain Blueprint** da Wave 4 — resolvendo o achado já registrado em D-069 (o "Wave 4" hoje nomeado como Enterprise Operations é um escopo distinto dos 7 Advisors restantes + Executive Intelligence/W3-8 deferidos pela própria Wave 3).

**Decision Log:** D-070.

## Roadmap — Harmonização oficial (2026-07-27): 8 Waves, Enterprise Advisors e Executive Intelligence destacados da Wave 3

Founder resolveu a condição de D-070 em "Founder Decision — Wave 4 Authorization", antes de qualquer implementação da Wave 4. Missão exclusivamente de governança — nenhum código/arquitetura/domínio/API/teste alterado.

**Decidido**
- Roadmap oficial passa a ter 8 Waves: 1 Enterprise Foundation, 2 Enterprise Platform, 3 **Enterprise Knowledge Platform** (renomeada de "Enterprise Intelligence" -- nome agora reflete o que foi de fato entregue), 4 Enterprise Operations, 5 **Enterprise Advisors** (nova -- os 7 Advisors restantes, antes W3-7b), 6 **Executive Intelligence** (nova -- antes W3-8), 7 **Enterprise Readiness** (nova, sem escopo definido ainda) e 8 **STRATECH Enterprise v1.0** (nova, sem escopo definido ainda).
- Cada Wave passa a declarar explicitamente de quais Waves anteriores depende (recomendação do Founder, adotada) -- reduz risco de inversão de dependências em decisões futuras.

**Alterado**
- `web/lib/mock/mission-control-data.ts` — `ENTERPRISE_PROGRAM_WAVES` reescrito para as 8 Waves oficiais com dependências explícitas.
- `docs/product/ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` — addendum no topo apontando para D-071 e para o Mission Control como fonte viva do roadmap; seções históricas (§2/§5/§7/§8) preservadas sem reescrita, mesma disciplina já usada em D-034/D-035.
- `docs/architecture/TECHNICAL_DEBT.md` — TD-011/012 corrigidos para referenciar "Wave 5 — Enterprise Advisors" em vez de "Wave 4".
- `docs/product/WAVE-3-EXECUTION-PLAN.md`, `docs/product/governance/WAVE-3-CLOSURE-REPORT.md` — nota de atualização apontando para os números de Wave definitivos.

**Preservação de histórico:** nenhum documento publicado sob o nome "Wave 3 — Enterprise Intelligence" foi reescrito ou renomeado.

**Decision Log:** D-071.

## Roadmap — Harmonização aprovada e concluída (2026-07-27): Enterprise Analytics e Productization resolvidos sem novas Waves

Founder aprovou formalmente a harmonização do roadmap em "Founder Decision — D-072", resolvendo a pergunta em aberto de D-071 sobre onde ficam Enterprise Analytics e Productization na estrutura de 8 Waves. Missão exclusivamente de governança.

**Decidido**
- Roadmap oficial confirmado nas 8 Waves de D-071 — sem alteração à lista.
- **Enterprise Analytics** deixa de ser uma Wave independente — passa a ser **capacidade transversal**, construída ao longo das Waves 4, 5 e 6.
- **Productization** deixa de ser uma Wave independente — passa a compor o escopo da **Wave 8 — STRATECH Enterprise v1.0** (distribuição, documentação, empacotamento, instalação, licenciamento, lançamento oficial).
- Nenhuma nova Wave será criada para absorver esses temas. Mission Control permanece a fonte oficial do roadmap vigente.

**Alterado**
- `web/lib/mock/mission-control-data.ts` — Waves 4/5/6 ganham nota sobre Enterprise Analytics como capacidade transversal; Wave 8 ganha o escopo explícito de Productization.
- `docs/product/ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` — addendum (D-071) atualizado, pergunta em aberto resolvida.
- `docs/architecture/TECHNICAL_DEBT.md` — nota junto ao TD-009 esclarecendo que a referência histórica a "Wave 5 Enterprise Analytics" (estrutura de 6 Waves, superada) agora aponta à capacidade transversal, sem reescrever o texto original da Wave 2 Closure Review.

**Autorizado:** início do ciclo institucional da **Wave 4 — Enterprise Operations** (Domain Blueprint → Revisão Arquitetural → Aprovação do Founder → Implementação → Governança → Executive Review).

**Decision Log:** D-072.

## Wave 4 — Domain Blueprint (2026-07-27): Enterprise Operations, grounding obrigatório + modelo operacional

Founder autorizou a Wave 4 em "Founder Kickoff — Wave 4 / Enterprise Operations", exigindo um levantamento (grounding) obrigatório antes de qualquer Blueprint. Missão documental — nenhum código produzido.

**Adicionado**
- `docs/architecture/WAVE-4-DOMAIN-BLUEPRINT.md` — levantamento obrigatório (§1): 5 sítios de emissão real de evento hoje (todos em `DomainService`, sem envelope de observabilidade completo); taxonomia aspiracional do `Event-Map.html` sem nenhum `.emit()` real; 2 workflows manuais síncronos sem evento (`KnowledgeRepository.ingest()`/`index()`, `AdministrationService.create_invitation()`); zero precedente de fila/retry/dead-letter em toda a base; achado crítico -- `src/workflows/pmo_workflow.py` (já reservado por CLAUDE.md, nunca conectado, instrução anterior de não remover) descreve orquestração multiagente já rejeitada pelo Founder e mistura workflow com lógica de negócio. Modelo operacional nascido do levantamento: Event Model (envelope com Event ID/Correlation ID/Timestamp/Tenant/Origin/Payload Version), 3 Event Contracts com produtor real (migração dos 5 existentes + `DocumentIndexed` + `InvitationCreated`), Event Publisher/Dispatcher in-process, Workflow Runtime mínimo (nunca substitui `AdvisorFramework.run()`), Execution Tracking, Retry/Dead Letter mínimos, Integration Gateway, Event Audit (extensão, não substituição, da auditoria de domínio). Epic Ledger W4-1 a W4-6.

**Decision Proposal registrada**
- Destino de `src/workflows/pmo_workflow.py`/`05-ai-orchestration-design.md` -- recomendação de reclassificar como superado sem remover o arquivo, decisão final do Founder antes da Architecture Review.

**Próximo passo:** decisão do Founder sobre a Decision Proposal, em seguida Architecture Review do Blueprint.

**Decision Log:** D-073.

## Wave 4 — Decision Proposal resolvida (2026-07-27): pmo_workflow.py classificado como Historical Superseded Architecture

Founder aprovou a Opção A (Wave 4 Domain Blueprint §6) em "Founder Decision — Wave 4 Decision Proposal: pmo_workflow.py".

**Alterado**
- `src/workflows/pmo_workflow.py` — aviso explícito adicionado ao topo (classificação Historical Superseded Architecture; proibição de import/extensão/uso; orquestração de Advisors substituída pelo `AdvisorFramework`; orquestração operacional pertence ao Workflow Runtime da Wave 4). Docstring histórico original preservado, não substituído. Arquivo não removido.
- `CLAUDE.md` — nota adicionada após a árvore de "Arquitetura oficial" esclarecendo que `workflows/` é reservado ao Workflow Runtime da Wave 4, e que `pmo_workflow.py` não representa a arquitetura vigente. Árvore de diretórios inalterada.
- `docs/architecture/WAVE-4-DOMAIN-BLUEPRINT.md` §6.1 — decisão do Founder registrada, com evidência de busca global documentada (zero imports, zero rotas, zero testes, zero uso em produção).

**Registrado:** gatilho de remoção futura (missão específica de limpeza arquitetural, ausência de dependências reconfirmada, referências históricas atualizadas, remoção isolada). Nenhuma reutilização/adaptação de `pmo_workflow.py` para a Wave 4.

**Restrição permanente:** proibida a coexistência de duas arquiteturas de workflow.

**Verificação:** nenhum comportamento de código alterado (apenas docstring/comentário); `ruff check src tests` limpo.

**Autorizado:** Wave 4 Domain Blueprint segue para Architecture Review.

**Decision Log:** D-074.

## AR-7 — Wave 4 Architecture Review (2026-07-27): veredito GO

Founder autorizou a Architecture Review em "Founder Decision — Wave 4 Architecture Review Authorization", com escopo mínimo de 5 pontos e restrição explícita de não criar documentação redundante.

**Adicionado**
- `docs/architecture/AR-7-WAVE-4-DOMAIN-BLUEPRINT-REVIEW.md` -- único artefato desta missão. Verificação item a item: Event Envelope (6 campos exigidos confirmados em todos os eventos propostos), Workflow Runtime (confirmado como orquestração operacional pura, nunca substitui `AdvisorFramework.run()`, nunca regra de negócio ou decisão de domínio), Event Publisher/Dispatcher (confirmado mínimo, in-process, sem broker/fila/registry genérico/infraestrutura especulativa), Integration Gateway (confirmado como reaproveitamento do padrão `NotificationProvider`/`EmbeddingProvider`), Conformidade arquitetural (CLAUDE.md, ausência de arquitetura paralela, ausência de duplicação, aderência a D-073/D-074, consistência com Waves 1-3).

**Riscos identificados (não bloqueantes, para o Technical Design)**
- Precisão de linguagem na promoção `EventEmitter`→`EventPublisher`; origem do `correlation_id` em chamadas sem um existente; relação entre Execution Tracking e Event Audit; semântica de Retry/Dead Letter.

**Veredito:** GO. Autorizado avançar ao Technical Design da Wave 4, mediante aprovação explícita do Founder a esta Architecture Review.

**Decision Log:** D-075.

## Technical Design — Wave 4 (2026-07-27): Enterprise Operations, 4 condições da AR-7 resolvidas

Founder aprovou a AR-7 ("Founder Decision — Wave 4 Architecture Review Approval") e autorizou o Technical Design, condicionado à resolução documental dos 4 riscos identificados.

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md` -- resolve as 4 condições: (1) `EventPublisher` -- responsabilidades, contrato público, migração atômica dentro do Epic W4-1 (`EventEmitter`/`NoOpEventEmitter` removidos, nunca coexistindo com o novo Publisher), compatibilidade com os 5 produtores existentes confirmada; (2) `correlation_id` -- origem única em `get_request_context`, propagação por parâmetro explícito, workflows sempre herdam do evento disparador; (3) Execution Tracking × Event Audit -- decididos como componentes distintos (`events`/`workflow_executions`), unidos só por `correlation_id`, justificado por cardinalidade não-1:1; (4) Retry/Dead Letter -- mínimo fixo (`MAX_ATTEMPTS=3`, sem backoff, `dead_letter_events` com estrutura mínima). Estrutura de diretórios, contratos públicos, migração de banco, sequência de chamadas ponta a ponta, estratégia de testes e critérios de aceite definidos.

**Restrições permanentes reafirmadas:** brokers distribuídos, filas externas, registries dinâmicos, engines genéricas, plugins, DSLs, infraestrutura especulativa -- todas confirmadas ausentes.

**Próximo passo:** aprovação explícita do Founder a este Technical Design antes de qualquer implementação do Epic W4-1.

**Decision Log:** D-076.

## Wave 4 — Epic W4-1 (2026-07-30): Event Model + Event Publisher, migração atômica concluída

Founder aprovou o Technical Design ("Founder Decision — Wave 4 Technical Design Approval") e autorizou a implementação do Epic W4-1, com 6 critérios obrigatórios e lista de evidências ao final.

**Removido**
- `src/services/events/interfaces.py::EventEmitter` (Protocol, Wave 1, D-049) e `src/services/events/noop_emitter.py::NoOpEventEmitter` — removidos definitivamente, sem período de coexistência com a nova abstração.

**Adicionado**
- `src/services/events/interfaces.py::DomainEvent` — envelope único (frozen dataclass) com os 6 campos exigidos (event_id, event_type, correlation_id, timestamp, organization_id-como-tenant, origin, payload_version) mais payload; `EventPublisher` Protocol (`publish(...) -> DomainEvent`).
- `src/services/events/in_process_publisher.py::InProcessEventPublisher` — implementação real: persiste o envelope em `events` (Event Audit) e despacha via `EventDispatcher`.
- `src/services/events/dispatcher.py::EventDispatcher` — pub/sub in-process, tabela de despacho fixa por `event_type`; Retry/Dead Letter mínimo (`MAX_ATTEMPTS = 3`, síncrono, sem backoff, sem fila; `dead_letter_events` gravado só após a 3ª falha; falha de despacho nunca propaga ao chamador).
- `alembic/versions/0018_wave4_event_publisher.py` — migração aditiva: cria `events` e `dead_letter_events`. `workflow_executions` (Execution Tracking) deliberadamente não criado — pertence ao Workflow Runtime, Epic W4-4, ainda inexistente.
- `tests/test_events_in_process_publisher.py` (3 casos), `tests/test_events_dispatcher.py` (5 casos), `tests/test_migration_0018_wave4_event_publisher.py` (upgrade/downgrade/re-upgrade em PostgreSQL real).

**Alterado**
- `src/services/domain_service.py` — construtor recebe `publisher: EventPublisher`; `create_portfolio`/`create_program`/`create_project` recebem `correlation_id: str` explícito e publicam via `.publish(...)` em vez de `.emit(...)`.
- `src/api/dependencies.py` — `build_event_publisher()` substitui `build_event_emitter()`.
- `src/api/routes/portfolio.py`, `program.py`, `project_delivery.py` — rotas de criação passam `correlation_id=context.request_id`.
- `tests/test_domain_service.py`, `tests/test_portfolio_api.py`, `tests/test_program_api.py`, `tests/test_project_delivery_api.py`, `tests/test_administration_api.py` — migrados para `InProcessEventPublisher`/`EventDispatcher`.

**Achado de implementação (refinamento do Technical Design, não um desvio de escopo):** a plataforma já possui, desde antes desta Wave, um mecanismo de origem única de correlação — `RequestIDMiddleware`/`request_id_var`, já propagado em `RequestContext.request_id`. Em vez de introduzir um segundo gerador de `correlation_id` (o que violaria "nunca duplicar código" e o próprio critério do Founder de "única origem"), a implementação reusa `context.request_id` diretamente. `DomainService` nunca cunha um `correlation_id` — apenas propaga o que recebe.

**Compatibilidade funcional confirmada:** os 5 `event_type` existentes (`portfolio.created`, `program.created`, `program.linked_to_portfolio`, `project_delivery.created`, `project_delivery.linked_to_program`) permanecem idênticos; suíte de API pré-existente (69 casos) roda sem alteração de asserção de comportamento.

**Busca global confirmando remoção completa:** zero `.emit(` em `src/`/`tests/`; zero `import EventEmitter`; zero `from src.services.events.noop_emitter`. Únicas menções restantes são comentários/docstrings históricos.

**Restrições permanentes confirmadas ausentes:** nenhum broker, fila externa, registry dinâmico, engine genérica, plugin, DSL ou infraestrutura baseada em hipótese futura.

**Verificação:** `ruff check src tests` limpo; suíte de testes backend completa (503 testes) passando.

**Recomendação Go/No-Go para o Epic W4-2:** GO.

**Próximo passo:** ciclo institucional retorna para Executive Review antes da autorização do Epic W4-2, per determinação explícita do Founder.

**Decision Log:** D-077.

## Executive Review — Epic W4-1 (2026-07-30): aprovado (GO), harmonização documental, ciclo do Epic W4-2 aberto

Founder analisou o pacote de evidências do Epic W4-1 ("Founder Decision — Epic W4-1 Executive Review") e emitiu veredito **APPROVED — GO**. Epic W4-1 formalmente encerrado.

**Alterado**
- `docs/architecture/TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md` §2 — harmonizado com o comportamento efetivamente implementado (reaproveitamento de `RequestIDMiddleware`/`request_id_var`/`RequestContext.request_id`, em vez do campo/gerador `RequestContext.correlation_id` descrito no documento original). Correção documental, sem nova decisão arquitetural e sem alteração de código.

**Achado de reconciliação de escopo, apresentado ao Founder antes do Technical Design do Epic W4-2:** o Epic Ledger original (`WAVE-4-DOMAIN-BLUEPRINT.md` §7) atribuía Event Dispatcher + Event Audit a W4-2 e Retry/Dead Letter a W4-5 — mas a própria autorização do Founder ao W4-1 exigiu Retry/Dead Letter como evidência obrigatória já dentro do W4-1. Os três componentes já foram entregues no W4-1; o escopo remanescente de W4-2 é apenas Event Metrics.

**Autorizado:** início do ciclo institucional do Epic W4-2 (confirmação do escopo → Technical Design, se exigido → Implementação → Testes → Governança → Executive Review). Nenhum Epic posterior antecipado.

**Decision Log:** D-078.

## Wave 4 Epic Replanning (2026-07-30): W4-2 dissolvido, escopo consolidado no W4-1, Event Metrics deferido, W4-3 promovido

Founder decidiu o replanejamento do Epic Ledger da Wave 4 ("Founder Decision — Wave 4 Epic Replanning"), em resposta ao achado de reconciliação de escopo apresentado na Executive Review do W4-1. **Registrado como replanejamento da Wave, não como alteração arquitetural.**

**Alterado**
- `docs/architecture/WAVE-4-DOMAIN-BLUEPRINT.md` §7 (Epic Ledger) — atualizado para refletir a realidade da plataforma: Event Dispatcher, Event Audit e Retry/Dead Letter mínimo (originalmente atribuídos a W4-2/W4-5) reclassificados como concluídos dentro do W4-1; texto original do Ledger preservado em nova §7.1 para rastreabilidade histórica.

**Decisão**
- Epic W4-2 dissolvido como Epic independente.
- Event Metrics classificado **Deferred — Awaiting First Consumer** (nenhum consumidor real: sem rota, painel, Workflow Runtime ou Advisor).
- W4-3 (`document.indexed` + `invitation.created`) promovido a próximo Epic da Wave 4, dependendo apenas de W4-1.

**Nota de sobreposição registrada, não resolvida nesta decisão:** o Ledger original também atribuía Retry/Dead Letter a W4-5 — mesmo texto agora consolidado no W4-1. O Founder não se pronunciou sobre a existência/dissolução de W4-5; permanece no Ledger, escopo a confirmar quando a sequência o alcançar.

**Verificação:** missão de governança/documentação — nenhum código de produção alterado; `ruff check src tests`/`tsc`/`eslint` seguem limpos.

**Próximo passo:** ciclo institucional do Epic W4-3 autorizado a iniciar, começando pela apresentação de escopo.

**Decision Log:** D-079.

## Wave 4 — Epic W4-3 (2026-07-30): `document.indexed` e `invitation.created` conectados ao padrão do W4-1

Founder aprovou a apresentação de escopo do Epic W4-3 e autorizou implementação direta, sem Technical Design específico — reuso estrito do contrato do W4-1.

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md` §11 — Implementation Note (pontos de publicação, dependências injetadas, correlation_id, momento da publicação, payload definitivo, comportamento em falha), per instrução do Founder de registrar no artefato existente sem criar novo documento.
- Testes: `test_index_publishes_document_indexed_with_full_envelope`, `test_index_does_not_publish_when_the_document_does_not_exist` (`test_knowledge_platform.py`); `test_publishes_invitation_created_with_full_envelope_and_no_secrets`, `test_does_not_publish_when_role_name_is_unknown` (`test_invitations.py`); `test_create_publishes_invitation_created_with_the_requests_correlation_id` (`test_invitations_api.py`, ponta a ponta via HTTP real).

**Alterado**
- `src/services/knowledge_platform/knowledge_repository.py` — `index()` publica `document.indexed` (`{document_id, version_id, chunk_count}`) após commit; ganhou `correlation_id: str` obrigatório; construtor ganhou `event_publisher: EventPublisher` obrigatório.
- `src/services/administration_service.py` — `create_invitation()` publica `invitation.created` (`{invitation_id, email, role_name}`, nunca token/hash) após a criação e a auditoria de domínio; ganhou `correlation_id: str` obrigatório; construtor ganhou `event_publisher: EventPublisher | None = None` opcional, com default real (mesma convenção de `password_hasher`/`notification_provider`).
- `src/api/routes/intelligence.py` — `build_knowledge_repository` injeta o singleton `build_event_publisher`.
- `src/api/routes/invitations.py` — `build_invitation_service` injeta o singleton `build_event_publisher`; rota `create_invitation` passa `correlation_id=context.request_id`.
- Todos os call sites pré-existentes de `KnowledgeRepository`/`.index()`/`AdministrationService` atualizados para as novas assinaturas, sem alteração de asserção de comportamento.

**Achado grounded, não desvio:** `KnowledgeRepository.index()` não tem nenhuma rota chamadora em produção hoje (confirmado por busca global) — exatamente o cenário já identificado e autorizado pelo Blueprint §4 item 2 (produtor real disponível para a Wave 5 sem exigir mudança estrutural futura).

**Compatibilidade funcional confirmada:** nenhuma mudança de retorno/persistência/regra de negócio; nenhum evento publicado quando a operação principal falha.

**Restrições permanentes confirmadas respeitadas:** nenhuma abstração nova, nenhum handler, nenhum Workflow Runtime, nenhum Event Metrics, nenhum Advisor, nenhum correlation_id gerado nos serviços, token/hash/URL nunca no payload.

**Verificação:** `ruff check src tests` limpo; suíte de testes backend completa verde.

**Recomendação Go/No-Go:** GO.

**Próximo passo:** ciclo institucional retorna para Executive Review antes da autorização do próximo Epic.

**Decision Log:** D-080.

## Wave 4 — Technical Design do Epic W4-4 (2026-07-30): Workflow Runtime + Execution Tracking, idempotência definida

Founder aprovou a apresentação de escopo do Epic W4-4 e autorizou o Technical Design, com 4 exigências: confirmar D-079 (workflow sem métrica), fixar a separação Dispatcher/Runtime como princípio arquitetural, documentar a política de idempotência, reafirmar restrições permanentes. **Missão documental — nenhum código escrito.**

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md` §12 — escopo confirmado (`document.indexed → WorkflowRuntime → Execution Tracking`, um único passo, sem métrica); princípio de separação (`EventDispatcher` permanece agnóstico e byte-a-byte inalterado, `WorkflowRuntime` é o único dono de `running`/`completed`/`failed`); contratos públicos (`WorkflowContext`, `WorkflowStep`, `WorkflowRuntime.run(workflow_name, steps, triggering_event) -> WorkflowContext`); política de idempotência (chave `(event_id, workflow_name)`, upsert seguro porque os passos são funções puras, constraint única no banco); migração (constraint adicional em `workflow_executions`); restrições permanentes reafirmadas; riscos residuais.

**Verificação:** `ruff check src tests` limpo; nenhum arquivo de código alterado.

**Recomendação Go/No-Go:** GO para a implementação, condicionado à aprovação explícita do Founder (Executive Review).

**Próximo passo:** nenhuma implementação iniciada — aguarda aprovação do Founder a este Technical Design.

**Decision Log:** D-081.

## Wave 4 — Epic W4-4 (2026-07-30): Workflow Runtime + Execution Tracking

Founder submeteu o Technical Design à Executive Review e aprovou a implementação ("Founder Decision — Epic W4-4 Technical Design Approval"), reafirmando 14 decisões arquiteturais e exigindo evidências específicas.

**Adicionado**
- `src/database/models.py::WorkflowExecution` (`workflow_executions`) — `UNIQUE(event_id, workflow_name)` como constraint de banco.
- `alembic/versions/0019_wave4_workflow_executions.py` — migração aditiva.
- `src/workflows/execution_tracking.py::ExecutionTracker` — único componente ciente de `workflow_executions`; upsert atômico (`INSERT ... ON CONFLICT DO UPDATE`, nunca SELECT-then-INSERT); `sanitize_error()` (tipo+mensagem truncados, nunca stack trace/payload).
- `src/workflows/runtime.py::WorkflowRuntime`/`WorkflowContext`/`WorkflowStep` — `WorkflowContext` só construído a partir do `DomainEvent` recebido (correlation_id herdado de forma estrutural); em falha, registra `failed` e relança a exceção original sem mascarar.
- `src/workflows/document_indexed_workflow.py` — o único workflow autorizado (`document.indexed` → 1 passo no-op → Execution Tracking), registrado como handler comum no `EventDispatcher`.
- Testes: `test_workflow_runtime.py` (9 casos), `test_document_indexed_workflow.py` (2 casos, cadeia completa + Dead Letter), `test_migration_0019_wave4_workflow_executions.py` (round-trip + constraint única).

**Alterado**
- `src/api/dependencies.py::build_event_publisher()` — constrói `WorkflowRuntime`/`ExecutionTracker`, registra o workflow no `EventDispatcher` compartilhado, antes de retornar o `InProcessEventPublisher`.

**Confirmado — `src/services/events/dispatcher.py` com zero linhas alteradas** (`git diff` vazio): o `EventDispatcher` do W4-1 nunca conhece `workflow_executions`, nunca conhece estados de workflow, apenas despacha. `WorkflowRuntime` é o único dono de `running`/`completed`/`failed`.

**Comportamento observado (per especificação do Founder):** falha total produz dois registros independentes — `dead_letter_events` (Dispatcher, W4-1) e `workflow_executions.status="failed"` (Runtime, W4-4) — nenhum lê/escreve a tabela do outro. Reexecução (retry síncrono do Dispatcher) reutiliza a mesma linha de execução, nunca duplica.

**Restrições permanentes confirmadas ausentes:** Event Metrics, Advisors, Integration Gateway, filas/brokers, DSL, Workflow Designer, automação genérica, workflows multi-passo, compensações, reprocessamento posterior, histórico de tentativas, nova política de Retry/Dead Letter.

**Verificação:** `ruff check src tests` limpo; suíte de testes backend completa verde (520 passed).

**Recomendação Go/No-Go:** GO para o encerramento do Epic.

**Próximo passo:** ciclo institucional retorna para Executive Review antes de qualquer Epic posterior.

**Decision Log:** D-082.

## Wave 4 — Encerramento oficial (2026-07-30): Epic W4-6 deferido, Epic W4-5 consolidado, Epic Ledger encerrado

Founder autorizou o Grounding Audit do Epic W4-6 e, em Executive Review, aprovou **NO GO para implementação** ("Founder Decision — Executive Review of Epic W4-6"). **Missão exclusivamente de governança — nenhum código escrito.**

**Grounding Audit:** zero clientes HTTP externos em `src/` (exceto o SDK `anthropic` já usado por `ProductionLLMProvider`), zero adaptadores/gateways, zero webhooks, zero `fetch` externo no frontend, `IntegrationGateway`/`IntegrationContract` nunca existiram no código. `LLMProvider`/`NotificationProvider`/`EmbeddingProvider` já atendem plenamente às necessidades da plataforma, cada um com exatamente um consumidor, sem duplicação nem acoplamento a resolver.

**Decisão:**
- Epic W4-6 classificado **Deferred — Awaiting First Real External Integration Need**.
- Epic W4-5 classificado **Consolidated into W4-1** — o Retry/Dead Letter do W4-1 já cobre qualquer handler, incluindo o Workflow Runtime; nenhum trabalho adicional necessário.
- Epic Ledger da Wave 4 (`WAVE-4-DOMAIN-BLUEPRINT.md` §7/§7.2) atualizado ao estado final: W4-1 Concluído, W4-2 Deferred, W4-3 Concluído, W4-4 Concluído, W4-5 Consolidated into W4-1, W4-6 Deferred. **Nenhum Epic em aberto.**

**Verificação:** `ruff check src tests` limpo; nenhum arquivo de código alterado.

**Missão:** Governança da Wave 4 oficialmente encerrada. Executive Summary de encerramento apresentada, com recomendação Go/No-Go para a abertura institucional da Wave 5 — Enterprise Advisors.

**Decision Log:** D-083.

## Wave 5 — Architecture Kickoff (2026-07-30)

Founder declarou oficialmente encerrada a Wave 4 e autorizou a preparação do Architecture Kickoff da Wave 5 — Enterprise Advisors, como documento orientador para a próxima etapa da STRATECH. **Missão documental — nenhum código escrito.**

**Adicionado**
- `docs/architecture/WAVE-5-ARCHITECTURE-KICKOFF.md` — grounded no `AdvisorContract`/`AdvisorFramework` real (não no `DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md` pré-Fase 3, especulação já superada); achado central de que `AIContextEngine.gather(project_name, kind)` só se encaixa diretamente no Delivery Advisor entre os 7 restantes (Portfolio/PMO/Executive precisam de extensão, Strategy pode não ter evidência hoje, Governance/Document têm fonte de evidência inteiramente diferente); `document.indexed` (W4-3) identificado como o único evento com produtor real já disponível para o Document Advisor; sequenciamento proposto (Delivery e Document Advisor como candidatos ao primeiro Epic, não decidido); princípios permanentes e itens fora de escopo reafirmados.

**Verificação:** `ruff check src tests` limpo; nenhum arquivo de código alterado.

**Próximo passo:** Architecture Review da Wave 5 sobre o Kickoff, seguida de aprovação explícita do Founder antes de qualquer Domain Blueprint individual de Advisor.

**Decision Log:** D-084.

## Wave 5 — Architecture Review: modelo definitivo dos Enterprise Advisors (AR-8, 2026-07-30)

Founder autorizou a Wave 5 Architecture Review, declarando a decisão resultante **permanente** até a STRATECH Enterprise v1.0. **Missão exclusivamente arquitetural — nenhum código, Domain Blueprint, Technical Design ou PoC produzido.**

**Adicionado**
- `docs/architecture/AR-8-WAVE-5-ENTERPRISE-ADVISOR-MODEL-REVIEW.md` — resolve a questão central do Kickoff (D-084): **Opção B decidida** (Advisor recebe evidência previamente coletada por uma camada comum) — estruturalmente exigida pelo portão anti-alucinação já em produção em `AdvisorFramework.run()`. `AIContextEngine` confirmado como coletor de evidências, nunca organizador de contexto. Classificação dos 7 Advisors em 4 classes (A: escopo único — Risk/Delivery; B: agregada — PMO/Portfolio/Executive; C: declarativa — Strategy; D: RAG primário — Document/Governance). Modelo definitivo nomeado **"Framework-Mediated Evidence Assembly"** (Rota → Montagem de Contexto por Advisor → `AdvisorFramework.run()` compartilhado → `Advisor.advise()`). Separações Workflow/Event/Domain reconfirmadas como definitivas e permanentes. 4 riscos residuais registrados, nenhum bloqueante.

**Verificação:** `ruff check src tests` limpo; nenhum arquivo de código alterado.

**Recomendação:** GO para a abertura do primeiro Domain Blueprint da Wave 5 — escolha do primeiro Advisor (Delivery ou Document) permanece decisão do Founder.

**Decision Log:** D-085.

## Wave 5 — AR-8 aprovado com emenda; Document Advisor escolhido como primeiro Domain Blueprint (2026-07-30)

Founder aprovou o AR-8 mantendo inalteradas todas as demais decisões, com um ajuste na definição do `AIContextEngine`, e escolheu o Document Advisor como primeiro Domain Blueprint da Wave 5.

**Alterado**
- `docs/architecture/AR-8-WAVE-5-ENTERPRISE-ADVISOR-MODEL-REVIEW.md` §3/§11 — definição do `AIContextEngine` substituída pela redação institucional oficial: "responsável pela preparação do contexto de IA... coletar, normalizar, consolidar e estruturar evidências para consumo dos Enterprise Advisors, sem executar regras de negócio nem interpretar domínio." A fronteira contra interpretação de domínio permanece intacta; o restante do AR-8 permanece inalterado.

**Decisão:** primeiro Domain Blueprint da Wave 5 = **Document Advisor** (único Advisor com produtor real de evento, Knowledge Platform, RAG Pipeline, Event Pipeline e Workflow Runtime já validados). Autorizada a abertura do Domain Blueprint, seguindo o ciclo institucional completo de 8 etapas, nenhuma etapa antecipada.

**Verificação:** `ruff check src tests` limpo; nenhum arquivo de código alterado.

**Decision Log:** D-086.

## Wave 5 — Domain Blueprint do Document Advisor (2026-07-30)

Etapa 1 de 8 do primeiro Epic da Wave 5. Missão exclusivamente documental — nenhum código, migração ou Technical Design produzido.

**Adicionado**
- `docs/architecture/DOMAIN-BLUEPRINT-DOCUMENT-ADVISOR.md` — grounded na Knowledge Platform (Wave 3) e no Event Pipeline (Wave 4), já prontos e testados. Achado crítico: `RecommendationEngine.build()` filtra citações exclusivamente por `Evidence.source_analysis_id`, tornando estruturalmente necessário que a Montagem de Contexto do Document Advisor popule esse campo com o `chunk_id` real (refina o risco residual #1 do AR-8). Modelo aplicado: Framework-Mediated Evidence Assembly, Classe D. Achado que exige decisão do Founder: `KnowledgeRepository.ingest()`/`.index()` não têm rota HTTP chamadora em produção hoje — duas opções de escopo apresentadas (incluir rota mínima de ingestão no Epic, ou cobrir apenas o Advisor) para a Architecture Review resolver.

**Verificação:** `ruff check src tests` limpo; nenhum arquivo de código alterado.

**Próximo passo:** Architecture Review do Domain Blueprint, resolvendo o gap de Document Ingestion antes de qualquer Technical Design.

**Decision Log:** D-087.

## Wave 5 — AR-9: Architecture Review do Document Advisor (2026-07-30)

Founder emitiu veredito APPROVED CONDITIONALLY sobre o Domain Blueprint do Document Advisor, exigindo resolução de dois pontos antes de qualquer Technical Design. Missão exclusivamente arquitetural — nenhum código, migração ou Technical Design produzido.

**Adicionado**
- `docs/architecture/AR-9-DOCUMENT-ADVISOR-ARCHITECTURE-REVIEW.md` — Decisão 1: Document Ingestion vira **W5-0**, Epic habilitador separado do Document Advisor (W5-1), com fluxo funcional completo (upload → ingest → index → document.indexed já conectado ao Event/Workflow Pipeline → RAG), status/auditoria/tratamento de erro reaproveitando mecanismos já existentes (`get_document()`/`list_versions()`, `AuditLog`, `sanitize_error()`), sem nenhum mecanismo novo. Decisão 2: `Evidence` evolui para um contrato genérico e aditivo (`source_type`/`source_id`/`source_label`/`content`/`metadata`), resolvendo a objeção do Founder contra `chunk_id` em `source_analysis_id` -- compatibilidade com o Risk Advisor preservada (apenas rename de campo em 4 arquivos, zero mudança de lógica), `RecommendationEngine`/portão anti-alucinação/`ExplanationEngine` inalterados. Único impacto estrutural identificado e divulgado: `AIContextEngine`/`AdvisorFramework` ganham um método fino novo (`normalize_rag_evidence`), aplicando concretamente a definição oficial do `AIContextEngine` (D-086) e evitando duplicação entre Document e Governance Advisor (ambos Classe D).

**Verificação:** `ruff check src tests` limpo; nenhum arquivo de código alterado.

**Recomendação:** GO para Technical Design de W5-0, seguido pela evolução do contrato `Evidence`, seguido pelo Technical Design do Document Advisor (W5-1).

**Decision Log:** D-088.

## Wave 5 — Technical Design do Epic W5-0: Document Ingestion (2026-07-30)

Founder aprovou o AR-9 ("Founder Decision — AR-9 Approved", GO para Technical Design do W5-0), oficializando 6 decisões. Missão de documentação -- nenhum código, nenhuma migração escrita.

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-W5-0-DOCUMENT-INGESTION.md` -- API Contract completo (`POST /documents`, `POST /documents/{id}/reindex`, `GET /documents`/`GET /documents/{id}`), extensões aditivas apenas (`chunk_count`, filtro de auditoria por entidade, duas novas permissões `knowledge.write`/`knowledge.read`), zero tabela nova. Fluxo oficial (Upload -> Document -> Version -> Chunks -> `document.indexed` -> Workflow Runtime) verificado contra código real -- `document.indexed` já integralmente conectado ao Event/Workflow Pipeline em produção, zero código novo necessário nesse trecho. Achado crítico registrado: `VectorRepository.similarity_search()` não filtra por versão mais recente -- chunks obsoletos de um documento reingerido permanecem pesquisáveis via RAG; risco residual explicitamente aceito, não resolvido especulativamente. Campo `confidence` em `Evidence` avaliado e recomendada a postergação (sem consumidor real, semanticamente falso para `AnalysisRecord`). `normalize_rag_evidence()` confirmado como puramente mecânico, implementação permanece de W5-1.

**Verificação:** `ruff check src tests` limpo; nenhum arquivo de código alterado.

**Recomendação:** GO para implementação, condicionado à confirmação do Founder sobre postergação de `confidence`, política de versionamento e naming das permissões. Nenhum código será escrito antes dessa aprovação.

**Decision Log:** D-089.

## Wave 5 — Founder Decision: Technical Design W5-0 aprovado, GO para implementação (2026-07-30)

Founder aprovou o Technical Design do W5-0, veredito **APPROVED — GO para implementação**.

**Adicionado**
- `docs/architecture/TECHNICAL_DEBT.md` -- **TD-014 (Evidence Confidence, Deferred)** registrado oficialmente, gatilho: primeiro produtor real capaz de calcular confiança de maneira objetiva.
- Decision Log -- **Decision Proposal "Knowledge Version Resolution"** registrada (não decidida silenciosamente): trigger é a primeira UI de reingestão documental ou primeiro caso real de múltiplas versões.

**Decisões oficiais:** `knowledge.read`/`knowledge.write` aprovados como nomes definitivos. Dois testes obrigatórios adicionados: Teste A (isolamento organizacional completo) e Teste B (fluxo ponta a ponta upload→ingest→index→`document.indexed`→Workflow Runtime→Execution Tracking sem intervenção manual). Nenhuma outra expansão de escopo autorizada.

**Decision Log:** D-090.

## Wave 5 — Epic W5-0 (Document Ingestion) implementado (2026-07-30)

Implementação completa per Technical Design e as 5 decisões de D-090. Missão exclusivamente Knowledge Platform -- nenhum arquivo toca `Evidence`/`AIContextEngine`/`AdvisorFramework`/`RecommendationEngine`/`src.agents`.

**Adicionado**
- Migração `0020` -- `knowledge.read`/`knowledge.write`, zero tabela nova (aditiva).
- `src/services/knowledge_platform/document_ingestion_service.py` -- composição fina de `KnowledgeRepository` + auditoria (`AdministrationRepository.record_audit()`/`list_audit_log()`, filtro por entidade aditivo) + `sanitize_error()` reaproveitado de W4-4.
- `src/api/routes/knowledge.py` -- `POST /documents`, `POST /documents/{id}/reindex`, `GET /documents`, `GET /documents/{id}`.
- `chunk_count`/`created_at` aditivos em `IngestedDocument`/`DocumentVersionInfo`; novo `KnowledgeRepository.list_documents()`.
- Interface administrativa mínima (`/administracao/documentos`): upload, lista com status, reindexação.
- `docs/product/governance/W5-0-EXECUTIVE-EVIDENCE.md` -- Teste A (isolamento organizacional completo) e Teste B (fluxo ponta a ponta upload→ingest→index→`document.indexed`→Workflow Runtime→Execution Tracking, sem intervenção manual), ambos verdes na camada de serviço e na camada HTTP real.

**Corrigido**
- Duas asserções pré-existentes (`test_administration_api.py`/`test_administration_repository.py`) atualizadas para refletir que `viewer` agora também tem `knowledge.read` -- consequência correta e prevista da migração aprovada, não uma regressão.

**Verificação:** suíte backend completa 539 passed, 0 failed; suíte frontend completa 503 passed (69 arquivos); `ruff`/`tsc`/`eslint` limpos.

**Riscos residuais (nenhum bloqueante):** TD-014 (`confidence`, Deferred); Decision Proposal "Knowledge Version Resolution" (não resolvida nesta Epic); TD-012 reconfirmado.

**Recomendação:** GO para o encerramento do Epic W5-0. Retorno obrigatório para Executive Review antes de qualquer trabalho do W5-1.

**Decision Log:** D-091.

## Wave 5 — Epic W5-0 oficialmente encerrado; ciclo institucional do W5-1 autorizado (2026-07-30)

Founder declarou o Executive Review do Epic W5-0 concluído e o Epic oficialmente encerrado, reconhecendo fluxo funcional entregue, Knowledge Platform operacional, Event Pipeline reutilizado sem alterações, Workflow Runtime revalidado, isolamento organizacional comprovado, ciclo ponta a ponta demonstrado, governança e suíte de testes confirmando estabilidade.

**Mudança de processo para a Wave 5:** ciclo institucional de Advisors passa a ter 6 etapas (antes 8), com uma etapa nova antes do Domain Blueprint: Advisor Specification → Domain Blueprint → Architecture Review → Technical Design → Implementação → Executive Review -- objetivo: consistência e menos retrabalho entre os 7 Advisors.

**Autorizado:** abertura do ciclo institucional do Epic W5-1 (Document Advisor), começando pela Advisor Specification.

**Decision Log:** D-092.

## Wave 5 — Advisor Specification do Document Advisor produzida (2026-07-30)

Primeiro uso do novo ciclo de 6 etapas (Advisor Specification → Domain Blueprint → Architecture Review → Technical Design → Implementação → Executive Review). Missão de documentação -- nenhum código de `src/`/`tests/` alterado.

**Adicionado**
- `docs/architecture/ADVISOR-SPECIFICATION-DOCUMENT-ADVISOR.md` -- consolida, no novo formato, decisões já tomadas em D-087/D-088 (identidade, objetivo, contrato, fonte de evidência, dependências, limites, critérios de sucesso); registra também o template reutilizável de 8 campos para os 6 Advisors restantes da Wave 5.

**Achado apresentado ao Founder, não decidido unilateralmente:** Domain Blueprint (D-087) e Architecture Review (D-088) do Document Advisor já existem, produzidos antes do novo ciclo ser anunciado -- documento pergunta explicitamente se essas etapas já estão satisfeitas (avançar direto para o Technical Design) ou se devem ser reescritas no novo formato.

**Verificação:** `ruff check src tests` limpo.

**Decision Log:** D-093.

## Governança — regra institucional permanente de aplicação prospectiva; GO para o Technical Design do Document Advisor (2026-08-01)

Founder respondeu ao achado de sequenciamento do §0 da Advisor Specification (D-093): decisão de **não reescrever** o Domain Blueprint (D-087) e a Architecture Review (D-088) do Document Advisor.

**Nova regra institucional permanente (toda a STRATECH):** a evolução dos processos de governança aplica-se prospectivamente -- artefatos produzidos sob um processo anteriormente aprovado permanecem válidos desde que continuem tecnicamente corretos, consistentes com as decisões vigentes, sem conflito arquitetural, e não revogados explicitamente. Nenhum documento é reescrito apenas por adequação de formato.

**Aplicação ao Document Advisor:** Etapa 1 (Advisor Specification, D-093) concluída; Etapa 2 (Domain Blueprint, D-087) e Etapa 3 (Architecture Review, D-088) consideradas atendidas. Ciclo avança direto para a Etapa 4 -- Technical Design do Document Advisor.

**Regra permanente para os próximos Advisors:** os 6 Advisors restantes da Wave 5 seguem integralmente o novo ciclo de 6 etapas, sem isenção de nenhuma etapa.

**Verificação:** `ruff check src tests` limpo.

**Decision Log:** D-094.

## Wave 5 — Technical Design do Document Advisor produzido (2026-08-02)

Etapa 4 de 6 do ciclo institucional do W5-1, autorizada por "Founder Authorization — Technical Design do Document Advisor" (GO). Missão de documentação técnica -- nenhum código escrito; todo o desenho verificado por leitura direta do código real.

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-DOCUMENT-ADVISOR.md` -- reuso integral do `AdvisorFramework` (`run()` inalterado); implementação de `normalize_rag_evidence()` (mecânica, em `AIContextEngine`); integração do contrato `Evidence` (`source_type`/`source_id`/`source_label`/`content`/`metadata`) confinada a 4 arquivos + 1 ponto de leitura adicional identificado (`intelligence.py::_risk_advisor_response()`); fluxo completo Knowledge Platform → RAG Pipeline → `normalize_rag_evidence()` → `AdvisorFramework.run()` → Document Advisor → LLM → resposta; garantias de rastreabilidade de citação, isolamento organizacional, portão anti-alucinação e ausência de regra de negócio em `AIContextEngine`; confirmações explícitas de que `AdvisorFramework.run()`, Workflow Runtime, Event Pipeline e `RecommendationEngine` permanecem inalterados/compatíveis. RBAC reutiliza `knowledge.read` (nenhuma migração nova). Request HTTP sem `project_name`/`project_id` (RAG search filtra só por `organization_id`).
- `docs/architecture/TECHNICAL_DEBT.md` -- **TD-015** (chave literal `"cited_analysis_ids"` em `AdvisorFramework.run()`, cosmético, não bloqueante).

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para iniciar a implementação (estratégia incremental de 4 passos). Nenhuma implementação iniciada; retorno obrigatório para Executive Review ao final.

**Decision Log:** D-095.

## Wave 5 — Epic W5-1 (Document Advisor) implementado (2026-08-03)

Implementação completa per a estratégia incremental de 4 passos da Technical Design (D-095), autorizada por "Founder Decision — Technical Design do Document Advisor" (GO). Inclui a evidência obrigatória de rastreabilidade multi-chunk exigida pelo Founder.

**Adicionado**
- `src/agents/document_advisor/agent.py` + `prompts/advise.md` -- novo `DocumentAdvisorAgent`, reaproveitando `parse_structured_output`/`render_analyst_prompt`/`ObservabilityRecorder` sem duplicação.
- `src/services/ai_foundation/context_engine.py` -- `normalize_rag_evidence()` (novo, mecânico) + passthrough em `AdvisorFramework`.
- `src/api/routes/intelligence.py` -- `POST /document-advisor/ask` (RBAC `knowledge.read` reutilizada, nenhuma migração nova).
- `tests/test_document_advisor_agent.py`, `test_document_advisor.py`, `test_document_advisor_api.py` (novos) -- incluindo `TestMultiChunkTraceability` (documento com múltiplos chunks, LLM cita apenas parte, resposta rastreável chunk→documento→versão→resposta).

**Alterado (aditivo, contrato `Evidence`)**
- `src/services/ai_foundation/types.py` -- `Evidence` evolui para `source_type`/`source_id`/`source_label`/`content`/`metadata`, per D-088.
- `src/services/ai_foundation/recommendation_engine.py`, `src/agents/risk_advisor/agent.py`, `src/api/routes/intelligence.py::_risk_advisor_response()` -- migrados para o novo contrato, zero mudança de lógica. Suíte completa do Risk Advisor passa sem nenhuma alteração de expectativa.

**Confirmado inalterado:** `AdvisorFramework.run()`; Workflow Runtime; Event Pipeline; `RecommendationEngine` (apenas rename de campo).

**Débito técnico:** TD-015 (chave `"cited_analysis_ids"` em `AdvisorFramework.run()`) atualizado para Deferred, gatilho oficializado: segundo Advisor baseado em RAG (Governance Advisor ou equivalente).

**Verificação:** suíte backend completa 561 passed, 0 failed (22 novos); suíte frontend completa 503 passed; `ruff`/`tsc`/`eslint` limpos.

**Recomendação:** GO para o encerramento do Epic W5-1. Retorno obrigatório para Executive Review antes de qualquer trabalho do próximo Advisor da Wave 5.

**Decision Log:** D-096.

## Wave 5 — Epic W5-1 (Document Advisor) oficialmente encerrado; próximo Advisor autorizado a abrir (2026-08-03)

Founder declarou o Executive Review do Epic W5-1 concluído e o Epic oficialmente encerrado, reconhecendo: reuso integral da arquitetura existente, evolução do contrato `Evidence` sem regressões, rastreabilidade documental comprovada, portão anti-alucinação íntegro, infraestrutura das Waves 3/4 validada em produção funcional, suíte de testes confirmando estabilidade.

**Autorizado:** abertura do ciclo institucional do próximo Enterprise Advisor, seguindo integralmente o processo de 6 etapas (Advisor Specification → Domain Blueprint → Architecture Review → Technical Design → Implementação → Executive Review). Escolha do Advisor específico (entre os 6 restantes do catálogo) aguarda confirmação do Founder.

**Decision Log:** D-097.

## Wave 5 — Governance Advisor definido como próximo Advisor; Advisor Specification produzida (2026-08-03)

Founder definiu oficialmente o Governance Advisor (segundo Advisor de Classe D, mesma infraestrutura RAG do Document Advisor) como o próximo Enterprise Advisor da Wave 5, priorizando reutilização arquitetural e redução de risco.

**Adicionado**
- `docs/architecture/ADVISOR-SPECIFICATION-GOVERNANCE-ADVISOR.md` -- etapa 1 de 6 do ciclo institucional. Contrato/fluxo idênticos ao Document Advisor, reaproveitando `normalize_rag_evidence()` sem alteração. Achado grounded (não resolvido): documentos de governança (Decision Log/TD Register) ainda não ingeridos na Knowledge Platform -- decisão de processo do Domain Blueprint, não lacuna arquitetural. Achado sinalizado: o gatilho de TD-015 ("segundo Advisor baseado em RAG") chegou -- avaliação reservada para a Architecture Review.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para o Domain Blueprint do Governance Advisor.

**Decision Log:** D-098.

## Wave 5 — Domain Blueprint do Governance Advisor produzido (2026-08-03)

Founder aprovou a Advisor Specification (GO para o Domain Blueprint), exigindo que este documento considere explicitamente 4 cenários de governança sem criar novas regras: ausência de evidência documental; documento inconsistente com outra decisão oficial; documento desatualizado em relação ao Decision Log; documentos conflitantes entre si.

**Adicionado**
- `docs/architecture/DOMAIN-BLUEPRINT-GOVERNANCE-ADVISOR.md` -- etapa 2 de 6. Confirma que nenhum dos 4 cenários exige mudança de Framework: `normalize_rag_evidence()`/`RecommendationEngine.build()` já suportam citação de múltiplos chunks de múltiplos documentos; identificação de inconsistência/conflito é interpretação de domínio do `GovernanceAdvisorAgent`, nunca um comparador novo no Framework. Corpus documental definido (Decision Log + Technical Debt Register). TD-015 explicitamente reservado para a Architecture Review, não resolvido aqui.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para a Architecture Review do Governance Advisor.

**Decision Log:** D-099.

## Wave 5 — AR-10: Architecture Review do Governance Advisor concluída (2026-08-03)

Founder aprovou o Domain Blueprint (GO para a Architecture Review), exigindo avaliação da hierarquia de autoridade entre documentos institucionais (definida apenas arquiteturalmente) e decisão explícita sobre TD-015 nesta etapa, preservando integralmente `AdvisorFramework`, `AIContextEngine`, Event Pipeline e Workflow Runtime.

**Adicionado**
- `docs/architecture/AR-10-GOVERNANCE-ADVISOR-ARCHITECTURE-REVIEW.md` -- hierarquia documental definida: Decision Log > Technical Debt Register > Mission Control/CHANGELOG > documentos de Epic, generalizando o princípio já estabelecido em D-094. Aplicação é conhecimento de domínio no prompt do Advisor, nunca um comparador no Framework -- nenhuma mudança a `Evidence`/`normalize_rag_evidence()` necessária.

**Alterado**
- `docs/architecture/TECHNICAL_DEBT.md` -- TD-015: decisão explícita de permanecer Deferred (resolver exigiria alterar `AdvisorFramework.run()`, que esta mesma revisão preserva integralmente); gatilho revisado para uma mudança de manutenção isolada, nunca bundlada à entrega de um Advisor.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para o Technical Design do Governance Advisor.

**Decision Log:** D-100.

## Wave 5 — Technical Design do Governance Advisor produzido (2026-08-03)

Founder aprovou AR-10 (GO para o Technical Design), exigindo classificação explícita de 5 estados de governança (`CONFORME`/`INCONSISTENTE`/`DESATUALIZADO`/`CONFLITANTE`/`SEM EVIDÊNCIA`) como comportamento exclusivo do Advisor, sem alterar o Framework.

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-GOVERNANCE-ADVISOR.md` -- resolve o achado central de como a classificação sobrevive até a resposta HTTP sem tocar `AdvisorFramework.run()`/`Recommendation`/`Explanation`: embutida como prefixo fixo em `answer`, extraída por uma função de rota (não de Framework). `SEM EVIDÊNCIA` mapeado ao portão anti-alucinação já existente. Fallback explícito (`"NÃO CLASSIFICADO"`) se o LLM não seguir o formato -- nunca uma classificação inventada. Reaproveita `CitedChunk` do Document Advisor sem duplicação. TD-015 confirmado sem incidência.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para a implementação.

**Decision Log:** D-101.

## Wave 5 — Governance Advisor implementado (2026-08-03)

Implementação completa per a estratégia incremental de 4 passos da Technical Design (D-101), autorizada por "Founder Decision — Technical Design do Governance Advisor" (GO). Inclui a evidência obrigatória de conflito Decision Log × Technical Debt Register exigida pelo Founder.

**Adicionado**
- `src/agents/governance_advisor/agent.py` + `prompts/advise.md` -- novo `GovernanceAdvisorAgent`, prompt codificando a hierarquia institucional de AR-10 e os 5 rótulos oficiais de classificação (primeira linha de `answer`, nada mais).
- `src/api/routes/intelligence.py` -- `POST /governance-advisor/ask` (RBAC `knowledge.read` reutilizada, nenhuma migração nova); `_parse_governance_classification()` exclusivamente na camada HTTP -- `AdvisorFramework`/`RecommendationEngine`/`ExplanationEngine` confirmados inalterados (`git diff` vazio). Fallback explícito `"NÃO CLASSIFICADO"` quando o LLM não segue o formato.
- `tests/test_governance_advisor_agent.py`, `test_governance_advisor.py`, `test_governance_advisor_api.py` (novos) -- incluindo `TestMandatoryConflictEvidence` (Decision Log × Technical Debt Register em conflito real, classificado CONFLITANTE, ambos citados).

**Confirmado inalterado:** `AdvisorFramework.run()`; `RecommendationEngine`; `ExplanationEngine`; `AIContextEngine`; Workflow Runtime; Event Pipeline. TD-015 mantido, sem incidência.

**Verificação:** suíte backend completa 580 passed, 0 failed (19 novos); suíte frontend completa 503 passed; `ruff`/`tsc`/`eslint` limpos.

**Recomendação:** GO para o encerramento do Epic. Retorno obrigatório para Executive Review antes de qualquer trabalho do próximo Advisor.

**Decision Log:** D-102.

## Wave 5 — Governance Advisor oficialmente encerrado; Delivery Advisor definido como próximo Advisor; Advisor Specification produzida (2026-08-03)

Founder declarou o Governance Advisor oficialmente concluído (arquitetura íntegra, reutilização comprovada, hierarquia documental aplicada corretamente, classificação sem alterar o Framework, rastreabilidade revalidada, suíte completa confirmando estabilidade). Terceiro Advisor da Wave 5 concluído.

**Autorizado:** abertura do ciclo institucional do Delivery Advisor.

**Adicionado**
- `docs/architecture/ADVISOR-SPECIFICATION-DELIVERY-ADVISOR.md` -- etapa 1 de 6. Delivery Advisor classificado Classe A (escopo único, mesma forma do Risk Advisor) -- reutiliza `AIContextEngine.gather()` sem nenhuma extensão, confirmado pelo achado de D-084. Achado grounded, não resolvido: qual `kind` exato (ou composição) de `AnalysisRecord` satisfaz "ações, riscos e histórico de análise" sem reclassificar o Advisor para Classe B -- reservado para o Domain Blueprint.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para o Domain Blueprint do Delivery Advisor.

**Decision Log:** D-103.

## Wave 5 — Definição institucional permanente de Classe A/B; Domain Blueprint do Delivery Advisor produzido (2026-08-04)

Founder resolveu o achado grounded deixado em aberto pela Advisor Specification (D-103), fixando uma decisão arquitetural permanente para toda a STRATECH: a fronteira entre Classe A e Classe B é a cardinalidade de fontes primárias de evidência (uma única chamada estrutural vs. duas ou mais) -- nunca a quantidade de assuntos abordados na resposta.

**Adicionado**
- `docs/architecture/AR-8-WAVE-5-ENTERPRISE-ADVISOR-MODEL-REVIEW.md` §4.2 -- definição institucional permanente de Classe A/Classe B registrada. Delivery Advisor confirmado Classe A, com fonte oficial `AnalysisRecord`/`kind="status"` -- podendo conter referências textuais a riscos/ações/bloqueios sem deixar de ser uma única evidência.
- `docs/architecture/DOMAIN-BLUEPRINT-DELIVERY-ADVISOR.md` -- etapa 2 de 6. Aplica a fonte já decidida (não a reabre); confirma por leitura de código que `AIContextEngine.gather(kind="status")` e `AdvisorFramework.run()` não exigem nenhuma extensão (mesma forma do Risk Advisor); caracteriza 3 cenários de uso (estado geral de entrega, bloqueios, ausência de evidência).

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para a Architecture Review do Delivery Advisor.

**Decision Log:** D-104.

## Wave 5 — AR-11: Architecture Review do Delivery Advisor concluída (2026-08-04)

Founder exigiu que esta revisão analisasse um unico ponto adicional: se a recencia do AnalysisRecord deve influenciar a interpretacao do Delivery Advisor.

**Adicionado**
- `docs/architecture/AR-11-DELIVERY-ADVISOR-ARCHITECTURE-REVIEW.md` -- confirma por leitura de codigo que `AnalysisRepository.list_analyses()` ja ordena por `created_at.desc()` para qualquer `kind`, sem excecao; `AIContextEngine.gather()` preserva essa ordem, nenhuma mudanca necessaria. Decisao: recencia tratada como conhecimento de dominio no prompt do `DeliveryAdvisorAgent` (Technical Design) -- o `AnalysisRecord` de status mais recente representa o estado atual, registros mais antigos citaveis apenas como historico -- mesmo principio ja validado pela hierarquia documental do Governance Advisor (AR-10). Nenhuma mudanca a `AdvisorFramework`/`AIContextEngine`/Workflow Runtime/Event Pipeline.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para o Technical Design do Delivery Advisor.

**Decision Log:** D-105.

## Wave 5 — Technical Design do Delivery Advisor produzido (2026-08-04)

Founder exigiu, alem de aplicar a recencia ja decidida, uma orientacao adicional de interpretacao de tendencia temporal (melhora/estabilidade/deterioracao) quando multiplos AnalysisRecords de status existirem -- exclusivamente no prompt do DeliveryAdvisorAgent, nenhum algoritmo adicional.

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-DELIVERY-ADVISOR.md` -- fluxo identico ao Risk Advisor (`gather_context(kind="status")` -> `AdvisorFramework.run()` byte-for-byte inalterado); `DeliveryAdvisorAgent` serializa a lista de status ja ordenada do mais recente para o mais antigo (garantia estrutural existente, confirmada em AR-11) sem nenhum codigo de ordenacao; prompt instrui o modelo a tratar o primeiro item como estado atual e descrever tendencia quando houver 2+ entradas -- nenhuma funcao de comparacao de datas/health_status implementada. `CitedAnalysis` reaproveitado do Risk Advisor. RBAC `intelligence.read` reutilizada, nenhuma migracao nova.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para a implementação.

**Decision Log:** D-106.

## Wave 5 — Delivery Advisor implementado (2026-08-04)

Implementacao completa per as 7 diretrizes obrigatorias de "Founder Decision -- Technical Design do Delivery Advisor" (GO). Inclui os tres cenarios temporais mandados (melhora/deterioracao/registro unico) e a prova de ausencia de segunda fonte (RAG incluido).

**Adicionado**
- `src/agents/delivery_advisor/agent.py` + `prompts/advise.md` -- novo `DeliveryAdvisorAgent`, mesma forma do `RiskAdvisorAgent`. Prompt declara explicitamente que o primeiro item do historico e o estado atual e que a tendencia deve respeitar a direcao temporal mais-recente-primeiro.
- `src/api/routes/intelligence.py` -- `POST /delivery-advisor/ask` (RBAC `intelligence.read` reutilizada, nenhuma migracao nova); `CitedAnalysis` reaproveitado do Risk Advisor sem duplicacao. Nenhuma chamada a `gather_rag_context()` -- confirmado por busca de codigo e por teste estrutural (rag_pipeline=None / dublê que lança excecao).
- `tests/test_delivery_advisor_agent.py`, `test_delivery_advisor.py`, `test_delivery_advisor_api.py` (novos, 23 testes) -- incluindo os tres cenarios temporais com timestamps explicitos, em duas camadas (Framework e HTTP).

**Confirmado inalterado:** `AdvisorFramework`; `AIContextEngine`; `RecommendationEngine`; `ExplanationEngine`; Workflow Runtime; Event Pipeline. `git diff --stat` vazio.

**Verificação:** suíte backend completa 603 passed, 0 failed (23 novos); suíte frontend completa 503 passed; `ruff`/`tsc`/`eslint` limpos.

**Recomendação:** GO para o encerramento do Epic. Retorno obrigatório para Executive Review antes de qualquer trabalho do próximo Advisor.

**Decision Log:** D-107.

## Wave 5 — Delivery Advisor oficialmente encerrado; Portfolio Advisor definido como proximo Advisor, primeiro Classe B (2026-08-04)

Founder declarou o Delivery Advisor oficialmente concluido (etapa 6 de 6) e autorizou a abertura do ciclo institucional do Portfolio Advisor -- primeiro Advisor Classe B (D-104), que deve validar a composicao de duas ou mais fontes independentes sem transferir essa responsabilidade para o AdvisorFramework.

**Adicionado**
- `docs/architecture/ADVISOR-SPECIFICATION-PORTFOLIO-ADVISOR.md` -- etapa 1 de 6. Proposta grounded (nao decisao final): resolver projetos-membro do portfolio reutilizando DomainService.list_programs()/list_projects() (Wave 2, ja em producao, ja org-scoped), entao chamar framework.gather_context(kind="status") uma vez por projeto, concatenando na rota antes de framework.run() -- nenhum metodo novo de Framework. Achados reservados para o Domain Blueprint: confirmacao do padrao de composicao, kind definitivo, volume de chamadas por portfolio.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para o Domain Blueprint do Portfolio Advisor.

**Decision Log:** D-108.

## Wave 5 — Domain Blueprint do Portfolio Advisor produzido (2026-08-04)

Founder exigiu que a composicao de evidencias nao ficasse na rota HTTP -- um componente proprio do Advisor deveria assumir essa responsabilidade, com nome e localizacao definidos nesta etapa.

**Adicionado**
- `docs/architecture/DOMAIN-BLUEPRINT-PORTFOLIO-ADVISOR.md` -- define `PortfolioEvidenceAssembler` (`src/agents/portfolio_advisor/evidence_assembler.py`, dentro do proprio pacote do Advisor, nao em `src/services/`) como o componente que resolve o Portfolio org-scoped via `DomainService`, lista Programs/Projects, solicita evidencia via `framework.gather_context(kind="status")` uma vez por projeto, e consolida antes de `framework.run()`. Rastreabilidade via enriquecimento de `Evidence.metadata` (project_id/project_name/program_id), sem alterar o dataclass `Evidence`. 8 casos de dominio obrigatorios resolvidos por composicao do ja existente, nenhuma logica nova. Gatilho objetivo de performance registrado (20+ chamadas sequenciais ou p95 > 3s), nenhuma otimizacao especulativa.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para a Architecture Review do Portfolio Advisor.

**Decision Log:** D-109.

## Wave 5 — AR-12: Architecture Review do Portfolio Advisor concluída (2026-08-04)

Founder exigiu analise explicita de dois pontos: peso da evidencia (um Evidence por Project?) e ordem da composicao (Programs->Projects representa prioridade?).

**Adicionado**
- `docs/architecture/AR-12-PORTFOLIO-ADVISOR-ARCHITECTURE-REVIEW.md` -- decide que cada Project contribui exatamente um Evidence (o mais recente, evidence[0], ja garantido pela ordenacao existente de list_analyses()), consistente com o Delivery Advisor por aplicar a mesma regra permanente (D-104) a unidade de composicao correta para cada Advisor. Confirma, por leitura de codigo, que a ordem Programs->Projects e puramente alfabetica/incidental (ORDER BY Program.code / Project.name), nunca prioridade -- nenhum algoritmo de reordenacao necessario, apenas instrucao textual de prompt no Technical Design.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para o Technical Design do Portfolio Advisor.

**Decision Log:** D-110.

## Wave 5 — Technical Design do Portfolio Advisor produzido (2026-08-04)

Founder exigiu um modelo de resposta com cobertura estrutural (total/com/sem evidencia) nunca calculada pelo LLM, e confirmou as proibicoes explicitas ao PortfolioEvidenceAssembler (nunca interpretar, comparar, ponderar, ou selecionar por regra adicional).

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-PORTFOLIO-ADVISOR.md` -- define o contrato definitivo do `PortfolioEvidenceAssembler` (selecao mecanica de evidence[0], enriquecimento de metadata com portfolio_id/program_id/project_id/project_name, contagem estrutural de cobertura) e do `PortfolioAdvisorResponse` (answer + total_projects + projects_with_evidence + projects_without_evidence + cited_projects, cobertura sempre calculada em codigo, nunca pelo LLM). Limites funcionais (tendencia historica do Portfolio proibida) garantidos estruturalmente -- nenhuma sequencia temporal por projeto chega ao prompt.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para a implementação.

**Decision Log:** D-111.

## Wave 5 — Portfolio Advisor implementado (2026-08-04)

Implementacao completa per as 8 diretrizes obrigatorias de "Founder Decision -- Technical Design do Portfolio Advisor" (GO). Primeiro Advisor Classe B. Inclui os 11 cenarios obrigatorios (A-K) e a prova de ausencia de segunda fonte (RAG incluido).

**Adicionado**
- `src/agents/portfolio_advisor/evidence_assembler.py` -- `PortfolioEvidenceAssembler`/`PortfolioAssemblyResult`, exclusivamente dentro do pacote do Advisor. Resolve Portfolio via `DomainService.get_portfolio()`, lista Programs/Projects, chama `gather_context(kind="status")` por Project, seleciona `evidence[0]` mecanicamente (nunca interpreta/compara/pondera/aplica regra adicional -- confirmado por leitura de codigo), enriquece `Evidence.metadata`, conta cobertura estruturalmente.
- `src/agents/portfolio_advisor/agent.py` + `prompts/advise.md` -- `PortfolioAdvisorAgent`, mesma forma do `DeliveryAdvisorAgent`.
- `src/api/routes/intelligence.py` -- `POST /portfolio-advisor/ask` (RBAC `intelligence.read` reutilizada, `build_domain_service` reaproveitado de `portfolio.py` sem duplicacao). `PortfolioAdvisorResponse{answer, total_projects, projects_with_evidence, projects_without_evidence, cited_projects}` -- contagens sempre calculadas em codigo, nunca pelo LLM.
- `tests/test_portfolio_advisor_evidence_assembler.py`, `test_portfolio_advisor_agent.py`, `test_portfolio_advisor.py`, `test_portfolio_advisor_api.py` (novos, 35 testes) -- cobrindo os 11 cenarios obrigatorios (A-K) em duas camadas.

**Confirmado inalterado:** `AdvisorFramework`; `AIContextEngine`; `RecommendationEngine`; `ExplanationEngine`; Workflow Runtime; Event Pipeline; `DomainService`/`DomainRepository`; contrato `Evidence`. `git diff --stat` vazio.

**Verificação:** suíte backend completa 638 passed, 0 failed (35 novos); suíte frontend completa 503 passed; `ruff`/`tsc`/`eslint` limpos.

**Recomendação:** GO para o encerramento do Epic. Retorno obrigatório para Executive Review antes de qualquer trabalho do próximo Advisor.

**Decision Log:** D-112.

## Wave 5 — Portfolio Advisor oficialmente encerrado; PMO Advisor definido como proximo Advisor, segundo Classe B (2026-08-04)

Founder declarou o Portfolio Advisor oficialmente concluido e autorizou a abertura do ciclo institucional do PMO Advisor -- segundo Advisor Classe B (D-104). Exigencia explicita: avaliar primeiro se o PMO Advisor deve consumir fontes primarias diretamente ou compor resultados estruturados ja produzidos pelos Advisors existentes -- nenhuma decisao tomada silenciosamente.

**Adicionado**
- `docs/architecture/ADVISOR-SPECIFICATION-PMO-ADVISOR.md` -- etapa 1 de 6. Questao arquitetural central resolvida: o PMO Advisor consome exclusivamente fontes primarias (AnalysisRecord via AIContextEngine.gather()), nunca compoe Recommendation/Explanation de outros Advisors -- fundamentado em restricao ja permanente do AdvisorFramework desde a Fase 3 ("nunca delegacao de um Advisor para outro"). Fonte proposta: AnalysisRecord/kind="status", com leitura adicional de created_at para detectar ausencia de atualizacao. Limites contra sobreposicao com Portfolio/Governance/Delivery/Executive Advisor definidos explicitamente.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para o Domain Blueprint do PMO Advisor.

**Decision Log:** D-113.

## Wave 5 — Domain Blueprint do PMO Advisor produzido, etapa 2 de 6 (2026-08-05)

Founder aprovou a Advisor Specification (GO para o Domain Blueprint) com 7 diretrizes: proibicao explicita de usar Recommendation/Explanation/resposta de outro Advisor como evidencia; avaliar unidade de agregacao (Portfolio/Program/Project); avaliar necessidade de kind="meeting" com base em consumidor real; avaliar staleness objetivamente (prompt vs. logica estrutural); avaliar generalizacao do PortfolioEvidenceAssembler sem criar abstracao antecipada; avaliar risco de duplicidade entre kinds futuros sem implementar solucao; preservar infraestrutura compartilhada.

**Adicionado**
- `docs/architecture/DOMAIN-BLUEPRINT-PMO-ADVISOR.md` -- etapa 2 de 6. Unidade de composicao decidida: Project, forcada pelo modelo de dados (AnalysisRecord so se associa a project_id, nunca a Portfolio/Program). Escopo de resolucao decidido: organizacional, via DomainService.list_projects(organization_id, program_id=None) -- ja em producao, nenhum metodo novo. kind="meeting" avaliado e considerado desnecessario: unico consumidor real (ProjectSummaryService.list_action_items()) resolve necessidade de UI, nao deteccao de padrao, e nao tem campo de conclusao. Decisao: manter exclusivamente kind="status", lido como historico completo por Project (nao apenas evidence[0]). Staleness definida como calculo estrutural, nunca de prompt -- mesma disciplina das contagens do Portfolio Advisor; limiar numerico reservado ao Technical Design. Generalizacao do PortfolioEvidenceAssembler avaliada e rejeitada nesta etapa -- logica de selecao de evidencia (evidence[0] vs. historico completo) e resolucao de escopo divergem estruturalmente entre os dois Advisors; gatilho real de generalizacao futura registrado (terceiro consumidor Classe B com comportamento identico). Risco de duplicidade de evidencia entre kinds futuros registrado, nao resolvido (especulativo, nao incide hoje).

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para a Architecture Review do PMO Advisor.

**Decision Log:** D-114.

## Wave 5 — AR-13: Architecture Review do PMO Advisor concluida, etapa 3 de 6 (2026-08-05)

Founder aprovou o Domain Blueprint (GO para a Architecture Review), confirmando unidade de composicao (Project), escopo (organizacional) e fonte (kind="status" exclusivo, historico completo) como oficiais, e delegando quatro decisoes: staleness, controle de volume, modelo de cobertura estrutural, confirmacao de preservacao de infraestrutura.

**Adicionado**
- `docs/architecture/AR-13-PMO-ADVISOR-ARCHITECTURE-REVIEW.md` -- etapa 3 de 6. Staleness: limiar inicial de 14 dias sem novo status (duas janelas de reporte semanal perdidas), registrado explicitamente como heuristica nao-empirica, calculo estrutural na PMOEvidenceAssembler, sem configuracao por organizacao. Controle de volume: limite de 5 registros mais recentes por Project (janela temporal descartada por risco de zerar evidencia de Project ativo), corte em memoria sobre lista ja ordenada por created_at DESC, zero mudanca de assinatura em AdvisorFramework/AIContextEngine. Cobertura estrutural: cinco contagens (total_projects/projects_with_status/projects_without_status/projects_stale/projects_current) calculadas em codigo, relacoes aritmeticas explicitas, distincao clara entre "sem status" e "desatualizado". Infraestrutura compartilhada reconfirmada preservada.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para o Technical Design do PMO Advisor.

**Decision Log:** D-115.

## Wave 5 — Technical Design do PMO Advisor produzido, etapa 4 de 6 (2026-08-05)

Founder aprovou a AR-13 (GO para o Technical Design), oficializando staleness (limiar de 14 dias), controle de volume (5 registros mais recentes por Project), cobertura estrutural (5 contagens). Exigencias desta etapa: constante nomeada, timezone, data de referencia, comportamento na fronteira exata de 14 dias, gatilho de recalibracao, 13 cenarios de teste obrigatorios.

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-PMO-ADVISOR.md` -- etapa 4 de 6. PMOEvidenceAssembler (src/agents/pmo_advisor/evidence_assembler.py) com contrato definitivo: resolve Projects org-scoped via DomainService.list_projects(organization_id), sem portfolio_id e portanto sem caso de 404 (escopo organizacional sempre resolve pela sessao). Staleness: constante PMO_STALENESS_THRESHOLD_DAYS=14, timezone UTC (datetime.now(timezone.utc), mesmo padrao ja permanente no codigo), reference_time capturada uma unica vez por chamada, fronteira de 14 dias inclusiva (staleness_days >= 14), mesma convencao ja usada em Invitation.status(). Gatilho de recalibracao futura registrado explicitamente, nunca ajuste silencioso. Modelo de resposta PMOAdvisorResponse reaproveita CitedProject do Portfolio Advisor sem duplicacao; cited_projects pode conter o mesmo project_id mais de uma vez (comportamento intencional documentado, rastreabilidade ate AnalysisRecord especifico). Cobertura estrutural: tres invariantes garantidas pela propria aritmetica do laco da Assembler. 13 cenarios de teste obrigatorios nomeados A-M. Infraestrutura compartilhada confirmada preservada.

**Verificação:** `ruff check src tests` limpo.

**Recomendação:** GO para a implementação do PMO Advisor.

**Decision Log:** D-116.

## Wave 5 — PMO Advisor implementado, etapa 5 de 6 (2026-08-05)

Founder aprovou o Technical Design (GO para implementacao) com 8 diretrizes: PMOEvidenceAssembler exclusivo do pacote; staleness com 5 regras (UTC, referencia unica, 13/14/15 dias, Project sem status nunca stale, sem config por organizacao); volume evidence[:5] sem janela/batch/cache/paralelismo; cobertura estrutural com invariantes; rastreabilidade -- interromper antes de alterar contratos compartilhados caso CitedProject nao suportasse citacoes repetidas distinguiveis; fonte unica kind=status; preservacao integral da infraestrutura; 13 cenarios A-M + 7 provas adicionais.

**Adicionado**
- `src/agents/pmo_advisor/evidence_assembler.py` -- PMOEvidenceAssembler, PMOAssemblyResult, PMO_STALENESS_THRESHOLD_DAYS=14, PMO_MAX_RECORDS_PER_PROJECT=5. Resolve DomainService.list_projects(organization_id) sem portfolio_id (sem caso de 404). reference_time capturada uma unica vez por chamada (datetime.now(timezone.utc)). staleness_days/is_stale calculados uma vez por Project, replicados em todos os itens de Evidence daquele Project. Corte evidence[:5] em memoria, apos o calculo de staleness, sem tocar AdvisorFramework/AIContextEngine.
- `src/agents/pmo_advisor/agent.py` -- PMOAdvisorAgent, mesma forma dos demais Advisors baseados em AnalysisRecord.
- `src/agents/pmo_advisor/prompts/advise.md` -- instrui: registros ja trazem staleness_days/is_stale prontos; mesmo project_id agrupa historico, primeiro registro = estado atual; conjunto sem prioridade por posicao.
- Rota `POST /pmo-advisor/ask` em `src/api/routes/intelligence.py` -- PMOAdvisorRequest (question apenas, sem portfolio_id/project_id), PMOAdvisorResponse (5 contagens + cited_projects), reaproveitando CitedProject do Portfolio Advisor sem alteracao (source_analysis_id ja torna citacoes repetidas do mesmo Project distinguiveis -- avaliacao cumprida, nenhuma interrupcao necessaria).
- 48 testes novos: `tests/test_pmo_advisor_evidence_assembler.py` (17, unitario), `tests/test_pmo_advisor_agent.py` (6, unitario), `tests/test_pmo_advisor.py` (16, integracao Framework/Postgres), `tests/test_pmo_advisor_api.py` (9, HTTP/Postgres/RBAC) -- cobrindo os 13 cenarios A-M e as 7 provas adicionais (captura unica da data de referencia, Project sem status nunca stale, staleness unica por Project, cap de 5 evidencias, rastreabilidade de citacoes repetidas, ausencia de chamada ao LLM sem evidencia, ausencia de segunda fonte).
- `docs/product/governance/PMO-ADVISOR-EXECUTIVE-EVIDENCE.md` -- Executive Evidence completa.

**Verificação:** `git diff --stat` vazio em AdvisorFramework/AIContextEngine/RecommendationEngine/ExplanationEngine/Workflow Runtime/Event Pipeline/DomainService/DomainRepository/Evidence. Suite backend completa 680 passed (era 638). Suite frontend completa 503 passed. `ruff`/`tsc`/`eslint` limpos.

**Recomendação:** GO para o encerramento do Epic do PMO Advisor.

**Decision Log:** D-117.

## Wave 5 — PMO Advisor oficialmente encerrado; validacao do padrao Classe B encerrada; ciclo do Executive Advisor autorizado a abrir (2026-08-05)

Founder aprovou a Executive Evidence do PMO Advisor -- encerramento oficial. 6 de 8 Advisors da Wave 5 concluidos. Decisao permanente: PMOEvidenceAssembler constitui o segundo padrao consolidado para Advisors Classe B; PortfolioEvidenceAssembler e PMOEvidenceAssembler permanecem coexistindo, sem generalizacao, condicionada ao gatilho ja aprovado (terceiro consumidor estruturalmente equivalente). Validacao do padrao Classe B oficialmente encerrada -- proximos Advisors Classe B podem reutilizar os padroes ja estabelecidos sem nova validacao arquitetural. Autorizada exclusivamente a abertura do ciclo institucional do Executive Advisor -- setimo Advisor da Wave 5. Nenhum trabalho paralelo autorizado.

**Verificação:** missão de governança -- nenhum código de `src/`/`tests/` alterado; `ruff check src tests` limpo.

**Decision Log:** D-118.

## Wave 5 — Advisor Specification do Executive Advisor produzida, etapa 1 de 6 (2026-08-05)

Founder autorizou formalmente a abertura do ciclo institucional do Executive Advisor (setimo Advisor da Wave 5), iniciando pela Advisor Specification, missao exclusivamente documental.

**Adicionado**
- `docs/architecture/ADVISOR-SPECIFICATION-EXECUTIVE-ADVISOR.md` -- etapa 1 de 6. Classificacao Classe B confirmada (ja registrada em AR-8 SS4/D-085: multiplos projetos e/ou multiplos kind), tambem satisfeita pela definicao permanente de cardinalidade (D-104) -- kind=status + kind=risk ja constituem duas fontes primarias independentes. Fontes confirmadas: AnalysisRecord/kind=status e AnalysisRecord/kind=risk. Candidatas nao decididas, reservadas ao Domain Blueprint: kind=meeting, Knowledge Platform/RAG. Nao-duplicacao demonstrada contra os 6 Advisors existentes -- nenhum combina multiplos kinds de evidencia primaria para sintese de decisao executiva. Seis questoes arquiteturais abertas registradas, nenhuma decidida: conjunto definitivo de kinds; participacao de RAG; reaproveitamento de ProjectSummaryService vs. novo componente de composicao; escopo de resolucao; controle de volume; necessidade real de gather_context_many() no AdvisorFramework (extensao ja prevista condicionalmente em AR-8 SS3). Visao arquitetural registrada: progressao Delivery (projeto) -> Portfolio (portfolio) -> PMO (organizacao, processo) -> Executive (organizacao, decisao, multiplos kinds).

**Verificação:** missão de documentação -- nenhum código de `src/`/`tests/` alterado; `ruff check src tests` limpo.

**Recomendação:** GO para o Domain Blueprint do Executive Advisor.

**Decision Log:** D-119.

## Wave 5 — Domain Blueprint do Executive Advisor produzido, etapa 2 de 6 (2026-08-05)

Founder aprovou a Advisor Specification (GO para o Domain Blueprint), fixando fontes iniciais (kind=status + kind=risk), seis fontes fora de escopo inicial, identidade definitiva, e exigindo avaliacao obrigatoria de ProjectSummaryService e gather_context_many(), sem aprovacao automatica.

**Adicionado**
- `docs/architecture/DOMAIN-BLUEPRINT-EXECUTIVE-ADVISOR.md` -- etapa 2 de 6. Escopo organizacional confirmado via DomainService.list_projects(). ProjectSummaryService avaliado e rejeitado como fonte: summarize()/_aggregate() sem source_id por item (reprovado); list_action_items() reprovado por escopo (kind=meeting); list_latest_risks() passa no teste de rastreabilidade mas rejeitado por acoplamento a UI e falta de parametrizacao de volume -- decisao: composicao direta via AnalysisRecord. gather_context_many() avaliado e rejeitado: duas chamadas explicitas (kind=status + kind=risk) no ExecutiveEvidenceAssembler resolvem sem tocar o Framework, necessidade real nao demonstrada. Componente nomeado: ExecutiveEvidenceAssembler, terceiro componente Classe B, estruturalmente distinto dos dois ja existentes. Volume: exatamente 1 status + 1 risco mais recentes por Project, nunca historico -- torna estruturalmente impossivel alegar tendencia. Cobertura estrutural em duas dimensoes independentes (status e risco). Achado de rastreabilidade registrado: CitedProject nao carrega kind, duas solucoes candidatas registradas, reservado ao Technical Design. Infraestrutura compartilhada confirmada preservada.

**Verificação:** missão de documentação -- nenhum código de `src/`/`tests/` alterado; `ruff check src tests` limpo.

**Recomendação:** GO para a Architecture Review do Executive Advisor.

**Decision Log:** D-120.

## Wave 5 — AR-14: Architecture Review do Executive Advisor concluida, etapa 3 de 6 (2026-08-05)

Founder aprovou o Domain Blueprint (GO para a Architecture Review), confirmando escopo, fontes e rejeicoes (ProjectSummaryService, gather_context_many()) como oficiais, delegando modelo de citacao, cobertura estrutural e tratamento de ausencia/cobertura parcial.

**Adicionado**
- `docs/architecture/AR-14-EXECUTIVE-ADVISOR-ARCHITECTURE-REVIEW.md` -- etapa 3 de 6. Modelo de citacao: novo ExecutiveCitedEvidence (project_id/project_name/source_analysis_id/kind/created_at), especifico do Advisor -- CitedProject nao e alterado, permanece intocado para Portfolio/PMO Advisor. Cobertura estrutural: sete contagens (total_projects, projects_with_status/without_status, projects_with_risk/without_risk, projects_with_status_and_risk, projects_without_any_evidence), invariantes matematicas registradas. Ausencia total aciona no_evidence() sem LLM; cobertura parcial permite sintese com limitacao declarada, usando as contagens ja calculadas. Contrato do ExecutiveEvidenceAssembler descrito (forma, nao codigo). Limite adicional confirmado: nenhum ranking deterministico calculado em codigo. Infraestrutura compartilhada e contratos existentes (CitedProject, PortfolioAdvisorResponse, PMOAdvisorResponse) confirmados preservados.

**Verificação:** missão de documentação -- nenhum código de `src/`/`tests/` alterado; `ruff check src tests` limpo.

**Recomendação:** GO para o Technical Design do Executive Advisor.

**Decision Log:** D-121.

## Wave 5 — Technical Design do Executive Advisor produzido, etapa 4 de 6 (2026-08-05)

Founder aprovou a AR-14 (GO para o Technical Design), oficializando modelo de citacao, cobertura estrutural, tratamento de ausencia/cobertura parcial e proibicao de ranking deterministico -- delegando a esta etapa o contrato completo de implementacao, sem escrever codigo.

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-EXECUTIVE-ADVISOR.md` -- etapa 4 de 6. ExecutiveEvidenceAssembler contratado: duas chamadas explicitas gather_context(kind=status)/gather_context(kind=risk) por Project, evidence[0] de cada, enriquecimento minimo (project_id/project_name), sete contagens calculadas na mesma passada. Invariantes matematicas confirmadas, incluindo projects_without_any_evidence = total_projects - projects_with_status - projects_with_risk + projects_with_status_and_risk. Modelo de resposta definido: ExecutiveAdvisorRequest, ExecutiveCitedEvidence (novo, isolado, kind lido de Evidence.metadata), ExecutiveAdvisorResponse (sete contagens + cited_evidence). ExecutiveAdvisorAgent transporta content sem achatar campos (schemas de status e risk sao estruturalmente diferentes). 13 cenarios de teste A-M nomeados. Estrategia incremental de 4 passos definida, mesma sequencia de Delivery/Portfolio/PMO Advisor. Riscos residuais registrados, nenhum bloqueante. Infraestrutura compartilhada confirmada preservada.

**Verificação:** missão de documentação -- nenhum código de `src/`/`tests/` alterado; `ruff check src tests` limpo.

**Recomendação:** GO para a implementação do Executive Advisor.

**Decision Log:** D-122.

## Wave 5 — Executive Advisor implementado, etapa 5 de 6 (2026-08-05)

Founder aprovou o Technical Design (GO para implementacao) com 7 diretrizes obrigatorias.

**Adicionado**
- `src/agents/executive_advisor/evidence_assembler.py` -- ExecutiveEvidenceAssembler + ExecutiveAssemblyResult. Duas chamadas explicitas gather_context(kind=status)/gather_context(kind=risk) por Project, evidence[0] de cada, enriquecimento minimo (project_id/project_name), sete contagens estruturais calculadas na mesma passada.
- `src/agents/executive_advisor/agent.py` + `src/agents/executive_advisor/prompts/advise.md` -- ExecutiveAdvisorAgent, content transportado sem achatar campos (schemas de status e risk sao estruturalmente diferentes).
- `src/api/routes/intelligence.py` -- ExecutiveAdvisorRequest, ExecutiveCitedEvidence (novo, isolado), ExecutiveAdvisorResponse, rota POST /executive-advisor/ask (RBAC intelligence.read reutilizada, nenhuma migracao nova).
- `tests/test_executive_advisor_evidence_assembler.py` (16 testes unitarios), `tests/test_executive_advisor_agent.py` (6 testes unitarios), `tests/test_executive_advisor.py` (16 testes de integracao via AdvisorFramework real), `tests/test_executive_advisor_api.py` (9 testes HTTP, RBAC).

**Verificação:** 13 cenarios A-M comprovados em quatro camadas. Invariantes de cobertura comprovadas por teste. Fonte unica confirmada estruturalmente (kind=meeting nunca contribui evidencia; RAG nunca consultado). git diff --stat vazio em AdvisorFramework/AIContextEngine/RecommendationEngine/ExplanationEngine/Workflow Runtime/Event Pipeline/CitedProject/PortfolioAdvisorResponse/PMOAdvisorResponse. Suite backend completa e suite frontend completa sem regressao. ruff/tsc/eslint limpos.

**Recomendação:** GO para o encerramento do Epic do Executive Advisor.

**Decision Log:** D-123.

## Wave 5 — Executive Advisor oficialmente encerrado (2026-08-05)

Founder aprovou a Executive Evidence do Executive Advisor -- Epic oficialmente encerrado.

**Decisão permanente registrada**
- Executive Advisor estabelece o padrao definitivo para Advisors Classe B que compoem multiplos tipos de evidencia primaria (multiplos kinds), distinto dos dois padroes ja consolidados (Portfolio: multiplos Projects/um kind; PMO: multiplos Projects/um kind/historico capado).
- Tres padroes Classe B coexistem oficialmente sem generalizacao automatica: PortfolioEvidenceAssembler, PMOEvidenceAssembler, ExecutiveEvidenceAssembler.
- Gatilho de generalizacao reafirmado: quarto consumidor estruturalmente equivalente com duplicacao real e comprovada.
- 7 de 8 Advisors da Wave 5 concluidos (Risk Advisor -- referencia; Document Advisor -- W5-1; Governance Advisor; Delivery Advisor; Portfolio Advisor; PMO Advisor; Executive Advisor). Resta apenas o Strategy Advisor.

**Verificação:** missão de governança -- nenhum código de `src/`/`tests/` alterado; `ruff check src tests` limpo.

**Autorizado:** abertura exclusiva do ciclo institucional do Strategy Advisor. Nenhum trabalho da Wave 6 antes do encerramento completo da Wave 5.

**Decision Log:** D-124.

## Wave 5 — Advisor Specification do Strategy Advisor produzida, etapa 1 de 6 (2026-08-05)

Founder autorizou formalmente a abertura do ciclo institucional do Strategy Advisor (oitavo e ultimo Advisor da Wave 5), missao exclusivamente documental.

**Adicionado**
- `docs/architecture/ADVISOR-SPECIFICATION-STRATEGY-ADVISOR.md` -- etapa 1 de 6. Achado que corrige a premissa factual de AR-8 SS4 (sem reescreve-lo): objetivos declarados nao vivem em AnalysisRecord, vivem nos campos reais Portfolio.strategic_objective/Program.objective/Project.objective, ja em producao desde a Wave 2. Classificacao determinada: Classe B, justificada per D-104 -- a propria identidade (verificar coerencia entre execucao e estrategia declarada) exige composicao de duas fontes independentes. Fontes identificadas, nenhuma decidida: campos de dominio (nunca antes usados como Evidence citavel) + AnalysisRecord kind=status/risk + RAG sobre documentos estrategicos (candidata, ja antecipada em WAVE-3-INTEGRATION-BLUEPRINT.md SS6). Nao-duplicacao demonstrada contra os 7 Advisors existentes. Distincao Executive vs Strategy registrada literalmente per a recomendacao do Founder. Sete questoes arquiteturais abertas registradas, nenhuma decidida. Avaliacao explicita: Strategy Advisor e a ultima dependencia estrutural nomeada para o encerramento da Wave 5 e, por consequencia, para a Wave 6 poder iniciar (Mission Control + WAVE-3-INTEGRATION-BLUEPRINT.md SS5/SS11).

**Verificação:** missão de documentação -- nenhum código de `src/`/`tests/` alterado; `ruff check src tests` limpo.

**Recomendação:** GO para o Domain Blueprint do Strategy Advisor.

**Decision Log:** D-125.

## Wave 5 — Domain Blueprint do Strategy Advisor produzido, etapa 2 de 6 (2026-08-05)

Founder aprovou a Advisor Specification (GO para o Domain Blueprint), confirmando Classe B definitivamente e que Portfolio.strategic_objective/Program.objective/Project.objective substituem oficialmente a hipotese preliminar de AR-8 SS4 -- delegando seis resolucoes: fonte oficial da estrategia, unidade de alinhamento, composicao de evidencias, tratamento de ausencia, cobertura parcial, escopo definitivo da comparacao.

**Adicionado**
- `docs/architecture/DOMAIN-BLUEPRINT-STRATEGY-ADVISOR.md` -- etapa 2 de 6. Fonte oficial confirmada: os tres campos de dominio, RAG permanece candidato nao decidido. Unidade de alinhamento decidida: tres unidades independentes -- Portfolio, Program, Project -- cada uma contra seu proprio campo de objetivo, nunca por heranca entre niveis. Composicao decidida: gather_context(kind=status)/gather_context(kind=risk) uma vez por Project, agregacao para Program/Portfolio e reagrupamento em memoria sem nova consulta -- volume identico ao ja aprovado para o Executive Advisor. Componente nomeado: StrategyEvidenceAssembler, quarto componente Classe B, estruturalmente distinto dos tres ja existentes. Primeira vez que DomainService se torna Evidence citavel, nao apenas resolucao de escopo. Tratamento de ausencia total (no_evidence()) e parcial (sintese com limitacao declarada) decididos. Escopo definitivo: organizacional, reaproveitando a traversal Portfolio->Program->Project ja estabelecida pelo Portfolio Advisor, para todos os Portfolios da organizacao. gather_context_many() reafirmado, nao reaberto. Infraestrutura compartilhada confirmada preservada.

**Verificação:** missão de documentação -- nenhum código de `src/`/`tests/` alterado; `ruff check src tests` limpo.

**Recomendação:** GO para a Architecture Review do Strategy Advisor.

**Decision Log:** D-126.

## Wave 5 — AR-15: Architecture Review do Strategy Advisor concluida, etapa 3 de 6 (2026-08-05)

Founder aprovou o Domain Blueprint (GO para a Architecture Review), delegando cinco resolucoes: regra conceitual de alinhamento, conflitos entre niveis, ausencia em niveis intermediarios, precedencia entre unidades, modelo definitivo de citacoes.

**Adicionado**
- `docs/architecture/AR-15-STRATEGY-ADVISOR-ARCHITECTURE-REVIEW.md` -- etapa 3 de 6. Regra de alinhamento: sempre julgamento semantico do LLM, nunca calculo deterministico, sempre fundamentado em citacao explicita. Conflitos entre niveis: nao e responsabilidade formal do Advisor, observacao textual permitida, nunca decide qual nivel prevalece. Ausencia em niveis intermediarios: confirmado que nunca afeta niveis vizinhos. Precedencia entre unidades: nao existe -- observacoes paralelas, nunca hierarquia de autoridade. Achado critico encontrado nesta revisao: RecommendationEngine.build() agrupa evidencias exclusivamente por source_id, sem considerar kind -- Strategy Advisor e o primeiro Advisor a combinar dois espacos de identificador (AnalysisRecord.id e Portfolio/Program/Project.id) na mesma chamada, risco real de colisao. Resolvido sem tocar Evidence/RecommendationEngine: source_id sintetico e disjunto (negativo, namespaced por nivel) para evidencia de estrategia declarada, id real preservado em metadata, nunca exposto na resposta HTTP. Modelo de citacao decidido: StrategyCitedEvidence (novo, isolado, level/entity_id/entity_name/kind com terceiro valor declared_strategy/source_id/created_at) -- CitedProject e ExecutiveCitedEvidence intocados. Infraestrutura compartilhada confirmada preservada.

**Verificação:** missão de documentação -- nenhum código de `src/`/`tests/` alterado; `ruff check src tests` limpo.

**Recomendação:** GO para o Technical Design do Strategy Advisor.

**Decision Log:** D-127.

## Wave 5 — Technical Design do Strategy Advisor produzido, etapa 4 de 6 (2026-08-05)

Founder aprovou condicionalmente a AR-15 (GO para o Technical Design), impondo dez condicoes explicitas, incluindo formalizacao matematica do namespace sintetico com prova de ausencia de colisao.

**Adicionado**
- `docs/architecture/TECHNICAL-DESIGN-STRATEGY-ADVISOR.md` -- etapa 4 de 6. StrategyEvidenceAssembler contratado: traversal Portfolio->Program->Project, gather_context uma vez por Project (execution_by_project reaproveitado, nunca refeito), unidades restritas ao proprio objetivo. Formula definitiva: synthetic_source_id = -(real_entity_id * 10 + level_code), com prova formal de ausencia de colisao (sempre negativo vs. AnalysisRecord.id sempre positivo; digito das unidades identifica o nivel de forma unica). Id real preservado em metadata["real_entity_id"], nunca vaza para consulta ao banco, resposta HTTP ou prompt do LLM. StrategyCitedEvidence definido (level/entity_id/entity_name/kind/source_id/created_at). Politica de timestamp: created_at=None para declared_strategy, fundamentado em leitura de models.py (Portfolio/Program/Project so tem created_at de linha, nao do campo objetivo). Modelo de cobertura: 18 contagens (6 por nivel x 3 niveis), sem condensacao. Ausencia total aciona no_evidence() automaticamente; cobertura parcial permite sintese com limitacao declarada. 15 cenarios de teste obrigatorios, incluindo prova de colisao potencial e teste de propriedade da decodificacao. Estrategia incremental de 4 passos. Infraestrutura compartilhada confirmada preservada.

**Verificação:** missão de documentação -- nenhum código de `src/`/`tests/` alterado; `ruff check src tests` limpo.

**Recomendação:** GO para a implementação do Strategy Advisor.

**Decision Log:** D-128.

## Wave 5 — Technical Design do Strategy Advisor harmonizado, correção de inconsistência de citação, ainda etapa 4 de 6 (2026-08-06)

Founder identificou, por leitura direta de código, incompatibilidade real entre o Technical Design original e `RecommendationEngine.build()`: registros `declared_strategy` enviavam ao LLM `metadata["real_entity_id"]` no campo `source_id`, valor diferente do `Evidence.source_id` real (o sintético) usado por `by_id = {item.source_id: item for item in evidence}` para correlacionar citações -- nenhuma citação de estratégia declarada teria sido resolvida corretamente.

**Corrigido**
- `docs/architecture/TECHNICAL-DESIGN-STRATEGY-ADVISOR.md` -- `StrategyAdvisorAgent` (secao 10) corrigido: `records_json` agora envia `"source_id": item.source_id` sempre (sintetico para declared_strategy, AnalysisRecord.id real para status/risk), distinto de `"entity_id"` (sempre real, para o modelo se referir a unidade em prosa). source_id sintetico passa a ser exposto ao LLM exclusivamente como token tecnico opaco de citacao -- nunca identidade real, nunca usado em consulta ao banco, nunca retornado ao cliente, nunca exibido ao usuario, sempre convertido para identidade real antes da resposta HTTP. Nova secao 10.2: prova por leitura direta de recommendation_engine.py de que nenhum outro mecanismo de correlacao existe sem alterar RecommendationEngine. Oito cenarios de teste adicionais incorporados (secao 12.1): citacao real de declared_strategy ponta a ponta (P), conversao do token sintetico para identidade real (Q), ausencia de vazamento do token na resposta HTTP (R), mesmo id real gerando tokens distintos por nivel (S), ausencia de colisao com AnalysisRecord (J), estrategia e execucao citadas simultaneamente (T), descarte de token inventado (U), propriedade do round-trip (K) -- total 21 cenarios obrigatorios. Formula do namespace sintetico, mapeamento StrategyCitedEvidence, politica de timestamp e modelo de cobertura confirmados inalterados e corretos. Infraestrutura compartilhada confirmada preservada.

**Verificação:** missão de documentação -- nenhum código de `src/`/`tests/` alterado; `ruff check src tests` limpo.

**Autorização:** implementação da etapa 5 de 6 autorizada a prosseguir sem nova pausa.

**Decision Log:** D-129.

## Wave 5 — Strategy Advisor implementado, etapa 5 de 6, oitavo e ultimo Advisor da Wave (2026-08-06)

D-129 autorizou a implementacao a prosseguir sem nova pausa, condicionada a nenhuma outra inconsistencia arquitetural ser encontrada. Esta missao implementa integralmente o contrato do Technical Design ja harmonizado.

**Adicionado**
- `src/agents/strategy_advisor/evidence_assembler.py` -- StrategyEvidenceAssembler/StrategyAssemblyResult: tres unidades de alinhamento independentes (Portfolio/Program/Project), cada uma comparada exclusivamente contra seu proprio objetivo declarado; gather_context(kind=status)/gather_context(kind=risk) chamado exatamente uma vez por Project, reaproveitado para Program/Portfolio; formula do namespace sintetico implementada conforme aprovada; 18 contagens estruturais calculadas na mesma passada.
- `src/agents/strategy_advisor/agent.py` -- StrategyAdvisorAgent: records_json envia source_id sempre igual a item.source_id (correcao de D-129), entity_id sempre real e separado.
- `src/agents/strategy_advisor/prompts/advise.md` -- diretrizes de que source_id e token opaco de citacao, cada unidade avaliada apenas contra seus proprios registros.
- `src/api/routes/intelligence.py` -- StrategyAdvisorRequest/StrategyCitedEvidence/StrategyAdvisorResponse/rota POST /strategy-advisor/ask, mesmo padrao de ask_executive_advisor.

**Achado adicional corrigido durante a implementacao:** o rascunho de referencia do Technical Design coletava Projects exclusivamente via traversal Portfolio->Program->Project, o que excluiria silenciosamente Projects orfaos (program_id IS NULL) da contagem de nivel Project -- contradizendo decisao ja oficial do Domain Blueprint (orfaos participam normalmente da unidade Project). Nao e nova questao arquitetural -- correcao de fidelidade de implementacao a decisao ja tomada. Resolvido via DomainService.list_projects(organization_id) organizacional para o nivel Project, travessia via Program/Portfolio inalterada para agregacoes superiores.

**Testado**
- `tests/test_strategy_advisor_evidence_assembler.py` (15 testes, unit/fakes), `tests/test_strategy_advisor_agent.py` (8 testes, unit/fakes), `tests/test_strategy_advisor.py` (12 testes, integracao/Postgres real), `tests/test_strategy_advisor_api.py` (12 testes, HTTP/Postgres real) -- 47 testes novos, 21 cenarios obrigatorios (A-U) comprovados, incluindo P (citacao real de declared_strategy ponta a ponta) e R (ausencia de vazamento do token na resposta HTTP completa).

**Verificação:** `ruff check src tests` limpo; suite backend completa sem regressao; `git diff --stat` vazio em AdvisorFramework/AIContextEngine/RecommendationEngine/ExplanationEngine/Workflow Runtime/Event Pipeline/contrato Evidence/CitedProject/PortfolioAdvisorResponse/PMOAdvisorResponse/ExecutiveAdvisorResponse.

**Missão:** Strategy Advisor implementado -- oitavo e ultimo Advisor da Wave 5. Retorno obrigatório para Executive Review antes de encerramento do Advisor/Wave 5 e antes de qualquer inicio da Wave 6.

**Decision Log:** D-130.
