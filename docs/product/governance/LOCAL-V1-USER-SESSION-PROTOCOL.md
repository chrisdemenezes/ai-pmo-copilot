# Local V1 User Session Protocol

**Autorização:** "Founder Decision — Local V1 Windows Pilot Preparation" + "Founder Decision — Local V1 Pilot Dataset Completion". Companion de `docs/operations/LOCAL-V1-WINDOWS-RUNBOOK.md` — aquele cobre a preparação técnica da máquina, este cobre o conteúdo/roteiro/critérios da sessão humana em si. **Não** é Controlled User Pilot formal, W7-1 Staging Validation, Production AI Validation, ou Enterprise Readiness. Gates A/B/C = `NOT AVAILABLE`, Gate D = `NOT APPROVED` — inalterados.

**Correção elevada com transparência:** a Seção 1 original (Founder Decision "Local V1 Windows Pilot Preparation") registrava Projetos/Ações/Decisões/Aprendizados/Documents como vazios por design, com a correção de `seed_demo_data.py` explicitamente fora de escopo. Uma missão seguinte ("Local V1 Pilot Dataset Completion") autorizou e executou exatamente essa correção — ver `docs/product/governance/LOCAL-V1-PILOT-DATASET-EXECUTIVE-EVIDENCE.md`. Esta seção é reescrita para refletir o estado real corrigido; a versão anterior não é apagada da história do repositório (Decision Log D-207 não é reescrito retroativamente).

---

## 1. Pilot Dataset — achado real, verificado após a correção

Verificado diretamente contra um banco recém-migrado + `python3 demo/seed_demo_data.py` (corrigido): **a STRATECH tem 2 modelos de dado paralelos — ambos agora populados, mas por 2 identidades/organizações distintas, uma consequência arquitetural real, não uma escolha de conveniência (ver `LOCAL-V1-PILOT-DATASET-EXECUTIVE-EVIDENCE.md` Seção 1).**

| Superfície | Fonte de dado | Estado após a correção |
|---|---|---|
| Priorização (Portfolio) | Enterprise Domain (`portfolios`/`programs`/`projects`, migrations `0002`+`0008`) | **Populado** — em ambas as organizações |
| Program Management | idem | **Populado** |
| Project Delivery | idem | **Populado** |
| Dashboard — KPIs de Portfólio/Programa | idem | **Populado** |
| Mission Control | Dado estático por design (`web/lib/mock/mission-control-data.ts`) | **Populado** (sempre, por arquitetura) |
| Administration (Usuários/Chaves/Sessões/Convites) | Tabelas de admin, criadas no boot | **Populado** (usuário demo + Administrator bootstrapado) |
| **Projetos** (legado, `/projects`, `usePortfolioSummary`) | `analysis_records` (`project_status`/`risk_review`/`meeting_intelligence`) | **Populado em "Organização Principal"** (6 projetos) — **vazio em "Demo Organization"** |
| **Ações** | idem (derivado de `meeting_intelligence`) | **Populado em "Organização Principal"** (8 itens) — vazio em "Demo Organization" |
| **Decisões** | idem (deriva de status `red`/`yellow` + riscos de alta atenção) | **Populado em "Organização Principal"** — vazio em "Demo Organization" |
| **Aprendizados** | idem (recorrência exata, `MIN_OCCURRENCES=3`) | **Populado em "Organização Principal"** (1 risco recorrente + 1 ação recorrente) — vazio em "Demo Organization" |
| Documents | Knowledge Platform | **Populado em "Organização Principal"** (1 documento sintético, indexado) — vazio em "Demo Organization" |
| Dashboard — Decision Center/Actions Center/Recent Activity/AI Recommendations | Dado simulado embutido no componente (rótulo explícito "demonstração, Sprint 1, dados simulados") | **Populado, mas explicitamente rotulado como simulação** — não confundir com dado real |

**Por que 2 organizações, não 1:** o usuário demo (`demo@stratech.local`, "Demo Organization") tem papel `viewer` reafirmado a cada boot do backend, por design (`bootstrap_demo_user()`, "Demo Mode demonstrates, never mutates") — corretamente sem `intelligence.write`/`knowledge.write`. Nenhuma API real permite elevar essa permissão de dentro de "Demo Organization" (nenhum administrador existe lá por padrão, nenhuma rota de auto-registro). A única identidade de escrita local disponível é o Administrator bootstrapado (`STRATECH_ADMIN_EMAIL`/`STRATECH_ADMIN_PASSWORD`), que vive em **"Organização Principal"** — daí o dataset populado estar lá, não em "Demo Organization". Achado mecânico, não presumido — diagnóstico completo em `LOCAL-V1-PILOT-DATASET-EXECUTIVE-EVIDENCE.md`.

**Login recomendado para a sessão completa:** organização `organizacao-principal`, e-mail = `STRATECH_ADMIN_EMAIL`, senha = `STRATECH_ADMIN_PASSWORD` (`demo/.env`) — vê o dataset completo. **Login somente-leitura, preservado, útil para ilustrar RBAC restrito:** `demo-organization`/`demo@stratech.local`/`WORKSPACE_PASSWORD` — mesmo Enterprise Domain, mas Projetos/Ações/Decisões/Aprendizados/Documents vazios (não um defeito, RBAC funcionando como projetado).

Um documento sintético já existe e é reutilizado automaticamente pelo passo de seed (`demo/synthetic-document.md`) — nenhuma preparação manual adicional necessária para o Bloco F.

---

## 2. AI Boundary — obrigatório, per achado do rehearsal (D-205) e diagnóstico F7 (D-211)

**Confirmado mecanicamente (D-205):** sem `ANTHROPIC_API_KEY` real, Advisors/Decision Support/Executive Narrative retornam `HTTP 502` — comportamento **fail-closed correto e desejável** (o `AdvisorFramework` recusa corretamente fabricar uma recomendação a partir de uma resposta não estruturada do `MockLLMProvider`), não um defeito de produto.

**Correção F7 (Local V1 Pilot Hardening Review, D-210/D-211):** a validação física na máquina Windows (D-209) usou a pergunta de teste "Quero fazer um teste com esta função" em Decision Support e observou **"Base insuficiente para responder a esta pergunta com o escopo selecionado"** em vez do `502` documentado acima. Diagnóstico definitivo (D-210): essa pergunta não contém nenhum termo do `VOCABULARY` de nenhum dos 8 Advisors (`src/services/executive_orchestrator/catalog.py`) — `evaluate_selection_rule()` (função pura, determinística) retorna `selected=()`, e `ExecutiveOrchestrator.run()` devolve `insufficient_basis(SELECTION_EMPTY)` **antes** de qualquer coleta de evidência ou chamada de LLM. Não é uma máscara de indisponibilidade de IA — é o comportamento correto e deliberado do contrato (`InsufficientBasisReason`, Domain Blueprint §4, D-138) diante de uma pergunta sem vocabulário de domínio. **A pergunta de teste, não o produto, estava incorreta.**

**Pergunta de teste recomendada para a sessão (substitui a usada em D-209):**

> "Quais são os principais riscos ativos que exigem atenção da liderança?"

Verificado mecanicamente contra `evaluate_selection_rule()` (sem precisar de backend/LLM real — função pura):

| Escopo | Advisors selecionados |
|---|---|
| Organização | `risk_advisor`, `executive_advisor` |
| Projeto (qualquer um dos 7 projetos do Enterprise Domain) | `risk_advisor` |

Atende aos 5 critérios do mandato: usa o tema do dataset sintético (o seed criou 1 risco recorrente real); representa um caso de uso real de PMO; é compreensível por um usuário não técnico; ativa deterministicamente pelo menos 1 Advisor elegível em qualquer escopo testado; não exige dado corporativo real. Com essa pergunta, Decision Support **não** deve mais retornar `insufficient_basis(SELECTION_EMPTY)` por falta de vocabulário — o resultado real observado (evidência suficiente vs. `COLLECTION_EMPTY` vs. o `502` fail-closed de sempre) depende do estado real dos dados e da credencial de IA no momento da sessão, e deve ser registrado como observado, não presumido.

**Observação não bloqueante, registrada, não implementada nesta missão:** o backend já retorna `insufficient_basis_reason` (`SELECTION_EMPTY` ou `COLLECTION_EMPTY`) no corpo da resposta (`src/api/routes/intelligence.py`), mas a UI (`web/components/dashboard/decision-support-panel.tsx`) descarta esse campo e sempre mostra a mesma mensagem genérica "Base insuficiente para responder a esta pergunta com o escopo selecionado", independentemente da causa real. Isso não afeta a pergunta recomendada acima (que evita `SELECTION_EMPTY`), mas facilitadores devem saber que, se `insufficient_basis` aparecer por outro motivo durante a sessão, a UI não distingue "nenhum Advisor selecionado" de "Advisor selecionado, mas sem evidência coletável" — apenas Decision Log/D-210 documenta a distinção. Nenhuma alteração de UI foi autorizada ou feita para isso.

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
| **B. Login / primeira impressão** | 5 min | Autenticação real | Fazer login sozinho (organização `organizacao-principal`, e-mail = `STRATECH_ADMIN_EMAIL`, senha comunicada separadamente — ver Seção 1) | Login PASS/FAIL; primeira reação à tela |
| **C. Dashboard** | 10 min | KPIs reais + limites de IA | Explorar o Dashboard livremente | KPIs de Portfólio/Programa fazem sentido; ao alcançar Decision Support/Narrativa Executiva, aplicar a Seção 2 |
| **D. Portfolio/Program/Projects** | 10 min | Domínio real | Navegar Priorização → Program Management → Project Delivery, abrir 1-2 itens | Dados coerentes entre as 3 telas (mesma origem, Enterprise Domain) |
| **E. Actions/Decisions/Learnings** | 10 min | Dataset real, incluindo Aprendizados | Navegar as 3 telas | Ações/Decisões/Aprendizados populados (Seção 1) — Aprendizados mostra exatamente 1 risco recorrente + 1 ação recorrente (limiar real do produto, `MIN_OCCURRENCES=3`, não mais itens que isso) |
| **F. Documents** | 10 min | Upload real | Enviar um segundo documento sintético (o primeiro já foi populado pelo seed) ou apenas revisar o já indexado | Upload → "Indexado" → visível na listagem (papel `organization_admin`, já ativo neste login) |
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
- [ ] Backend (`demo/logs/backend.log` sem erro na inicialização)
- [ ] `/health` (200, sem erro)
- [ ] `/ready` (200)
- [ ] `python3 demo/seed_demo_data.py` executado, `All calls produced structured output.` (Enterprise Domain + Projetos/Ações/Decisões/Aprendizados/Documents populados em "Organização Principal", ver Seção 1)
- [ ] Frontend (`demo/logs/frontend.log` sem erro na inicialização)
- [ ] Login (testado manualmente uma vez antes da sessão, organização `organizacao-principal`)
- [ ] Navigation (os 14 itens acessíveis)
- [ ] Documents (papel `organization_admin` confirmado no usuário de sessão — já ativo pelo login recomendado)
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
