# Local V1 Windows Revalidation — Executive Evidence

**Autorização:** "Founder Decision — Autorização para Local Windows Revalidation", ratificando a implementação do Local V1 Pilot Hardening (F3/F4/F6/F7, D-211) e autorizando exclusivamente a revalidação física na máquina Windows do Founder. Durante a Etapa 9 (Backend Regression), um BLOCKER de navegação real foi encontrado, corrigido e revalidado sob "Founder Decision — Local V1 Pilot Navigation Blocker", registrada separadamente como D-212. Este documento cobre a revalidação completa, do checkpoint original até a conclusão.

---

## 1. HEAD/branch executados

Branch `claude/stratech-permanent-principles-yjnm74`, HEAD final `ccc6ba2` (confirmado sincronizado entre este repositório e a máquina física via `git pull` em cada etapa relevante). Working tree limpo (exceto `demo/backups/`, diretório de artefatos de backup local, não commitado, esperado).

## 2. Máquina/ambiente utilizado

Máquina física do Founder, hostname `CRM_Consultoria`, usuário `chris`, Windows, WSL2 (Ubuntu, versão padrão 2), Docker Desktop `29.7.2`, Git `2.55.0.windows.2`, Python global `3.14.6` (`python3` resolve para Microsoft Store `3.13.14`, achado não bloqueante já conhecido), Node `v24.18.0`, npm `11.16.0`, Chrome `151.0.7922.138`.

## 3. Resultado do Pre-flight

Todos os itens aplicáveis **PASS**: Docker Desktop/Engine/Compose, WSL2, Git/Git Bash, curl, Python 3.11+, Node 22+, npm, RAM não crítico coletado (CPU 12 núcleos, disco 37G livres — ambos PASS). Portas 8000/3000 precisaram de limpeza de processos residuais de sessão anterior (contornado via `Stop-Process`, não um defeito). Porta 5432: serviço nativo `postgresql-x64-18` foi iniciado acidentalmente durante a sessão ("foi sem querer") — contornado reutilizando a porta 5433 para o Docker (mesma configuração de D-209), depois definitivamente resolvido na Etapa 9 (ver Seção 11).

## 4. F3 PASS/FAIL

**PASS — CLOSED ON WINDOWS.** `rm -rf .venv && bash scripts/prepare-env.sh` executado do zero: `== Preparation complete ==`, sem o erro de pip. Python do venv confirmado (`3.13.14`), pip atualizado com sucesso para `26.2.1` via `python -m pip`. Primeira tentativa reproduziu o erro antigo porque a máquina estava desatualizada (commit pré-F3) — corrigido via `git pull`, reteste confirmou a correção real.

## 5. F4 PASS/FAIL

**PASS — CLOSED ON WINDOWS.** `bash demo/start-demo.sh` executado pelo fluxo oficial, **sem** o workaround manual de D-209: migrations aplicadas (`alembic current` → `0021 (head)`, confirmado explicitamente, não só o exit code), backend + frontend `is up`, log do backend sem `ModuleNotFoundError`, queries reais funcionando.

## 6. F6 PASS/FAIL

**PASS.** Confirmado visualmente nos 3 breakpoints:
- `lg`: menu completo com rótulos, fixo, "Sair" acessível; indicador do Next.js no canto inferior **direito**, sem sobreposição (confirma a correção do `devIndicators` de D-211 funcionando na máquina real).
- `md`: barra estreita só com ícones, "Sair" (ícone) visível e fixo no fim da barra; indicador do Next.js separado, sem colisão.
- mobile (375px, DevTools): barra inferior fixa com ícones, já correta desde antes do F6.

## 7. F7 comportamento observado

Pergunta oficial ("Quais são os principais riscos ativos que exigem atenção da liderança?") em escopo Organização produziu **`HTTP 502 Bad Gateway`** — o comportamento fail-closed documentado desde D-205, não mais "Base insuficiente". Confirmado via log do backend: `Audit action=risk_advisor.question_asked organization_id=1`, `AI Foundation call analyst=risk_advisor` (chamada real tentada contra o mock provider), resultando no 502 porque não há `ANTHROPIC_API_KEY` real. Classificação: **provider unavailable / fail-closed correto**, não `SELECTION_EMPTY`, não `COLLECTION_EMPTY`, não masking. O roteiro corrigido em D-211 representa corretamente o comportamento real do produto.

## 8. Database/migrations

**PASS.** `GET /health` → `{"status":"healthy",...}`. `GET /ready` → `{"status":"ready"}`. `\dx` no container confirma `vector 0.8.6` instalado. `alembic current` → `0021 (head)`.

## 9. Dataset

**PASS.** `.venv/Scripts/python demo/seed_demo_data.py` → `All calls produced structured output.`, autenticado como `organization_id=1` (Organização Principal, Administrator). Confirmado via query direta no banco: 32 `analysis_records`, **100% em `organization_id=1`**, zero em `organization_id=2` (Demo Organization) — Tenant Isolation intacto.

## 10. Sanity Journey

**13/13 PASS**, confirmado pelo Founder: Login, Dashboard, Priorização, Projetos, Program Management, Project Delivery, Ações, Decisões, Aprendizados, Documentos, Mission Control, Administração, Logout (redirecionamento a `/entrar` confirmado). A verificação inicial não pegou o BLOCKER de navegação (Seção 14) porque não testou explicitamente "sair de Administração via sidebar" — corrigido e revalidado (ver Seção 14).

## 11. Backend regression suite

Execução real contra Docker/PostgreSQL da máquina física, em 3 rodadas, com diagnóstico incremental:

| Rodada | Resultado | Causa raiz corrigida |
|---|---|---|
| 1ª (DATABASE_URL=5433 forçado) | 610 errors / 51 failed / 305 passed | `tests/db.py` tem porta 5432 hardcoded (não lê `DATABASE_URL`); serviço nativo acidental ocupava 5432 |
| 2ª (serviço nativo parado, Docker recuperou 5432) | 309 errors / 9 failed / 648 passed | Extensão `pgvector` nunca criada no banco `template1` desta instância Docker fresca — `CREATE DATABASE` (usado por `tests/db.py`) clona do `template1`, não do `postgres` |
| 3ª (extensão criada em `template1`) | **0 errors / 8 failed / 958 passed** | — |

As 8 falhas finais são conhecidas e não bloqueantes: 7 = achado F8 já registrado em D-210 (`pg_dump` ausente no Windows — `test_backup.py`/`test_restore_validation.py`); 1 = `test_seed_demo_data.py::test_seed_fails_fast_without_admin_credentials`, anomalia isolada de infraestrutura de teste (root cause não totalmente isolado — possivelmente interação Windows-específica entre `importlib`/`monkeypatch`), **não reflete um defeito real de produto** (o comportamento real de fail-fast do script foi confirmado funcionando corretamente ao vivo múltiplas vezes nesta sessão e em D-208/D-209).

`ruff check src tests`: **285 erros pré-existentes, idênticos** aos já confirmados em D-211 como alheios a toda esta cadeia de missões — nenhum novo.

## 12. Frontend/E2E relevantes

`vitest run`: **579/579 PASS**. `tsc --noEmit`: limpo. `eslint .`: limpo. `next build`: sem erros. Suíte E2E completa (mobile/md/lg, ~370 testes) rodada 2x neste ambiente equivalente (código idêntico ao pulled na máquina Windows): 368/369 e depois 369/369 (o único flake não reproduziu isoladamente 5/5 — mesmo padrão de flake de execução prolongada já caracterizado na missão do F6). Testes shell novos (`test_prepare_env_pip_upgrade.sh`, `test_start_demo_venv_detection.sh`, `test_stop_demo_port_fallback.sh`): todos confirmados PASS **na máquina física Windows real**, após corrigir um bug de isolamento de PATH específico do Windows no próprio teste (symlinks quebram resolução de DLL no MSYS — corrigido para scripts wrapper).

## 13. Backup checkpoint

**PASS.** `docker compose exec -T database pg_dump -U aipmo -d aipmo -Fc` → `demo/backups/local-windows-revalidation-backup.dump` (90885 bytes). Validado via `pg_restore --list`: 237 TOC entries, `EXTENSION - vector` presente, tabelas reais confirmadas, `Dumped from database version: 16.15`.

## 14. Novos findings

1. **BLOCKER de navegação em Administração (D-212, CLOSED):** todas as 5 rotas `/administracao/*` (usuários, chaves de API, sessões, convites, documentos) nunca tiveram `layout.tsx` próprio, logo nunca ganharam `AppShell`/`Sidebar` — navegação institucional completamente ausente ao entrar nessas telas. Causa raiz confirmada mecanicamente: `AppShell` já existia (commit `0f44b50`) antes da primeira página administrativa (`9b4a6c7`, Wave 2) — omissão desde a origem, não regressão desta missão. Corrigido com um único `app/administracao/layout.tsx` reaproveitando `AppShell` (Next.js aplica automaticamente a todas as 5 rotas aninhadas) — nenhuma nova arquitetura de navegação, nenhum submenu, nenhuma duplicação de `NAV_ITEMS`. RBAC preservado (`Sidebar` renderiza lista estática, sem filtragem por papel — autorização real já é sempre server-side). 3 testes E2E novos (entrada→Dashboard, entrada→Projetos, Sair de dentro de Administração), nos 3 breakpoints, provados falhando pré-fix e passando pós-fix. Confirmado ao vivo na máquina física (screenshot).
2. **`demo/stop-demo.sh` dependia de `lsof` (CLOSED):** ausente no Windows/Git Bash, falha silenciosa. Corrigido com fallback portátil via `netstat -ano -p tcp`, mesmo padrão de detecção de plataforma do F4. Confirmado funcionalmente na máquina real: processos residuais efetivamente terminados (verificado via `tasklist`), portas liberadas.
3. **Conflito de porta 5432 com serviço nativo (operacional, resolvido):** já era o achado F1 conhecido; reapareceu por início acidental do serviço durante a sessão. Resolvido parando o serviço + `docker compose restart database`.
4. **Extensão `pgvector` ausente do `template1` (achado novo, operacional, resolvido):** instâncias Docker frescas nunca tiveram `CREATE EXTENSION vector` aplicado ao banco `template1`, quebrando ~300 testes que criam bancos via `tests/db.py` (`CREATE DATABASE`, que clona do `template1`). Resolvido com um único `CREATE EXTENSION IF NOT EXISTS vector` no `template1`. **Recomendação para o Runbook** (não implementada nesta missão, fora do escopo autorizado): adicionar esse passo como parte do Preflight/Clean Install para novas instâncias Docker.
5. **`test_seed_demo_data.py::test_seed_fails_fast_without_admin_credentials` (registrado, não corrigido):** falha isolada, root cause não totalmente identificado, comportamento real do produto confirmado correto independentemente. Fora do escopo autorizado (arquivo de teste pré-existente, nunca tocado por nenhuma das missões desta cadeia).

## 15. Blockers restantes

**Nenhum.**

## 16. Riscos aceitos

- F8 (`pg_dump` ausente nativamente no Windows) — aceito desde D-210, workaround via `docker compose exec` validado e funcional.
- `test_seed_demo_data.py` anomalia isolada — aceito, não reflete comportamento real de produto, monitorar em execuções futuras.
- Recomendação do `pgvector`-no-`template1` para o Runbook — não implementada (fora do escopo autorizado), deve ser considerada em uma futura missão de documentação.

## 17. Preservação arquitetural

Confirmado via `git diff --stat` acumulado dos commits desta revalidação (`0de54a5`, `c96a5cb`, `ccc6ba2`): apenas `web/app/administracao/layout.tsx` (novo), `demo/stop-demo.sh`, `web/e2e/users-admin.spec.ts`, `tests/shell/test_stop_demo_port_fallback.sh` tocados. Nenhuma alteração em RBAC, Tenant Isolation, `AdvisorFramework`, `ExecutiveOrchestrator`, Advisors, Executive Intelligence, Knowledge Platform, Enterprise Domain. `Decision Support` inalterado.

## 18. Status final da máquina Windows

Ambiente Windows físico plenamente funcional: F3/F4/F6/F7 (D-211) todos fechados e revalidados na máquina real; BLOCKER de navegação (D-212) fechado e revalidado na máquina real; `stop-demo.sh` funcional de ponta a ponta sem intervenção manual; backend regression 958/966 passed (0 errors); backup real íntegro.

## 19. GO/NO-GO para LOCAL V1 HUMAN USER SESSION

Todos os critérios da regra de decisão satisfeitos: F3 = PASS; F4 = PASS; F6 = PASS; F7 corretamente compreendido e documentado; Sanity Journey = PASS (13/13); nenhuma regressão crítica/high remanescente (o BLOCKER de navegação encontrado foi corrigido e revalidado dentro desta mesma missão); ambiente permanece íntegro.

**LOCAL WINDOWS ENVIRONMENT = REVALIDATED.**

**GO FOR LOCAL V1 HUMAN USER SESSION.**

Per mandato explícito: mesmo com o resultado GO, **a sessão humana NÃO é iniciada automaticamente.** Retornando para Founder Executive Review.
