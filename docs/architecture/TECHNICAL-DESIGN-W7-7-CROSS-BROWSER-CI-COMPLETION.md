# Technical Design — W7-7: Cross-Browser & CI Completion

**Autorização:** "Founder Decision — W7-4 Checkpoint Ratification + W7-7 Cross-Browser & CI Completion — Institutional Opening". O checkpoint W7-4 Controlled Pilot Security Baseline está `SATISFIED` (F1/F2/F4 `CLOSED`, ratificado D-192) — W7-4 permanece `OPEN` (F3/F5/F6/F7 fora de escopo desta missão). Autorizada exclusivamente a abertura institucional do W7-7: **Assessment + Architecture/Technical Design**, nenhuma implementação. **Nenhuma alteração de código de produto para resolver findings encontrados.**

**Objetivo:** determinar, com grounding mecânico no repositório real, o estado de prontidão da STRATECH V1 para execução consistente em browsers suportados e para validação automatizada em CI — respondendo objetivamente às 16 perguntas mandatadas (Seção 3), distinguindo em todo o documento **`TEST EXISTS`** de **`BEHAVIOR IS ACTUALLY EXERCISED`**.

---

## 1. Executive Summary

A suíte E2E da STRATECH V1 é **real e substancial** (14 arquivos, 2.266 linhas, 110 `test()`), mas roda **exclusivamente contra o engine Chromium**, nunca Firefox ou WebKit — os três "projects" já configurados (`mobile`/`md`/`lg`) são **perfis de viewport, não engines diferentes**: todos os três usam `devices["Desktop Chrome"]`, variando apenas `width`/`height`. Nenhum browser é declarado como suportado em nenhuma documentação do produto (nenhum `browserslist`, nenhuma menção em README/blueprint) — o suporte é inteiramente implícito, nunca comprovado por teste, em qualquer engine além do Chromium.

**O CI roda E2E realmente**, em todo `pull_request` e `push` para `main` (job `frontend`, `.github/workflows/ci.yml`), mas **apenas o project `lg`** (`npx playwright test --project=lg`) — `mobile` e `md`, apesar de existirem e serem exercitáveis localmente, **nunca rodam em CI**. Nenhum retry configurado (mascaramento de falha inexistente); 3 skips condicionais encontrados, todos legítimos e documentados (nenhuma falha real escondida); nenhum flake documentado no código.

**Cobertura de fluxo crítico é forte onde existe, mas 4 dos 18 fluxos mandatados têm apenas o link de navegação verificado, nunca o comportamento da página** (`Program Management`, `Project Delivery`, `Documents`, `Mission Control`) — `shell.spec.ts` confirma apenas que o `href` do item de menu está correto, nunca que a página carrega ou funciona. `Session` está parcialmente coberta: login e o gate de autenticação são exercitados extensivamente, mas **nenhum teste E2E exercita logout**.

**Menor delta para `CONTROLLED PILOT BROWSER BASELINE`:** nenhuma implementação de novo engine é necessária — Chromium/Chrome já é o alvo real de todo usuário de piloto controlado esperado (equipe interna/early adopters, sem requisito de Safari/Firefox demonstrado). O delta real está em **fechar os gaps de cobertura de fluxo** (Documents, Mission Control minimamente) e **rodar `mobile`/`md` também em CI**, não em adicionar engines novos.

**GO/NO-GO para implementação do W7-7:** GO para o Founder autorizar uma implementação futura pequena e incremental (Seção 11) — nenhuma nesta missão.

---

## 2. Scope & Authorization

Dentro do escopo: assessment mecânico completo da configuração Playwright, cobertura E2E real, pipeline de CI, responsividade, e as duas baselines (Controlled Pilot / Enterprise Production). Fora do escopo: qualquer implementação; qualquer correção de finding; W7-1, W7-3, a implementação de segurança do W7-4 (F1/F2/F4, já `CLOSED`), o Deployment Contract do W7-5 — todos inalterados; qualquer outro Epic.

---

## 3. Grounding Obrigatório — as 16 perguntas, respondidas mecanicamente

| # | Pergunta | Resposta (grounded no código real) |
|---|---|---|
| 1 | Quais browsers são atualmente testados? | Apenas **Chromium** — os 3 `projects` em `web/playwright.config.ts` (`mobile`, `md`, `lg`) usam todos `devices["Desktop Chrome"]` |
| 2 | Quais browsers são declarados ou implicitamente suportados? | **Nenhum declarado explicitamente** — nenhum `browserslist` em `web/package.json`, nenhuma menção a suporte de browser em `README.md`/`docs/product/blueprint/*.html`. Suporte é inteiramente implícito (convenção de framework Next.js 16/React), nunca comprovado por teste fora de Chromium |
| 3 | Playwright executa Chromium apenas ou múltiplos engines? | **Apenas Chromium** — confirmado, nenhum `devices["Desktop Firefox"]`/`devices["Desktop Safari"]`/`webkit` em nenhum project |
| 4 | Mobile/md/lg representam viewport ou engines diferentes? | **Apenas viewport** — mesmo engine (`Desktop Chrome`) nos 3 projects, variando somente `viewport: { width, height }` |
| 5 | Existe validação real em Chromium, Firefox e WebKit? | Chromium: sim, localmente (3 projects) e em CI (`lg` apenas). Firefox: **não**. WebKit: **não** |
| 6 | Quais fluxos críticos possuem cobertura E2E? | Ver matriz, Seção 6 |
| 7 | Quais fluxos críticos não possuem cobertura? | `Program Management`, `Project Delivery`, `Documents`, `Mission Control` — link de navegação verificado, comportamento de página nunca exercitado (Seção 6) |
| 8 | A suíte E2E roda atualmente no CI? | **Sim** — job `frontend`, `.github/workflows/ci.yml`, dispara em `pull_request` e `push` para `main` |
| 9 | Se roda, em quais condições? | Após `npm ci` → `tsc --noEmit` → `eslint .` → `npm test` (vitest) → `npm run build` passarem; instala **somente Chromium** (`npx playwright install --with-deps chromium`); roda **somente o project `lg`** (`npx playwright test --project=lg`) |
| 10 | O CI bloqueia merge/release quando E2E falha? | O job `frontend` falha (comportamento padrão do GitHub Actions quando qualquer step falha). **Se isso bloqueia o merge real depende de regras de proteção de branch configuradas no GitHub** — configuração externa ao repositório, **não verificável por inspeção de código**, não presumida por este documento (GAP de verificação, Seção 10) |
| 11 | Existe diferença entre suíte completa e smoke test? | **Sim** — `smoke.spec.ts` (52 linhas, 4 testes) é um subconjunto minimalista, parametrizável via `PLAYWRIGHT_BASE_URL`/`SMOKE_BACKEND_URL`/`SMOKE_LOGIN_*` (W7-5 Etapa 6), com skips condicionais, destinado a validar um ambiente real pós-deploy — distinto dos outros 13 arquivos (106 testes) que rodam contra o dev server + `mock-backend.mjs` local |
| 12 | Quais skips existem e por quê? | 3, todos legítimos: `shell.spec.ts:94` pula um check mobile-only fora do viewport mobile; `smoke.spec.ts:33`/`:41` pulam checks de backend real quando `SMOKE_BACKEND_URL`/credenciais de login não estão configurados — nenhuma falha real mascarada |
| 13 | Quais flakes conhecidos existem? | **Nenhum documentado no código** (nenhum comentário/TODO referenciando flakiness); `fullyParallel: false` + `workers: 1` (execução estritamente sequencial) reduz estruturalmente o risco de flakiness por concorrência |
| 14 | Existem retries ou mecanismos capazes de mascarar failures? | **Não** — `retries` não é declarado em `playwright.config.ts` (default do Playwright é 0 quando omitido); nenhum `retries`/`.describe.configure` em nenhum spec |
| 15 | Menor delta para Controlled Pilot Browser Baseline? | Ver Seção 8 |
| 16 | Delta adicional para Enterprise Production Browser Readiness? | Ver Seção 9 |

**Autenticação usada pelo E2E:** login real via a rota real do BFF (`POST /api/bff/session`) contra um **backend mockado** (`web/e2e/mock-backend.mjs`, HTTP standalone, nunca `src/`) — significa que `Argon2`/`AuthService`/`LoginBruteForceGuard` (F1, D-188) **nunca são exercitados pela suíte E2E**, apenas a emissão/verificação real do cookie de sessão pelo BFF (`web/lib/session.ts`).

**Mocks/stubs:** `mock-backend.mjs` espelha as formas de resposta já testadas do backend real (`src/api/routes/intelligence.py`), com cenários por endpoint (`workspaceScenario`) permitindo simular sucesso/erro/lentidão por painel independentemente — usado para provar isolamento de falha entre painéis (`workspace.spec.ts`), não para validar o backend real.

---

## 4. Matriz de Browsers

| Engine testado | Browser comercial equivalente | Validado hoje? | Ressalva |
|---|---|---|---|
| Chromium | Google Chrome | Sim (local: 3 projects; CI: `lg` apenas) | Chrome real usa o mesmo engine Blink/V8, mas com telemetria/extensões/políticas corporativas próprias — Chromium é uma aproximação real, não uma garantia de paridade 1:1 |
| Chromium | Microsoft Edge | Não testado diretamente | Edge é baseado em Chromium (Blink/V8) desde 2020 — mesma aproximação do Chrome acima, nunca comprovada por teste específico de Edge |
| WebKit | Safari | **Não testado, nenhum project existe** | Safari é o único browser principal que **não** compartilha engine com Chromium — nenhuma equivalência pode ser assumida; requer validação própria se necessária |
| Firefox (Gecko) | Firefox | **Não testado, nenhum project existe** | Engine e motor JS (SpiderMonkey) totalmente distintos de Chromium — nenhuma equivalência pode ser assumida |

**Não afirmado:** suporte a Safari só porque WebKit existe (WebKit não está configurado); suporte a Edge só porque Chromium existe (testado, mas nunca contra o binário real do Edge) — ambos deliberadamente não presumidos, per mandato do Founder.

---

## 5. Responsividade

`mobile` (375×812), `md` (900×800), `lg` (1280×900) — confirmado (Seção 3, pergunta 4) que representam **exclusivamente perfis de viewport**, nenhuma diferença adicional de runtime (mesmo engine, mesmo `launchOptions`).

| Cobertura real de responsividade | Evidência |
|---|---|
| Sidebar muda de forma por breakpoint | `shell.spec.ts`: "shows the sidebar shape appropriate to the current breakpoint" |
| Barra de navegação inferior no mobile não sobrepõe conteúdo | `shell.spec.ts`: "the bottom nav bar does not overlap the last scrollable content on mobile" |
| Grid do Dashboard empilha em coluna única em viewport estreito | `dashboard.spec.ts`: "dashboard grid stacks to a single column on narrow viewports" |
| Check mobile-only pulado corretamente fora do viewport mobile | `shell.spec.ts:94` (`test.skip(width >= MOBILE_BREAKPOINT, ...)`) |

**Gaps específicos identificados:** nenhum teste dedicado de overflow/dialogs/tables em viewport reduzido além dos 3 itens acima; os painéis executivos (Decision Support/Executive Narrative, Workspace) só são exercitados nos testes existentes sob o viewport padrão do arquivo (majoritariamente `lg`, já que `dashboard.spec.ts`/`workspace.spec.ts` não fixam um project específico via `test.use()`) — **não confirmado que Decision Support/Executive Narrative/Workspace funcionam corretamente em `mobile`/`md`**, apenas que a página inicial e a navegação respondem à responsividade.

---

## 6. Matriz de Fluxos Críticos

| Fluxo | Classificação | Evidência (`TEST EXISTS`) | `BEHAVIOR IS ACTUALLY EXERCISED`? |
|---|---|---|---|
| Login | **COVERED** | `dashboard.spec.ts`: senha incorreta mostra erro; senha correta loga e chega a `/dashboard` | Sim — fluxo completo, sucesso e falha |
| Session | **PARTIALLY COVERED** | Gate de autenticação exercitado em praticamente todo spec ("redirects unauthenticated access to X to the login page") | Login e o gate, sim. **Logout nunca é exercitado por nenhum teste E2E** (`grep` por "logout"/"sair" em `web/e2e/*.spec.ts`: zero ocorrências) |
| Dashboard | **COVERED** | `dashboard.spec.ts`, 22 testes — KPIs, widgets, estados vazio/erro/timeout/loading, refetch, responsividade, não-exposição de secrets |
| Navigation | **COVERED** | `shell.spec.ts` — 14 itens de nav renderizados, item ativo correto, forma do sidebar por breakpoint |
| Decision Support | **COVERED** | `dashboard.spec.ts` — resposta com escopo de organização citando Advisors; bloqueio de submissão sem escopo; "Base Insuficiente" |
| Executive Narrative | **COVERED** | `dashboard.spec.ts` — geração com escopo de organização citando Advisors; bloqueio sem escopo; "Base Insuficiente" para projeto sem evidência |
| Projects | **COVERED** | `projects.spec.ts` — fluxo completo Dashboard→menu→listagem→seleção→Workspace, busca, encoding de nome com `/`, estados vazio/erro/loading |
| Program Management | **NOT COVERED** | `shell.spec.ts:54` — apenas `href="/program-management"` verificado | Não — nenhuma página/comportamento exercitado |
| Project Delivery | **NOT COVERED** | `shell.spec.ts:56` — apenas `href="/project-delivery"` verificado | Não |
| Actions | **COVERED** | `actions.spec.ts` + seção Ações de `workspace.spec.ts` — agrupamento por urgência, navegação, itens de ação |
| Decisions | **COVERED** | `decisions.spec.ts` — Executive Decision Queue, degradação graciosa, estado vazio/erro |
| Learnings ("Aprendizados") | **COVERED** | `organizational-intelligence.spec.ts` — padrão honesto de threshold, degradação graciosa |
| Documents | **NOT COVERED** | `shell.spec.ts:72` — apenas `href="/administracao/documentos"` verificado | Não — nenhum teste E2E de upload/listagem de documento existe (o endpoint `POST /api/documents` real, incluindo o limite de tamanho do F4/D-190, é testado em `tests/test_document_upload_size_limit.py`, mas exclusivamente no nível de integração Python/HTTP, nunca via browser) |
| Administration (Users) | **COVERED** | `users-admin.spec.ts`, 13 testes — CRUD completo, busca, filtros, papéis, auto-proteção de admin |
| API Keys | **COVERED** | `api-keys-admin.spec.ts` — criação, exibição única do segredo, listagem mascarada, cópia, revogação |
| Sessions (admin) | **COVERED** | `sessions-admin.spec.ts` — listagem da sessão atual, revogação |
| Invites | **COVERED** | `convites-admin.spec.ts` — criação, exibição única do link, cancelamento, aceite público sem sessão |
| Mission Control | **NOT COVERED** | `shell.spec.ts:74` — apenas `href="/mission-control"` verificado | Não |

**Cobertura incidental adicional, além dos 18 fluxos mandatados:** `workspace.spec.ts` (19 testes — painéis independentes, Risk Advisor, submissão de análise Status/Risco/Reunião) e `executive-memory.spec.ts` (3 testes — insights de memória executiva) — ambos substanciais, não redesenhados nem tocados por esta missão.

---

## 7. CI — Pipeline Real

```
commit/PR
  → job "validate" (backend): checkout → setup Python 3.11 → pip install → ruff check → pytest --cov (falha se cobertura < 80%)
  → job "frontend" (paralelo ao backend, não depende dele):
       checkout → setup Node 22 → npm ci → tsc --noEmit → eslint . → npm test (vitest)
       → npm run build → playwright install --with-deps chromium → playwright test --project=lg
```

| Item | Real |
|---|---|
| O que realmente executa | Lint + testes unitários/integração backend com cobertura mínima 80%; typecheck + lint + testes unitários frontend + build + E2E (`lg`/Chromium apenas) no frontend |
| O que é obrigatório (falha o job) | Qualquer step falho falha o job correspondente (`validate` ou `frontend`) — comportamento padrão do GitHub Actions, nenhum `continue-on-error` encontrado em nenhum step |
| O que é opcional | Nada explicitamente marcado como opcional/`continue-on-error` |
| O que não existe | Deploy/publicação de artefato (nenhum step de deploy no workflow — **não inventado**, confirmado ausente); execução de `mobile`/`md` no CI; execução em Firefox/WebKit; dependency scanning (já registrado como F6, W7-4, `OPEN`) |
| Quais failures bloqueiam | Qualquer falha em `validate` ou `frontend` falha o respectivo job — se isso bloqueia merge depende de branch protection (pergunta 10, não verificável por código) |
| Quais failures podem ser ignorados | Nenhuma configurada para ser ignorada |

---

## 8. Controlled Pilot Browser Baseline

**Proposto: Chromium/Chrome é suficiente para o Controlled Pilot.**

**Justificativa:** um piloto controlado (per definição já estabelecida em W7-4, D-187: população pequena e confiável — equipe interna/early adopters) não tem, até o momento, nenhum requisito de negócio demonstrado exigindo Safari ou Firefox — nenhuma menção a isso em nenhuma decisão anterior (`DECISION-LOG.md`), nenhum requisito de cliente registrado. Chrome/Edge (ambos Chromium) cobrem, segundo dados públicos de mercado amplamente conhecidos, a esmagadora maioria de uso corporativo/desktop — mas esta afirmação de mercado **não é validada por nenhum dado real da STRATECH** (nenhuma telemetria de uso existe ainda, produto pré-piloto) e é registrada aqui como suposição razoável, não fato comprovado.

**Menor delta técnico necessário (não implementado nesta missão):**

| Item | Ação proposta | Já existe mecanismo? |
|---|---|---|
| Rodar `mobile`/`md` também em CI, não só `lg` | Adicionar `--project=mobile --project=md` (ou matriz de job) ao step de E2E | Sim — os projects já existem, só não são invocados em CI |
| Fechar o gap de `Documents` (E2E) | Um teste mínimo de upload via browser (feliz + rejeição por tamanho, reaproveitando F4) | Não — spec novo necessário |
| Fechar o gap de `Mission Control` | Um teste mínimo de carregamento da página | Não — spec novo necessário |
| `Program Management`/`Project Delivery` | Avaliar se essas páginas têm funcionalidade real hoje (não verificado nesta missão — decisão fora de escopo, ver Seção 10) antes de decidir se merece teste dedicado ou se é dívida aceitável para o piloto | A determinar |
| Logout E2E | Um teste mínimo confirmando que logout invalida a sessão no browser | Não — spec novo necessário |

**Não proposto:** nenhum engine novo (Firefox/WebKit) — nenhuma necessidade demonstrada para um piloto controlado.

---

## 9. Enterprise Production Browser Readiness

Delta adicional, **não implementado, não necessariamente aprovado** — apenas mapeado para quando houver necessidade real demonstrada (per mandato explícito de não overengineering):

| Item | Quando se tornaria necessário |
|---|---|
| Matriz real de Firefox/WebKit | Se/quando surgir requisito de cliente real (ex.: contrato exigindo suporte formal a Safari) |
| CI rodando a matriz completa (3 viewports × múltiplos engines) | Mesma condição acima — custo de CI cresce linearmente com o produto de projects × engines |
| Dependency scanning integrado ao E2E/build (F6, já registrado em W7-4) | Já um item independente do W7-4, não duplicado aqui |
| Verificação formal de branch protection bloqueando merge em falha de E2E | Decisão operacional de GitHub, não uma mudança de código |
| Cobertura E2E completa dos 4 fluxos hoje `NOT COVERED` | Antes de qualquer certificação formal de compatibilidade enterprise |

---

## 10. Findings

| # | Finding | Classificação |
|---|---|---|
| G1 | Nenhum engine além de Chromium jamais validado (Firefox/WebKit ausentes) | `READINESS GAP` — não bloqueia o piloto (Seção 8), bloqueia certificação Enterprise Production |
| G2 | CI roda apenas o project `lg`; `mobile`/`md` nunca rodam em CI apesar de existirem | `READINESS GAP` — menor delta do Controlled Pilot Baseline (Seção 8) |
| G3 | `Documents` sem cobertura E2E (apenas link de nav) | `BLOCKS CONTROLLED PILOT` se o piloto incluir upload de documentos via browser como fluxo crítico; caso contrário `READINESS GAP` — decisão de escopo do piloto pertence ao Founder, não decidida aqui |
| G4 | `Mission Control` sem cobertura E2E (apenas link de nav) | `READINESS GAP` |
| G5 | `Program Management`/`Project Delivery` sem cobertura E2E (apenas link de nav) | `READINESS GAP` — severidade depende de quanta funcionalidade real essas páginas já têm hoje, não avaliado nesta missão (fora do grounding mandatado, que era sobre E2E/CI, não sobre o estado funcional dessas páginas em si) |
| G6 | Logout nunca exercitado por E2E | `READINESS GAP` — a lógica de logout já é testada no nível de unidade (`web/lib/session.test.ts`), mas nunca ponta a ponta via browser |
| G7 | Nenhuma verificação de branch protection real bloqueando merge em falha de E2E | `NON-BLOCKING DEBT` — configuração operacional do GitHub, não um gap de código |
| G8 | Nenhum browser declarado formalmente como suportado em nenhuma documentação | `NON-BLOCKING DEBT` — cosmético/documental, não um gap funcional |
| G9 | Suporte a Edge nunca testado diretamente (apesar de Chromium-based) | `ACCEPTED` — mesma aproximação de engine já aceita implicitamente para o piloto (Seção 8) |

Nenhuma dívida cosmética elevada a blocker, per mandato explícito.

---

## 11. Estratégia Incremental (proposta, não implementada)

### Necessárias ao Controlled Pilot

| Etapa | Objetivo | Arquivos prováveis | Testes necessários | Risco | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| 1 | Rodar `mobile`/`md` em CI | `.github/workflows/ci.yml` | Nenhum novo — reusa os projects já existentes | Baixo — só aumenta tempo de CI | Nenhuma | 3 execuções (`mobile`/`md`/`lg`) verdes em CI |
| 2 | Cobertura E2E mínima de `Documents` | `web/e2e/documents-admin.spec.ts` (novo) | 2-3 testes (upload feliz, rejeição por tamanho, listagem) | Baixo — reaproveita padrão já estabelecido pelos specs de admin existentes | F4 (D-190) já fechado no backend | Spec novo verde, cobrindo upload feliz + rejeição |
| 3 | Cobertura E2E mínima de `Mission Control` | `web/e2e/mission-control.spec.ts` (novo) | 1-2 testes (carregamento, elementos essenciais) | Baixo | Nenhuma | Spec novo verde |
| 4 | Cobertura E2E de logout | Extensão de `web/e2e/shell.spec.ts` ou novo teste em spec existente | 1 teste (logout invalida sessão, redireciona) | Baixo | Nenhuma | Teste novo verde |
| 5 | Avaliar `Program Management`/`Project Delivery` | Nenhum (avaliação, não implementação) | N/A | N/A | Resultado da avaliação decide se entra no piloto ou fica como dívida aceitável | Achado registrado, decisão do Founder |

### Adicionais, apenas para Enterprise Production

| Etapa | Objetivo | Dependências |
|---|---|---|
| 6 | Adicionar projects Firefox/WebKit ao `playwright.config.ts` | Necessidade real demonstrada (Seção 9) |
| 7 | CI rodando a matriz completa de engines × viewports | Etapa 6 |
| 8 | Confirmar/configurar branch protection real | Decisão operacional do Founder/GitHub admin |

Nenhuma etapa acima foi executada nesta missão.

---

## 12. Preservação Arquitetural

Confirmado — nenhuma alteração nesta missão a `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, `ExecutiveOrchestrator`, os Enterprise Advisors, Executive Intelligence, Workflow Runtime, Event Pipeline, Enterprise Domain, Knowledge Platform, W7-1, W7-3, a implementação de segurança do W7-4 (F1/F2/F4), ou o Deployment Contract do W7-5 — missão inteiramente documental/governança, nenhum arquivo de `src/`/`web/app/`/`web/lib/` tocado.

---

## 13. Riscos

| Risco | Registro |
|---|---|
| `Documents`/`Mission Control`/`Program Management`/`Project Delivery` sem cobertura E2E real até a implementação futura | Registrado como G3/G4/G5, não bloqueante do assessment em si |
| Branch protection real não verificável — falha de E2E pode não estar de fato bloqueando merge hoje | G7, decisão/verificação operacional pendente |
| Nenhum dado real de uso (telemetria) sustenta a suposição de que Chromium/Chrome é suficiente para o piloto | Suposição razoável, mas explicitamente não comprovada por dado real da STRATECH (Seção 8) |

Nenhum risco novo além destes foi identificado.

---

## 14. GO/NO-GO

**GO para o Founder avaliar a Estratégia Incremental (Seção 11)** — o assessment está completo, fundamentado no código real.

**GO técnico para a implementação do W7-7 (Etapas 1-5, Seção 11)** — nenhuma delas exige engine novo nem infraestrutura nova; todas são pequenas e independentes. **Condicionado a nova autorização explícita do Founder** — nenhuma iniciada nesta missão.

**Impacto esperado sobre a prontidão do Controlled User Pilot:** nenhum bloqueio adicional identificado além de G3 (Documents), cuja severidade depende de decisão de escopo do Founder (se upload de documento via browser é um fluxo crítico do piloto ou não). Todos os demais gaps são `READINESS GAP`/`NON-BLOCKING DEBT`, não bloqueantes.

Nenhuma implementação começa automaticamente. Retornando obrigatoriamente para Executive Review.
