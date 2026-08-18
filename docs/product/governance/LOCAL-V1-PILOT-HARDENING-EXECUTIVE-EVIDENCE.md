# Local V1 Pilot Hardening — Executive Evidence

**Autorização:** "Founder Decision — Autorização do Local V1 Pilot Hardening", em resposta à ratificação de `docs/product/governance/LOCAL-V1-PILOT-HARDENING-REVIEW.md` (D-210). Implementação incremental e estritamente limitada a **F3 (MUST FIX)**, **F4 (MUST FIX)**, **F6 (SHOULD FIX, autorizado nesta missão)** e **F7 (DOCUMENTATION FIX, obrigatório)**. Nenhum outro finding autorizado. Nenhuma sessão humana autorizada por este documento.

**Regra de execução seguida:** cada etapa foi revalidada (causa raiz), implementada com o menor delta necessário, testada (foco + regressão relevante), documentada e commitada/pushed individualmente antes de avançar para a próxima — nenhum commit agrupa correções não relacionadas.

---

## 1. F3 — pip no Windows

**Antes:** `scripts/prepare-env.sh` chamava `pip install --quiet --upgrade pip` diretamente após ativar o venv. No Windows, isso falha — o pip não pode sobrescrever seu próprio executável em uso (`ERROR: To modify pip, please run ...python.exe -m pip install...`).

**Depois:** ambas as chamadas de pip (`--upgrade pip` e `-r requirements.txt`) passaram a usar `python -m pip`, que resolve corretamente para o Python do venv ativo em qualquer plataforma (Linux/macOS/Windows) e evita o problema de auto-sobrescrita.

**Commit:** `4125272` — `fix(F3): use python -m pip for self-upgrade in prepare-env.sh (Windows-compatible)`

**Arquivos alterados:**
- `scripts/prepare-env.sh` (2 linhas)
- `tests/shell/test_prepare_env_pip_upgrade.sh` (novo)

**Teste focado:** `tests/shell/test_prepare_env_pip_upgrade.sh` — guarda de regressão estática (confirma que o padrão vulnerável `pip install --upgrade pip` não retornou) + prova comportamental (executa a linha real do script contra um stub de `pip` que falha exatamente como o Windows falha, e um stub de `python` que só sucede via `-m pip`). Resultado: **3/3 checks PASS**.

**Regressão:** `python -m pip --version` confirmado funcional contra o venv real do repositório (Linux, preservando o comportamento existente).

---

## 2. F4 — Venv detection no Windows

**Antes:** `demo/start-demo.sh` só verificava `.venv/bin` (layout POSIX), nunca `.venv/Scripts` (layout Windows) — nos passos 20-25 originais. No Windows, isso resultava em usar o Python global (Microsoft Store), não o do projeto, causando `ModuleNotFoundError: No module named 'pgvector'` (root cause já confirmado em D-209). Mesmo corrigindo o PATH isoladamente, a chamada `python3 -m alembic upgrade head` continuaria falhando, pois o venv do Windows cria `python.exe`, nunca `python3.exe`.

**Depois:** bloco de resolução explícita de `PYTHON_BIN`:
1. `.venv/bin/python3` existe → `PATH` prefixado com `.venv/bin`, `PYTHON_BIN=.venv/bin/python3`.
2. Senão, `.venv/Scripts/python.exe` existe → `PATH` prefixado com `.venv/Scripts`, `PYTHON_BIN=.venv/Scripts/python.exe`.
3. Senão → `PYTHON_BIN=python3` (fallback idêntico ao comportamento anterior quando não há venv).

A chamada de migrations passou a usar `"$PYTHON_BIN" -m alembic upgrade head`. A chamada `uvicorn` (já bare) permanece inalterada — resolve corretamente via `PATH` agora que `.venv/Scripts` também é prefixado.

**Commit:** `fe68917` — `fix(F4): resolve PYTHON_BIN explicitly in demo/start-demo.sh (Windows-compatible)`

**Arquivos alterados:**
- `demo/start-demo.sh` (bloco de resolução + 1 linha da chamada alembic)
- `tests/shell/test_start_demo_venv_detection.sh` (novo)

**Teste focado:** `tests/shell/test_start_demo_venv_detection.sh` — extrai o bloco real de resolução do script (não uma reimplementação) e testa contra fixtures sintéticas, cobrindo os 6 cenários mandatados:
- **A.** layout `.venv/bin` — PASS
- **B.** layout `.venv/Scripts` — PASS
- **C.** ausência de cross-match entre layouts — PASS
- **D.** precedência do venv sobre um `python3` global no PATH — PASS
- **E.** ausência de venv → fallback explícito `python3` — PASS
- **F.** preservação bit-a-bit do comportamento Linux/macOS pré-fix — PASS

**Regressão:** confirmado ao vivo contra o repositório real (Linux) — `PYTHON_BIN` resolve para `.venv/bin/python3`, `alembic --version` executa com sucesso via o binário resolvido.

Nenhum workaround específico para a máquina do Founder foi introduzido — a lógica é genérica para os 2 layouts de venv reais.

---

## 3. F6 — Logout UX (menu fixo no viewport)

**Antes:** `AppShell` usava `min-h-full` no container externo — não limita a altura ao viewport. Quando o conteúdo principal excede a altura do viewport, o container flex inteiro (incluindo a sidebar, uma irmã flex sob `align-items:stretch` padrão) cresce além do viewport, e o botão "Sair" só fica acessível rolando a página inteira.

**Depois:**
- `web/components/shell/app-shell.tsx`: `min-h-full` → `min-h-screen` no container externo; `data-testid="app-content"` adicionado ao slot de conteúdo real (para permitir testes de regressão precisos, sem alterar visual/layout).
- `web/components/shell/sidebar.tsx`: `data-testid="sidebar-nav"` ganhou `md:sticky md:top-0 md:h-screen md:overflow-y-auto` — o menu completo (14 itens de navegação + "Sair") permanece fixo (pinned) ao viewport durante a rolagem da página, em qualquer tela da aplicação (layout compartilhado por todas as sessões/rotas autenticadas).

**Achado real descoberto durante a validação da própria correção, diagnosticado e corrigido (não mascarado), dentro do escopo desta mesma etapa:** ao fixar a sidebar exatamente no canto inferior esquerdo do viewport (`h-screen` + `sticky`), o botão "Sair" no breakpoint `md` (56px de largura) passou a colidir com o indicador de rota do Next.js em modo dev (`next dev`, usado tanto pelo Runbook local quanto pela suíte E2E) — que renderiza por padrão no canto inferior-esquerdo (`<nextjs-portal>`), interceptando o clique. Reproduzido de forma determinística (3/3 falhas) com o delta aplicado; confirmado ausente na base pré-fix (3/3 limpo) — prova de que era efeito direto desta correção, não flake pré-existente. Corrigido com `web/next.config.ts`: `devIndicators.position: "bottom-right"` — configuração de tooling de desenvolvimento apenas, zero efeito em `next build`/`next start` ou no layout da aplicação.

**Commit:** `ead39df` — `fix(F6): pin the desktop sidebar to the viewport (md/lg logout reachability)`

**Arquivos alterados:**
- `web/components/shell/app-shell.tsx`
- `web/components/shell/sidebar.tsx`
- `web/next.config.ts`
- `web/e2e/shell.spec.ts` (novo teste de regressão)

**Teste focado (novo):** `e2e/shell.spec.ts` — "keeps the sidebar pinned to the viewport while page content scrolls (md/lg)": força overflow real dentro do slot de conteúdo verdadeiro do `AppShell` (não um artefato fora dele) e confirma que a sidebar — e o botão "Sair" dentro dela — permanece fixa e alcançável (`toBeInViewport`) durante a rolagem, nos breakpoints `md`/`lg`. Mobile confirmado não afetado (já usa `position:fixed` genuíno).

**Validação obrigatória (mandato):**
- Mobile: não afetado, `position:fixed` já correto — confirmado.
- `md`/`lg`: sidebar fixa confirmada via bounding box (`y≈0`, tolerância de sub-pixel) mesmo com conteúdo real forçado a exceder o viewport.
- Botão visível: confirmado (`toBeVisible`).
- Botão acessível/alcançável: confirmado (`toBeInViewport`, clicável sem rolar a página).
- Alcançável por teclado: preservado — nenhuma alteração de `tabindex`/ordem DOM/foco; o botão continua um `<button>` nativo na mesma posição na árvore.
- Logout funcional: confirmado via `e2e/logout.spec.ts` (sessão invalidada no browser e no backend) — 5/5 em `md`, mais mobile/lg, após a correção do `devIndicators`.
- Ausência de regressão no sidebar: confirmado — 14 itens de navegação, breakpoints, nav ativo, todos os testes de `shell.spec.ts` PASS.
- Ausência de overflow indevido: confirmado — `md:overflow-y-auto` só ativa scroll interno na própria sidebar se seus itens (fixos, poucos) excederem a altura, o que não ocorre na prática.

**Regressão:** 3 execuções completas da suíte E2E (mobile/md/lg, ~360 testes) após a correção do `devIndicators` — a última **360/360 PASS, zero falhas**. `vitest run` completo (frontend): **579/579 PASS**. `tsc --noEmit` e `eslint` limpos nos arquivos tocados. `next build` (produção) concluído sem erros.

Nenhum redesenho do `AppShell` — apenas as classes CSS/atributos mínimos descritos acima.

---

## 4. F7 — Protocolo de Validação (documentação)

**Antes:** `docs/product/governance/LOCAL-V1-USER-SESSION-PROTOCOL.md`, Seção 2, não especificava uma pergunta de teste concreta para a Fronteira de IA — a validação física (D-209) usou "Quero fazer um teste com esta função", que não contém vocabulário de nenhum dos 8 Advisors e produziu `insufficient_basis(SELECTION_EMPTY)` antes de qualquer chamada de IA, observado como "Base insuficiente" em vez do `502` documentado.

**Depois:** Seção 2 atualizada com:
1. O diagnóstico definitivo (ratificado em D-210): causa raiz é a pergunta de teste, não o produto.
2. Pergunta de teste recomendada: **"Quais são os principais riscos ativos que exigem atenção da liderança?"** — verificada mecanicamente (função pura `evaluate_selection_rule()`, sem precisar de backend/LLM): seleciona `risk_advisor`+`executive_advisor` em escopo Organização, `risk_advisor` em escopo Projeto.
3. Confirmação de que `REAL AI CONTENT = NOT AVAILABLE` permanece documentado e inalterado.
4. Registro não bloqueante (não implementado): a UI descarta `insufficient_basis_reason`, retornado pelo backend mas não diferenciado na mensagem exibida.

**Decision Support não foi alterado** (nenhuma linha de código de produto tocada) — apenas documentação/roteiro, conforme mandatado.

**Commit:** `d6baae0` — `docs(F7): replace the AI Boundary test question with a domain-vocabulary one`

**Arquivos alterados:**
- `docs/product/governance/LOCAL-V1-USER-SESSION-PROTOCOL.md`
- `tests/test_executive_orchestrator_selection_rule.py` (novo: `TestLocalV1SessionProtocolQuestion`, 2 testes)

**Teste (novo):** pina a garantia documentada acima contra `evaluate_selection_rule()` real — função pura, sem dependência de banco de dados. **26/26 PASS** no arquivo (incluindo os 2 novos).

---

## 5. Regressão automatizada (Seção 6 do mandato)

| Suíte | Resultado |
|---|---|
| `ruff check` nos arquivos tocados (`tests/test_executive_orchestrator_selection_rule.py`) | PASS |
| `pytest` — arquivo tocado (`test_executive_orchestrator_selection_rule.py`) | **26/26 PASS** |
| `pytest` — suíte completa do backend | **Não executável nesta sessão remota** — ver Seção 6 abaixo |
| `vitest run` (frontend completo) | **579/579 PASS** (78 arquivos) |
| `tsc --noEmit` (frontend) | Limpo |
| `eslint` (arquivos tocados) | Limpo |
| `next build` (produção) | Concluído sem erros |
| E2E completo (mobile/md/lg, `npx playwright test --project=mobile --project=md --project=lg`) | **360/360 PASS** (última execução, após a correção do `devIndicators`) |
| `tests/shell/test_prepare_env_pip_upgrade.sh` | 3/3 checks PASS |
| `tests/shell/test_start_demo_venv_detection.sh` | 6/6 cenários (A-F) PASS |

### Achado ambiental, registrado, não corrigido (fora do escopo desta missão)

O `pytest` completo do backend **não pôde ser executado nesta sessão remota**: Docker não está disponível neste ambiente (`docker ps` falha — daemon ausente), portanto não há PostgreSQL/pgvector real acessível. Confirmado mecanicamente: uma execução completa produziu 610 `error` + 50 `failed`; o traceback de um teste isolado confirma a causa exata — `sqlalchemy.exc.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused`. Todos os 660 casos afetados são testes de migrations/backup/restore/repository que dependem de um banco real (`test_migration_*.py`, `test_backup.py`, `test_restore_validation.py`, `test_delete_policy.py`, `test_strategy_advisor*.py`, `test_workflow_runtime.py`, etc.) — confirmado que nenhum desses arquivos foi tocado por esta missão (idênticos a 4 commits antes do início de F3, via `git show`/`diff`). **100% atribuível à ausência de Docker nesta sessão, zero relação com F3/F4/F6/F7.** Não corrigido (fora do escopo autorizado — não é F3/F4/F6/F7); registrado transparentemente, não mascarado.

### Achado adicional, registrado, não corrigido (fora do escopo desta missão)

`ruff check src tests` (usando o `ruff` pinado pelo projeto via `requirements.txt`, instalado no `.venv`) reporta 285 erros pré-existentes, concentrados em arquivos nunca tocados por esta missão (ex.: `tests/test_strategy_advisor_api.py`, `tests/test_workflow_runtime.py` — regra `RUF059`, variáveis desempacotadas não usadas). Confirmado via `git show`/`diff` que esses arquivos são idênticos a 4 commits antes do início desta missão — pré-existente, não introduzido por F3/F4/F6/F7. Fora do escopo autorizado (corrigi-los não é F3/F4/F6/F7); registrado, não corrigido.

---

## 6. Preservação arquitetural

Confirmado mecanicamente via `git diff --stat` acumulado dos 4 commits desta missão — nenhuma alteração em:
- RBAC, Tenant Isolation, Authentication, Session
- `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`
- `ExecutiveOrchestrator`, Advisors (nenhum dos 8 `AdvisorContract` alterado)
- Executive Intelligence, Knowledge Platform, Workflow Runtime, Event Pipeline
- Enterprise Domain

Todos os arquivos alterados nas 4 etapas: `scripts/prepare-env.sh`, `demo/start-demo.sh`, `web/components/shell/app-shell.tsx`, `web/components/shell/sidebar.tsx`, `web/next.config.ts`, `web/e2e/shell.spec.ts`, `docs/product/governance/LOCAL-V1-USER-SESSION-PROTOCOL.md`, `tests/test_executive_orchestrator_selection_rule.py`, mais os 2 novos testes de shell — nenhum toca `src/services/executive_orchestrator/`, `src/services/advisor_framework/`, `src/agents/`, migrações, ou RBAC/Tenant Isolation. `Decision Support` (rota/orquestração/seleção) permanece byte-a-byte inalterado.

W7-1 permanece `OPEN`. External Gates A/B/C/D inalterados. Nenhuma Production AI Validation. Nenhum dado corporativo real.

---

## 7. Findings novos (registrados, não corrigidos silenciosamente)

1. **Colisão do indicador de dev do Next.js com a sidebar fixa (F6)** — descoberto e corrigido dentro do escopo da própria etapa F6 (não uma correção separada não autorizada); ver Seção 3.
2. **`pytest` completo inexecutável nesta sessão remota (ausência de Docker)** — ambiental, fora de escopo, registrado na Seção 5.
3. **285 erros pré-existentes de `ruff check`** em arquivos não tocados por esta missão — fora de escopo, registrado na Seção 5.

Nenhum dos 3 foi corrigido silenciosamente; nenhum requer nova correção de código de produto além do já descrito no achado 1 (já corrigido, dentro do escopo do F6).

---

## 8. Riscos residuais

- **F3/F4:** o delta foi verificado por testes sintéticos + execução real contra o venv deste ambiente (Linux) — a confirmação definitiva de que o Windows real (máquina do Founder) sobe sem os contornos manuais de D-209 só ocorre na revalidação física (Seção 9).
- **F6:** a correção do `devIndicators` é específica de `next dev`; em produção (`next build`/`next start`) o indicador nunca existe, então esse risco específico não se aplica a produção — apenas a sessões locais/dev, que é exatamente onde a sessão piloto ocorre.
- **F7:** a pergunta recomendada evita `SELECTION_EMPTY` deterministicamente, mas não garante que a evidência seja suficiente (`COLLECTION_EMPTY` ainda é possível dependendo do estado real dos dados no momento da sessão) — isso deve ser observado e registrado durante a sessão, não presumido.
- **Ambiental:** a ausência de Docker nesta sessão remota significa que o `pytest` completo do backend não foi reconfirmado aqui — recomenda-se rodá-lo na máquina física Windows (que tem Docker+PostgreSQL reais) como parte da revalidação da Seção 9, mesmo que não seja estritamente um item do Runbook original.

---

## 9. Necessidade de revalidação física Windows

**Confirmado: a implementação NÃO encerra o Hardening.** Conforme o mandato, a máquina física Windows do Founder deve executar novamente o procedimento oficial (Runbook), com o objetivo principal de provar que F3 e F4 foram eliminados e que o ambiente sobe pelo procedimento oficial **sem** os workarounds manuais usados em D-209. Também deve ser revalidado nessa sessão futura: PostgreSQL/pgvector, migrations 0021, dataset, `/health`, `/ready`, frontend, login, Sanity Journey, F6 nos breakpoints aplicáveis (agora incluindo a verificação visual do indicador de dev do Next.js reposicionado), Documents, comportamento documentado de Decision Support (com a nova pergunta de teste), logout, backup checkpoint.

Esta revalidação física é uma missão/checkpoint separado, a ser autorizado por nova Founder Decision.

---

## 10. Status final desta missão

- F3: implementado, testado, commitado (`4125272`).
- F4: implementado, testado, commitado (`fe68917`).
- F6: implementado, testado, commitado (`ead39df`) — incluindo achado real descoberto e corrigido dentro do escopo.
- F7: implementado (documentação), testado, commitado (`d6baae0`).
- Nenhum outro finding (F1/F2/F5/F8/F9) alterado nesta missão.
- Nenhuma sessão humana iniciada. Nenhuma alteração de arquitetura, RBAC, Tenant Isolation, Advisors, `ExecutiveOrchestrator`. Nenhuma infraestrutura adicionada. W7-1 não resolvido. Nenhum uso de Anthropic/Voyage real. Nenhum staging. Nenhum DR Drill. Nenhum outro Epic iniciado.

**GO FOR LOCAL WINDOWS REVALIDATION.** Não é declarado GO para a sessão humana nesta etapa — esse veredito permanece pendente da revalidação física (Seção 9).
