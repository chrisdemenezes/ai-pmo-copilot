# Local V1 Pilot Final Hardening — Executive Evidence

- **Missão:** FOUNDER DECISION — LOCAL V1 PILOT FINAL HARDENING (Fechamento dos Achados HIGH da User Session #2)
- **Data:** 2026-08-21
- **Baseline SHA:** `d9206eb95f2a9825307b0b684bb4d26a27997f75`
- **Escopo:** diagnóstico, correção, teste e evidência exclusivamente dos 2 achados HIGH registrados em D-222 (Local V1 Human User Session #2) — H1 (Dashboard, discoverability de dados demonstrativos) e H2 (robustez do bootstrap de organização do piloto).

## 1. H1 — Dashboard

### ROOT CAUSE
`variant="outline"` (D-219) é um selo pequeno, borda fina, texto neutro (`text-ink-muted`), inline junto ao título de cada seção — numa página densa de 13 seções quase idênticas visualmente, sem nenhum tratamento visual ambiente distinguindo a "zona" de dado demonstrativo. Confirmado pela Human User Session #2 (D-222): usuário rolou a página inteira duas vezes sem notar.

### SOLUTION
**1ª tentativa** (testada e reprovada ao vivo): nova variante de Badge (`"demo"`, fundo preenchido com a cor de destaque da marca) + aviso contextual único antes de qualquer seção. Micro-teste humano = **FAIL** — mesmo visível e colorido, não percebido.

**2ª tentativa, decisão explícita do Founder**: remoção das 5 seções alimentadas por mock (Demandas/Riscos/Issues/Mudanças, Decision Center, Actions Center, Recent Activity, AI Recommendations) do Dashboard do piloto — zero ambiguidade em vez de um sinal que depende do usuário notá-lo. Componentes (`WorkItemsOverview`, `DecisionCenterPanel`, `ActionsCenterTable`, `RecentActivityTimeline`, `AIRecommendationsPanel`) e dado mock (`web/lib/mock/cockpit-data.ts`) preservados no repositório para uma futura Capability real. Variante `"demo"` do Badge revertida (sem call site).

### BEFORE
5 seções demonstrativas visíveis no Dashboard, sem distinção perceptível de dado real.

### AFTER
5 seções removidas do Dashboard do piloto; Dashboard reduzido às seções reais (Executive Overview, Situação do Portfólio, Situação dos Programas, Program Execution, Executive Focus, Decision Support, Narrativa Executiva, Projetos, Distribuição de saúde, Maior concentração de risco).

### AUTOMATED TESTS
`web/app/dashboard/page.test.tsx`: confirma que nenhuma das 5 seções renderiza e que todas as seções reais continuam presentes. `web/e2e/dashboard.spec.ts`: confirma ausência das 5 seções na página real.

### HUMAN MICRO-TEST
Pergunta ao Founder, sem apontar nada: "Antes de analisar os números, há alguma informação nesta tela que você entende que não representa dados reais da organização?" — **1ª tentativa (badge + aviso) = FAIL** (respondeu "não" mesmo com o aviso visível). **2ª tentativa (seções removidas) = PASS** (respondeu "não" — corretamente, pois não há mais nada demonstrativo na tela).

### RESULT
**H1 = CLOSED.**

## 2. H2 — Organization Bootstrap

### ROOT CAUSE
`demo/start-demo.sh` carregava `demo/.env` via `source "$ENV_FILE"` sob `set -a`/`set +a` — executando cada linha como comando bash, não como um parser de `.env` dedicado. Um valor com espaço sem aspas (`PILOT_ORGANIZATION_NAME=Piloto Externo A`, o próprio exemplo do Runbook) é interpretado como "atribuir `PILOT_ORGANIZATION_NAME=Piloto`, depois executar um comando chamado `Externo` com argumento `A`" — reproduzido isoladamente sob `set -euo pipefail` (como o script real roda), esse "command not found" aborta o script inteiro; combinado com um acidente de edição do Founder (colar o texto de um comando heredoc como conteúdo literal do arquivo), o efeito observado ao vivo foi mais brando (variável nunca exportada, script conclui normalmente) — ambos os efeitos têm a mesma causa raiz.

### SOLUTION
`demo/start-demo.sh` (único ponto do repositório que fazia `source` de um `.env`, confirmado por busca) substituído por um loader linha-a-linha: lê cada linha literalmente (sem re-interpretar como sintaxe de shell), separa `KEY`/`VALUE` no primeiro `=`, remove um par de aspas ao redor do valor se presente (compatível com valores já citados), exporta via `set -a`/`set +a`. Nenhum endpoint novo, nenhuma UI nova, nenhum mecanismo paralelo de bootstrap — `AuthService.bootstrap_organization()` intocado.

### WINDOWS/GIT BASH
Cenário H (CRLF): linhas terminadas em `\r\n` (comum em edições feitas em editores de texto Windows) são tratadas corretamente — `\r` removido antes do parsing.

### LINUX
Cenário G: variáveis existentes com URLs contendo `:`, `/`, `@` (ex. `DATABASE_URL`) continuam carregando corretamente, sem regressão.

### TESTS
`tests/shell/test_start_demo_env_loader.sh` (novo) — 8 cenários (A-H): nome simples sem espaço; um espaço (exemplo exato do Runbook); múltiplos espaços; caracteres PT-BR (acentuados, com e sem aspas); configuração ausente; configuração inválida (aspas desencontradas — falha de forma segura, sem abortar o script); variáveis existentes com URLs; quebras de linha CRLF. **8/8 PASS.** Suíte de shell completa (4 arquivos) revalidada sem regressão.

### RESULT
**H2 = CLOSED.**

## 3. Files Changed

```
demo/start-demo.sh                                                  |  33 ++-
docs/operations/LOCAL-V1-PILOT-ORGANIZATION-PROVISIONING-RUNBOOK.md |   2 +
tests/shell/test_start_demo_env_loader.sh                           | 140 +++++
web/app/dashboard/page.test.tsx                                     |  36 ++-
web/app/dashboard/page.tsx                                          |  87 ++---
web/e2e/dashboard.spec.ts                                           |  12 +-
6 files changed, 235 insertions(+), 75 deletions(-)
```

## 4. Tests Added

- `tests/shell/test_start_demo_env_loader.sh` (8 testes, cenários A-H)
- `web/app/dashboard/page.test.tsx` (2 testes atualizados para a remoção das 5 seções)
- `web/e2e/dashboard.spec.ts` (1 teste atualizado)

## 5. Backend

`ruff check src tests`: limpo (nenhum arquivo Python alterado nesta missão).

## 6. Frontend

`tsc --noEmit`: limpo. `eslint . --max-warnings=0`: limpo. `vitest run` (suíte completa): **592/592 PASS**, 80 arquivos, zero regressão. `next build`: sucesso.

## 7. E2E

`web/e2e/dashboard.spec.ts` atualizado e revisado; execução real depende do backend mock e Playwright, validado via CI (mesmo padrão desde D-214).

## 8. Shell

4/4 suítes de shell PASS: `test_prepare_env_pip_upgrade.sh`, `test_start_demo_env_loader.sh` (novo), `test_start_demo_venv_detection.sh`, `test_stop_demo_port_fallback.sh`.

## 9. Build

`next build`: sucesso, todas as rotas listadas normalmente, nenhum erro.

## 10. Architectural Preservation

`git diff --stat origin/main HEAD`: **6 arquivos alterados**, exatamente o escopo H1/H2 autorizado. Zero arquivo tocado em RBAC, Tenant Isolation, Authentication, Session, AdvisorFramework, AIContextEngine, ExecutiveOrchestrator, Advisors, Executive Intelligence, Knowledge Platform, Enterprise Domain, Workflow Runtime, Event Pipeline, migrations, W7-1/W7-3/W7-4/W7-7.

## 11. New Findings

- **Priorização — banner de risco degradado:** durante a sessão, a tela de Priorização mostrou "Não foi possível carregar os riscos -- mostrando apenas o sinal de Status" — comportamento gracioso já documentado do produto (degradação sem bloquear o sinal de Status), não investigado a fundo por estar fora do escopo H1/H2 desta missão. Registrado sem correção.
- **Cache de build do Next.js ao trocar de branch:** ao trocar de branch na máquina física do Founder, `web/.next` ficou dessincronizado, causando 404 em todas as rotas `/api/bff/*` (incluindo login) — mascarado inicialmente como problema de senha do Administrator, consumindo tempo real de diagnóstico. Resolvido sem alteração de código (`rm -rf web/.next` + restart). Recomendado documentar esse passo como higiene padrão ao trocar de branch no Runbook/Windows Session Protocol, em missão futura.
- **Reset de senha do Administrator:** o Founder esqueceu a senha do admin local; sem mecanismo existente de reset (nem endpoint, nem UI), a senha foi redefinida via um script Python local ad-hoc (não commitado), reutilizando `Argon2PasswordHasher` já existente para atualizar `password_hash` diretamente no banco local. Não é uma solução de produto — é uma operação manual de desenvolvimento local, registrada com transparência.

## 12. Remaining Blocker

Nenhum.

## 13. Remaining High

Nenhum relacionado ao piloto controlado.

## 14. Controlled External Pilot Technical Gate

**SATISFIED** (herdado de D-221, revalidado, sem regressão).

## 15. Controlled External Pilot Experience Remediation

**SATISFIED.** H1 = CLOSED (correção + micro-teste humano PASS). H2 = CLOSED (correção + validação técnica PASS, 8/8 cenários). Zero BLOCKER. Zero HIGH remanescente relacionado ao piloto. G8 (Intent to Use = TALVEZ, de D-222) preservado sem manipulação — nenhuma feature criada para elevar essa resposta, conforme mandato explícito.

## 16. Controlled External Pilot

**READY FOR EXTERNAL VALIDATION.** Isso não inicia o piloto externo automaticamente — retorna para Founder Executive Review.

## 17. Next Recommended Action

Founder Executive Review desta evidência → nova Founder Decision explícita para: (a) decidir se um usuário PMO/gestão externo (sem vínculo com o desenvolvimento da STRATECH) inicia a validação de Intent to Use real; (b) decidir se o achado do banner de risco degradado em Priorização merece investigação própria; (c) decidir se o passo de limpeza de cache do Next.js ao trocar de branch deve ser documentado no Runbook/Windows Session Protocol.
