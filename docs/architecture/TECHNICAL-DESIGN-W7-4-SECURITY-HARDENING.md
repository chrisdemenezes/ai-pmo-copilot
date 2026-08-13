# Technical Design — W7-4: Security Hardening for Production Exposure

**Autorização:** "Founder Decision — Wave 7 — W7-3 Checkpoint Approval + Abertura Institucional do W7-4 — Security Hardening for Production Exposure". O checkpoint W7-3 Etapas 1–4 está APPROVED (Backup/Restore Contract implementados, TD-002 encerrado, DR Procedure documentado, RTO=8h/RPO=24h) — W7-3 permanece OPEN, Disaster Recovery não é `Delivered`, Etapa 5 (DR Drill) continua bloqueada pelo Gate A de W7-1. Nenhum trabalho adicional em W7-1/W7-3 nesta missão. Autorizada exclusivamente a abertura institucional do W7-4: Architecture Review + Security Readiness Assessment + Technical Design. **Nenhuma implementação, nenhuma correção de vulnerabilidade, nenhuma infraestrutura nova, nenhum teste destrutivo contra ambiente real, nenhum outro Epic iniciado.**

**Objetivo:** responder objetivamente "o que ainda impede a STRATECH V1, do ponto de vista de segurança, de ser disponibilizada para um piloto controlado com usuários reais?" — distinguindo explicitamente **CONTROLLED PILOT SECURITY BASELINE** de **ENTERPRISE PRODUCTION SECURITY BASELINE**. Princípio explícito: nenhum security theater, nenhum mecanismo enterprise sofisticado sem risco concreto demonstrado.

---

## 1. Executive Summary

A STRATECH V1 tem uma base de segurança **estruturalmente sólida e já comprovada** nos fundamentos que mais importam para multi-tenancy: RBAC real (`SqlPermissionChecker`, testado com 403s reais), isolamento de tenant real (`organization_id` nunca aceito do cliente, `CrossTenantViolationError` testado), Configuration Contract com fail-fast (W7-5), hashing de senha com Argon2, comparação de API key em tempo constante (`hmac.compare_digest`), sessão HMAC-assinada com `HttpOnly`/revogação server-side. Nenhuma vulnerabilidade estrutural de tenant isolation ou RBAC foi encontrada nesta revisão.

O que falta é **operacional, não arquitetural**: (1) proteção de força bruta no login continua ausente (débito já registrado em `PRI-009`, reconfirmado); (2) nenhum header de segurança HTTP é enviado pelo frontend (CSP/HSTS/X-Frame-Options/X-Content-Type-Options/Referrer-Policy — nenhum configurado, achado novo); (3) upload de documento não tem limite de tamanho (achado novo, risco de exaustão de memória); (4) o kill switch `DISABLE_WORKSPACE_SESSION_GATE` não é coberto pelo Configuration Contract fail-fast (achado novo — se setado `true` em staging/produção, desativa toda a autenticação do workspace, sem nenhum alarme); (5) nenhum scanning de dependências (`pip audit`/`npm audit`/Dependabot) existe na CI; (6) falhas de login são logadas em texto, não em `audit_logs` — distinção funcional vs. observability ainda não fechada.

**Nenhum desses gaps exige redesenho arquitetural.** Todos são fecháveis com mudanças pequenas, localizadas, proporcionais ao estágio da V1 — exatamente o padrão de "menor hardening necessário" mandatado. **Nenhuma correção foi feita nesta missão** — apenas identificação, classificação e uma estratégia incremental proposta (Seção 20).

**GO/NO-GO atual para CONTROLLED USER PILOT (Seção 23):** condicional — nenhum finding `CRITICAL` bloqueia um piloto interno/controlado hoje, mas 2 findings `HIGH` (brute-force, session-gate kill switch sem fail-fast) devem ser fechados antes de expor a usuários reais externos, mesmo em piloto.

---

## 2. Scope

Dentro do escopo: toda a superfície de ataque real da STRATECH V1 (Seção 4) — autenticação, sessão, RBAC/tenant isolation, secrets/configuração, rede/HTTP, ingestão de documentos/Knowledge Platform, fronteiras de provider de IA, auditabilidade, supply chain, tratamento de erro/disclosure. Fora do escopo: implementação de qualquer correção; nova infraestrutura; W7-1 (Staging & Production AI Validation) e W7-3 (Resilience & DR), ambos inalterados; W7-2 (Measurement, explicitamente não antecipado na Seção 14 de Auditabilidade); qualquer outro Epic da Wave 7.

---

## 3. Current Security State

Revalidação mecânica contra o código real (não contra documentação antiga), mandatória por esta missão.

| Dimensão | Estado real confirmado | Evidência |
|---|---|---|
| Autenticação | `POST /api/auth/login` (backend), Argon2 (`Argon2PasswordHasher`), mensagem de erro genérica ("Invalid organization, email or password" — nunca revela qual campo errou) | `src/api/routes/auth.py`, `src/services/identity/auth_service.py` |
| Sessão | Cookie HMAC-assinado (`web/lib/session.ts`), `HttpOnly: true`, `Secure: NODE_ENV === "production"`, `SameSite: "lax"`, TTL 12h, comparação de assinatura com `crypto.timingSafeEqual` | `web/lib/session.ts` |
| Revogação de sessão | `sessions` table (`UserSession`), `revoked_at`; logout é best-effort (cookie sempre expira no cliente; revogação server-side pode falhar silenciosamente se o backend estiver inacessível) | `web/app/api/bff/session/route.ts` `DELETE`, `src/database/models.py` |
| API Keys (server-to-server) | `verify_api_key` usa `hmac.compare_digest` (tempo constante); falha 503 se `API_KEY` não configurada, 401 se inválida | `src/api/security.py` |
| RBAC | `require_permission("<resource>.<verb>")` aplicado rota a rota; `knowledge.py` (4/4 rotas), `administration.py` (20 ocorrências), `intelligence.py` (19 ocorrências) — cobertura confirmada por grep, nenhuma rota encontrada sem `verify_api_key` no nível do router | `src/api/authorization.py`, todos os módulos de `src/api/routes/` |
| Tenant isolation | `organization_id` sempre resolvido de `RequestContext` (nunca do corpo da requisição); `CrossTenantViolationError` testado | `src/database/enterprise_repository.py`, `tests/test_enterprise_repository.py` (AR-18 já confirmou) |
| BFF (workspace gate) | `web/proxy.ts` — matcher cobre todas as rotas protegidas + `/api/bff/:path*`; kill switch `DISABLE_WORKSPACE_SESSION_GATE=true` desativa o gate inteiro **sem nenhuma checagem de fail-fast** | `web/proxy.ts`, `web/lib/startup-config.ts` (confirmado: não verifica esta variável) |
| CORS | `CORS_ALLOWED_ORIGINS` obrigatório em staging/produção (fail-closed); `allow_methods=["GET","POST"]`, `allow_headers=["Content-Type","X-API-Key"]` | `src/main.py`, `src/api/startup_config.py` |
| Headers HTTP de segurança | **Nenhum configurado** — `web/next.config.ts` só define `output: "standalone"`; nenhum CSP/HSTS/X-Frame-Options/X-Content-Type-Options/Referrer-Policy em nenhuma camada | `web/next.config.ts`, `web/proxy.ts` (nenhum header adicionado) |
| Rate limiting | Único limitador global (`RateLimiter`, em memória, por processo), chave = `X-API-Key`, default 60 req/60s, aplicado a toda rota via `dependencies=[Depends(enforce_rate_limit)]` no nível do router | `src/api/rate_limiter.py` |
| Brute-force/login | **Nenhuma proteção específica** além do rate limiter genérico acima — sem lockout, sem CAPTCHA, sem contagem de tentativas por usuário/IP | `src/api/routes/auth.py` (nenhum mecanismo adicional), débito já registrado em `PRI-009` §1 |
| Secrets/Configuration | Configuration Contract (backend `src/api/startup_config.py`, frontend `web/lib/startup-config.ts`) — fail-fast em staging/produção para `DATABASE_URL`/`API_KEY`/`LLM_PROVIDER`+`ANTHROPIC_API_KEY`/`EMBEDDING_PROVIDER`+`VOYAGE_API_KEY`/`CORS_ALLOWED_ORIGINS` (backend) e `SESSION_SECRET`/`WORKSPACE_PASSWORD`/`BACKEND_URL`/`API_KEY` (frontend) — **não cobre `DISABLE_WORKSPACE_SESSION_GATE`** | Ambos os arquivos, revalidados linha a linha nesta missão |
| Upload de documento | `POST /documents` (`knowledge.py`) — exige UTF-8 decodificável (rejeita binário estruturalmente), rejeita vazio — **nenhum limite de tamanho**, `raw_bytes = file.file.read()` sem bound | `src/api/routes/knowledge.py` |
| Auditabilidade | `audit_logs` cobre mutações de domínio (Enterprise Administration); falhas de login são logadas via `logger.info` (texto), **não** em `audit_logs` — distinção funcional vs. observability ainda não fechada | `src/database/models.py` (`AuditLog`), `src/services/identity/auth_service.py` linhas 72-108 |
| Dependency/Supply chain | `requirements.txt` (14 linhas, sem hash-pinning), `web/package.json` — **nenhum `pip audit`/`npm audit`/Dependabot/Snyk configurado** em `.github/workflows/ci.yml` nem em nenhum outro lugar do repositório | `.github/workflows/ci.yml` (revalidado, nenhuma etapa de scanning), busca por `dependabot*`/`*.snyk` (nenhum resultado) |
| Error handling | Nenhum handler catch-all genérico; handlers específicos para `ProviderConfigError`/`ProviderUnavailableError` retornam detalhe sanitizado; nenhum `debug=True`/stack trace exposto | `src/main.py` |
| `/health`/`/ready` | **Não autenticados** (por design — liveness/readiness não podem depender de credencial) — `/ready` expõe a lista `problems` (nomes de variáveis ausentes, ex. `"ANTHROPIC_API_KEY is not set"`) a qualquer chamador anônimo | `src/main.py` |
| PostgreSQL | Não exposto externamente em staging/produção desde D-179 (W7-1) — preservado, revalidado, nenhuma mudança nesta missão | `docker-compose.yml` |
| Providers de IA | `ProductionLLMProvider`/`VoyageEmbeddingProvider` falham fechado sem credencial; credenciais somente via variável de ambiente, nunca no código | `src/llm/providers/production_provider.py`, `src/services/knowledge_platform/embedding_provider.py` |

Nenhuma documentação antiga foi assumida como representando o comportamento atual — todos os itens acima foram confirmados por leitura direta do código nesta missão.

---

## 4. Threat Surface

| # | Fronteira | Trust boundary | Authentication | Authorization | Validation | Secrets envolvidos | Contexto de tenant | Auditabilidade | Proteções conhecidas | Gaps conhecidos |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Browser → Frontend | Internet → rede do Compose | Cookie de sessão (verificado em `proxy.ts`) | N/A (roteamento de página) | N/A | `SESSION_SECRET` (server-side) | Resolvido do cookie | N/A | `HttpOnly`/`SameSite=lax`/assinatura HMAC | Nenhum header de segurança HTTP |
| 2 | Browser → BFF (`/api/bff/*`) | Mesma origem (Next.js API routes) | Cookie de sessão (`proxy.ts` matcher) | Delegada ao backend | Corpo JSON validado por handler | `SESSION_SECRET`, `API_KEY` (repassada ao backend) | Do cookie, nunca do corpo | Nenhuma auditoria própria do BFF | Gate de sessão, timeout de 8s nas chamadas ao backend | Login sem rate limit próprio; `DISABLE_WORKSPACE_SESSION_GATE` sem fail-fast |
| 3 | BFF → Backend API | Rede interna do Compose (server-to-server) | `X-API-Key` (`verify_api_key`, `hmac.compare_digest`) | `require_permission` por rota | Pydantic por rota | `API_KEY` compartilhada | `organization_id` do `RequestContext`, nunca do BFF | Rate limiter (chave = API key) | Nenhuma credencial de usuário cruza esta fronteira, só a sessão já resolvida | Rate limiter compartilhado por TODOS os usuários de uma org (mesma API key) |
| 4 | Authentication/session boundary | `POST /api/auth/login` (backend) | Email+senha+organização (Argon2) | N/A | Pydantic (`min_length`/`max_length`) | Hash Argon2 no banco | Resolvido por `organization` (slug) + `email`, nunca busca global | Login falho logado (`logger.info`, não `audit_logs`) | Erro genérico, sem enumeração de usuário | Sem lockout/backoff por tentativa |
| 5 | Backend → PostgreSQL | Rede interna do Compose | Credencial de conexão (`DATABASE_URL`) | RBAC da aplicação, nunca do banco | ORM/SQLAlchemy parametrizado | `POSTGRES_PASSWORD` | `organization_id` em toda tabela relevante | `audit_logs` para mutações de domínio | Porta não exposta externamente (D-179); FK `RESTRICT`-equivalente (D-184) | Nenhum novo |
| 6 | Backend → Anthropic | Internet (HTTPS, fora do controle da STRATECH) | `ANTHROPIC_API_KEY` | N/A (fronteira externa) | N/A | `ANTHROPIC_API_KEY` | Prompt/evidência já filtrados por tenant antes do envio | Nenhum log de conteúdo enviado confirmado | Fail-fast sem credencial; `ProviderUnavailableError` tratado | Nenhuma chamada real jamais validada (W7-1, Gate C `PENDING`) |
| 7 | Backend → Voyage | Internet (HTTPS, fora do controle da STRATECH) | `VOYAGE_API_KEY` | N/A | N/A | `VOYAGE_API_KEY` | Texto do chunk já filtrado por tenant antes do envio | Nenhum log de conteúdo enviado confirmado | Fail-fast sem credencial; `EmbeddingProviderUnavailableError` tratado | Nenhuma chamada real jamais validada (W7-1, Gate B `PENDING`); Data/DPA Gate D `PENDING` |
| 8 | Document upload/ingestion | `POST /documents` | Sessão → BFF → `X-API-Key` | `require_permission("knowledge.write")` | UTF-8 obrigatório, não-vazio | N/A | `organization_id` do `RequestContext` | Evento `document.indexed` publicado (Event Pipeline) | Rejeita binário estruturalmente (decode UTF-8) | **Sem limite de tamanho** |
| 9 | Knowledge/RAG | `KnowledgeRepository.search()` | Herdada da rota que chama | `knowledge.read`/via Advisor | `organization_id` filtra a busca vetorial | N/A | Filtro direto por `organization_id`, sem join | Indireta (via `document.indexed`) | Retrieval já provado org-scoped (AR-18) | Conteúdo de documento entra no prompt do LLM como contexto — risco de prompt injection, ver Seção 14 |
| 10 | Administrative functions | `administration.py` (Organizations/Users/Roles/Audit Log) | Sessão → BFF → `X-API-Key` | `require_permission` por rota (20 ocorrências) | Pydantic | N/A | `organization_id` do `RequestContext` | `audit_logs` cobre mutações | Proteção de "last active admin" (`LastActiveAdminError`) | Nenhum novo |
| 11 | API keys | `ApiKey` (criação/revogação) | Sessão → BFF → `X-API-Key` | `require_permission` | Hash Argon2, `key_prefix` exibível | Segredo nunca reexibido pós-criação | `organization_id` | Criação/revogação são mutações auditadas | Mesmo padrão de `Invitation` (prefix seguro + hash) | Nenhum novo |
| 12 | Health/readiness endpoints | `GET /health`, `GET /ready` | **Nenhuma** (por design) | N/A | N/A | N/A | N/A | N/A | Liveness/readiness não podem depender de credencial | `/ready` expõe nomes de variáveis de config ausentes a qualquer chamador anônimo |
| 13 | Container/network boundary | Docker Compose network | N/A | N/A | N/A | `POSTGRES_PASSWORD` (D-179) | N/A | N/A | Postgres não exposto (D-179); portas 8000/3000 expostas por design | TLS/HTTPS depende do provedor de staging (Gate A de W7-1, `PENDING`) — fora do controle deste documento |

---

## 5. Existing Controls

Controles já comprovados por teste real, preservados sem alteração:

- RBAC (`SqlPermissionChecker`) — 403 real testado.
- Tenant isolation (`CrossTenantViolationError`) — testado.
- Configuration Contract (backend + frontend) — fail-fast testado (W7-5, D-179).
- Delete policy `RESTRICT`-equivalente — testado (D-184).
- API key / password comparison em tempo constante (`hmac.compare_digest`, `crypto.timingSafeEqual`).
- Sessão HMAC-assinada, `HttpOnly`, revogável server-side.
- PostgreSQL não exposto em staging/produção (D-179).
- Mensagens de erro de autenticação genéricas (sem enumeração de usuário/organização).
- Rejeição estrutural de upload binário (exige UTF-8 decodificável).

## 6. Findings

Cada finding classificado por `SEVERITY` (CRITICAL/HIGH/MEDIUM/LOW), `READINESS IMPACT` (BLOCKS CONTROLLED PILOT/BLOCKS ENTERPRISE PRODUCTION/NON-BLOCKING) e `STATUS` (OPEN/CONTROLLED/ACCEPTED/N/A), per mandato do Founder. Nenhum CVSS artificial usado — nenhuma necessidade demonstrada de formalismo adicional.

| # | Finding | Categoria (Seção 3 do mandato) | SEVERITY | READINESS IMPACT | STATUS |
|---|---|---|---|---|---|
| F1 | Ausência de proteção de força bruta/lockout no login (`src/api/routes/auth.py` — apenas o rate limiter genérico, compartilhado por toda a organização, se aplica) | A — obrigatório antes do piloto | HIGH | BLOCKS CONTROLLED PILOT | OPEN |
| F2 | `DISABLE_WORKSPACE_SESSION_GATE` (`web/proxy.ts`) sem checagem de fail-fast em `web/lib/startup-config.ts` — se `true` em staging/produção, desativa toda a autenticação do workspace sem alarme | A — obrigatório antes do piloto | HIGH | BLOCKS CONTROLLED PILOT | OPEN |
| F3 | Nenhum header de segurança HTTP (CSP/HSTS/X-Frame-Options/X-Content-Type-Options/Referrer-Policy) — `web/next.config.ts` só define `output: "standalone"` | B — obrigatório antes de produção enterprise, recomendável já para piloto | MEDIUM | BLOCKS ENTERPRISE PRODUCTION | OPEN |
| F4 | Upload de documento sem limite de tamanho (`src/api/routes/knowledge.py`, `raw_bytes = file.file.read()` sem bound) | A — obrigatório antes do piloto | HIGH | BLOCKS CONTROLLED PILOT | OPEN |
| F5 | Rate limiter compartilhado por todos os usuários de uma organização (chave = `X-API-Key`, a mesma para toda a org — `src/api/rate_limiter.py`) | C — melhoria recomendável | MEDIUM | BLOCKS ENTERPRISE PRODUCTION | OPEN |
| F6 | Nenhum scanning de dependências na CI (`pip audit`/`npm audit`/Dependabot/Snyk ausentes de `.github/workflows/ci.yml`) | C — melhoria recomendável (D para bloqueio de piloto) | LOW | NON-BLOCKING | OPEN |
| F7 | Falhas de login logadas em texto (`logger.info`, `src/services/identity/auth_service.py`), não em `audit_logs` — eventos de segurança sem trilha estruturada | C — melhoria recomendável | LOW | NON-BLOCKING | OPEN |
| F8 | `/ready` expõe nomes de variáveis de configuração ausentes sem autenticação (`src/main.py`) — nunca valores/segredos | D — technical debt não bloqueante | LOW | NON-BLOCKING | ACCEPTED |
| F9 | Logout best-effort — revogação server-side pode falhar silenciosamente se o backend estiver inacessível (`web/app/api/bff/session/route.ts` `DELETE`) — cookie sempre expira no cliente | D — technical debt não bloqueante | LOW | NON-BLOCKING | ACCEPTED |
| F10 | Nenhuma criptografia/rotação de secrets além de variável de ambiente | E — risco já adequadamente controlado para o estágio da V1 (ver Seção 12) | LOW | NON-BLOCKING | ACCEPTED |

---

## 7. Controlled Pilot Security Baseline

| Item | Status | Bloqueia? |
|---|---|---|
| Autenticação obrigatória | READY | — |
| Isolamento organizacional | READY | — |
| RBAC | READY | — |
| Sessão segura (cookie) | READY | — |
| Cookies (`HttpOnly`/`SameSite`) | READY | — |
| HTTPS requirement | PARTIALLY READY — depende do provedor de staging (Gate A W7-1), a aplicação não força HTTPS por si só | BLOCKS ENTERPRISE PRODUCTION (não bloqueia um piloto interno atrás de um proxy HTTPS já operado por infraestrutura existente, se houver) |
| Brute-force/login protection | NOT READY (F1) | **BLOCKS PILOT** |
| Rate limiting | PARTIALLY READY (existe, mas compartilhado — F5) | NON-BLOCKING para piloto pequeno |
| Logout/session invalidation | PARTIALLY READY (F9, best-effort) | NON-BLOCKING |
| Secrets | READY (Configuration Contract) com uma lacuna (F2) | **BLOCKS PILOT** (F2 especificamente) |
| CORS | READY | — |
| Frontend/backend exposure | READY | — |
| Database non-exposure | READY (D-179) | — |
| Auditability | PARTIALLY READY (F7) | NON-BLOCKING para piloto pequeno |
| Document upload | PARTIALLY READY (F4) | **BLOCKS PILOT** |
| File type/size validation | PARTIALLY READY (tipo OK, tamanho não — F4) | **BLOCKS PILOT** |
| Error disclosure | READY | — |
| Admin endpoints | READY | — |
| API keys | READY | — |
| Logging | READY (funcional), PARTIALLY READY (auditoria de segurança — F7) | NON-BLOCKING |

## 8. Enterprise Production Security Baseline

Adiciona ao baseline de piloto: headers de segurança HTTP completos (F3); scanning de dependências contínuo (F6); rotação/gestão formal de secrets além de variável de ambiente (avaliado e **não necessário agora**, Seção 12); rate limiting por usuário/sessão, não só por API key compartilhada (F5); auditoria de segurança completa incluindo eventos de autenticação (F7); TLS/HSTS forçado na borda; observability operacional correlacionada (fora do escopo — pertence a W7-2, per mandato explícito de não antecipar).

## 9. Authentication

Ver Seção 3/4. Argon2 (`Argon2PasswordHasher`), resolução por `organization` (slug) + `email` (nunca busca global de email entre organizações — `EO-015`), mensagens de erro genéricas, senha rehashed automaticamente em login se o parâmetro Argon2 mudar (`"Rehashed password on login"`, achado positivo, boa prática já presente). Nenhuma política de complexidade de senha encontrada além de `min_length=1` no schema de request — **nota, não finding formal**: a política de complexidade, se existir, vive na criação de usuário (fora do escopo desta rota), não revisada em profundidade aqui por não ser a fronteira de autenticação em si.

## 10. Session Security

| Propriedade | Valor real | Adequado para piloto? |
|---|---|---|
| `HttpOnly` | `true` | Sim |
| `Secure` | `process.env.NODE_ENV === "production"` | Sim, desde que o deployment real rode com `NODE_ENV=production` (padrão de build do Next.js) |
| `SameSite` | `lax` | Sim — mitiga CSRF cross-site para a maioria dos casos, sem quebrar navegação normal |
| Expiração | 12h, embutida e assinada no próprio token | Sim |
| Refresh/renovação | Não existe — expira e exige novo login | Aceitável para piloto (fricção baixa, sessão de 12h) |
| Logout | `DELETE /api/bff/session` — expira cookie sempre; revoga server-side best-effort (F9) | Aceitável para piloto, registrado como debt não bloqueante |
| Session fixation | Não aplicável — `session_id` é mintado pelo backend no login (`AuthService.create_session`), nunca aceito de fonte externa | Sim |
| Armazenamento | Cookie assinado, sem estado adicional client-side | Sim |
| Comportamento cross-tenant | `organizationId` embutido no token assinado, nunca no controle do cliente | Sim |

**Conclusão: o modelo de sessão atual é suficiente para um piloto real**, sem necessidade de mudança.

## 11. RBAC/Tenant Isolation

Não redesenhado (já `Ready` desde o Kickoff da Wave 7). Revalidação restrita a bypass:

- Nenhuma rota encontrada sem `Depends(verify_api_key)` no nível do router (grep confirma presença em todo `src/api/routes/*.py`).
- `knowledge.py`: 4 rotas, 4 `require_permission` — cobertura 1:1 confirmada.
- `administration.py`/`intelligence.py`: 20/19 ocorrências de `require_permission`, consistentes com o número de rotas reais de cada módulo (não contadas rota a rota nesta missão por proporcionalidade — proposto como item da Security Test Matrix, Seção 19, item H).
- Nenhum `organization_id` aceito do corpo da requisição em nenhuma rota inspecionada — sempre resolvido de `RequestContext`.
- BFF nunca repassa `organization_id` do cliente ao backend — resolvido do cookie assinado.

**Nenhum bypass de RBAC/tenant isolation encontrado.** Nenhum finding provado por código/teste nesta dimensão.

## 12. Secrets/Configuration

Delta sobre o Configuration Contract já implementado (W7-5, preservado):

| Item | Estado |
|---|---|
| Secrets em arquivos versionados | Nenhum encontrado (`.env.example` só tem placeholders vazios) |
| Secrets em build do frontend | Nenhum — `NEXT_PUBLIC_*` não usado para nenhum secret (confirmado: `SESSION_SECRET`/`API_KEY`/`BACKEND_URL` são server-side only, nunca prefixados `NEXT_PUBLIC_`) |
| Vazamento em logs | Nenhuma chamada de log encontrada imprimindo `API_KEY`/`ANTHROPIC_API_KEY`/`VOYAGE_API_KEY`/`SESSION_SECRET`/`POSTGRES_PASSWORD` diretamente |
| Docker Compose | Já revisado exaustivamente em D-179 — interpolação `${VAR:-default}`, nenhum literal exceto o default de dev | 
| Repository history | Fora do escopo prático desta missão (nenhum mecanismo local razoável de scanning de histórico git existe no repositório) — não avaliado |
| Provider credentials | `ANTHROPIC_API_KEY`/`VOYAGE_API_KEY` — só variável de ambiente, fail-fast sem elas |
| Separação staging/produção | `ENVIRONMENT` já distingue; nenhum secret compartilhado por padrão além do que o operador decidir |

**Secrets manager: não necessário para o piloto.** Variáveis de ambiente + Configuration Contract fail-fast já cobrem o requisito mínimo verificável — nenhuma evidência concreta de necessidade de rotação automática, versionamento de segredo, ou distribuição centralizada no estágio atual (equipe pequena, poucos ambientes). **Modelo-alvo para enterprise:** um secrets manager real (Vault/AWS Secrets Manager/equivalente) passa a fazer sentido quando houver múltiplos operadores/ambientes/clientes reais — não antes, per mandato de não overengineering.

## 13. HTTP/Network

| Item | Estado | Finding |
|---|---|---|
| HTTPS/TLS | Não forçado pela aplicação — depende do reverse proxy/provedor de staging | Fora do controle deste código; depende do Gate A de W7-1 |
| Security headers (CSP/HSTS/X-Frame-Options/X-Content-Type-Options/Referrer-Policy) | **Nenhum configurado** | F3 |
| CORS | `CORS_ALLOWED_ORIGINS` fail-closed em staging/produção | Adequado |
| Porta do backend/frontend | Expostas por design (8000/3000), atrás do proxy futuro | Esperado |
| Porta do banco | Não exposta em staging/produção (D-179) | Preservado, sem mudança |
| `/health`/`/ready` exposição | Não autenticados por design; `/ready` revela nomes de variável ausente (F8) | Baixo impacto — nomes de variável, nunca valores |

## 14. Document/Knowledge Security

Fluxo real confirmado por leitura direta: `upload (multipart) → decode UTF-8 → DocumentIngestionService.upload() → KnowledgeRepository.ingest()/index() → chunking determinístico → embedding real → persistência → retrieval por organization_id`.

| Item | Estado |
|---|---|
| Tipos permitidos | Implícito: qualquer arquivo decodificável como UTF-8 é aceito — sem allowlist de extensão, mas a decodificação UTF-8 já rejeita binário estruturalmente (imagens, PDFs, executáveis falham o `decode("utf-8")`) |
| Tamanho | **Sem limite** (F4) — `file.file.read()` sem bound; risco de exaustão de memória em um upload muito grande |
| Filename/path handling | `source_name`/`file.filename` usados apenas como string de exibição — nunca usados para construir caminho de arquivo (não há escrita em disco; conteúdo vai direto para `document_versions.content` no Postgres) — sem risco de path traversal |
| Parser risk | Nenhum parser binário real existe ainda (TD-012, deferred) — texto é tratado como string, sem `eval`/execução |
| Documentos malformados | Rejeitados cedo (decode/empty check); nenhum crash encontrado nos testes existentes de ingestão |
| Tenant isolation | `organization_id` do `RequestContext`, nunca do payload |
| Autorização | `knowledge.write` exigido |
| Prompt injection via documento | **Risco inerente e conhecido de qualquer arquitetura RAG** — o texto do documento entra como contexto no prompt do LLM (via `Evidence`/`AttributedExplanation`). Nenhuma amplificação além do padrão RAG: o LLM nunca executa ações automáticas nem chama ferramentas com base no conteúdo do documento — a saída é sempre texto narrativo + citações, consumido por um humano. Não é tratado como finding formal (nenhuma evidência de risco concreto além do já inerente à categoria), mas registrado explicitamente como risco aceito da categoria RAG, não uma AI Safety architecture nova |
| Propagação de conteúdo não confiável | Confinada ao pipeline de Knowledge Platform — nunca alcança execução de código, nunca alcança outro tenant |
| Logging de dado sensível | Nenhum log encontrado imprimindo o conteúdo integral de um documento — apenas metadados (`document_id`, `version_id`, `chunk_count`) |

**Nenhuma nova AI Safety architecture proposta** — per mandato explícito de não criar uma sem necessidade demonstrada.

## 15. AI Provider Boundaries

| Provider | Dado enviado | Tenant context | Credencial | Timeout | Falha do provider | Retenção de dados |
|---|---|---|---|---|---|---|
| Anthropic | Prompt + evidência já filtrada por `organization_id` (nunca cross-tenant) | Implícito no conteúdo do prompt, resolvido antes do envio | `ANTHROPIC_API_KEY`, só env var | Não configurado explicitamente no client (biblioteca `anthropic` usa seu próprio default) | `ProviderUnavailableError` tratado, 502 ao chamador | Assunção de política padrão do fornecedor — não verificada nesta missão (fora do escopo; Data/DPA Gate C de W7-1 é o mecanismo formal para isso) |
| Voyage | Texto de chunk (para embedding) | Idem | `VOYAGE_API_KEY`, só env var | `timeout=30.0` explícito (`VoyageEmbeddingProvider`) | `EmbeddingProviderUnavailableError` tratado | Data/DPA Gate D de W7-1, `PENDING` — nenhum dado corporativo real deve ser enviado até resolvido |

Nenhuma chamada real foi feita nesta missão. Nenhuma decisão de provider foi alterada. O Data/DPA Gate já existente (W7-1) permanece a autoridade sobre quando dado corporativo real pode fluir para qualquer um dos dois — este documento não o substitui nem o antecipa.

## 16. Auditability

`audit_logs` (Enterprise Administration) já cobre mutações de domínio — confirmado `Ready` desde o Kickoff, revalidado sem regressão.

| Evento de segurança | Auditado em `audit_logs`? | Onde está hoje |
|---|---|---|
| Login (sucesso) | Não | `logger.info` (`auth_service.py`) |
| Login failure | Não | `logger.info` (`auth_service.py`, com motivo específico) |
| Logout | Não | `logger.info` (`auth_service.py`) |
| Permission denial (403) | Não | Resposta HTTP + logs de acesso padrão do servidor, não estruturado |
| Administrative action (ex. criar usuário, mudar papel) | **Sim** | `audit_logs` |
| API key operations (criar/revogar) | **Sim** | `audit_logs` |
| Document ingestion | Parcial — evento `document.indexed` publicado (Event Pipeline, `events` table), não `audit_logs` | `events` |
| Destructive actions | Nenhuma existe hoje (D-184: nenhum hard delete de entidade CRITICAL em produção) | N/A |

**Distinção explícita mantida (mandato do Founder):** `audit_logs` é o log **funcional** de mutação de domínio, já maduro. Eventos de **segurança** (login/logout/permission denial) hoje vivem apenas em observability operacional (`logger.info`, texto não estruturado, não consultável como trilha formal) — esta é a lacuna real (F7), não uma falha do que já existe. **Não antecipa W7-2** (Measurement/Observability) — este documento apenas identifica o gap, não propõe instrumentação de observability nova.

## 17. Dependency/Supply Chain

| Item | Estado |
|---|---|
| Python dependencies | `requirements.txt`, 14 linhas, sem hash-pinning (`==` sem `--hash`) |
| npm dependencies | `web/package.json` + `package-lock.json` (lockfile presente, confirma reprodutibilidade de instalação) |
| CI | `.github/workflows/ci.yml` — `pip install -r requirements.txt` + `npm ci`, nenhuma etapa de scanning de vulnerabilidade |
| Dependency scanning | **Nenhum** (`pip audit`/`npm audit`/`safety`/Dependabot/Snyk) — confirmado, nenhum arquivo de configuração encontrado |
| Image/build discipline | `Dockerfile`/`web/Dockerfile` usam imagens base oficiais (`python:3.12-slim` — confirmado em sessão anterior — e Node LTS via `web/Dockerfile`), `RELEASE_SHA` rastreável |

**Mínimo necessário para piloto:** nenhum — o risco de uma dependência vulnerável não exercitada é baixo no estágio atual (poucos usuários, superfície controlada), classificado `NON-BLOCKING`. **Mínimo necessário para enterprise:** `pip audit`/`npm audit` como etapa de CI (bloqueante ou não, a decidir) — mudança pequena, sem necessidade de nova plataforma. Nenhuma ferramenta adicionada por esta missão.

## 18. Error/Information Disclosure

| Fonte | Comportamento real | Adequado? |
|---|---|---|
| Stack traces | Nenhum handler `debug=True`; sem catch-all genérico — FastAPI/Starlette retornam `500` genérico por padrão para exceção não tratada | Sim |
| Erros de banco | Não expostos diretamente ao cliente em nenhuma rota inspecionada | Sim |
| Erros de provider | `ProviderConfigError`/`ProviderUnavailableError` retornam `{"error": "...", "detail": str(exc)}` — `detail` é a mensagem da exceção já sanitizada no próprio provider (nunca inclui a chave) | Sim |
| Erros de autenticação | Genéricos, sem enumeração de organização/usuário | Sim |
| Lookup cross-tenant | `CrossTenantViolationError` já tratado como não-encontrado (nunca confirma existência em outra org) — comportamento já testado (AR-18, `EnterpriseRepository`) | Sim, padrão já em uso preservado |
| Semântica 401/403/404 | 401 = credencial ausente/inválida; 403 = autenticado mas sem permissão; 404 = recurso não encontrado (incluindo cross-tenant, nunca 403 para não confirmar existência) — padrão consistente | Sim |
| `/health`/`/ready` | `/ready` retorna nomes de variáveis de config ausentes (F8) — nunca valores/segredos | Baixo risco, mas nunca autenticado |
| Frontend errors | Mensagens genéricas em português já observadas (`web/app/api/bff/session/route.ts`) | Sim |

**Confirmado: um ID pertencente a outra organização nunca revela sua existência** — o padrão já estabelecido (`CrossTenantViolationError` → tratamento como não-encontrado) é consistente em toda a plataforma, revalidado nesta missão, não redesenhado.

## 19. Security Test Matrix

| Letra | Cenário | Já existe? | Onde |
|---|---|---|---|
| A | Brute-force/login | **Falta** | — |
| B | Session cookie security (`HttpOnly`/`Secure`/`SameSite`) | Falta um teste automatizado dedicado (comportamento existe, não testado explicitamente) | — |
| C | Logout/invalidation | Falta | — |
| D | RBAC bypass | Existe parcialmente (403 testado por `SqlPermissionChecker`) | `tests/test_authorization.py` |
| E | Cross-tenant project | Existe | `tests/test_enterprise_repository.py` |
| F | Cross-tenant portfolio | Existe (mesmo padrão de E) | `tests/test_enterprise_repository.py`/`tests/test_portfolio_api.py` |
| G | Cross-tenant document | Falta um teste explícito de tenant isolation no nível de `documents`/`chunks` (a busca já filtra por `organization_id` no código, mas sem teste negativo dedicado confirmado nesta revisão) | — |
| H | Administrative route access | Existe parcialmente | `tests/test_administration_api.py` |
| I | Malformed input | Existe parcialmente (upload UTF-8/vazio) | `src/api/routes/knowledge.py` + testes de ingestão |
| J | Oversized/invalid upload | **Falta** (não há limite a testar — F4) | — |
| K | CORS | Falta um teste automatizado dedicado | `tests/test_cors.py` (existe, cobertura a confirmar em implementação futura) |
| L | Security headers | **Falta** (nenhum header existe — F3) | — |
| M | Secret absence/fail-fast | Existe | `tests/test_startup_config.py` |
| N | Secret non-leakage | Existe parcialmente (D-182, backup metadata redigido) | `tests/test_backup.py` |
| O | Provider error sanitization | Existe parcialmente | testes de `ProductionLLMProvider`/`VoyageEmbeddingProvider` |
| P | Database non-exposure | Existe (validado via `docker compose config`, D-179) | Manual, não pytest |
| Q | Health/readiness exposure | Existe (comportamento coberto) | `tests/test_readiness_endpoint.py` |
| R | API key protection | Existe (`hmac.compare_digest`) | `tests/test_api_security.py` |
| S | Audit security events | **Falta** (F7 — não existe o que testar ainda) | — |
| T | Executive Intelligence tenant isolation | Existe parcialmente (via `RequestContext`/`organization_id`) | testes de `intelligence.py` |

**Classificação:** 9 letras já cobertas (D, E, F, H parcial, I parcial, M, N parcial, P, Q, R), 4 parciais precisando de teste dedicado (B, G, K, O), 6 genuinamente ausentes (A, C, J, L, S, T-parcial).

## 20. Incremental Implementation Strategy

Proposta, não autorizada nesta missão. Agrupamento por gaps relacionados, preferindo correções pequenas e localizadas — capaz de parar em `CONTROLLED PILOT SECURITY BASELINE` sem obrigatoriamente completar a maturidade enterprise.

| Etapa | Escopo | Fecha |
|---|---|---|
| 1 | Rate limiting de login dedicado (por usuário/organização + IP, não a chave de API compartilhada) + lockout temporário | F1 |
| 2 | Fail-fast para `DISABLE_WORKSPACE_SESSION_GATE=true` em staging/produção (`web/lib/startup-config.ts`) | F2 |
| 3 | Limite de tamanho de upload (`MAX_UPLOAD_SIZE_BYTES`, configurável, default razoável) | F4 |
| 4 | Headers de segurança HTTP mínimos (X-Content-Type-Options, X-Frame-Options, Referrer-Policy) — CSP/HSTS avaliados separadamente por exigirem mapeamento de origens externas (fontes/scripts) antes de aplicar sem quebrar a aplicação | F3 (parcial, suficiente para piloto) |
| 5 | Eventos de segurança em `audit_logs` (login/logout/permission denial) | F7 |
| 6 | `pip audit`/`npm audit` na CI (não-bloqueante inicialmente) | F6 |

**Etapas 1–3 fecham o `CONTROLLED PILOT SECURITY BASELINE`** (todos os itens `BLOCKS PILOT` da Seção 7). Etapas 4–6 avançam para o `ENTERPRISE PRODUCTION SECURITY BASELINE`, mas não bloqueiam um piloto controlado. Esta sequência não está aprovada — mediante nova Founder Decision.

**Preservação arquitetural confirmada para todas as 6 etapas propostas:** nenhuma delas toca `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, `ExecutiveOrchestrator`, os Enterprise Advisors, Executive Intelligence, Workflow Runtime, Event Pipeline, Enterprise Domain, Knowledge Platform, o Configuration Contract do W7-5, ou o Backup/Restore Contract do W7-3 — todas são localizadas em `src/api/rate_limiter.py`/`src/api/routes/auth.py` (Etapa 1), `web/lib/startup-config.ts` (Etapa 2), `src/api/routes/knowledge.py` (Etapa 3), `web/next.config.ts`/middleware de resposta (Etapa 4), `src/database/models.py`/`AuditLog` writes já existentes (Etapa 5, aditivo, sem alterar o schema de auditoria), `.github/workflows/ci.yml` (Etapa 6). **Nenhum finding desta missão exigiu mudança estrutural em nenhum desses componentes** — nenhuma elevação ao Founder por esse motivo foi necessária.

## 21. Risks

| Risco | Registro |
|---|---|
| Brute-force real contra login antes de F1 ser fechado | Real, mitigável apenas pela Etapa 1 futura — não mitigado nesta missão |
| `DISABLE_WORKSPACE_SESSION_GATE` setado por engano em staging/produção | Baixa probabilidade (requer ação deliberada), impacto total (bypass de toda autenticação do workspace) — mitigável pela Etapa 2 futura |
| Upload muito grande causando pressão de memória | Real até a Etapa 3 futura ser implementada |
| Ausência de headers de segurança expõe a clickjacking/MIME-sniffing | Presente até a Etapa 4 futura |
| Nenhuma chamada real a Anthropic/Voyage jamais validada (W7-1) | Já registrado, não resolvido por este documento |
| Prompt injection via documento ingerido | Risco inerente à categoria RAG, sem amplificação concreta identificada — aceito, não bloqueante |

## 22. Founder Decisions Required

1. Autorizar (ou não) a Estratégia Incremental da Seção 20, e em que ordem.
2. Confirmar se `CONTROLLED PILOT SECURITY BASELINE` (Etapas 1–3) é suficiente para o primeiro piloto, ou se exige também itens do `ENTERPRISE PRODUCTION SECURITY BASELINE`.
3. Decidir a política de complexidade de senha (não avaliada em profundidade nesta missão — fora da fronteira de autenticação revisada).
4. Confirmar se CSP/HSTS entram no escopo do piloto ou ficam para produção enterprise (Seção 20, Etapa 4 nota).
5. Confirmar se scanning de dependências (F6) deve ser bloqueante de CI desde já ou apenas informativo inicialmente.

## 23. GO/NO-GO

**GO para o Founder decidir a Estratégia Incremental (Seção 20/22)** — o assessment está completo, fundamentado no código real, sem necessidade de mais investigação técnica antes dessas decisões.

**GO/NO-GO atual para CONTROLLED USER PILOT: NO-GO condicional.** Nenhum finding `CRITICAL` existe. Mas 3 findings `HIGH`/`BLOCKS PILOT` (F1 brute-force, F2 kill switch sem fail-fast, F4 upload sem limite) devem ser fechados antes de expor a STRATECH a usuários reais externos — mesmo em piloto controlado. Um piloto **estritamente interno**, com usuários de confiança já conhecidos e sem exposição pública, poderia prosseguir com risco aceito explícito do Founder — mas isso é uma decisão de negócio, não uma classificação técnica automática.

**NO-GO para qualquer implementação nesta missão** — nenhuma correção foi feita. **NO-GO para W7-4 ser declarado implementado.** Nenhum outro Epic da Wave 7 foi iniciado. W7-1 e W7-3 permanecem inalterados. Retornando obrigatoriamente para Executive Review do Founder.
