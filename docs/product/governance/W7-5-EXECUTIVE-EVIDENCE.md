# W7-5 EXECUTIVE EVIDENCE — Deployment / Environment / Release Discipline

**Autorização:** "Founder Decision — Wave 7 Enterprise Readiness — W7-5 Technical Design Approval + Implementation Authorization", aprovando `TECHNICAL-DESIGN-W7-5-DEPLOYMENT-ENVIRONMENT-RELEASE-DISCIPLINE.md` (D-171), decidindo **hospedagem de frontend = containerizada, mesma disciplina de deployment do backend**, e autorizando implementação incremental de exatamente 6 Etapas nomeadas — cada uma com escopo próprio, testes, verificação de regressão, registro de governança e commit independente e rastreável.

**Explicitamente fora de escopo desta missão (verbatim das proibições do Founder):** provisão de staging real; provisão de produção real; início de W7-1; início de Disaster Recovery; definição de RTO/RPO; escolha de backend de embedding de produção; decisão RESTRICT/CASCADE; implementação de `EnterpriseMemoryService`; início de W7-3/W7-4/W7-7; introdução de Kubernetes; introdução de vault de segredos; introdução de nova plataforma cloud sem necessidade demonstrada; alteração de funcionalidade de negócio.

---

## Etapas executadas

| Etapa | Commit | Escopo |
|---|---|---|
| 1 — Configuration Contract + Fail-Fast | `1391373` | `ENVIRONMENT`, fail-fast no boot |
| 2 — Readiness | `c5feae7` | `GET /ready` |
| 3 — Release Identity | `e8cf418` | `RELEASE_SHA` em `GET /health` |
| 4 — Frontend Containerizado | `8b9ab0e` | `web/Dockerfile`, serviço `web` |
| 5 — Migration Discipline | `9ad507a` | Migração separada do boot; revisão PRI-008/PRI-009 |
| 6 — Smoke Test Parametrizável | `0975483` | `PLAYWRIGHT_BASE_URL`, `smoke.spec.ts` |

Cada etapa foi implementada, testada e verificada isoladamente (`ruff`/suíte relevante) antes do commit correspondente, e cada commit foi empurrado para `origin/claude/stratech-permanent-principles-yjnm74` imediatamente após a verificação — nenhuma etapa depende de trabalho não persistido no repositório remoto.

---

## Configuration Contract (final)

`src/api/startup_config.py` (backend) + `web/lib/startup-config.ts` (frontend, espelho):

- **`ENVIRONMENT`**: `dev` (default quando ausente) | `staging` | `production`. Qualquer outro valor falha explicitamente (`StartupConfigError`).
- **DEV**: `collect_startup_config_problems("dev")` sempre retorna `[]` — nenhuma validação é executada, comportamento idêntico ao pré-existente. Confirmado por teste e por não haver nenhum script/CI (`Makefile`, `.github/workflows/ci.yml`, `demo/*.sh`, `scripts/*.sh`) que defina `ENVIRONMENT` hoje — todo entry point local/demo permanece implicitamente `dev`.
- **STAGING/PRODUCTION** (backend): falham no boot (`validate_startup_config`, chamado em `src/main.py`'s `lifespan`, antes de qualquer outra inicialização) se:
  - `DATABASE_URL` ausente, **ou** resolvendo para `sqlite` — elimina estruturalmente a possibilidade de SQLite silencioso em staging/produção;
  - `API_KEY` ausente;
  - `LLM_PROVIDER=mock` (não permitido fora do dev), **ou** `LLM_PROVIDER=anthropic` sem `ANTHROPIC_API_KEY`;
  - `EMBEDDING_PROVIDER=mock` (não permitido fora do dev);
  - `CORS_ALLOWED_ORIGINS` ausente.
- **STAGING/PRODUCTION** (frontend, BFF): falham no boot (`web/instrumentation.ts`, hook `register()` do Next.js) se `SESSION_SECRET`/`WORKSPACE_PASSWORD`/`BACKEND_URL`/`API_KEY` estiverem ausentes.

### Prova de fail-fast

`tests/test_startup_config.py` (25 cenários) + `web/lib/startup-config.test.ts` (19 cenários) cobrem, individualmente: dev permissivo; staging válido; staging inválido (cada variável faltando isoladamente + múltiplas simultâneas); production válido; production inválido (mesma matriz); `ENVIRONMENT` ausente; `ENVIRONMENT` inválido.

**Garantia central demonstrada:** `DATABASE_URL` ausente em staging/produção nunca cai silenciosamente para SQLite (`src/database/engine.py`'s `DEFAULT_DATABASE_URL` continua existindo para DEV, mas staging/produção nunca alcançam esse fallback — o boot já falhou antes). Misconfiguração de LLM/embedding nunca permanece latente até a primeira requisição real fora do dev — falha no `lifespan`, antes do primeiro `uvicorn` aceitar conexões.

### DEV / STAGING / PRODUCTION estruturalmente distinguíveis

A variável `ENVIRONMENT` é a única fonte de verdade de qual conjunto de regras se aplica — não há inferência por hostname, porta, ou heurística. Demo Mode (que nunca define `ENVIRONMENT`) resolve para `dev` e permanece permissivo por definição — **não pode representar silenciosamente staging**, porque staging exige `ENVIRONMENT=staging` explícito, que Demo Mode nunca define.

---

## Readiness (`GET /ready`)

Distinto de `GET /health` (liveness, inalterado — confirmado por `tests/test_readiness_endpoint.py::TestHealthUnchanged`). `/ready`:

- reutiliza `collect_startup_config_problems()` (mesmo Configuration Contract da Etapa 1);
- testa conectividade real com o banco (`SELECT 1` via `Depends(build_repository)`, mesmo padrão de DI de `src/api/routes/portfolio.py`);
- nunca crasheia o processo — captura qualquer falha de conexão e a reporta como um `problem` explícito (`# noqa: BLE001`, justificado: readiness deve reportar qualquer dependência quebrada, nunca derrubar a probe);
- responde `200 {"status": "ready"}` quando tudo está saudável, `503 {"status": "not_ready", "problems": [...]}` caso contrário;
- **não faz nenhuma chamada LLM** — nenhum Technical Design demonstrou essa necessidade, e isso tornaria toda probe cara e cobrada pelo provider.

Testado: caminho feliz com banco real; `503` com config crítica ausente em staging; `503` com banco inalcançável (via `app.dependency_overrides`, o seam correto para `Depends()` capturado em tempo de registro de rota).

---

## Release Identity

`Dockerfile` (backend) e `web/Dockerfile` (frontend, Etapa 4): `ARG GIT_SHA=unknown` + `ENV RELEASE_SHA=${GIT_SHA}`, definidos no build. `GET /health` do backend e `GET /api/health` do frontend expõem `"release"` (o SHA, ou `"unknown"` se não informado no build). Nenhum sistema de versionamento novo — reutiliza Git. `docker-compose.yml` propaga `GIT_SHA` para ambos os serviços via `build.args`, com `${GIT_SHA:-unknown}` como default seguro para um `docker compose build` sem nenhuma variável exportada.

Isso prepara — sem implementar automação de promoção, fora de escopo — a regra registrada em `PRI-009` §2: o artefato validado em staging é o mesmo promovido para produção (`docker compose build` uma vez, mesma imagem `up` em ambos os ambientes), nunca um rebuild silencioso.

---

## Frontend Containerizado (Founder Decision — hospedagem)

Decisão do Founder: containerizado, mesma disciplina de deployment do backend. Implementado:

- `web/next.config.ts`: `output: "standalone"` — confirmado via `node_modules/next/dist/docs/.../output.md` (não assumido de treinamento, per `web/AGENTS.md`) como o padrão correto e documentado para uma imagem Docker mínima e reproduzível.
- `web/Dockerfile`: multi-stage (`deps`/`builder`/`runner`), mesma convenção de release identity do backend.
- `web/app/api/health/route.ts`: liveness própria do container (`status`/`service`/`release`), não uma proxy do backend.
- `docker-compose.yml`: serviço `web` — build separado, porta `3000`, variáveis do BFF, `depends_on: [api]`. **Artefato separado do backend, sem acoplamento em um único container**, exatamente como decidido.
- Confirmado por `npm run build` real: `/api/health` no manifesto de rotas; `find .next/standalone -iname "*instrumentation*"` confirma que o hook de fail-fast da Etapa 1 (`instrumentation.ts`) é corretamente rastreado no output standalone.

---

## Migration Discipline

`docker-compose.yml`'s serviço `api`: comando volta a ser apenas `uvicorn src.main:app ...` — `alembic upgrade head` deixou de fazer parte do comando de start. `PRI-009` §2 reescrita em 5 passos explícitos: backup → build (com `GIT_SHA`) → **migração como etapa isolada e separadamente falhável** (`docker compose run --rm api alembic upgrade head`, interrompendo o deploy se falhar) → subida da aplicação sobre o schema já migrado → confirmação (`alembic current`). Alinhado ao Deployment Contract do Technical Design (Build → Validate → Migrate → Deploy → Readiness → Smoke → Promote).

### Revisão de PRI-008/PRI-009 contra o schema V2 real (mandato explícito desta etapa)

Antes de confiar nos procedimentos existentes, ambos os runbooks foram revisados contra o schema V2 real e as **20 migrations reais** (`alembic/versions/0001_initial.py` a `0020_w5_0_document_ingestion.py` — confirmado por listagem direta do diretório, não por suposição). Dois achados relevantes, elevados e **não mascarados**:

1. **PRI-008 descrevia a imagem do banco como `postgres:16`.** A imagem real, desde a Wave 3 (Enterprise Knowledge Platform Fase 1), é `pgvector/pgvector:pg16`. Corrigido no texto de abertura do runbook.
2. **A validação pós-restauração (PRI-008 §4) checava apenas a tabela `analysis_records`** — a única tabela que existia quando o runbook foi escrito (V1). O schema V2 real tem ~20 tabelas cobrindo Identity/RBAC, Enterprise Domain e a Enterprise Knowledge Platform. A restauração em si **não tem essa lacuna** (`pg_restore` restaura o dump lógico inteiro, todas as tabelas — confirmado por leitura do procedimento §1/§3), apenas a validação pós-restauração ficou desatualizada. Documentado como gap explícito em PRI-008 §4, nomeando o que falta (contagem por domínio crítico: `organizations`, `users`, `chunks`) para ser fechado antes de qualquer restauração real em produção — **não é um redesenho de Disaster Recovery**, RTO/RPO permanecem fora de escopo desta revisão, conforme explicitamente mandatado.

Também corrigida a alegação desatualizada em PRI-009 §3 (Rollback) de "única migração" para "20 migrations reais".

---

## Smoke Test Parametrizável

`web/playwright.config.ts`: `PLAYWRIGHT_BASE_URL`, quando definida, sobrepõe `baseURL` e desliga o `webServer` local (nunca sobe um dev server que mascararia o ambiente real apontado). `web/e2e/smoke.spec.ts`: 4 checks — app acessível (`/entrar`); `GET /api/health` do frontend; `GET /ready` do backend (via `SMOKE_BACKEND_URL`); login básico até um endpoint funcional (via `SMOKE_LOGIN_EMAIL`/`SMOKE_LOGIN_PASSWORD`/`SMOKE_LOGIN_ORGANIZATION`). **Nenhuma credencial hardcoded** — os 2 checks que dependem de variáveis de ambiente são pulados (`test.skip`), nunca falham, quando ausentes. Verificado end-to-end nesta missão com credenciais do mock backend simuladas via env vars: os 3 checks aplicáveis passam, o 4º pula corretamente por falta de um backend real alcançável neste sandbox. Não substitui a suíte E2E completa (que continua cobrindo os fluxos funcionais reais) nem os 5 passos manuais de validação pós-deploy já documentados em `PRI-009` §5.

---

## Testes executados e resultados

| Suíte | Resultado |
|---|---|
| Backend completo (`pytest`) | **900 passed**, 0 failed |
| `ruff check src tests` (arquivos novos/alterados) | Limpo — única exceção é `B008` (`Depends()` em default de argumento), padrão pré-existente e idêntico em toda rota do codebase (confirmado via `ruff check src/api/routes/portfolio.py`), não introduzido por esta missão |
| Frontend completo (`vitest`) | **567 passed** (78 arquivos) |
| `npx tsc --noEmit` | Limpo |
| `npx eslint .` | Limpo |
| `npm run build` | OK — `/api/health` no manifesto; `instrumentation.js` corretamente rastreado no output `standalone` |
| E2E completo (`playwright test`, mobile/md/lg) | **322 passed, 0 failed, 8 skipped** |

Os 8 skips são todos esperados: 1 skip pré-existente de `shell.spec.ts` (`the bottom nav bar does not overlap...`, específico de mobile) × os projetos onde não se aplica, e os 2 smoke tests condicionados a `SMOKE_BACKEND_URL`/`SMOKE_LOGIN_*` (não fornecidas nesta execução de verificação) × 3 viewports. Um flake isolado de `users-admin.spec.ts::assigns and removes a role` observado em uma execução anterior do `--project=lg` foi confirmado como flake (rerodado isoladamente, passou; e passou novamente na execução final completa) — não uma regressão desta missão.

---

## Preservação arquitetural

Nenhuma Capability alterada semanticamente. Nenhum componente enterprise compartilhado reestruturado — confirmado por `git diff --stat` desta missão contra `01353ef` (base pré-implementação): as únicas alterações fora dos arquivos listados acima são de governança (Decision Log, CHANGELOG, `mission-control-data.ts`). Enterprise Domain, Knowledge Platform, `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, Workflow Runtime, Event Pipeline, os 8 Enterprise Advisors, Executive Orchestrator, Decision Support, Executive Narrative, tenant isolation, RBAC e auditability permanecem byte-a-byte inalterados.

---

## Nota operacional (transparência de execução)

No meio desta missão, o container de execução foi reciclado. O checkout local do branch de trabalho estava desatualizado — parado em um commit muito anterior ao próprio Technical Design (`01353ef`, já publicado em `origin`) —, o que significa que as 6 Etapas então já implementadas e commitadas localmente **não haviam sido empurradas para `origin` a tempo** e foram perdidas com o container. O branch local foi resincronizado com a ponta real de `origin` (`git reset --hard origin/claude/stratech-permanent-principles-yjnm74`, sem perda real — o commit local órfão já era ancestral de `main`) e as 6 Etapas foram **reconstruídas do zero, com o mesmo conteúdo e a mesma disciplina de commit por etapa**, sobre a base correta. A partir da reconstrução, cada commit foi empurrado para `origin` imediatamente após sua verificação, eliminando o risco de nova perda de trabalho não persistido remotamente. Nenhum atalho de escopo foi tomado por causa deste incidente — todas as verificações (ruff/pytest/tsc/eslint/vitest/E2E) descritas acima foram executadas contra o código efetivamente reconstruído e commitado.

---

## Riscos residuais (reconfirmados, nenhum resolvido nem escondido)

1. **PRI-008 §4 (validação pós-restauração) permanece parcial** — cobre apenas `analysis_records`, não os ~20 domínios do schema V2 real. Documentado como gap explícito nesta missão; sua resolução (expandir a validação por domínio crítico) não foi executada, por não ser mandato desta etapa além de documentar/elevar.
2. **Mitigação de força bruta em `/api/bff/session` continua pendente** (já registrada em `PRI-009` §1 antes desta missão) — condição formal para deploy além de uso interno/piloto, não alterada por W7-5.
3. **Nenhum ambiente de staging real foi provisionado** — o Configuration Contract, a Readiness, a Release Identity e o Deployment Contract agora existem e são testáveis, mas nunca foram exercitados contra uma infraestrutura real de staging/produção. Essa validação real é o objeto do W7-1, explicitamente não iniciado por esta missão.
4. **Frontend hospedado containerizado, decisão já tomada e implementada** — nenhum risco residual de decisão em aberto aqui; a única pendência é a validação operacional real (W7-1).

---

## Itens que pertencem ao W7-1 (explicitamente não iniciados)

- Validação real de staging/produção com provedor LLM real.
- Provisionamento de qualquer ambiente staging/produção real.
- Exercício real do Deployment Contract (Build → Validate → Migrate → Deploy → Readiness → Smoke → Promote) fora deste repositório local.
- Expansão da validação pós-restauração do PRI-008 por domínio crítico (gap elevado nesta missão, não resolvido).
- Absorção de TD-011 (via W7-1, per D-171).

---

## GO / NO-GO

**GO para o encerramento de W7-5.** As 6 Etapas mandatadas pelo Founder foram implementadas integralmente, cada uma no seu próprio escopo, com testes, verificação de regressão e commit rastreável. Nenhuma prova mandatada falhou. Nenhuma proibição explícita foi violada. Nenhuma Capability ou componente enterprise compartilhado foi alterado.

**Nenhum trabalho do W7-1 foi iniciado.** Retornando obrigatoriamente para Executive Review.
