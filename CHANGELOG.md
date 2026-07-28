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
