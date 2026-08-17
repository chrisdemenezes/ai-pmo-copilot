# Local V1 User Session Protocol

**Autorização:** "Founder Decision — Local V1 Windows Pilot Preparation". Companion de `docs/operations/LOCAL-V1-WINDOWS-RUNBOOK.md` — aquele cobre a preparação técnica da máquina, este cobre o conteúdo/roteiro/critérios da sessão humana em si. **Não** é Controlled User Pilot formal, W7-1 Staging Validation, Production AI Validation, ou Enterprise Readiness. Gates A/B/C = `NOT AVAILABLE`, Gate D = `NOT APPROVED` — inalterados.

---

## 1. Pilot Dataset — achado real, não presumido

Verificado diretamente (screenshots do Local V1 Validation Rehearsal, D-205) contra um banco recém-migrado (`alembic upgrade head`, sem `seed_demo_data.py`): **a STRATECH tem 2 modelos de dado paralelos, com estados de seed muito diferentes.**

| Superfície | Fonte de dado | Estado com o seed atual |
|---|---|---|
| Priorização (Portfolio) | Enterprise Domain (`portfolios`/`programs`/`projects`, migrations `0002`+`0008`) | **Populado** — 2 organizations, 6 portfolios, 8 programs, 14 projects reais |
| Program Management | idem | **Populado** |
| Project Delivery | idem | **Populado** |
| Dashboard — KPIs de Portfólio/Programa | idem | **Populado** |
| Mission Control | Dado estático por design (`web/lib/mock/mission-control-data.ts`) | **Populado** (sempre, por arquitetura) |
| Administration (Usuários/Chaves/Sessões/Convites) | Tabelas de admin, criadas no boot (usuário demo) | **Populado minimamente** (1 usuário demo) |
| **Projetos** (legado, `/projects`, `usePortfolioSummary`) | `analysis_records` (`project_status`/`risk_review`/`meeting_intelligence`) | **VAZIO** — "Nenhum projeto com análise registrada ainda" |
| **Ações** | idem (derivado de `meeting_intelligence`) | **VAZIO** — "Nenhuma ação registrada em reuniões ainda" |
| **Decisões** | idem (derivado de `risk_review`) | **VAZIO** — "Nenhuma decisão pendente" |
| **Aprendizados** | idem (agregação de Ações+Decisões) | **VAZIO** — "Nenhum aprendizado organizacional identificado" |
| Dashboard — Decision Center/Actions Center/Recent Activity/AI Recommendations | Dado simulado embutido no componente (rótulo explícito "demonstração, Sprint 1, dados simulados") | **Populado, mas explicitamente rotulado como simulação** — não confundir com dado real |

**A causa raiz da coluna "VAZIO" é o mesmo achado já registrado em D-206:** o único mecanismo que popularia `analysis_records` com conteúdo realista sem credencial Anthropic real (`demo/seed_demo_data.py`, via Demo Mode/`MOCK_LLM_RESPONSE_FILE`) está atualmente quebrado — falha com `HTTP 400` porque não envia o contexto de identidade institucional que as rotas `/api/*/analyze` passaram a exigir. **Corrigir esse script exigiria uma alteração de código (adicionar os 3 headers `X-Stratech-*` às chamadas do script), fora do escopo autorizado nesta missão** (Seção 17 do mandato autoriza apenas correções documentais). Registrado aqui como um gap real, não mascarado — se o Founder quiser um dataset mais rico para a sessão (Projetos/Ações/Decisões/Aprendizados populados), a correção de `seed_demo_data.py` precisaria ser autorizada explicitamente em uma missão futura.

**Dataset mínimo confirmado disponível hoje, reutilizando exclusivamente o seed já existente (nenhum dado novo criado):** Organization (`demo-organization` + `Demo Organization`, 2 orgs reais), User (usuário demo, papel `viewer` por padrão — atribuir `pmo` se Documents estiver no roteiro, ver Seção 3), Portfolio (3-6, variando pela organização), Program (4-8), Projects (7-14). **Actions/Decisions/Learnings devem ser tratados como telas vazias esperadas nesta sessão** — não um defeito a ser investigado ao vivo. Um documento sintético (`.md`/`.txt`) deve ser preparado previamente para o passo de Documents (Seção 3, bloco F).

---

## 2. AI Boundary — obrigatório, per achado do rehearsal (D-205)

**Confirmado mecanicamente (D-205):** sem `ANTHROPIC_API_KEY` real, Advisors/Decision Support/Executive Narrative retornam `HTTP 502` — comportamento **fail-closed correto e desejável** (o `AdvisorFramework` recusa corretamente fabricar uma recomendação a partir de uma resposta não estruturada do `MockLLMProvider`), não um defeito de produto.

**Regra obrigatória para a sessão:**

- Classificar essas 3 capabilities explicitamente como **`TECHNICAL MECHANISM PRESENT` / `REAL AI CONTENT = NOT AVAILABLE`** — nunca apresentadas ao usuário como "IA funcionando".
- **Não criar fallback fake.** Não pré-carregar uma resposta fictícia para parecer que a IA respondeu.
- **Não mascarar o erro.** Se o usuário clicar em "Perguntar"/"Gerar Narrativa", o `502` real deve aparecer — é a evidência correta do estado real do sistema.
- **Não alterar o comportamento fail-closed.**
- **Como conduzir sem induzir má interpretação:** antes de chegar a essas 3 seções do Dashboard (Seção 3, bloco C), explicar verbalmente ao usuário: *"Estas 3 seções (Advisors, Decision Support, Narrativa Executiva) têm todo o mecanismo real implementado e testado — seleção de especialistas, auditoria, coleta de evidência — mas a chamada final a um modelo de IA real (Anthropic) ainda não está configurada nesta máquina. Você vai ver um erro aqui, e é esperado — não é um defeito do produto, é a ausência da credencial."* Isso preserva a UX sem inventar nada.
- Documents/Knowledge upload continuam sendo demonstrados normalmente (mecanismo real, indexação real via embedding mock) — apenas a qualidade semântica da busca não é validável, mesma fronteira já registrada desde D-201/D-205.

---

## 3. User Session Script (60-90 minutos)

| Bloco | Duração | Objetivo | Tarefa do usuário | O que observar |
|---|---|---|---|---|
| **A. Contexto** | 5 min | Explicar o propósito da sessão: validação de produto, não demonstração guiada | Ouvir; ler o AI Boundary (Seção 2) resumido em 2 frases | — |
| **B. Login / primeira impressão** | 5 min | Autenticação real | Fazer login sozinho com as credenciais fornecidas (organização `demo-organization`, e-mail `demo@stratech.local`, senha comunicada separadamente) | Login PASS/FAIL; primeira reação à tela |
| **C. Dashboard** | 10 min | KPIs reais + limites de IA | Explorar o Dashboard livremente | KPIs de Portfólio/Programa fazem sentido; ao alcançar Decision Support/Narrativa Executiva, aplicar a Seção 2 |
| **D. Portfolio/Program/Projects** | 10 min | Domínio real | Navegar Priorização → Program Management → Project Delivery, abrir 1-2 itens | Dados coerentes entre as 3 telas (mesma origem, Enterprise Domain) |
| **E. Actions/Decisions/Learnings** | 10 min | Honestidade sobre o dataset | Navegar as 3 telas | **Esperado: vazias** (Seção 1) — explicar antes de o usuário chegar lá, para não ser lido como defeito |
| **F. Documents** | 10 min | Upload real | Enviar o documento sintético preparado previamente | Upload → "Indexado" → visível na listagem (papel `pmo`/`organization_admin` necessário — ver Runbook) |
| **G. Navigation/discoverability** | 5 min | Usabilidade da navegação | Pedir para o usuário achar 2-3 itens específicos sem indicação | Tempo até achar; hesitação |
| **H. Mission Control/Admin** | 5 min | Painel executivo + administração básica | Explorar Mission Control; olhar Administração (Usuários) | Renderização correta |
| **I. Feedback livre** | 10-20 min | Captura de opinião não guiada | Falar livremente sobre a experiência | Registrar tudo per Seção 4 |

**Não demonstrar IA real enquanto Gates B/C estiverem indisponíveis** — a Seção 2 já cobre exatamente essa regra.

---

## 4. Feedback Model

Para cada achado durante a sessão, registrar:

| Campo | Descrição |
|---|---|
| Area | Ex.: "Documents", "Dashboard", "Navigation" |
| Task | O que o usuário estava tentando fazer |
| Expected | O que se esperava acontecer |
| Observed | O que de fato aconteceu |
| Severity | `BLOCKER` / `HIGH` / `MEDIUM` / `LOW` / `UX` / `IDEA` |
| User comment | Citação direta do usuário, quando houver |
| Screenshot | Referência ao arquivo, se capturado |
| Reproducible | `YES`/`NO` |

**Separar rigorosamente, per mandato:**

- **`DEFECT`** — o produto se comportou diferente do especificado/esperado.
- **`USABILITY`** — o produto funcionou como especificado, mas foi confuso/difícil.
- **`FEATURE REQUEST`** — o usuário queria algo que não existe.
- **`BUSINESS INSIGHT`** — observação sobre valor/mercado/prioridade, não sobre o produto em si.

---

## 5. Exit Criteria

- **`SESSION PASSED`** — nenhum `BLOCKER`, o usuário completou o roteiro da Seção 3 sem obstrução.
- **`SESSION PASSED WITH FINDINGS`** — nenhum `BLOCKER`; um ou mais `HIGH`/`MEDIUM`/`LOW`/`UX`/`IDEA` registrados.
- **`SESSION FAILED`** — qualquer `BLOCKER` (ex.: login não funciona, dado corrompido, sessão trava de forma irrecuperável).

**Feedback do usuário nunca vira backlog ou alteração de arquitetura automaticamente — tudo retorna primeiro para Founder Executive Review**, exatamente como todo achado desta missão institucional já retornou.

---

## 6. Session-Day Checklist (executar ~30 minutos antes)

- [ ] Git baseline (branch + commit SHA conferidos, `git status` limpo)
- [ ] Docker (Desktop rodando, `docker ps` sem erro)
- [ ] PostgreSQL (`docker compose ps` → `database` healthy)
- [ ] pgvector (extensão confirmada disponível)
- [ ] Migrations (`alembic current` → `0021 (head)`)
- [ ] Synthetic/demo data (Enterprise Domain visível; documento sintético do bloco F preparado)
- [ ] Backend (`demo/logs/backend.log` sem erro na inicialização)
- [ ] `/health` (200, sem erro)
- [ ] `/ready` (200)
- [ ] Frontend (`demo/logs/frontend.log` sem erro na inicialização)
- [ ] Login (testado manualmente uma vez antes da sessão)
- [ ] Navigation (os 14 itens acessíveis)
- [ ] Documents (papel `pmo`/`organization_admin` confirmado no usuário de sessão)
- [ ] Disk (espaço livre confirmado)
- [ ] Ports (8000/3000/5432 livres antes de iniciar)
- [ ] Logs (arquivos limpos/rotacionados, prontos para captura de evidência real da sessão)
- [ ] Backup recovery point (executado uma vez antes da sessão, per Runbook)
- [ ] Browser clean session (Chrome, sem extensões que possam interferir, sessão anônima recomendada)
- [ ] AI limitations confirmed (Seção 2 revisada, pronta para ser comunicada)

**Cada item PASS/FAIL. Qualquer `BLOCKER` = `NO-GO` para iniciar a sessão.**

---

## 7. Status

Este protocolo está pronto para execução assim que `docs/operations/LOCAL-V1-WINDOWS-RUNBOOK.md` confirmar `WINDOWS PROCEDURE READY FOR EXECUTION` na máquina real do Founder. Nenhuma sessão iniciada automaticamente por este documento.
