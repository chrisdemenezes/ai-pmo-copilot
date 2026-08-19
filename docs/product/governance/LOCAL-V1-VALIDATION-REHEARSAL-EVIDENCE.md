# Local V1 Validation Rehearsal — Evidence

**Autorização:** "Founder Decision — Local V1 Validation Rehearsal", em resposta ao Local V1 User Validation Plan (D-203, APPROVED) e à correção de documentação (D-204). `LOCAL V1 USER VALIDATION = AUTHORIZED FOR PREPARATION`. Este rehearsal prova tecnicamente que a STRATECH V1 está pronta para uma sessão humana controlada — **não é** Controlled User Pilot formal, W7-1 Staging Validation, Production AI Validation, Enterprise Readiness, ou DR Drill.

**Fronteira de execução, declarada com honestidade antes de qualquer resultado:** este rehearsal foi executado no ambiente Linux desta sessão do Claude Code (container isolado, efêmero), **não na máquina Windows real do Founder**, à qual esta sessão não tem acesso. Ele prova que o procedimento oficial funciona em Linux/PostgreSQL real — a mesma base já usada durante toda a Wave 7 desta missão institucional. A aplicabilidade a Windows permanece derivada dos scripts (que já preveem Git Bash/Windows explicitamente, ver Seção 2) e da Seção 7 do Local V1 User Validation Plan, **não re-executada aqui**.

Nenhum "humano" literal participou — na ausência de um usuário real nesta sessão, o próprio agente conduziu o rehearsal via browser real (Chromium), exatamente como a Seção 7 do mandato permite ("provar tecnicamente... que a STRATECH V1 está pronta", distinto da sessão humana real que vem depois).

---

## 1. Correção de documentação (pré-requisito, D-204)

Executada e commitada independentemente **antes** deste rehearsal, per mandato Seção 1. Ver D-204: `.env.example`, `demo/start-demo.sh`, `demo/.env.example` corrigidos — PostgreSQL + pgvector declarado datastore obrigatório, variáveis de Voyage documentadas, nenhuma alteração de comportamento.

---

## 2. Pre-flight da máquina (executado nesta sessão Linux)

| Requisito | Resultado |
|---|---|
| Git | `git version 2.43.0` — OK |
| Docker Desktop / Docker | `Docker version 29.3.1` — OK (disponível nesta sessão; irrelevante ao caminho final, que usou PostgreSQL nativo, não containerizado) |
| Docker Compose | `v5.1.1` — OK |
| WSL2 | Não aplicável (ambiente já é Linux nativo) |
| Python 3.11+ | `Python 3.11.15` — OK |
| Node 22+ | `v22.22.2` — OK |
| npm | `10.9.7` — OK |
| Portas 8000/3000/5432 | Todas livres antes do início — OK |
| Espaço em disco | 28G disponíveis de 252G — OK |
| PostgreSQL/pgvector | PostgreSQL 16 iniciado; `pg_available_extensions` confirma `vector` disponível — OK |
| Acesso ao repositório | Já clonado nesta sessão | — |
| Branch/commit | `claude/stratech-permanent-principles-yjnm74` @ `16b7a9d8f20c586c9fe343256a634f9dcee24e63` |

**Nenhum requisito obrigatório ausente — nenhum STOP necessário nesta etapa.**

---

## 3. Clean Local Install

Caminho oficial executado exatamente como documentado (`Makefile`), nenhum script novo criado:

| Passo | Comando | Resultado |
|---|---|---|
| Setup | `bash scripts/prepare-env.sh` | OK, 4.3s — **nota de honestidade:** este container já continha `.venv`/`web/node_modules` pré-instalados no início da sessão (parte do provisionamento padrão do ambiente); esta execução foi idempotente ("already installed"), não uma medição de instalação zero-a-pronto genuinamente do zero |
| DB create | `bash scripts/rc2-db.sh create` | OK, idempotente ("already exists, skipping") |
| Migrate | `alembic upgrade head` | OK — `0020 -> 0021` aplicada, head confirmado |
| Dev (backend+frontend) | `DATABASE_URL=... bash demo/start-demo.sh` | OK, zero intervenção manual além de exportar `DATABASE_URL` (já documentado como necessário desde D-204 quando não se usa `make dev`) |

**Nenhuma intervenção manual não documentada foi necessária.**

---

## 4. Database Validation

| Checagem | Resultado |
|---|---|
| Conectividade | OK |
| Migration head | `0021 (head)` confirmado via `alembic current` |
| Schema/integridade | `validate_restore(engine, expect_populated=False)` → **OK**, zero problemas (mesmo mecanismo aprovado no W7-3, D-183) |
| pgvector | `vector(1024)` confirmado diretamente na coluna `chunks.embedding` |
| Seed/demo data | `organizations=2, portfolios=6, programs=8, projects=14, roles=4` confirmados |
| Tenant isolation básica | Estrutural, reconfirmada (per D-201): `organization_id` NOT NULL desde a migration `0010`, `CrossTenantViolationError` presente |
| Readiness | Ver Seção 5 |

**SQLite não foi utilizado em nenhum momento**, per mandato explícito.

---

## 5. Application Startup

| Componente | Resultado |
|---|---|
| Backend startup | OK, sem erro, log limpo |
| `GET /health` | `{"status":"healthy","service":"AI PMO Copilot","release":"unknown"}` — `release=unknown` esperado (este é um run local via `uvicorn` direto, não uma imagem Docker com `GIT_SHA` — `RELEASE_SHA` só é baked em build de imagem, per Configuration Contract) |
| `GET /ready` | `{"status":"ready"}` |
| Frontend startup | OK, sem erro |
| `GET /entrar` (frontend) | HTTP 200 |
| `GET /api/health` (frontend) | `{"status":"healthy","service":"STRATECH Frontend","release":"unknown"}` |
| BFF connectivity | Confirmada (login real, Seção 7) |

**URLs finais:** `http://localhost:3000` (frontend), `http://localhost:8000` (backend).

---

## 6. Synthetic/Demo Data

Usados exclusivamente: seed real das migrations `0002`+`0008` (Organizations/Roles/Portfolios/Programs/Projects), e um documento sintético criado especificamente para este rehearsal (`rehearsal-synthetic.md`, conteúdo genérico, sem qualquer dado real). **Nenhum dado corporativo real, nenhum documento real de cliente.**

**Achado real, registrado, não corrigido silenciosamente:** `python3 demo/seed_demo_data.py` (o enriquecimento opcional com o portfólio fictício SAP) **falhou** — `HTTP 400: X-Stratech-User-Id, X-Stratech-Organization-Id and X-Stratech-Session-Id are all required (or X-Stratech-Api-Key)`. O script chama o backend diretamente apenas com `X-API-Key`, mas o backend hoje exige também o contexto de identidade institucional (3 headers `X-Stratech-*`, normalmente injetados pelo BFF) — um requisito adicionado depois que este script foi escrito (predata a Identity Foundation). A própria mensagem de erro impressa pelo script ("See demo/README.md -- Impedimento conhecido") também está desatualizada — `demo/README.md` não contém nenhuma seção com esse nome. **Classificação: `DOCUMENTATION`/`CONFIGURATION` defect no tooling de demo, severidade `MEDIUM`** — não bloqueia a jornada principal (o dado de domínio já existe via migrations), mas impede o enriquecimento opcional. Não corrigido nesta missão, per mandato ("Não corrigir silenciosamente").

---

## 7. Human Journey Rehearsal (browser real, Chromium, contra o stack local real)

Login real executado com o usuário demo bootstrapado no boot (`bootstrap_demo_user`, `src/services/identity/auth_service.py`) — organização **`demo-organization`** (slug), e-mail `demo@stratech.local`, senha = `WORKSPACE_PASSWORD` de `demo/.env`.

**Correção transparente a uma afirmação anterior (D-201):** a Readiness Review classificou `WORKSPACE_PASSWORD` como "exigido no boot mas nunca consumido em nenhuma lógica de autenticação real" — essa afirmação era **incompleta**, verificada apenas contra o frontend (`web/`). O **backend** (`src/services/identity/auth_service.py:bootstrap_identities`) **consome `WORKSPACE_PASSWORD` ativamente**, criando um usuário demo real na organização "Demo Organization" no boot. D-201 não é editado retroativamente — esta é a correção, registrada aqui com transparência.

**Achado real durante o login:** `demo/README.md` instrui apenas "senha em demo/.env" para o login, sem mencionar a organização (slug `demo-organization`) ou o e-mail (`demo@stratech.local`) necessários nos outros 2 campos do formulário — confirmado empiricamente (a primeira tentativa, usando o nome de exibição "Demo Organization" em vez do slug, falhou com `401`/"organization not found"). **Classificação: `DOCUMENTATION` defect, severidade `LOW`** (facilmente contornável uma vez conhecido o padrão, mas causa falha real na primeira tentativa de qualquer pessoa seguindo o README literalmente).

| Capability | PASS/FAIL | Evidência |
|---|---|---|
| Login | **PASS** | `/dashboard` alcançado |
| Dashboard | **PASS** | Heading + KPIs reais renderizados (screenshot) |
| Navigation | **PASS** | Todos os 10 itens principais navegados sem erro |
| Priorização | **PASS** | Renderizado |
| Projects | **PASS** | Renderizado |
| Program Management | **PASS** | Renderizado |
| Project Delivery | **PASS** | Renderizado |
| Actions | **PASS** | Renderizado |
| Decisions | **PASS** | Renderizado |
| Learnings | **PASS** | Renderizado |
| Documents | **PASS** (após correção de papel do usuário demo — ver abaixo) | Upload sintético → status "Indexado", 1 chunk, visível na listagem |
| Knowledge/RAG mechanism | **PASS (mecanismo)** | Indexação via `MockEmbeddingProvider` completou sem erro |
| Advisors mechanism | **PASS (mecanismo, fail-closed corretamente)** | Ver Seção 8 |
| Decision Support mechanism | **PASS (mecanismo, fail-closed corretamente)** | Ver Seção 8 |
| Executive Narrative mechanism | **PASS (mecanismo, fail-closed corretamente)** | Ver Seção 8 |
| Mission Control | **PASS** | Renderizado (dado estático por design) |
| Administration | **PASS** | Renderizado |
| Logout | **PASS** | Redirecionamento a `/entrar`, rota protegida exige login de novo |

**Achado real durante Documents (RBAC funcionando corretamente, não um defeito):** o usuário demo bootstrapado tem exclusivamente o papel `viewer` (por design — `bootstrap_demo_user()` comenta explicitamente "re-ensure `viewer` on every boot"), que **não** tem a permissão `knowledge.write` — confirmado via consulta direta a `role_permissions` (`organization_admin`/`pmo`/`project_manager` têm `knowledge.write`; `viewer` não). O upload retornou corretamente `403`/"missing permission: knowledge.write" na primeira tentativa — **RBAC funcionando exatamente como projetado**, não um defeito. Para completar a jornada de rehearsal, o papel `pmo` foi atribuído ao usuário demo via `EnterpriseRepository.assign_role_in_session()` (o mesmo método que o próprio bootstrap já usa internamente) — configuração de ambiente de teste, não uma correção de produto. Após isso, o upload funcionou de ponta a ponta.

**Achado ambiental real, diagnosticado e resolvido (não um defeito de produto):** a primeira tentativa de acessar `/api/bff/admin/documents` (e outras rotas `/api/bff/admin/*`) retornou **404 persistente**, apesar dos arquivos de rota existirem e funcionarem corretamente quando testados sem sessão (401 correto). Diagnosticado como cache `.next/dev` (Turbopack) corrompido/obsoleto, compartilhado entre múltiplos processos `next dev` iniciados em portas diferentes ao longo desta mesma sessão (E2E na porta 3100 mais cedo, demo na porta 3000 agora) — mesma classe de problema já encontrada e corrigida anteriormente nesta sessão (Etapa de Final Validation do W7-7). **Resolvido limpando `web/.next`** (ação de diagnóstico/tooling, não uma alteração de código) e reiniciando — confirmado 200 OK de forma consistente depois. **Classificação: `ENVIRONMENT` defect, não `PRODUCT` defect** — o código da rota estava correto o tempo todo.

---

## 8. AI Boundary (Gates B/C indisponíveis, per D-202 — inalterado)

**`PRODUCT/MECHANISM = PASS` para Advisors/Decision Support/Executive Narrative — `AI CONTENT QUALITY = NOT VALIDATED`.**

Exercitados via browser real, escopo "Organização", com `LLM_PROVIDER=mock` (Demo Mode padrão, sem `response_file` para essas 4 capabilities — confirmado em D-203 que o Demo Mode não as cobre). Resultado observado: **`Backend respondeu 502`** em ambos (Decision Support e Executive Narrative).

**Achado real e refinamento transparente de D-203:** os logs do backend confirmam mecanicamente que toda a cadeia real executou corretamente antes da falha — RBAC (`permission check ... granted=True`), auditoria (`Audit action=strategy_advisor.question_asked` e equivalentes para `risk_advisor`/`delivery_advisor`/`pmo_advisor`/`executive_advisor`, confirmando seleção multi-advisor real do `ExecutiveOrchestrator`), coleta real de evidência (dezenas de queries reais a `analyses`/`projects`/`portfolios`/`programs`), e a chamada ao LLM configurado (`AI Foundation call analyst=strategy_advisor ... latency_ms=0.1`). A falha ocorre **depois** disso, em `AdvisorFramework.run()` (`src/services/advisor_framework/framework.py:96-98`): o framework valida que `model_output.get("structured")` é verdadeiro e que `answer` é uma string — o `MockLLMProvider` padrão retorna o texto estático `"mock analysis output"`, que `parse_structured_output()` corretamente degrada para `{"structured": False, "raw_output": ...}`, **e o Framework corretamente recusa tratar isso como uma recomendação válida**, levantando `AdvisorExecutionError` → HTTP 502 (`src/api/routes/intelligence.py`, mapeamento já existente, não novo).

**Isso é comportamento correto e desejável — fail-closed, nunca fabrica uma recomendação a partir de uma resposta não conforme ao schema — não um defeito.** Refina (não contradiz) a afirmação de D-203 de que essas rotas "executam de ponta a ponta sem crash": a afirmação era verdadeira na camada de parsing, mas incompleta uma camada acima — o `AdvisorFramework` intencionalmente rejeita conteúdo não estruturado antes de compor uma resposta HTTP 200. D-203 não é editado retroativamente; este é o refinamento, registrado aqui com transparência.

**Conclusão da Seção 8:** o mecanismo completo (RBAC → auditoria → coleta de evidência → seleção de Advisors → chamada ao provider → validação de resposta) está comprovadamente real e íntegro, inclusive seu comportamento de segurança em caso de resposta não conforme. **Nenhuma qualidade de conteúdo de IA foi validada** — isso permanece exclusivamente dependente do Gate C (Anthropic real), inalterado.

---

## 9. Backup Safety Point

Executado o mecanismo real do W7-3 (`src/database/backup.py`, D-182) contra o banco local usado neste rehearsal (incluindo o documento sintético e as alterações de papel feitas durante a sessão):

```
{
  "path": ".../aipmo_local-rehearsal_20260814T215603Z.dump",
  "environment": "local-rehearsal",
  "alembic_revision": "0021",
  "size_bytes": 83324
}
```

**PASS.** Artefato + metadata sidecar gerados com sucesso, mesma verificação objetiva via `pg_restore --list` já embutida no mecanismo aprovado. **Nenhum DR Drill executado** (nenhum restore destrutivo, per mandato explícito) — apenas a prova de que um recovery point pode ser gerado antes de qualquer sessão humana.

---

## 10. Defeitos encontrados — classificação

| # | Achado | Classificação | Severidade | Bloqueia sessão humana? |
|---|---|---|---|---|
| 1 | `demo/seed_demo_data.py` falha com `HTTP 400` (headers de identidade ausentes) — script desatualizado desde a Identity Foundation | `CONFIGURATION`/`DOCUMENTATION` (tooling de demo, não produto) | MEDIUM | Não — jornada principal usa dado já seedado pelas migrations |
| 2 | `demo/README.md` não documenta organização/e-mail do login, apenas a senha | `DOCUMENTATION` | LOW | Não — contornável uma vez conhecido |
| 3 | Cache `.next/dev` obsoleto causou 404 persistente em rotas `/api/bff/admin/*` | `ENVIRONMENT` | MEDIUM (resolvido nesta sessão) | Não, após `rm -rf web/.next` — recomendável limpar antes de qualquer sessão real |
| 4 | Usuário demo bootstrapado só tem papel `viewer`, insuficiente para exercitar upload de Documents | `CONFIGURATION` (comportamento de RBAC correto, papel padrão restritivo) | LOW | Não — papel `pmo` facilmente atribuível para a sessão real, se o roteiro incluir upload |
| 5 | Advisors/Decision Support/Executive Narrative retornam 502 com `LLM_PROVIDER=mock` padrão | **Não é defeito** — comportamento fail-closed correto e desejável | N/A | Não — esperado e já classificado na Seção 8 |

**Nenhum `BLOCKER` ou `HIGH` encontrado.** Nenhuma correção de código foi aplicada nesta missão — apenas ações de diagnóstico/configuração de ambiente de teste (limpeza de cache, atribuição de papel), nenhuma delas uma alteração de `src/`/`web/` versionada.

---

## 11. Duração e intervenções

- **Duração total do rehearsal** (pre-flight → backup): aproximadamente 20 minutos de execução ativa.
- **Intervenções manuais registradas:** exportar `DATABASE_URL` para `demo/start-demo.sh` (já documentado desde D-204); limpeza de `web/.next` (diagnóstico de cache, não uma correção de produto); atribuição do papel `pmo` ao usuário demo (configuração de teste, não uma correção de produto); correção do slug de organização usado no login (`demo-organization`, não "Demo Organization" — achado do item 2 da Seção 10).

---

## 12. Decisão Final

1. **Clean installation = PASS**
2. **PostgreSQL/pgvector = PASS**
3. **Migrations = PASS**
4. **Backend = PASS**
5. **Frontend = PASS**
6. **Login = PASS**
7. **Core product journey = PASS**
8. **Documents = PASS** (após atribuição de papel `pmo`, configuração de teste)
9. **Knowledge/RAG mechanism = PASS**
10. **Advisors mechanism = PASS** (fail-closed corretamente validado)
11. **Decision Support mechanism = PASS** (fail-closed corretamente validado)
12. **Executive Narrative mechanism = PASS** (fail-closed corretamente validado)
13. **Logout = PASS**
14. **Backup recovery point = PASS**
15. **AI CONTENT QUALITY = NOT VALIDATED** (Gates B/C indisponíveis, inalterado desde D-202)
16. **Defeitos por severidade:** 0 BLOCKER, 0 HIGH, 2 MEDIUM (itens 1 e 3, item 3 já resolvido nesta sessão), 2 LOW (itens 2 e 4), 0 UX/FEEDBACK adicional
17. **Intervenções manuais:** 4, todas registradas na Seção 11, nenhuma uma alteração de código de produto
18. **LOCAL V1 USER SESSION = GO** — tecnicamente pronta, com as 4 observações da Seção 10 registradas (nenhuma bloqueante)

**Confirmações explícitas, per mandato:**

- **W7-1 permanece `OPEN`** — inalterado.
- **External Gates A/B/C/D permanecem exatamente como registrados em D-202** — inalterados (A/B/C `NOT AVAILABLE`, D `NOT APPROVED`).
- **Nenhuma Production AI Validation ocorreu** — `LLM_PROVIDER=mock`/`EMBEDDING_PROVIDER=mock` usados durante todo o rehearsal.
- **Nenhuma alegação de Enterprise Readiness foi feita.**
- **Nenhum dado corporativo real foi usado** — exclusivamente dado seedado pelas migrations e um documento sintético criado para este rehearsal.

Nenhuma sessão com usuário real iniciada automaticamente. Nenhum staging iniciado. Nenhum DR Drill executado. Nenhum outro Epic iniciado. Retornando obrigatoriamente para Executive Review.
