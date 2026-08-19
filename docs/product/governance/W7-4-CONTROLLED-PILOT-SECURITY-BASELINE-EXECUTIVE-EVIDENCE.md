# W7-4 — Controlled Pilot Security Baseline — Executive Evidence

**Autorização:** "Founder Decision — W7-4 Security Hardening — Controlled Pilot Security Baseline — Implementation Authorization", em resposta ao Technical Design (D-187, APPROVED). Autorizada exclusivamente a implementação necessária para eliminar F1 (login brute-force), F2 (kill switch sem fail-fast) e F4 (upload sem limite de tamanho) — os três findings `HIGH`/`BLOCKS CONTROLLED PILOT`. Nenhum outro finding, nenhuma nova infraestrutura (Redis/WAF/CAPTCHA/MFA/SIEM), nenhum item `MEDIUM`/`LOW`. Objetivo explícito: atingir e comprovar `CONTROLLED PILOT SECURITY BASELINE`, não concluir o W7-4 inteiro.

**Mandato de encerramento:** ao final das 3 etapas, revalidar explicitamente os controles já classificados adequados, comprovar mecanicamente o fechamento de F1/F2/F4 (nunca assumido), e produzir esta Executive Evidence. **STOP** — nenhum DR Drill, nenhum provisionamento de staging, nenhuma execução de W7-1, nenhum encerramento de W7-4, nenhum outro Epic iniciado.

---

## 1. Estado inicial

| Finding | Severidade | Estado antes desta missão |
|---|---|---|
| F1 — ausência de proteção de força bruta/lockout no login | HIGH, `BLOCKS CONTROLLED PILOT` | `OPEN` — apenas o rate limiter genérico (`enforce_rate_limit`), compartilhado por toda a organização via `X-API-Key`, se aplicava; nenhuma proteção específica de identidade de login |
| F2 — `DISABLE_WORKSPACE_SESSION_GATE` sem checagem de fail-fast | HIGH, `BLOCKS CONTROLLED PILOT` | `OPEN` — se `true` em staging/produção, desativaria toda a autenticação do workspace sem nenhum alarme |
| F4 — upload de documento sem limite de tamanho | HIGH, `BLOCKS CONTROLLED PILOT` | `OPEN` — `raw_bytes = file.file.read()` sem bound, risco de exaustão de memória |

Confirmado por leitura direta do código no início desta missão (D-187), não assumido.

---

## 2. Implementação F1 (login brute-force protection)

**Fluxo real confirmado antes de implementar:** Browser → BFF (`POST /api/bff/session`) → `POST /api/auth/login` (`X-API-Key` compartilhada por toda a organização) → `AuthService.authenticate()` (Argon2) → `AuthService.create_session()`.

**Solução:** `LoginBruteForceGuard` (`src/api/rate_limiter.py`, reutilizando o módulo/padrão de `RateLimiter` já existente). Chave = `organization.strip().lower() + ":" + normalize_email(email)` — escopada a uma única identidade, deliberadamente distinta da chave `X-API-Key` do rate limiter genérico (que é compartilhada por toda a organização). `record_failure()` roda uniformemente em todo `authenticate() is None`, qualquer que seja a causa (senha errada, usuário inexistente, organização inexistente, conta inativa) — garantindo que uma identidade inexistente bloqueia exatamente como uma real, sem permitir enumeração. `check()` roda antes de `authenticate()`; se bloqueada, `429` genérico.

**Valores definidos e documentados:** `LOGIN_LOCKOUT_MAX_ATTEMPTS=5` (default), `LOGIN_LOCKOUT_WINDOW_SECONDS=900` (15min), `LOGIN_LOCKOUT_DURATION_SECONDS=900` (15min) — configuráveis via variável de ambiente.

**Limitação documentada explicitamente (não escondida):** mecanismo process-local, em memória, single-instance — proporcional ao deployment atual (um único container `api`); em multi-instância futura, cada instância teria estado próprio, enfraquecendo o threshold efetivo — **não apresentado como solução de Enterprise Production**.

**Nenhuma alteração a:** Argon2, modelo de sessão, RBAC, tenant isolation.

**Registrado como D-188.**

---

## 3. Implementação F2 (authentication kill-switch fail-fast)

**Solução:** `web/lib/startup-config.ts` — `collectStartupConfigProblems()` ganha uma checagem: `DISABLE_WORKSPACE_SESSION_GATE === "true"` fora de `dev` é reportado como problema crítico, no mesmo array já consumido por `validateStartupConfig()`. Nenhum mecanismo paralelo — reutiliza exatamente o hook já existente (`web/instrumentation.ts`, `register()`, executado uma vez no boot do servidor Next.js).

**O próprio session gate (`web/proxy.ts`) não foi alterado** — o problema foi eliminado inteiramente na fronteira de configuração, exatamente como mandatado.

**Registrado como D-189.**

---

## 4. Implementação F4 (document upload size limit)

**Fluxo real confirmado antes de implementar:** `POST /api/documents` → `UploadFile` → `raw_bytes = file.file.read()` (o ponto real do achado, sem bound) → decode UTF-8 → `DocumentIngestionService.upload()` → `KnowledgeRepository`.

**Solução em duas camadas, defesa em profundidade:**
1. `MaxUploadSizeMiddleware` (`src/api/security.py`, ASGI puro, mesmo padrão de `RequestIDMiddleware`) — rejeita `413` antes do parser multipart do Starlette processar o corpo, com base no `Content-Length` declarado. Escopado exclusivamente a `POST /api/documents`.
2. Leitura limitada (`file.file.read(max_upload_size_bytes() + 1)`) em `upload_document()` — a camada precisa e definitiva: nunca materializa mais que `limite + 1` bytes em memória, independentemente do que qualquer header declare.

**`MAX_UPLOAD_SIZE_BYTES`**, default 10 MiB, mesmo padrão `env-var-com-default` já usado por `RATE_LIMIT_MAX_REQUESTS`/`DB_POOL_SIZE`.

**Achado corrigido durante a implementação, com transparência:** `Content-Length` mede o envelope `multipart/form-data` inteiro (boundaries, headers por parte, demais campos do formulário), não apenas os bytes do arquivo. A primeira versão do middleware comparava o valor bruto diretamente contra o limite, rejeitando incorretamente arquivos legitimamente pequenos — achado pelos próprios testes S/T/Z, que falharam antes da correção (não mascarado, corrigido na sequência). Corrigida para comparar contra `limite + 8192 bytes` de folga fixa para overhead de multipart — deliberadamente grosseira (rejeição antecipada, barata), nunca a fonte de verdade; a leitura limitada da camada 2 permanece a autoridade exata.

**Tipos de arquivo permitidos inalterados. Pipeline de ingestão não redesenhado** — apenas uma rejeição antecipada adicionada antes do primeiro passo.

**Registrado como D-190.**

---

## 5. Decisões técnicas

| Decisão | Justificativa |
|---|---|
| Chave de brute-force = organização+email, não IP | O backend nunca vê o IP real do browser (arquitetura BFF, server-to-server) de forma confiável; a chave escolhida ataca diretamente "uma única identidade" (requisito do Founder) sem depender de um dado indisponível |
| Guarda de login vive na camada de rota, não em `AuthService` | Preserva `AuthService.authenticate()`/Argon2 100% intocados, minimizando o raio de alteração |
| Mecanismo de lockout em memória, não Redis | Proporcional ao deployment atual (single-instance); Redis só se justificaria com escalonamento horizontal real, não demonstrado |
| Fail-fast de F2 na fronteira de configuração, não no gate | O Founder mandatou explicitamente essa escolha quando o problema pode ser eliminado ali |
| Upload: duas camadas (middleware + leitura limitada), não uma só | `Content-Length` sozinho não é autoritativo (ausente em chunked encoding, pode mentir); a leitura limitada sozinha perderia a rejeição mais cedo possível para uploads egregiamente grandes |
| Overhead de multipart tratado com folga fixa (8192 bytes), não medido com precisão | Medir precisamente exigiria pré-parsear o multipart, delegando de volta o problema original; uma folga fixa e generosa é suficiente para a rejeição-cedo ser correta, com a leitura limitada como autoridade final |

---

## 6. Testes

| Suite | Testes | Letras/cobertura |
|---|---|---|
| `tests/test_login_brute_force_guard.py` | 9 | B, C, D, E, F, H, I, K |
| `tests/test_login_brute_force_api.py` | 8 | A, D, E, F, G, H, I, J |
| `web/lib/startup-config.test.ts` (extensão) | 6 novos (29 no arquivo) | M, N, O, P, Q, R |
| `tests/test_document_upload_size_limit.py` | 8 | S, T, U, V, W, X, Y, Z |
| **Total novo** | **31** (25 Python + 6 TypeScript) | Todas as 26 letras mandatadas (A-Z) cobertas |

`L` (nenhuma mudança em RBAC/tenant isolation) coberta por regressão explícita (Seção 7), não por teste novo dedicado — não haveria o que testar de diferente do que já existe.

**Correção de contagem, elevada com transparência:** D-188 registrou `tests/test_login_brute_force_guard.py` como 8 testes; a contagem real, confirmada por `pytest --collect-only` nesta verificação final, é **9** (`TestThresholdAndLockout` tem 3 casos, não 2, como o texto de D-188 implicava ao somar "8+8=16"). D-188 não é editado retroativamente — este é o registro da correção. O total real de testes novos desta missão em Python é 25 (9+8 de F1, 8 de F4), confirmado exatamente pela diferença observada na suíte completa (Seção 6a: 957 − 932 = 25).

### 6a. Verificação final — suítes completas

| Suite | Resultado |
|---|---|
| Backend completo (`pytest tests/`) | **957 passed, 0 failed** (`0:11:45`) — baseline pré-missão 932 (D-186) + 25 testes Python novos (F1: 9+8, F4: 8) |
| Frontend completo (`npx vitest run`) | **577 passed, 0 failed**, 78 arquivos de teste — inclui os 6 novos de F2 |
| `ruff check` (repositório) | Limpo nos arquivos alterados; achados remanescentes (`B008`/`UP035`/`PLW1510`) confirmados pré-existentes via inspeção direta de cada um, não introduzidos por esta missão |
| `tsc --noEmit` | Limpo |
| `eslint .` | Limpo |
| E2E (Playwright) | **Avaliado, não executado** — a suíte E2E existente (`web/e2e/*.spec.ts`) roda contra um backend mockado (`web/e2e/mock-backend.mjs`), portanto não exercitaria F1 (backend real) nem F4 (backend real); F2 é uma checagem de boot do servidor Next.js (`web/instrumentation.ts`), não algo que um teste de browser possa exercitar. Nenhuma mudança desta missão é observável pela suíte E2E — execução determinada não aplicável, não pulada por conveniência |
| Flakes encontrados | Nenhum |

Nenhum teste relaxado, nenhum `skip`/`fixme`/retry usado para obter verde — todas as falhas encontradas durante a implementação (a comparação incorreta de `Content-Length`, Seção 4) foram corrigidas na origem, nunca contornadas no teste.

---

## 7. Regressão de segurança

Revalidados explicitamente os controles que o Technical Design (D-187) classificou como adequados — nenhum alterado "para melhorar", apenas revalidado:

| Controle | Suite(s) | Resultado |
|---|---|---|
| Authentication | `tests/test_auth_api.py` | verde |
| Session | `web/lib/session.test.ts`, `web/proxy.test.ts` | verde |
| Logout | `tests/test_auth_api.py` (`test_logout_acknowledges`) | verde |
| RBAC | `tests/test_authorization.py` | verde |
| Tenant isolation | `tests/test_enterprise_repository.py` | verde |
| API keys | `tests/test_api_security.py` | verde |
| Cross-tenant lookup | `tests/test_identity_context.py`, `tests/test_identity_context_api_key_auth.py`, `tests/test_documents_api.py` | verde |
| Document authorization | `tests/test_documents_api.py`, `tests/test_document_upload_size_limit.py` | verde |
| Configuration Contract | `tests/test_startup_config.py`, `web/lib/startup-config.test.ts` | verde |
| Database non-exposure | `docker-compose.yml`/`docker-compose.override.yml` — confirmado via `git diff` sem alteração desde o checkpoint W7-3 (D-186) | preservado |
| Error disclosure | `tests/test_auth_api.py` (mensagens uniformes), `tests/test_readiness_endpoint.py` | verde |

**Execução consolidada desta bateria:** `pytest tests/test_auth_api.py tests/test_login_brute_force_guard.py tests/test_login_brute_force_api.py tests/test_authorization.py tests/test_enterprise_repository.py tests/test_api_security.py tests/test_identity_context.py tests/test_identity_context_api_key_auth.py tests/test_documents_api.py tests/test_document_upload_size_limit.py tests/test_startup_config.py tests/test_readiness_endpoint.py tests/test_cors.py tests/test_release_identity.py` — **108 passed, 0 failed**.

Nenhuma regressão real encontrada em nenhum controle já classificado adequado.

---

## 8. Findings restantes

| Finding | Severidade | Status |
|---|---|---|
| F1 | HIGH | **CLOSED** |
| F2 | HIGH | **CLOSED** |
| F4 | HIGH | **CLOSED** |
| F3 — nenhum header de segurança HTTP | MEDIUM | `OPEN` — não autorizado nesta missão |
| F5 — rate limiter compartilhado por organização | MEDIUM | `OPEN` — não autorizado nesta missão |
| F6 — nenhum scanning de dependências na CI | LOW | `OPEN` — não autorizado nesta missão |
| F7 — falhas de login em texto, não em `audit_logs` | LOW | `OPEN` — não autorizado nesta missão |
| F8 — `/ready` expõe nomes de variáveis ausentes | LOW | `ACCEPTED` (D-187) |
| F9 — logout best-effort | LOW | `ACCEPTED` (D-187) |
| F10 — nenhum secrets manager | LOW | `ACCEPTED` (D-187) |

**Zero findings `CRITICAL`/`HIGH` novos encontrados durante a implementação.**

---

## 9. Preservação arquitetural

Confirmado mecanicamente — nenhuma alteração a `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, `ExecutiveOrchestrator`, os Enterprise Advisors, Executive Intelligence, Workflow Runtime, Event Pipeline, Enterprise Domain, Knowledge Platform, o Backup Contract do W7-3, a Restore Validation do W7-3, ou o Deployment Contract do W7-5. Especificamente provado:

- **RBAC intacto:** `tests/test_authorization.py` verde, nenhuma alteração a `src/api/authorization.py`/`src/services/authorization/checker.py`.
- **Tenant isolation intacto:** `tests/test_enterprise_repository.py` verde, nenhuma alteração a `EnterpriseRepository`.
- **Arquitetura de sessão intacta:** `web/lib/session.test.ts` verde, `web/lib/session.ts` não tocado nesta missão.
- **Knowledge ingestion não redesenhado:** `DocumentIngestionService`/`KnowledgeRepository` não tocados — apenas uma rejeição antecipada em `src/api/routes/knowledge.py` antes do primeiro passo do pipeline.

Arquivos alterados no total (`git diff --stat` contra a base pré-D-188): `src/api/rate_limiter.py`, `src/api/routes/auth.py`, `web/lib/startup-config.ts`, `web/proxy.ts` (comentário), `src/api/security.py`, `src/main.py`, `src/api/routes/knowledge.py`, mais 4 arquivos de teste novos (`tests/test_login_brute_force_guard.py`, `tests/test_login_brute_force_api.py`, `tests/test_document_upload_size_limit.py`) e 1 arquivo de teste estendido (`web/lib/startup-config.test.ts`) — nenhum arquivo fora deste conjunto.

---

## 10. Riscos residuais

| Risco | Registro |
|---|---|
| `LoginBruteForceGuard` é single-instance, em memória | Documentado explicitamente no código; enfraquece proporcionalmente ao número de instâncias em um futuro deployment horizontal — não é a resposta de Enterprise Production |
| Overhead de multipart tratado com folga fixa, não exata | Aceitável — a leitura limitada é a autoridade real; a folga apenas evita falso positivo na rejeição antecipada |
| F3/F5/F6/F7 permanecem `OPEN`, F8/F9/F10 `ACCEPTED` | Nenhum bloqueia o Controlled Pilot (Seção 8); ficam para o restante do W7-4/Enterprise Production Readiness |
| Nenhuma chamada real a Anthropic/Voyage jamais validada (W7-1) | Inalterado por esta missão |
| DR Drill do W7-3 ainda não executado | Inalterado por esta missão |

Nenhum risco novo além destes foi identificado durante a implementação.

---

## 11. Controlled Pilot Security Gate

Comprovado mecanicamente, não assumido:

| Condição | Resultado |
|---|---|
| F1 = CLOSED | ✅ (D-188, 16 testes, regressão verde) |
| F2 = CLOSED | ✅ (D-189, 6 testes mandatados + 29 no arquivo, regressão verde) |
| F4 = CLOSED | ✅ (D-190, 8 testes, regressão verde) |
| Zero novo CRITICAL/HIGH blocker | ✅ (Seção 8) |
| Security regression verde | ✅ (Seção 7 — 108 passed, 0 failed) |

**`CONTROLLED PILOT SECURITY BASELINE = SATISFIED`.**

Isso significa exclusivamente que a **dimensão de segurança** deixou de bloquear um piloto controlado — **não** significa `W7-4 COMPLETED`, e **não** significa `ENTERPRISE PRODUCTION SECURITY READY`. Outros gates da Wave 7 (W7-1 Gates A-D, W7-3 DR Drill) permanecem inteiramente independentes e inalterados por esta missão.

---

## 12. GO/NO-GO para Controlled User Pilot (dimensão Security)

**GO — SECURITY DIMENSION FOR CONTROLLED USER PILOT.**

A dimensão de segurança do Controlled Pilot Security Baseline está satisfeita. Isso não é uma autorização para iniciar o piloto — outros gates da Wave 7 (Staging Host, credenciais reais, Data/DPA, DR Drill) permanecem pendentes e são decisões independentes do Founder.

---

## 13. GO/NO-GO para continuar W7-4

**NO-GO para encerrar o W7-4** — F3, F5, F6, F7 permanecem `OPEN`, não avaliados para implementação nesta missão. **GO para o Founder autorizar, em uma missão futura, a continuação do W7-4** rumo ao `ENTERPRISE PRODUCTION SECURITY BASELINE` (Etapas 4-6 já propostas no Technical Design D-187), mediante nova autorização explícita.

Nenhum trabalho posterior inicia automaticamente. Retornando obrigatoriamente para Executive Review.
