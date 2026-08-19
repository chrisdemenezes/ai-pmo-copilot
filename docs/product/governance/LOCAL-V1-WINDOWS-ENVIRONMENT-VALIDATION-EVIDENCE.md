# Local V1 Windows Environment — Validation Evidence

**Autorização:** "Founder Decision — Execução da Validação Local da V1 em Windows", em resposta à ratificação de D-207 e à conclusão do Local V1 Pilot Dataset (commit `877946e`). Missão exclusivamente de **validação operacional** — execução do `docs/operations/LOCAL-V1-WINDOWS-RUNBOOK.md` já aprovado, na máquina física Windows real do Founder, conduzida interativamente (Claude Code sem acesso direto à máquina). **Nenhuma alteração de código foi feita nesta missão** — todos os achados abaixo foram contornados operacionalmente ou registrados sem correção.

W7-1 permanece `OPEN`. Gates A/B/C = `NOT AVAILABLE`, Gate D = `NOT APPROVED` — inalterados. Nenhuma Production AI Validation, nenhum dado corporativo real, nenhum outro Epic iniciado.

---

## 1. Identificação da máquina física

- Hostname: `CRM_Consultoria`
- Usuário Windows: `chris`
- Sistema: Windows (build `10.0.26200`, compatível com WSL2)

## 2. Baseline do ambiente

- Windows version: build `26200` — acima do mínimo `19041` exigido para WSL2.
- WSL2: instalado durante esta missão (`wsl --install`), distro Ubuntu provisionada. `wsl --status` confirma `Versão Padrão: 2`.
- Docker Desktop: instalado durante esta missão (`v4.87.0`, Engine confirmado rodando).

## 3. Versões dos softwares

| Software | Versão observada | Nota |
|---|---|---|
| Git | `2.55.0.windows.2` | OK |
| curl (Git Bash) | `8.21.0` | OK |
| Python (`python`, Git Bash) | `3.14.6` | **WARNING** — acima do que o CI valida (3.11); registrado, não bloqueou |
| Python (`python3`, usado por `prepare-env.sh`) | `3.13` (Microsoft Store) | Resolução de PATH diferente de `python`; usado só na 1ª tentativa de `start-demo.sh` (ver Finding F4) |
| Node.js | `v24.18.0` | **WARNING** — acima do que o CI valida (22); não causou problema real |
| npm | `11.16.0` | OK |
| Docker | `29.7.2, build a7dcaa6` | OK |
| Docker Compose | `v5.4.0` | OK |
| psycopg2-binary | `2.9.12` | OK (após resolver o conflito de porta, ver Finding F1) |

## 4. Branch utilizada

`claude/stratech-permanent-principles-yjnm74`

## 5. Commit SHA utilizado

`877946ea99fd7c5769a2eab2c8cf23a3a7a68f21` (`877946e`) — confirmado via `git rev-parse HEAD` logo após o clone, batendo exatamente com o mínimo exigido.

## 6. Estado do working tree

`git status` → `nothing to commit, working tree clean`, confirmado imediatamente após o clone. Uma pasta anterior (`~/ai-pmo-copilot`, em `main`, commit `3eb9f18`, com alterações locais não commitadas em `setup.bat`/`start.bat`/`web/package-lock.json` e uma subpasta aninhada não identificada) foi substituída por um clone novo **com autorização explícita do Founder** ("pode substituir esta pasta ou até excluir, é resultado de versão antiga").

## 7. PostgreSQL

Container `pgvector/pgvector:pg16` via `docker compose up -d database` — `healthy` em ~14s (primeira vez, com pull da imagem). **Achado real (Finding F1):** a porta 5432 já estava ocupada por um PostgreSQL 18 nativo (`postgresql-x64-18`), instalado deliberadamente pelo Founder para outro uso ("instalei ele e montei as bases para já deixar pronto"). Resolvido publicando o container também na porta **5433** (arquivo de override externo ao repositório, não commitado, ver Finding F1 completo abaixo) — o Postgres nativo do Founder foi preservado intocado. Toda a validação a partir daqui usa porta 5433.

## 8. pgvector

Confirmado disponível — migration `0016` (`CREATE EXTENSION IF NOT EXISTS vector`) aplicada sem erro durante o `alembic upgrade head`; backup final (Seção 18) confirma a extensão presente no dump (`EXTENSION - vector`).

## 9. Migration Head

`alembic current` → **`0021 (head)`**, confirmado explicitamente (não apenas o exit code do `upgrade head`), após aplicar as 21 migrations sem traceback (na porta 5433, ver Finding F1).

## 10. Dataset

`python demo/seed_demo_data.py` (via `.venv/Scripts/python`) executado com sucesso na máquina física: autenticado como `organization_id=1 user_id=1` (Administrator, "Organização Principal"), 6 projetos com status+risco, 6 reuniões com ações, 1 documento sintético indexado (3 chunks). `All calls produced structured output.` — idêntico ao comportamento já validado no ambiente Linux (D-208).

## 11. Backend health

`GET /health` → `{"status":"healthy","service":"AI PMO Copilot","release":"unknown"}` — `release: unknown` é o esperado (sem imagem Docker com `GIT_SHA` baked, per Runbook Seção 5).

## 12. Backend readiness

`GET /ready` → `{"status":"ready"}`.

## 13. Frontend

`next dev` (Turbopack) — `Ready in 9.5s`, `http://localhost:3000/entrar` retorna `200`.

## 14. Autenticação

**PASS**, com um achado de procedimento real no meio do caminho (Finding F5): a primeira tentativa de login resultou em uma sessão de browser autenticada como `organization_id=2` (usuário demo/viewer, "Demo Organization"), não `organization_id=1` (Administrator, "Organização Principal") como pretendido — confirmado via log do backend (`Listed 0 analyses organization_id=2`). Diagnosticado como erro de sessão/digitação, não defeito de produto — resolvido com logout + login correto, confirmado por log subsequente mostrando `organization_id=1` corretamente.

## 15. Matriz da V1 Sanity Journey

| Capability | Resultado | Nota |
|---|---|---|
| Dashboard | PASS | KPIs reais do Enterprise Domain |
| Priorização | PASS | 6 projetos do seed, decisões corretas |
| Projetos | PASS | 6 de 6, saúde/riscos/ações batendo com o seed |
| Program Management | PASS | 4 programas, Enterprise Domain |
| Project Delivery | PASS | 7 projetos, Enterprise Domain (confirma ao vivo a colisão de nomes já documentada em D-208 — "Implantação SAP S/4HANA" com acento é entidade diferente de "Implantacao SAP S/4HANA" sem acento) |
| Ações | PASS | 8 itens, ação recorrente em 3 projetos |
| Decisões | PASS | fila real (status + risco) |
| Aprendizados | PASS | risco recorrente em 3 projetos + ação recorrente em 3 projetos — confirma exatamente o gatilho `MIN_OCCURRENCES=3` desenhado em D-208 |
| Documentos | PASS | documento do seed indexado |
| Mission Control | PASS | Decision Log D-208...D-201 renderizando corretamente |
| Administração | PASS | 2 usuários reais listados (Administrator + um usuário criado pelo próprio Founder em exploração anterior) |
| Logout | PASS | mecanismo funciona; achado de UX real (Finding F6 — botão não fica fixo na tela) |

## 16. Documents

Upload manual pela UI testado com `demo/synthetic-document.md` — indexado com sucesso (3 chunks), somando-se ao documento já indexado pelo seed. **Nenhum dado corporativo real foi ingerido** — uma primeira tentativa selecionou um arquivo `.xlsx` real do Founder por engano, mas foi corretamente **rejeitada pela validação** (`File must be UTF-8 encoded text/markdown`) antes de qualquer processamento — confirma a validação de formato funcionando como esperado.

## 17. Limitações de IA

**Achado real, diferente do documentado (Finding F7):** sem `ANTHROPIC_API_KEY`, o Decision Support **não retorna o `502` fail-closed documentado** (D-205, User Session Protocol Bloco C) — retorna, em vez disso, **"Base insuficiente para responder a esta pergunta com o escopo selecionado"**, tanto em escopo Projeto (qualquer um dos 7 projetos do Enterprise Domain, todos sem `analysis_records` associados) quanto em escopo Organização (que deveria agregar toda a evidência, incluindo as análises do seed). A chamada de IA real nunca chega a ser tentada. Root cause não totalmente investigada — provavelmente ligada à mesma colisão de nomes de projeto (D-208), mas o escopo Organização também falhar sugere algo adicional não identificado. `AI CONTENT QUALITY` permanece `NOT VALIDATED` — Gates B/C inalterados. Registrado para correção da documentação da sessão em missão futura (não corrigido aqui).

## 18. Backup checkpoint

**PASS**, com contorno registrado (Finding F8): `src/database/backup.py` falhou com `pg_dump binary not found on PATH` (ferramentas cliente do PostgreSQL ausentes no Windows; o instalador oficial do EDB usado pelo Founder não permitiu selecionar "somente Command Line Tools" sem o servidor completo). Contornado executando `pg_dump`/`pg_restore --list` **dentro do container Docker** (`docker compose exec -T database pg_dump ...`), redirecionando a saída para `demo/backups/local-v1-backup.dump` no Windows. Resultado: arquivo de **88865 bytes**, validado via `pg_restore --list` — **237 TOC entries**, extensão `vector` presente, tabelas reais confirmadas (`alembic_version`, `analysis_records`, etc.), `Dumped from database version: 16.15`. Este é o recovery point anterior à sessão humana. **Nenhum DR Drill executado** — fora do escopo desta missão.

## 19. Intervenções manuais necessárias

1. Instalação de WSL2 (`wsl --install`) e Docker Desktop (nenhum dos dois estava presente no início).
2. Resolução do conflito de porta 5432 com o PostgreSQL nativo (Finding F1) — porta 5433 usada em todo o restante da validação.
3. Contorno do bug de auto-upgrade do `pip` em `scripts/prepare-env.sh` no Windows (Finding F3).
4. Contorno do bug de detecção de venv em `demo/start-demo.sh` no Windows (Finding F4) — backend/frontend iniciados manualmente com caminhos explícitos do `.venv`/`node_modules`.
5. Correção de sessão de login (Finding F5) — logout + login novamente com a identidade correta.
6. Rolagem da página inteira para acessar o botão "Sair" (Finding F6).
7. Backup executado via `docker compose exec` em vez do wrapper Python nativo (Finding F8), por ausência de `pg_dump` local.

## 20. Findings encontrados

| ID | Observed | Classification | Severity | Status |
|---|---|---|---|---|
| F1 | Porta 5432 já ocupada por PostgreSQL nativo (`postgresql-x64-18`) do Founder | ENVIRONMENT | MEDIUM | Contornado (porta 5433), não corrigido no repositório |
| F2 | `scripts/rc2-db.sh create` (Runbook 3.4) exige `psql` local desnecessariamente — o próprio script recomenda pulá-lo com Docker | DOCUMENTATION | LOW | Não corrigido — divergência real entre Runbook e comentário do script |
| F3 | `scripts/prepare-env.sh` chama `pip install --upgrade pip` diretamente; falha no Windows (não pode sobrescrever o próprio executável em uso) | PRODUCT | MEDIUM | Não corrigido — contornado com `python -m pip install --upgrade pip` manual |
| F4 | `demo/start-demo.sh` só detecta `.venv/bin` (Linux/Mac), nunca `.venv/Scripts` (Windows) — usa Python errado (Microsoft Store) em vez do `.venv` do projeto | **PRODUCT — Windows venv detection defect in demo/start-demo.sh** | MEDIUM | **Não resolvido.** Contornado com comandos explícitos (`.venv/Scripts/python -m uvicorn`, `web/node_modules/.bin/next`) |
| F5 | Sessão de login inicial resolveu para a organização/usuário errados (viewer/Demo Organization em vez de admin/Organização Principal) | PROCEDURE/TEST | LOW | Resolvido com logout + login correto — não é defeito de produto |
| F6 | Botão "Sair" não fica fixo na tela — só visível rolando a página inteira até o final | PRODUCT (UX) | LOW-MEDIUM | Não corrigido — sugestão do Founder registrada: manter fixo como o resto do menu |
| F7 | Decision Support retorna "Base insuficiente" em vez do `502` fail-closed documentado, em qualquer escopo (Projeto ou Organização) | DATASET / PRODUCT (não totalmente investigado) | MEDIUM | Não corrigido — muda a experiência real da Fronteira de IA na sessão humana |
| F8 | `pg_dump`/`psql` client tools ausentes no Windows; instalador EDB não permite seleção granular sem instalar o servidor | ENVIRONMENT | MEDIUM | Contornado via `docker compose exec`, não corrigido |
| F9 | `docs/operations/LOCAL-V1-WINDOWS-RUNBOOK.md` Seção 5 registra commit SHA desatualizado (`3ff0dae`, já defasado por 2 commits) | DOCUMENTATION | LOW | Não corrigido nesta missão (fora do escopo de governança autorizado, Seção 19 do mandato) |

## 21. Limitações remanescentes

- `AI CONTENT QUALITY` = `NOT VALIDATED` (Gates B/C inalterados).
- Fronteira de IA não se comporta como documentado no User Session Protocol (Finding F7) — a Seção 2 desse documento precisa ser corrigida numa missão futura autorizada, para não confundir o facilitador da sessão humana.
- `demo/start-demo.sh` continua não funcional no Windows tal como está (Finding F4) — qualquer execução futura precisará repetir o contorno manual, a menos que uma correção seja autorizada.
- `pg_dump`/`psql` locais continuam ausentes nesta máquina — qualquer backup futuro via `src/database/backup.py` precisará do mesmo contorno via Docker, a menos que as ferramentas cliente sejam instaladas.

## 22. Preservação arquitetural

**Confirmada — nenhuma alteração de código nesta missão.** Todos os 9 findings acima foram contornados operacionalmente (comandos, variáveis de ambiente, arquivos de override externos ao repositório) ou apenas registrados, nunca corrigidos no código-fonte. Nenhuma alteração em RBAC, Tenant Isolation, Authentication, Session, Enterprise Domain, Capability, Executive Intelligence. Nenhum fallback de IA criado. Nenhum staging, DR Drill, novo Epic, ou dado corporativo real.

## 23. GO/NO-GO

- **LOCAL WINDOWS ENVIRONMENT = `VALIDATED`.**

Justificativa: todos os gates obrigatórios (Seção 16 do mandato) passaram — PostgreSQL iniciou (após resolver F1), pgvector confirmado disponível, migrations atingiram `0021`, backend/frontend iniciaram e responderam `/health`/`/ready` corretamente (após contornar F4), autenticação funcionou corretamente (após corrigir F5), nenhuma violação de tenant isolation ou RBAC foi observada (pelo contrário, ambos foram comprovados corretos), o dataset obrigatório carregou integralmente, e nenhum erro exigiu alteração de arquitetura. Nenhum `FAIL` foi suavizado para `WARNING` para obter este veredito — os 9 findings reais estão listados na Seção 20 com sua severidade real.

**Nota importante para o Founder antes da sessão humana:** os Findings F4 (script de inicialização quebrado no Windows), F6 (botão Sair mal posicionado) e F7 (Fronteira de IA mostra mensagem diferente da documentada) devem ser considerados antes de conduzir a sessão — especialmente F7, que muda o que o facilitador precisa explicar ao usuário no Bloco C do roteiro.

- **GO FOR LOCAL V1 HUMAN USER SESSION**, condicionado a:
  1. Repetir os contornos manuais de F1/F3/F4/F8 documentados aqui (ou obter autorização para corrigi-los em código antes da sessão).
  2. Atualizar verbalmente ou por escrito a explicação da Fronteira de IA (F7) para o facilitador, já que a mensagem real difere de "Backend respondeu 502".
  3. Estar ciente de F6 (Sair no final da página) para não gerar confusão durante a sessão.

W7-1 permanece `OPEN`. External Gates A/B/C/D inalterados. Nenhuma Production AI Validation executada. Enterprise Readiness não reivindicada.
