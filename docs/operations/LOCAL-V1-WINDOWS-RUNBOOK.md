# Local V1 Windows Runbook

**Autorização:** "Founder Decision — Local V1 Windows Pilot Preparation", em resposta ao Local V1 Validation Rehearsal (D-205, APPROVED, `LOCAL V1 USER SESSION = GO`). Objetivo: preparar e validar a máquina Windows física do Founder para a primeira sessão humana da STRATECH V1 em localhost.

**IMPORTANTE — fronteira de evidência, não negociável:** este documento foi produzido por inspeção mecânica do repositório e verificado end-to-end em Linux (Local V1 Validation Rehearsal, D-205) — **nunca executado na máquina Windows física real do Founder**, à qual esta sessão não tem acesso. O status máximo permitido antes da execução física é **`WINDOWS PROCEDURE READY FOR EXECUTION`** — nunca "Windows machine validated". Cada passo abaixo tem um resultado esperado explícito e uma ação de falha, precisamente para que a primeira execução real na máquina do Founder seja a validação.

W7-1 = `OPEN`. Gates A/B/C = `NOT AVAILABLE`. Gate D = `NOT APPROVED`. Production AI Validation = `NOT EXECUTED`. Enterprise Readiness = `NOT CLAIMED`. Nada disso é alterado por este documento.

---

## 1. Windows Preflight

| # | Requisito | Check | Resultado esperado | Ação em caso de falha |
|---|---|---|---|---|
| 1 | Windows version | Nenhum requisito de versão do próprio produto (nenhuma dependência nativa Windows-específica em `src`/`web`) — a única restrição real vem do Docker Desktop (recomendado, ver item 3): Windows 10 64-bit versão 2004+ (build 19041+) ou Windows 11, com suporte a WSL2 | — | Atualizar o Windows, ou usar PostgreSQL nativo (item 9) em vez de Docker |
| 2 | WSL2 | `wsl --status` (PowerShell) | WSL2 instalado e definido como versão padrão | Não é estritamente exigido pelos scripts do repositório (Git Bash roda os `.sh` diretamente, confirmado em `scripts/prepare-env.sh`) — só necessário se Docker Desktop for usado. Instalar via `wsl --install` se optar por Docker |
| 3 | Docker Desktop | `docker --version` (Git Bash ou PowerShell) | Versão instalada e respondendo | Instalar Docker Desktop (recomendado para PostgreSQL+pgvector — ver Seção 6). Se indisponível, usar PostgreSQL nativo (item 9) |
| 4 | Docker Engine rodando | `docker ps` | Retorna sem erro (mesmo que lista vazia) | Abrir o app Docker Desktop, aguardar o ícone indicar "Running" |
| 5 | Docker Compose | `docker compose version` | Versão exibida | Vem embutido no Docker Desktop moderno — reinstalar se ausente |
| 6 | Git | `git --version` | Versão exibida | Instalar Git for Windows (inclui Git Bash) |
| 7 | Git Bash | Abrir "Git Bash" no menu Iniciar | Terminal bash funcional | Reinstalar Git for Windows, garantindo a opção "Git Bash" marcada |
| 8 | `curl` dentro do Git Bash | `curl --version` (dentro do Git Bash) | Versão exibida | Git for Windows recente (2.28+) já inclui `curl.exe` — se ausente, atualizar o Git for Windows (usado pelos health checks de `demo/start-demo.sh`) |
| 9 | Python 3.11+ | `python --version` (Git Bash) | `Python 3.11.x` ou superior (verificado por `scripts/prepare-env.sh`) | Instalar Python 3.11+ do python.org, marcando "Add to PATH" |
| 10 | Node.js 22+ | `node --version` (Git Bash) | `v22.x` ou superior (verificado por `scripts/prepare-env.sh`) | Instalar Node.js 22 LTS do nodejs.org |
| 11 | npm | `npm --version` (Git Bash) | Versão exibida (vem com o Node) | Reinstalar Node.js |
| 12 | `make` | `make --version` (Git Bash) | **Não crítico** — Git Bash (MSYS2) não inclui `make` por padrão; este runbook usa os scripts `.sh` diretamente (`bash scripts/...`), nunca `make`, exatamente pela mesma razão que `README.md` já documenta ("no native `make`") | Nenhuma — não é necessário para este runbook |
| 13 | Portas 8000/3000/5432 livres | PowerShell: `Get-NetTCPConnection -LocalPort 8000,3000,5432 -ErrorAction SilentlyContinue` | Nenhum resultado (portas livres) | Encerrar o processo ocupando a porta, ou ajustar `BACKEND_PORT`/`FRONTEND_PORT` em `demo/.env` |
| 14 | RAM | MINIMUM 8 GB · RECOMMENDED 16 GB (Docker Desktop reserva memória própria de VM no Windows) | — | — |
| 15 | CPU | MINIMUM 2 núcleos · RECOMMENDED 4+ | — | — |
| 16 | Espaço em disco | MINIMUM 10 GB livres · RECOMMENDED 20 GB+ | — | Liberar espaço antes de prosseguir |
| 17 | Conectividade | Necessária apenas para o clone inicial e instalação de dependências — nenhuma chamada externa depois disso em Level 1 (mock) | — | — |
| 18 | Browser | Chrome/Chromium (único browser do Controlled Pilot Browser Baseline, D-199) | Versão estável instalada | Instalar Chrome |

**Nenhum requisito inventado além do que os scripts do repositório e o Docker Desktop exigem.**

---

## 2. Caminho oficial para Windows (determinado mecanicamente, não presumido)

Avaliados os 4 caminhos possíveis contra o repositório real:

- **B. Scripts `.bat` existentes (`setup.bat`/`start.bat`/`stop.bat`) — DESCARTADO.** Confirmado por leitura direta (D-206): esse fluxo nunca executa `alembic upgrade head`, usa `Base.metadata.create_all()` contra SQLite, e portanto nunca cria o Enterprise Domain, RBAC, ou o Knowledge Platform. É a fatia "V1 RC-1", muito anterior ao produto atual — não válido para esta missão, apesar do nome compartilhado.
- **A. Git Bash + os scripts `.sh` existentes, diretamente (sem `make`) — ESCOLHIDO para backend/frontend.** `scripts/prepare-env.sh` e `demo/start-demo.sh` já são portáveis (bash puro, sem dependência de utilitário GNU-específico ausente no Git Bash/MSYS2) e já tratam explicitamente o layout Windows do venv (`scripts/prepare-env.sh`: `.venv/Scripts/activate` vs `.venv/bin/activate`) e caminhos relativos vs. absolutos entre bash/Python/Node no Windows (comentário em `demo/.env.example` sobre `MOCK_LLM_RESPONSE_FILE`). Comprovado funcionando de ponta a ponta no rehearsal (D-205), em Linux — a portabilidade dos scripts para Git Bash é uma inferência razoável baseada nesse desenho explícito, **não uma execução real em Windows**.
- **C. Docker Compose — ESCOLHIDO exclusivamente para o serviço `database` (PostgreSQL+pgvector).** Evita a complexidade real de instalar `pgvector` nativamente no Windows (a distribuição oficial do instalador PostgreSQL para Windows não inclui `pgvector` pré-compilado). `docker-compose.yml` já usa exatamente a imagem `pgvector/pgvector:pg16` para isso.
- **D. Combinação — CAMINHO FINAL RECOMENDADO:** Docker Desktop exclusivamente para PostgreSQL (item C), backend/frontend nativos via Git Bash + Python/Node (item A) — não o `docker compose up` completo dos 3 serviços, para manter o loop de desenvolvimento rápido e os logs diretamente visíveis, exatamente como o rehearsal já validou (D-205) com backend/frontend nativos.

**Nenhum instalador novo criado nesta missão** — os caminhos A e C já existem e cobrem o necessário.

---

## 3. Windows Clean Install Runbook (copy/paste, Git Bash)

Todos os comandos abaixo rodam dentro do **Git Bash**, a partir da raiz do repositório, salvo indicação contrária.

### 3.1 Clone e branch

```bash
git clone <URL-do-repositório>
cd ai-pmo-copilot
git checkout claude/stratech-permanent-principles-yjnm74
git status   # esperado: "nothing to commit, working tree clean"
```
**Resultado esperado:** clone completo, branch correta, árvore limpa. **Erro:** `git status` mostrando arquivos modificados/untracked indica um checkout corrompido — refazer o clone.

### 3.2 PostgreSQL + pgvector via Docker Desktop

```bash
docker compose up -d database
```
**Resultado esperado:** container `database` sobe e fica `healthy` em poucos segundos (health check já definido em `docker-compose.yml`).
**Verificar:** `docker compose ps` — coluna `STATUS` deve mostrar `healthy`.
**Erro:** se a porta 5432 já estiver em uso, parar o processo conflitante ou ajustar a porta publicada.

### 3.3 Dependências (Python + Node)

```bash
bash scripts/prepare-env.sh
```
**Resultado esperado:** `== Preparation complete ==`, sem `ERROR` no meio.
**Erro:** mensagens `ERROR: python/node not found` — instalar per Seção 1 (itens 9/10) e reabrir o Git Bash antes de tentar de novo.

### 3.4 Banco (role/database, contra o Postgres do Docker)

```bash
export PGHOST=localhost
export PGPORT=5432
export PGPASSWORD=aipmo
bash scripts/rc2-db.sh create
```
**Resultado esperado:** `Database 'aipmo' ready (role 'aipmo').`
**Erro:** `psql: command not found` — o Docker Desktop não inclui `psql` no PATH do Windows; instalar apenas o cliente `psql` (não o servidor completo) via o instalador oficial do PostgreSQL, ou rodar o comando equivalente dentro do container: `docker compose exec database psql -U aipmo -c "SELECT 1"` para confirmar conectividade básica sem depender de `psql` local.

### 3.5 Migrations

**Correção documental (Local Windows Revalidation, D-211/D-212):** desde o F4 (Local V1 Pilot Hardening), `demo/start-demo.sh` (Seção 3.6) já aplica `alembic upgrade head` automaticamente e sem exigir o contorno manual usado em D-209 — o script resolve `PYTHON_BIN` explicitamente (`.venv/bin/python3` no Linux/macOS, `.venv/Scripts/python.exe` no Windows) antes de rodar a migration. Isso não é comportamento novo do F4 em si (o script sempre aplicou migrations por conta própria, de forma idempotente); o F4 corrigiu apenas qual interpretador é usado para isso. **Não execute uma migration manual separada aqui** — rodá-la antes da Seção 3.6 não quebra nada (`alembic upgrade head` é idempotente), mas mascara a prova de que a Seção 3.6, sozinha, resolve `PYTHON_BIN` e aplica as migrations corretamente no Windows.

**Verificação explícita (rodar depois da Seção 3.6, nunca confiar apenas no exit code do script):**
```bash
.venv/Scripts/python -m alembic current
```
**Resultado esperado:** `0021 (head)`.
**Erro:** qualquer resultado diferente de `0021 (head)`, ou qualquer traceback — **STOP**, não prosseguir; diagnosticar antes de corrigir (per disciplina já estabelecida nesta missão institucional).

### 3.6 Backend + Frontend (Demo Mode)

```bash
export DATABASE_URL="postgresql://aipmo:aipmo@localhost:5432/aipmo"
bash demo/start-demo.sh
```
**Resultado esperado:** as 2 mensagens `is up` (backend e frontend), URLs finais impressas.
**Erro:** se travar em "Waiting for backend health check" além de ~30s, checar `demo/logs/backend.log` para o erro real (não presumir — diagnosticar).

### 3.7 Health / Readiness

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
```
**Resultado esperado:** `{"status":"healthy",...}` e `{"status":"ready"}`.

### 3.8 Seed do Pilot Dataset

```bash
python3 demo/seed_demo_data.py
```
**Resultado esperado:** `All calls produced structured output.` — popula Projetos/Ações/Decisões/Aprendizados/Documents (Founder Decision, "Local V1 Pilot Dataset Completion"). Autentica como o Administrator bootstrapado (`STRATECH_ADMIN_EMAIL`/`STRATECH_ADMIN_PASSWORD`, já preenchidos em `demo/.env.example`) — o usuário demo (`WORKSPACE_PASSWORD`) é deliberadamente somente-leitura e não pode executar este passo.
**Erro:** `STRATECH_ADMIN_EMAIL / STRATECH_ADMIN_PASSWORD are not set` — confirmar que `demo/.env` tem essas 2 variáveis (herdadas de `demo/.env.example`); `HTTP 400`/`401` no login — confirmar que o backend (passo 3.6) terminou de inicializar antes de rodar este passo. Ver `docs/product/governance/LOCAL-V1-PILOT-DATASET-EXECUTIVE-EVIDENCE.md` para o diagnóstico completo.

### 3.9 Login

Duas organizações reais, per o passo 3.8:
- **Login recomendado (jornada completa, dataset populado):** organização `organizacao-principal`, e-mail = valor de `STRATECH_ADMIN_EMAIL`, senha = valor de `STRATECH_ADMIN_PASSWORD` (`demo/.env`).
- **Login somente-leitura (ilustra RBAC restrito, Projetos/Ações/Decisões/Aprendizados/Documents vazios nesta organização):** organização `demo-organization`, e-mail `demo@stratech.local`, senha = valor de `WORKSPACE_PASSWORD` (`demo/.env`).

Abrir `http://localhost:3000/entrar` no browser e usar um dos dois.
**Resultado esperado:** redirecionamento a `/dashboard`.

---

## 4. Environment Contract Local (Level 1 — Local Product Validation, sem Anthropic/Voyage)

| Variável | Classificação | Valor para esta validação | Observação |
|---|---|---|---|
| `ENVIRONMENT` | REQUIRED | `dev` | Nunca `staging`/`production` nesta missão — o Configuration Contract fail-fast exigiria credenciais reais |
| `DATABASE_URL` | REQUIRED | `postgresql://aipmo:aipmo@localhost:5432/aipmo` | PostgreSQL real, nunca SQLite (Seção 1 do achado de D-203/D-206) |
| `API_KEY` | REQUIRED | qualquer segredo local, ex. `local-pilot-secret-key` | Nunca um valor de produção real |
| `LLM_PROVIDER` | REQUIRED | `mock` | `anthropic` só quando o Gate C for resolvido — fora de escopo desta missão |
| `EMBEDDING_PROVIDER` | REQUIRED | `mock` | `voyage` só quando o Gate B for resolvido — fora de escopo desta missão |
| `WORKSPACE_PASSWORD` | REQUIRED | qualquer valor não vazio | Consumido pelo backend para criar o usuário demo real, somente-leitura (achado de D-205) |
| `STRATECH_ADMIN_EMAIL` / `STRATECH_ADMIN_PASSWORD` | REQUIRED | qualquer par não vazio, ex. `admin@stratech.local` / valor local | Consumido pelo backend para criar o Administrator real em "Organização Principal" — a única identidade local com `intelligence.write`/`knowledge.write`; sem isso, `demo/seed_demo_data.py` (passo 3.8) falha (Founder Decision, "Local V1 Pilot Dataset Completion") |
| `SESSION_SECRET` | REQUIRED | gerado automaticamente por `demo/start-demo.sh` na primeira execução | Nunca reutilizar entre ambientes |
| `ANTHROPIC_API_KEY` | NOT USED WITHOUT AI CREDENTIALS | deixar vazio | Só lido se `LLM_PROVIDER=anthropic` |
| `VOYAGE_API_KEY` | NOT USED WITHOUT AI CREDENTIALS | deixar vazio | Só lido se `EMBEDDING_PROVIDER=voyage` |
| `MODEL_NAME` | OPTIONAL | deixar vazio | Só relevante com `LLM_PROVIDER=anthropic` |
| `CORS_ALLOWED_ORIGINS` | OPTIONAL | deixar vazio | Irrelevante para acesso via `localhost` direto |
| `RATE_LIMIT_MAX_REQUESTS`/`RATE_LIMIT_WINDOW_SECONDS` | OPTIONAL | deixar vazio (defaults 60/60) | — |
| `DISABLE_WORKSPACE_SESSION_GATE` | NÃO DEFINIR | — | Proibido fora de dev pelo Configuration Contract (F2, W7-4) — e nem necessário em dev |

**Nenhum valor secreto real listado aqui.**

---

## 5. Release Baseline (para a sessão humana)

| Item | Valor |
|---|---|
| Branch | `claude/stratech-permanent-principles-yjnm74` |
| Commit SHA no momento da produção deste runbook | `3ff0dae` (confirmar `git rev-parse HEAD` no momento real da preparação — pode ter avançado) |
| `git status` | Deve estar limpo antes de iniciar a sessão — `git status --short` sem saída |
| Migration head | `0021` |
| Release identifier | `GET /health` retornará `"release":"unknown"` neste caminho (não é uma imagem Docker com `GIT_SHA` baked) — identidade real da sessão é o par branch+commit acima, registrado manualmente no início da sessão |
| Timestamp da preparação | Registrar a data/hora real em que a Seção 3 foi executada com sucesso na máquina do Founder |

**Nenhuma mudança de código deve ocorrer durante a sessão humana** — se um defeito real for encontrado, `STOP`, diagnosticar, registrar, nunca corrigir ao vivo durante a sessão.

---

## 6. Pre-Session Reset (baseado no achado real de D-205 sobre cache `.next`)

Executar **apenas se** uma sessão anterior de `next dev` rodou nesta mesma máquina/checkout (o achado de D-205 foi especificamente sobre cache `.next` compartilhado entre processos de portas diferentes ao longo de uma mesma sessão longa):

```bash
bash demo/stop-demo.sh
rm -rf web/.next
```

**Não apagar `.venv`, `web/node_modules`, ou qualquer dado do banco** — apenas o cache de build do Next.js. Depois, repetir os passos 3.6-3.9 (o passo 3.8, seed, é idempotente per `docs/product/governance/LOCAL-V1-PILOT-DATASET-EXECUTIVE-EVIDENCE.md` — seguro repetir). Se nenhuma sessão `next dev` anterior rodou nesta máquina, este passo é desnecessário (não presumir a necessidade sem o sintoma real: erros `404` inesperados em rotas que deveriam existir).

---

## 7. Pre-Flight Automation Assessment

Os checks necessários **já são executáveis pelos scripts existentes** — reutilizados integralmente nas Seções 1 e 3, nenhuma ferramenta nova necessária:

- `scripts/prepare-env.sh` já valida Python/Node.
- `make health`-equivalente já existe como `curl http://localhost:8000/health` (usado diretamente aqui já que `make` não é assumido no Windows).
- `demo/start-demo.sh` já espera e confirma health/readiness antes de retornar.

**Nenhum script novo proposto.** Um único script Windows/local adicional (ex. um `.sh` consolidando a Seção 9 do `LOCAL-V1-USER-SESSION-PROTOCOL.md`, o Session-Day Checklist, em comandos executáveis) **poderia** reduzir erro humano no dia da sessão, mas não é criado nesta missão — per mandato explícito ("propor, mas NÃO implementar automaticamente"). Fica proposto como um possível próximo passo, condicionado a nova autorização.

---

## 8. Status

**`WINDOWS PROCEDURE READY FOR EXECUTION`** — não "Windows machine validated". Este runbook nunca foi executado na máquina física real do Founder; a primeira execução real na Seção 3, na máquina Windows, é a validação.
