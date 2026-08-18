# Local V1 Pilot Hardening Review

**Autorização:** "Founder Decision — Local V1 Pilot Hardening Review", em resposta à ratificação de D-209 (`LOCAL WINDOWS ENVIRONMENT = VALIDATED`). Missão exclusivamente de **diagnóstico e classificação** dos 9 findings reais encontrados na validação física Windows — **nenhuma implementação autorizada**. A sessão humana permanece **NÃO autorizada** até uma Founder Decision futura.

W7-1 permanece `OPEN`. Gates A/B/C = `NOT AVAILABLE`, Gate D = `NOT APPROVED`. Nenhuma alteração de arquitetura, RBAC, Tenant Isolation, Advisors, ExecutiveOrchestrator, infraestrutura. Nenhum uso de Anthropic/Voyage real. Nenhum staging, DR Drill, novo Epic, ou sessão humana iniciados por este documento.

---

## 1. Revalidação — os 9 findings

### F1 — PostgreSQL nativo ocupando a porta 5432

- **Descrição:** um PostgreSQL 18 nativo (`postgresql-x64-18`), instalado deliberadamente pelo Founder para outro uso, já ocupava a porta 5432 quando o Docker tentou publicar o container do projeto na mesma porta.
- **Classificação atual:** `ENVIRONMENT`.
- **Severidade:** MEDIUM.
- **Esperado:** `docker compose up -d database` publica 5432 sem conflito.
- **Observado:** porta já ocupada; resolvido publicando o container também em 5433 (arquivo de override externo ao repositório, não commitado).
- **Reprodução:** qualquer máquina Windows com um PostgreSQL nativo pré-instalado e rodando.
- **Causa raiz:** ambiental, não uma falha do produto — coexistência de dois PostgreSQL na mesma máquina, escolha legítima do Founder.
- **Impacto na sessão humana:** nenhum, se o Runbook orientar a checagem de porta antes da Seção 6 (Postgres).
- **Impacto em produção:** nenhum — cenário exclusivamente local/dev.
- **Workaround existente:** comprovado e funcional (porta 5433).
- **Recomendação:** manter como limitação ambiental. O Runbook (Preflight item 13) já pede checar a porta 5432 livre, mas a ação de falha é genérica ("encerrar o processo ou ajustar a porta") — **SHOULD FIX**: tornar essa orientação explícita para o cenário real observado (checar especificamente um serviço PostgreSQL nativo concorrente, com o comando `Get-Process -Id (Get-NetTCPConnection -LocalPort 5432 -State Listen).OwningProcess`). É uma correção de **documentação**, não de código.

### F2 — `scripts/rc2-db.sh create` desnecessário no caminho Docker

- **Descrição:** o Runbook (Seção 3.4) manda rodar `bash scripts/rc2-db.sh create`, mas o próprio script diz, no comentário de cabeçalho: *"Using the bundled docker-compose Postgres instead? Skip this script -- the container creates POSTGRES_DB/POSTGRES_USER on first boot."*
- **Classificação atual:** `DOCUMENTATION`.
- **Severidade:** LOW.
- **Esperado (Runbook):** rodar o script.
- **Observado (código):** o script recomenda pular esse passo inteiro no caminho Docker.
- **Causa raiz comprovada:** divergência real entre o texto do Runbook e o comentário do próprio script — confirmado por leitura direta.
- **Impacto na sessão humana:** nenhum funcional (o passo, mesmo desnecessário, não quebra nada quando roda com sucesso) — só desperdiça tempo instalando `psql` sem necessidade.
- **Impacto em produção:** nenhum.
- **Workaround existente:** pular o passo e confirmar via `docker compose exec database psql ...` (já comprovado).
- **Recomendação:** **DOCUMENTATION UPDATE** — reescrever a Seção 3.4 do Runbook para declarar explicitamente que esse passo é dispensável no caminho Docker (Caminho D já escolhido), citando o próprio comentário do script como fonte.

### F3 — `pip install --upgrade pip` falha no Windows

- **Descrição:** `scripts/prepare-env.sh` chama `pip install --quiet --upgrade pip` diretamente; no Windows, o pip não consegue sobrescrever seu próprio executável em execução.
- **Classificação atual:** `PRODUCT`.
- **Severidade:** MEDIUM.
- **Esperado:** pip se atualiza silenciosamente.
- **Observado:** `ERROR: To modify pip, please run the following command: ...python.exe -m pip install --quiet --upgrade pip` — o script (`set -euo pipefail`) aborta.
- **Causa raiz comprovada (leitura direta, `scripts/prepare-env.sh` linha 62):** o script invoca `pip` como binário direto, não `python -m pip` — limitação de bloqueio de arquivo específica do Windows, não reproduzida em Linux/Mac.
- **Impacto na sessão humana:** bloqueia a preparação do ambiente até ser contornado manualmente.
- **Impacto em produção:** nenhum (script de preparação local, nunca roda em produção).
- **Workaround existente:** `python -m pip install --upgrade pip` manual antes de re-rodar o script.
- **Recomendação:** **SHOULD FIX BEFORE PILOT** — correção trivial e de baixíssimo risco: trocar a linha 62 de `pip install --quiet --upgrade pip` para `"$PYTHON_BIN" -m pip install --quiet --upgrade pip` (reutilizando a variável `PYTHON_BIN` já definida na linha 15 do mesmo script). Funciona identicamente em Linux/Mac/Windows — `python -m pip` é a forma canônica recomendada pelo próprio projeto pip justamente por evitar esse problema em qualquer plataforma.

### F4 — Windows venv detection defect in `demo/start-demo.sh`

Ver Seção 2 (diagnóstico dedicado, conforme mandato).

### F5 — Sessão de login inicial incorreta

- **Descrição:** a primeira tentativa de login na sessão de validação resolveu para `organization_id=2` (usuário demo/viewer, "Demo Organization"), não `organization_id=1` (Administrator, "Organização Principal") como pretendido.
- **Classificação atual:** `PROCEDURE/TEST`.
- **Severidade:** LOW.
- **Esperado:** login com as credenciais do Administrator autentica como `organization_id=1`.
- **Observado:** confirmado via log do backend (`Listed 0 analyses organization_id=2`) que a sessão estava em `organization_id=2`.
- **Causa raiz:** não uma falha de produto — o mecanismo de login/sessão resolveu corretamente **as credenciais que foram de fato submetidas** (não há evidência de bug; o comportamento é determinístico e correto para qualquer input real). Mais provável: digitação com a organização/e-mail do usuário demo na primeira tentativa.
- **Impacto na sessão humana:** nenhum, se o Session-Day Checklist reforçar a conferência das credenciais antes do login.
- **Impacto em produção:** nenhum.
- **Workaround existente:** logout + login correto, confirmado funcional.
- **Recomendação:** **ACCEPTED FOR PILOT** — nenhuma correção necessária. Opcionalmente, **DOCUMENTATION UPDATE** de baixa prioridade: adicionar ao Session-Day Checklist um lembrete explícito de qual organização/e-mail usar.

### F6 — Logout UX (botão "Sair" não fixo)

Ver Seção 4 (diagnóstico dedicado, conforme mandato).

### F7 — Decision Support retorna "Base insuficiente"

Ver Seção 3 (diagnóstico dedicado, conforme mandato).

### F8 — `pg_dump`/`psql` ausentes no Windows

- **Descrição:** `src/database/backup.py` falhou com `pg_dump binary not found on PATH`; o instalador oficial do PostgreSQL (EDB) usado pelo Founder não permitiu selecionar "somente Command Line Tools" sem instalar o servidor completo (risco de recriar o conflito de porta do F1).
- **Classificação atual:** `ENVIRONMENT`.
- **Severidade:** MEDIUM.
- **Esperado:** `src/database/backup.py` produz um backup + metadata via `pg_dump` local.
- **Observado:** binário ausente; contornado com `docker compose exec -T database pg_dump ... > arquivo` — resultado real e validado (88865 bytes, 237 TOC entries, `pg_restore --list` íntegro).
- **Causa raiz:** ausência de ferramentas cliente do PostgreSQL no Windows, agravada pelo instalador EDB não oferecer instalação granular nesta tentativa.
- **Impacto na sessão humana:** nenhum — o objetivo funcional (ter um recovery point real antes da sessão) foi cumprido pelo contorno.
- **Impacto em produção:** nenhum — mecanismo de produção (`src/database/backup.py`) roda em ambientes Linux (staging/produção), onde `pg_dump` é uma dependência de sistema já garantida pelo próprio Dockerfile/imagem — este gap é exclusivamente do ambiente de desenvolvimento local Windows.
- **Workaround existente:** comprovado, funcional, produz um artefato de backup real e íntegro.
- **Avaliação per Seção 5 do mandato ("pg_dump via Docker pode ser solução operacional válida se não houver requisito real para instalação nativa"):** **sim, é válida** — não há requisito real de que o backup do piloto passe pelo wrapper Python; o objetivo funcional (recovery point) foi atingido integralmente pelo caminho via Docker.
- **Recomendação:** **ACCEPTED FOR PILOT**. Opcionalmente, **DOCUMENTATION UPDATE**: registrar o procedimento via `docker compose exec` como alternativa oficial no Runbook para máquinas Windows sem `pg_dump` local, evitando repetir o diagnóstico a cada preparação.

### F9 — SHA desatualizado no Runbook

- **Descrição:** `docs/operations/LOCAL-V1-WINDOWS-RUNBOOK.md` Seção 5 (Release Baseline) registra o commit `3ff0dae`, hoje defasado por 2 commits (`044829d`, `877946e`).
- **Classificação atual:** `DOCUMENTATION`.
- **Severidade:** LOW.
- **Impacto:** nenhum funcional — o próprio Runbook já instrui reconfirmar via `git rev-parse HEAD` no momento real.
- **Recomendação:** **DOCUMENTATION UPDATE**, baixa prioridade, sem urgência.

### Nota suplementar — versões Python/Node (não numerada como finding F1-F9, mas mandatada pela Seção 5)

Python `3.14.6`/`python3`=`3.13` (Microsoft Store) e Node `v24.18.0` estão acima do que o CI valida (3.11/22). **Avaliação empírica, não presumida:** `pip install -r requirements.txt` e `npm install` **completaram com sucesso** nessas versões durante a validação real — nenhuma falha de compatibilidade foi observada. **Downgrade para informativo — nenhuma ação necessária.** Continuam registradas no Preflight como WARNING apenas para visibilidade, não como um finding acionável.

---

## 2. F4 — Diagnóstico definitivo: Windows Startup

**Causa raiz mecanicamente confirmada** (leitura direta de `demo/start-demo.sh`, linhas 20-25):

```bash
# Prefer the project venv (uvicorn, alembic) regardless of whether the
# caller already activated it -- covers both direct invocation and
# `make dev`, which calls this script in its own subshell.
if [ -d "$ROOT_DIR/.venv/bin" ]; then
  PATH="$ROOT_DIR/.venv/bin:$PATH"
fi
```

Essa checagem só reconhece o layout POSIX (`.venv/bin/`). No Windows, o `venv` do Python cria `.venv/Scripts/`, não `.venv/bin/` — a condição é sempre falsa, o `PATH` nunca é ajustado, e as duas chamadas subsequentes do script resolvem para o que estiver no PATH do sistema (nesta máquina, o Python da Microsoft Store, sem nenhuma dependência do projeto instalada).

**Comparação com o mecanismo já correto no mesmo repositório** (`scripts/prepare-env.sh`, linhas 54-58, comprovadamente funcional durante toda a validação Windows):

```bash
if [ -f "$VENV_DIR/bin/activate" ]; then
  ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
  ACTIVATE_SCRIPT="$VENV_DIR/Scripts/activate"
```

`prepare-env.sh` já trata os dois layouts corretamente — `start-demo.sh` é o único lugar do repositório com essa lacuna.

**Segunda camada da causa raiz, não presumida — confirmada por inspeção dos 2 pontos de invocação real do script (`grep` direto):**

| Linha | Comando | Resolução no Windows após só adicionar `.venv/Scripts` ao PATH |
|---|---|---|
| 65 | `python3 -m alembic upgrade head` | **Ainda falharia.** `venv` no Windows cria `.venv/Scripts/python.exe`, nunca `.venv/Scripts/python3.exe` — o nome `python3` não existe nesse diretório por padrão. |
| 72 | `uvicorn src.main:app ...` | **Seria resolvido corretamente.** `pip install` cria `.venv/Scripts/uvicorn.exe` (console-script padrão), equivalente ao `.venv/bin/uvicorn` do Linux/Mac. |

Ou seja: **apenas adicionar `.venv/Scripts` ao `PATH` (replicando literalmente o padrão de `prepare-env.sh`) resolveria a chamada `uvicorn`, mas não a chamada `python3`** — uma correção incompleta se feita ingenuamente. A causa raiz completa tem 2 partes, não 1.

**Outros pontos do script que dependem implicitamente de layout Unix:** nenhum outro além dos 2 já listados — confirmado por `grep` completo do arquivo (`python3|uvicorn|alembic| npm |node_modules`). O `./node_modules/.bin/next` (linha 82) já usa caminho relativo explícito, não depende de PATH — não afetado.

**Achado suplementar, fora do escopo estrito do mandato (registrado para visibilidade, não avaliado a fundo):** `demo/stop-demo.sh` usa `lsof` como mecanismo de segurança para matar processos por porta — `lsof` normalmente não vem instalado no Git Bash/MSYS2. O caminho primário (matar por PID salvo em `.pid`) não depende disso, então não é bloqueante, mas pode silenciosamente não limpar processos órfãos numa porta ocupada no Windows.

### Menor delta proposto (não implementado)

Duas mudanças pequenas e aditivas, no mesmo arquivo, seguindo o padrão já comprovado de `prepare-env.sh`:

1. **Resolver um `PYTHON_BIN` explícito**, no lugar do `PATH`-prepend genérico, para a chamada de `alembic` (linha 65):
```bash
if [ -x "$ROOT_DIR/.venv/bin/python3" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python3"
elif [ -x "$ROOT_DIR/.venv/Scripts/python.exe" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/Scripts/python.exe"
else
  PYTHON_BIN="python3"
fi
```
   ...substituindo `python3 -m alembic upgrade head` por `"$PYTHON_BIN" -m alembic upgrade head`.

2. **Adicionar o ramo `.venv/Scripts` ao `PATH`-prepend existente** (resolve a chamada bare `uvicorn`):
```bash
if [ -d "$ROOT_DIR/.venv/bin" ]; then
  PATH="$ROOT_DIR/.venv/bin:$PATH"
elif [ -d "$ROOT_DIR/.venv/Scripts" ]; then
  PATH="$ROOT_DIR/.venv/Scripts:$PATH"
fi
```

**Por que isso não altera o comportamento Linux/macOS:** em qualquer sistema POSIX, `.venv/bin/python3` sempre existe quando o venv foi criado via `python3 -m venv` — o primeiro ramo de cada condicional é exatamente idêntico ao comportamento atual, byte a byte. Nenhum caminho novo é percorrido fora do Windows.

### Testes de regressão necessários (não implementados)

Não existe hoje nenhuma cobertura automatizada para `demo/start-demo.sh` (nem pytest, nem vitest, nem harness de shell script) — confirmado por busca no repositório. Proposta mínima, proporcional:

1. **Teste de shell isolado e determinístico** (novo arquivo pequeno, ex. `tests/shell/test_start_demo_venv_detection.sh`), que cria diretórios `.venv/bin/python3` e `.venv/Scripts/python.exe` sintéticos (fake, vazios, só para existir no filesystem) em dois cenários separados, extrai a lógica de resolução do `PYTHON_BIN`/`PATH` do script para uma função isolada testável, e afirma que cada cenário resolve para o caminho esperado. Não precisa rodar em CI imediatamente — pode rodar manualmente (`bash tests/shell/...`) até decisão de integração.
2. **Reexecução manual no Windows físico** (já necessária de qualquer forma antes do piloto): confirmar que `bash demo/start-demo.sh`, sem nenhum comando manual adicional, sobe backend + frontend corretamente na mesma máquina onde F4 foi observado.

**Classificação final: `PRODUCT — Windows venv detection defect in demo/start-demo.sh`. `MUST FIX BEFORE PILOT`** — confirmado, nenhuma evidência objetiva encontrada que justifique rebaixar. É o único caminho documentado de subir a aplicação no Windows (Runbook Seção 3.6); sem correção, toda preparação futura da máquina exige repetir os comandos manuais desta sessão, risco real de erro humano numa sessão com usuário externo.

---

## 3. F7 — Diagnóstico definitivo: Decision Support

**Rastreamento ponta a ponta, por leitura direta do código (não presumido):**

```
DecisionSupportPanel (UI)
  → POST /api/bff/decision-support (BFF -- só resolve identidade institucional, repassa)
    → POST /api/decision-support/ask (backend, src/api/routes/intelligence.py:1417)
      → ExecutiveOrchestrator.run() (src/services/executive_orchestrator/orchestrator.py)
        1. evaluate_selection_rule(signals) -- src/services/executive_orchestrator/selection_rule.py
        2. SE outcome.selected estiver vazio → retorna insufficient_basis(SELECTION_EMPTY) IMEDIATAMENTE, sem coletar evidência, sem chamar nenhum Advisor.
        3. SE houver Advisors selecionados → provision() coleta evidência por Advisor
        4. AdvisorFramework.run(): SE evidence estiver vazia → retorna no_evidence() SEM chamar advisor.advise() (o LLM nunca é invocado)
        5. SE toda evidência selecionada estiver vazia (any_had_evidence=False) → retorna insufficient_basis(COLLECTION_EMPTY)
        6. SÓ SE houver evidência real → advisor.advise() chama o LLM de fato
      → API mapeia result.is_insufficient_basis / result.insufficient_basis_reason para o JSON de resposta (intelligence.py:1497-1499)
    → UI (decision-support-panel.tsx:95-97): SE insufficient_basis for true → mostra sempre o MESMO texto genérico "Base insuficiente para responder a esta pergunta com o escopo selecionado.", independente do valor de insufficient_basis_reason (que o tipo já carrega, `web/lib/dashboard/types.ts:57`, mas o componente nunca lê).
```

**Achado decisivo, comprovado por inspeção do catálogo fixo de vocabulário** (`src/services/executive_orchestrator/catalog.py`, `VOCABULARY`):

```python
VOCABULARY = {
    "risk_advisor": {"risco", "riscos", "mitigação", "ameaça", "escalação"},
    "delivery_advisor": {"entrega", "status", "andamento", "progresso"},
    "portfolio_advisor": {"portfólio", "portfolio", "equilíbrio", "sobreposição"},
    "pmo_advisor": {"pmo", "processo de acompanhamento", "acompanhamento"},
    "executive_advisor": {"liderança", "atenção da liderança", "executivo"},
    "strategy_advisor": {"estratégia", "estratégico", "alinhamento", "objetivo declarado"},
    "document_advisor": {"documento", "documentos", "runbook"},
    "governance_advisor": {"governança", "conformidade", "política"},
}
```

A pergunta usada durante a validação física foi **"Quero fazer um teste com esta função"** — texto genérico de smoke test, sem nenhum termo desse vocabulário. `evaluate_selection_rule()` (`selection_rule.py:84-108`) é uma **função pura e determinística**: dado esse texto exato, ela produz `selected=()` (vazio) para **qualquer** escopo (Projeto, Portfólio ou Organização) — matematicamente comprovável por inspeção, sem precisar reexecutar na máquina física. Isso confirma que o motivo real observado quase certamente foi `SELECTION_EMPTY`, não `COLLECTION_EMPTY` — o Selection Rule rejeitou a pergunta **antes mesmo de tentar coletar evidência**, e portanto muito antes de qualquer chance de chegar ao LLM.

### Respostas às 10 perguntas do mandato

1. **O LLM chegou a ser chamado?** **Não.** `SELECTION_EMPTY` retorna na linha 78-81 do orchestrator, antes de qualquer `provision()`/`AdvisorFramework.run()`.
2. **Qual provider estava ativo?** Irrelevante para este caminho específico — `LLM_PROVIDER=mock` estava configurado, mas nunca foi consultado.
3. **Qual resultado interno foi produzido?** `ExecutiveIntelligenceResult.insufficient_basis(capability, trace, InsufficientBasisReason.SELECTION_EMPTY)`.
4. **Por que a API/UI retornou `insufficient_basis`?** Porque nenhum termo do vocabulário fixo dos 8 Advisors aparece na pergunta de teste usada — nenhum Advisor foi selecionado, para nenhum escopo testado.
5. **O comportamento é deliberado pelo contrato atual?** **Sim** — `evaluate_selection_rule()` é documentada exatamente para produzir esse resultado determinístico (Domain Blueprint §2.2, D-138).
6. **Existe erro sendo transformado em "Base insuficiente"?** **Não.** Não há exceção nem falha envolvida — é um retorno estrutural correto do fluxo normal, sem nenhum `try/except` mascarando nada.
7. **A UI está representando corretamente o estado do backend?** Parcialmente. Mostra corretamente que `insufficient_basis=true`, mas **descarta a informação de qual motivo** (`insufficient_basis_reason`, que a API já retorna) — sempre a mesma frase genérica, independente de `SELECTION_EMPTY` ou `COLLECTION_EMPTY`.
8. **O protocolo D-207/Session Protocol está desatualizado?** **Sim.** O Bloco C do `LOCAL-V1-USER-SESSION-PROTOCOL.md` presumia que o `502` fail-closed do `AdvisorFramework` (uma camada bem mais profunda, só alcançável com evidência real presente) seria o que a sessão observaria — não previu que uma pergunta de teste sem vocabulário de domínio nunca chegaria nem perto dessa camada.
9. **Há risco de o usuário interpretar "Base insuficiente" como ausência de dados quando o problema real é indisponibilidade de IA?** Neste caso concreto, **não** — o problema real observado foi realmente "nenhum termo reconhecido na pergunta", não indisponibilidade de IA. Mas a mensagem genérica de fato **não distingue** os dois cenários possíveis (falta de vocabulário vs. falta de evidência vs., mais adiante, falta de credencial de IA) — um ponto de clareza real, não uma falha crítica.
10. **O finding é `PRODUCT`, `DOCUMENTATION` ou ambos?** **Principalmente `DOCUMENTATION`** (o roteiro da sessão humana precisa de uma pergunta de teste com vocabulário de domínio real, ex. "Quais são os riscos deste projeto?", para efetivamente alcançar e demonstrar o comportamento fail-closed documentado) — com um **`PRODUCT` (UX) secundário e não-bloqueante**: a UI poderia usar `insufficient_basis_reason` para diferenciar a mensagem ("nenhum especialista relevante para esta pergunta" vs. "nenhuma evidência disponível para este escopo"), mas isso é uma melhoria de clareza, não uma correção obrigatória para o piloto.

**Não há mascaramento semântico de indisponibilidade de IA como insuficiência de evidência neste caso** — não elevado como finding de produto crítico, per a instrução condicional do mandato.

**Classificação final: `DOCUMENTATION` (principal) + `PRODUCT`/UX (secundário, opcional). `SHOULD FIX BEFORE PILOT`** — não pela gravidade técnica (nenhuma), mas porque, sem corrigir o roteiro da sessão com uma pergunta de teste real, o facilitador corre risco real de repetir a mesma confusão observada nesta validação, ao vivo, na frente do usuário piloto.

---

## 4. F6 — Diagnóstico: Logout UX

**Avaliação mecânica dos 3 breakpoints** (leitura direta de `web/components/shell/sidebar.tsx` + `web/components/shell/app-shell.tsx`):

| Breakpoint | Componente renderizado | Posicionamento do "Sair" | Resultado |
|---|---|---|---|
| mobile (`<768px`) | `<nav data-testid="bottom-nav">` | `className="fixed inset-x-0 bottom-0 ..."` — **fixo ao viewport** | **Não afetado.** Sempre visível, independente do scroll da página. |
| md (`768-1023px`) | `<div data-testid="sidebar-nav">` (mesma estrutura de `lg`, só `md:w-14`) | Sem `sticky`/`fixed` — segue o fluxo normal do documento | **Afetado** (mesma causa raiz de `lg`, ver abaixo — inferido por análise de código; não retestado fisicamente neste breakpoint específico) |
| lg (`>=1024px`) | `<div data-testid="sidebar-nav">` (`lg:w-[220px]`) | Idem `md` | **Confirmado afetado ao vivo** na validação física (D-209) |

**Causa raiz comprovada** (`web/components/shell/app-shell.tsx`):

```tsx
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-full flex-1">
      <Sidebar />
      <div className="flex-1 pb-16 md:pb-0">{children}</div>
    </div>
  );
}
```

`min-h-full` (não `h-screen`/`min-h-screen`) não limita a altura do container à viewport — quando o conteúdo principal (`children`) é mais alto que a tela, a `<div>` externa cresce junto, e como `Sidebar` é um irmão flex sem `sticky`/`fixed`/`overflow-y-auto` próprio, ela estica (`align-items: stretch`, padrão do flexbox) para acompanhar essa altura total. O botão "Sair", posicionado no final da `Sidebar`, só fica visível rolando a **página inteira**, não a barra lateral isoladamente — exatamente o sintoma relatado ("aparece e some" ao dar F5, porque o skeleton/carregamento inicial é mais curto que o conteúdo final).

**Classificação:** **`USABILITY`**, com componente de **`ACCESSIBILITY`** (navegação persistente — incluindo um controle de segurança como logout — convencionalmente esperada como sempre alcançável, sem depender de rolar até o fim de uma página potencialmente longa; não é uma violação técnica de WCAG, mas se alinha ao espírito de "navegação previsível"). **Não é `COSMETIC`** (afeta a capacidade de completar a tarefa de forma eficiente) nem `FUNCTIONAL` (o mecanismo em si funciona perfeitamente uma vez alcançado — confirmado, o clique redireciona corretamente para `/entrar`).

### Menor delta visual proposto (não implementado, não redesenha o Shell)

Ajuste de classes Tailwind, sem novos componentes nem reestruturação:

1. `AppShell`: trocar `min-h-full` por `min-h-screen` no container externo.
2. `Sidebar` (`data-testid="sidebar-nav"`): adicionar `md:sticky md:top-0 md:h-screen md:overflow-y-auto` à classe existente — mantém a barra lateral fixa ao viewport em `md`/`lg`, com rolagem própria caso o menu (não o botão) precise dela, sem alterar a estrutura de `<nav>`/`<div>` já existente.

Nenhuma mudança na barra mobile (`bottom-nav`), que já está correta.

---

## 5. Demais findings (F1, F2, F3, F5, F8, F9)

Avaliados individualmente na Seção 1, com a mesma disciplina de evidência/classificação — nenhum presumido como "precisa corrigir" sem justificativa. Resumo das 3 orientações explícitas do mandato:

- **Conflito de porta PostgreSQL (F1):** pode permanecer como limitação ambiental — o Runbook já pede checar a porta, só precisa de uma orientação mais específica (documentação, não código).
- **`pg_dump` via Docker (F8):** confirmado como solução operacional válida — não há requisito real de instalação nativa para o objetivo funcional do piloto (recovery point real, já produzido e validado).
- **Versões Python/Node (nota suplementar):** avaliadas contra compatibilidade real (não só CI) — nenhuma falha observada, rebaixadas a informativo.

---

## 6. Pilot Hardening Matrix

| Finding | Severity | Pilot Impact | Root Cause | Classification | Required Before Pilot? | Proposed Action |
|---|---|---|---|---|---|---|
| F1 | MEDIUM | Baixo (com doc melhor) | Postgres nativo pré-existente na porta 5432 | ENVIRONMENT | Não | Melhorar Runbook Preflight item 13 |
| F2 | LOW | Nenhum | Runbook diverge do comentário do script | DOCUMENTATION | Não | Corrigir Runbook Seção 3.4 |
| F3 | MEDIUM | Alto (bloqueia preparação) | `pip install --upgrade pip` direto, incompatível com Windows | PRODUCT | **Sim** | 1 linha: `python -m pip` em vez de `pip` |
| F4 | MEDIUM | Alto (único caminho de start no Windows) | `.venv/bin` únicos, nunca `.venv/Scripts`; `python3` inexistente no Windows venv | **PRODUCT — Windows venv detection defect** | **Sim** | 2 blocos pequenos, replicando padrão já usado em `prepare-env.sh` |
| F5 | LOW | Nenhum (com checklist) | Erro de digitação/procedimento, não produto | PROCEDURE/TEST | Não | Reforçar Session-Day Checklist (opcional) |
| F6 | LOW-MEDIUM | Médio (UX de um controle de segurança) | Sidebar sem `sticky`, shell sem altura de viewport travada | PRODUCT (UX/Accessibility) | Recomendado, não obrigatório | 2 classes Tailwind |
| F7 | MEDIUM | Alto (roteiro da sessão desatualizado) | Pergunta de teste sem vocabulário de domínio nunca aciona nenhum Advisor (`SELECTION_EMPTY`) | DOCUMENTATION (+ PRODUCT/UX opcional) | **Sim** (documentação) | Corrigir roteiro da sessão com pergunta de domínio real |
| F8 | MEDIUM | Nenhum (contorno já validado) | `pg_dump`/`psql` ausentes no Windows | ENVIRONMENT | Não | Documentar alternativa via Docker no Runbook |
| F9 | LOW | Nenhum | SHA desatualizado | DOCUMENTATION | Não | Atualizar quando conveniente |

### Consolidação

- **MUST FIX BEFORE PILOT:** F3, F4 (código — pequenos, de baixo risco, isolados em scripts de orquestração local, nunca tocam `src/`/produto).
- **SHOULD FIX BEFORE PILOT:** F7 (documentação — roteiro da sessão), F1/F8 (documentação — Runbook, recomendado mas não bloqueante).
- **ACCEPTED FOR PILOT:** F5 (não é defeito), F6 (recomendado mas não bloqueante — logout funciona, só mal posicionado), F8 (contorno já validado e suficiente).
- **DOCUMENTATION UPDATE:** F1, F2, F5 (opcional), F6 (se não corrigido em código), F7, F8, F9.

---

## 7. Escopo de implementação

**Nenhuma implementação foi realizada nesta missão.** Todas as propostas acima (F3, F4, F6, F7) são diagnósticos e recomendações, não código ou documentação alterados. Nenhuma alteração de arquitetura, RBAC, Tenant Isolation, Advisors, ExecutiveOrchestrator, infraestrutura. Nenhum uso de Anthropic/Voyage real. Nenhum staging, DR Drill, novo Epic, ou sessão humana.

---

## 8. Risco residual

Se F3/F4 não forem corrigidos antes da sessão: qualquer preparação futura da máquina exige repetir manualmente os contornos operacionais já documentados em D-209 — risco real de erro humano numa sessão com tempo limitado e usuário observando. Se F7 não for corrigido na documentação da sessão: risco real de o facilitador repetir a mesma confusão ao vivo, com uma pergunta de teste sem vocabulário de domínio, e interpretar "Base insuficiente" incorretamente na frente do usuário piloto. F6, se não corrigido, é um inconveniente reconhecido, não um bloqueio.

---

## 9. Estimativa de prontidão após as correções

Se F3 (1 linha) + F4 (2 blocos pequenos, script de orquestração local, não `src/`) + a atualização do roteiro da sessão (F7, documentação) forem autorizados e implementados: **prontidão técnica estimada em 1 sessão de trabalho curta**, dado que:
- Nenhuma das correções toca `src/`, RBAC, Tenant Isolation, ou qualquer Capability.
- F3/F4 têm exatamente o mesmo padrão já comprovado funcional em `prepare-env.sh` no mesmo repositório — não é um caminho novo, é replicar um caminho já validado.
- F7 é uma correção de texto no roteiro da sessão, não de código.
- Após a correção, uma nova execução completa do Runbook na máquina física (repetindo a Etapa 6/Sanity Journey) seria necessária para reconfirmar `LOCAL WINDOWS ENVIRONMENT = VALIDATED` com as correções aplicadas — não presumido automaticamente válido só pela correção estar implementada.

---

## 10. GO/NO-GO

- **GO para implementação do Hardening** (F3 + F4 + atualização do roteiro F7), **condicionado a nova Founder Decision explícita** autorizando essa implementação especificamente — nenhuma correção foi ou será feita sem essa autorização.
- **NO-GO atual para a sessão humana** — permanece exatamente como definido pela Founder Decision que abriu esta missão: a sessão humana não está autorizada até uma decisão futura, após o Hardening (se autorizado) ser implementado e revalidado.

W7-1 permanece `OPEN`. External Gates A/B/C/D inalterados. Nenhuma Production AI Validation. Enterprise Readiness não reivindicada.
