# W7-7 — Controlled Pilot Browser Baseline — Executive Evidence

**Autorização:** "Founder Decision — W7-7 Controlled Pilot Browser Baseline — Implementation Authorization", em resposta ao Technical Design/Assessment (D-193, APPROVED). Chromium/Chrome ratificado como browser oficialmente suportado do Controlled Pilot; Firefox/WebKit explicitamente fora de escopo desta missão (não a Enterprise Production Browser Certification). Autorizadas exatamente as 5 Etapas mandatadas: CI Viewport Coverage; Documents E2E; Mission Control E2E; Logout E2E; classificação IN/OUT de Program Management/Project Delivery.

**Mandato de encerramento:** ao final das 5 etapas, executar as verificações aplicáveis (backend completo, frontend completo, E2E completo mobile/md/lg, ruff, tsc, eslint), diagnosticar qualquer falha antes de qualquer correção, produzir esta Executive Evidence e retornar obrigatoriamente para Executive Review — **não** iniciar automaticamente W7-2, W7-8, ou qualquer outro Epic.

---

## 1. Etapas executadas e commits

| Etapa | Descrição | Commit | Decision Log |
|---|---|---|---|
| 1 | CI Viewport Coverage — `mobile`/`md`/`lg` no pipeline | `fbad941` | D-194 |
| 2 | Documents E2E | `1d24e26` | D-195 |
| 3 | Mission Control E2E | `224dba8` | D-196 |
| 4 | Logout E2E — achado real registrado | `4641bef` | D-197 |
| 5 | Program Management/Project Delivery = IN PILOT BASELINE | `18c667e` | D-198 |

Todas as 5 Etapas mandatadas foram implementadas, cada uma com commit e push independente, per disciplina de governança já estabelecida.

---

## 2. Browser/Engine final e cobertura de viewport

**Browser/Engine:** Chromium (via `devices["Desktop Chrome"]"`), exatamente como já era — nenhum engine novo adicionado, per mandato explícito (Firefox/WebKit permanecem fora de escopo).

**Viewport coverage:** `.github/workflows/ci.yml`, job `frontend`, step `E2E test` passa de `npx playwright test --project=lg` (único project) para `npx playwright test --project=mobile --project=md --project=lg` — os 3 projects Playwright já existentes, nenhum novo, nenhum alterado. Executado e comprovado localmente antes do commit (Seção 6).

---

## 3. Documents — evidência

`web/e2e/documents-admin.spec.ts` (5 testes): acesso via nav; redirecionamento não autenticado; estado vazio; upload válido com feedback de sucesso e documento visível na listagem depois; rejeição de arquivo vazio com a mensagem real do backend (`"File is empty"`).

**Infraestrutura de teste estendida** (não produto): `web/e2e/mock-backend.mjs` ganhou rotas reais para `/api/documents` (GET/POST) e `/api/documents/:id/reindex`, com um parser mínimo de `multipart/form-data` (sem dependência nova), replicando exatamente as 2 únicas validações reais de `src/api/routes/knowledge.py` (arquivo vazio / não-UTF-8 → 422) — nenhum comportamento de produto inventado.

**Fronteira de evidência declarada explicitamente:** esta suíte roda contra `mock-backend.mjs`, nunca o backend FastAPI real, nunca um pipeline real de embedding/indexação. Prova a integração Frontend → BFF → contrato real da rota, **não** prova ingestão/chunking/indexação vetorial reais — isso é provado pela suíte pytest do backend (`tests/test_document_upload_size_limit.py`, testes do Knowledge Platform), nunca reprovado aqui.

---

## 4. Mission Control — evidência

`web/e2e/mission-control.spec.ts` (2 testes, deliberadamente mínimo): redirecionamento não autenticado; acesso autenticado com renderização das seções executivas essenciais (Product Pulse, Enterprise Program — Waves, Decision Log) e o texto real de permissão hoje ("Acesso não restrito ainda — RBAC no Épico 3").

A página é inteiramente dado mock estático (`web/lib/mock/mission-control-data.ts`, sem `fetch`/hook) — não há estado de loading/erro/vazio a provar, diferente de toda outra página já coberta.

---

## 5. Logout — evidência

**Achado real, elevado antes de qualquer implementação (Preservação Arquitetural, Seção 11 do mandato):** não existe nenhum controle de logout em nenhuma UI da STRATECH hoje (`web/components/shell/sidebar.tsx`/`header.tsx` — sem "Sair", sem menu de usuário, em nenhum breakpoint). `DELETE /api/bff/session` é real, implementado desde W7-4 (F9, `ACCEPTED`, best-effort) e testado a nível de unidade, mas nada no browser jamais o invoca.

**Decisão tomada:** esta missão **não adiciona** um botão de logout — mudança de produto/UX fora do escopo de uma missão de baseline E2E/CI. Achado registrado explicitamente para decisão do Founder, não corrigido silenciosamente.

`web/e2e/logout.spec.ts` (1 teste) exercita o mecanismo real diretamente do browser (a chamada exata que um futuro controle de "Sair" executaria: `fetch("/api/bff/session", { method: "DELETE" })`), provando as duas metades exigidas pelo mandato:
- **Frontend state cleared:** `/dashboard` redireciona para `/entrar` depois.
- **Server-side session invalidated:** a mesma sessão desaparece de `GET /api/admin/sessions` (backend/mock), verificado independentemente do cookie do browser.

---

## 6. Program Management / Project Delivery — classificação

**Decisão registrada:** Program Management = **IN PILOT BASELINE**. Project Delivery = **IN PILOT BASELINE**.

**Evidência mecânica (nenhuma inferida):**
1. Ambas são Capabilities reais e já entregues (Capability 02/03, Release 0.2), hooks reais (`usePortfolios`/`usePrograms`/`useProjects`), sem dado mock, com skeleton/erro/vazio completos.
2. `web/components/shell/navigation.ts` tem uma regra de entrada absoluta: "contains only modules that are fully real ... no disabled/hidden/placeholder entries". Ambas estão em `NAV_ITEMS`, posicionadas na sequência de uso diário (Dashboard → Priorização → Projetos → **Program Management** → **Project Delivery** → Ações → Decisões), distintas do bloco de Enterprise Administration que vem depois.
3. Os dados de Program/Project alimentam a própria consolidação de KPIs do Dashboard (`consolidatePrograms`/`consolidatePortfolios`).
4. Nenhuma documentação de escopo de piloto existente as excluía — a única menção prévia (Technical Design W7-7, D-193, achado G5) explicitamente adiou a decisão para o Founder.
5. `web/e2e/mock-backend.mjs` já tinha fixtures reais para ambas (`DOMAIN_PORTFOLIOS`/`DOMAIN_PROGRAMS`/`DOMAIN_PROJECTS`), prontas e não utilizadas.

**Cobertura mínima implementada:** `web/e2e/program-management.spec.ts` e `web/e2e/project-delivery.spec.ts` (2 testes cada) — redirecionamento não autenticado; acesso via nav + a única lógica real de cada página (agrupamento correto sob o Portfolio/Program pai correto). Nenhum teste de estado vazio/erro artificial criado.

---

## 7. Achados corrigidos durante a implementação (transparência)

| # | Achado | Correção |
|---|---|---|
| 1 | Etapa 5: os 2 testes de agrupamento inicialmente localizavam a seção via `getByRole("heading", ...)`, assumindo que `CardTitle` (`web/components/ui/card.tsx`) expõe role `heading` — não expõe (`<div>` puro). Falha determinística nos 3 viewports (6 failed, nenhum flake), diagnosticada antes de qualquer correção. | Localização por `hasText` (texto do título) em vez de role. Comportamento de produto não alterado — o defeito era do teste, nunca da página. |

---

## 8. Branch Protection

**BRANCH PROTECTION ENFORCEMENT = UNVERIFIED.** Nenhuma ferramenta MCP GitHub disponível nesta sessão expõe a configuração real de branch protection do repositório (apenas issues/PRs/commits/actions/releases/branches por nome, nenhum endpoint de proteção). Se falha de E2E de fato bloqueia merge para `main` depende dessa configuração externa ao repositório — registrado como gap de governança/CI readiness, **não presumido, não inventado**. Não bloqueia tecnicamente o Controlled Pilot Browser Baseline, per mandato explícito.

---

## 9. Verificação final — suítes completas

| Suite | Resultado |
|---|---|
| Backend completo (`python3 -m pytest --cov=src --cov-fail-under=80`) | **957 passed, 0 failed** (10:35) — idêntico ao baseline pré-missão (D-191/D-193), coverage 97.38%. Zero alteração em `src/` nesta missão. |
| Frontend completo (`npm test`, vitest) | **577 passed, 0 failed**, 78 arquivos — idêntico ao baseline. |
| `ruff check src tests` | Limpo — nenhum finding. |
| `npx tsc --noEmit` | Limpo. |
| `npx eslint .` | Limpo. |
| `npm run build` | Sucesso — `/program-management`, `/project-delivery`, `/mission-control`, `/administracao/documentos` todas presentes no build de produção (checagem adicional, paridade com CI). |

### 9a. E2E completo — mobile/md/lg (366 testes = 122 × 3 viewports)

| Resultado | Contagem |
|---|---|
| Passed | **357** |
| Failed | **1** |
| Skipped | **8** |
| Retries configurados | **0** (`retries` ausente de `playwright.config.ts`, default do Playwright) |
| Flakes confirmados | **1** (abaixo) |

**A 1 falha, diagnosticada, não mascarada:** `[mobile] documents-admin.spec.ts:43 "navigates from the sidebar to Documentos"` — clique no link de nav não navegou dentro do timeout de 5s da assertion, permanecendo em `/dashboard`. O mesmo teste passou limpo no mesmo run em `md` (1.0s) e `lg` (1.1s), e havia passado limpo nos 3 viewports quando a Etapa 2 foi executada isoladamente (D-195). **Reproduzido isoladamente** (`--project=mobile -g` apenas esse teste): passou em 2.6s. Diagnóstico: flake ambiental (timing/contenção de recursos em um worker único após ~45 testes sequenciais), não um defeito determinístico de produto nem de teste — confirmado por 2 execuções limpas independentes do mesmo teste. Nenhum retry adicionado, nenhum timeout alterado, nenhum skip/fixme introduzido para mascará-lo.

**8 skips, todos legítimos e pré-existentes:** `shell.spec.ts`'s mobile-only check (2 skips em `md`/`lg`) + `smoke.spec.ts`'s 2 testes que exigem `SMOKE_BACKEND_URL`/credenciais reais, ausentes neste ambiente (6 skips nos 3 viewports). Nenhum skip introduzido por esta missão.

Nenhum teste relaxado, nenhum `skip`/`fixme`/retry usado para obter verde — a única falha de teste encontrada durante a implementação (Seção 7, `getByRole` incorreto) foi corrigida na origem, nunca contornada.

---

## 10. Preservação arquitetural

Confirmado mecanicamente via `git diff --stat` do intervalo completo desta missão (`fbad941..18c667e`): **nenhum arquivo de `src/`, `web/app/`, `web/lib/` (fora de `mission-control-data.ts`, governança), ou `web/components/` foi tocado.** Arquivos alterados no total:

- `.github/workflows/ci.yml` (CI, Etapa 1)
- `web/e2e/mock-backend.mjs` (fixtures de teste, Etapa 2)
- `web/e2e/documents-admin.spec.ts`, `mission-control.spec.ts`, `logout.spec.ts`, `program-management.spec.ts`, `project-delivery.spec.ts` (specs novos)
- `docs/product/stratech-v2/DECISION-LOG.md`, `CHANGELOG.md`, `web/lib/mock/mission-control-data.ts` (governança)

Nenhuma alteração a `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, `ExecutiveOrchestrator`, os Enterprise Advisors, Executive Intelligence, Workflow Runtime, Event Pipeline, Enterprise Domain, Knowledge Platform, os contratos do W7-1/W7-3, a implementação de segurança do W7-4, ou o Deployment Contract do W7-5 — confirmado tanto pela ausência de qualquer alteração em `src/` (Seção 9, suíte backend idêntica ao baseline) quanto pela lista de arquivos acima.

**Nenhum código de produto foi alterado por um teste revelando defeito real** — o único achado de produto desta missão (Seção 5, ausência de controle de logout na UI) foi registrado explicitamente para decisão do Founder, não corrigido silenciosamente, per Seção 11 do mandato.

---

## 11. Riscos residuais

| Risco | Registro |
|---|---|
| Nenhum controle de logout existe na UI da STRATECH | Registrado na Seção 5 — decisão de produto pendente do Founder, fora do escopo desta missão |
| `BRANCH PROTECTION ENFORCEMENT = UNVERIFIED` | Registrado na Seção 8 — não verificável pelas ferramentas disponíveis nesta sessão |
| Documents E2E prova apenas o contrato Frontend→BFF→rota, não ingestão/embedding real | Fronteira de evidência declarada explicitamente na Seção 3; provado pela suíte pytest do backend |
| Firefox/WebKit permanecem inteiramente não validados | Fora de escopo desta missão, per mandato explícito — reavaliação futura condicionada a necessidade real demonstrada |
| 1 flake ambiental confirmado em `documents-admin.spec.ts` (mobile, dentro do run completo) | Diagnosticado e reproduzido como passing isoladamente 2 vezes (Seção 9a) — não é defeito determinístico |

Nenhum risco novo além destes foi identificado durante a implementação.

---

## 12. Controlled Pilot Browser Baseline — critério de encerramento

Comprovado mecanicamente, não assumido:

| Condição | Resultado |
|---|---|
| Chromium/Chrome verde | ✅ (Seção 9a — 357/366, única falha diagnosticada como flake ambiental) |
| mobile/md/lg exercitados | ✅ (Seção 2, Seção 9a) |
| Documents coberto | ✅ (Seção 3) |
| Mission Control com cobertura mínima | ✅ (Seção 4) |
| Logout coberto | ✅ (Seção 5 — mecanismo real exercitado; achado de UI registrado, não mascarado) |
| Program Management/Project Delivery classificados explicitamente | ✅ (Seção 6 — ambos IN PILOT BASELINE, com cobertura mínima) |
| Nenhuma falha real mascarada | ✅ (Seção 7, Seção 9a — único achado de teste corrigido na origem; única falha de E2E diagnosticada como flake, não mascarada) |
| Nenhuma regressão introduzida | ✅ (Seção 9 — backend/frontend idênticos ao baseline pré-missão) |

**`CONTROLLED PILOT BROWSER BASELINE = SATISFIED`.**

Isso significa exclusivamente que a **dimensão Browser/Frontend** deixou de ser um gap de cobertura para um piloto controlado em Chromium/Chrome — **não** significa Enterprise Production Browser Certification (Firefox/WebKit permanecem fora de escopo), **não** resolve o achado de ausência de controle de logout na UI (Seção 5, decisão pendente do Founder), e **não** verifica Branch Protection real (Seção 8, UNVERIFIED).

---

## 13. GO/NO-GO para Controlled User Pilot (dimensão Browser/Frontend)

**GO — BROWSER/FRONTEND DIMENSION FOR CONTROLLED USER PILOT.**

A dimensão de cobertura de browser/E2E do Controlled Pilot Browser Baseline está satisfeita para Chromium/Chrome nos 3 viewports mandatados. Isso não é uma autorização para iniciar o piloto — outros gates da Wave 7 (W7-1 Gates A-D, W7-3 DR Drill, W7-4 F3/F5/F6/F7, Branch Protection UNVERIFIED, ausência de controle de logout na UI) permanecem pendentes e são decisões independentes do Founder.

---

## 14. Status oficial do W7-7

**W7-7 permanece `OPEN`.** O Controlled Pilot Browser Baseline está `SATISFIED` — isso não encerra o W7-7 inteiro. As 3 etapas adicionais propostas no Technical Design (D-193) para Enterprise Production Browser Certification (Firefox/WebKit conforme necessidade real demonstrada) permanecem `OPEN`, não avaliadas nesta missão.

Nenhum outro Epic da Wave 7 (W7-2, W7-8, ou qualquer outro) foi iniciado. Nenhum trabalho posterior inicia automaticamente. Retornando obrigatoriamente para Executive Review.
