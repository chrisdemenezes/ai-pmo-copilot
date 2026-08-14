# Local V1 User Validation — Plan

**Autorização:** "Founder Decision — Local V1 User Validation", em resposta ao Gate Check (D-202: Gates A/B/C `NOT AVAILABLE`, `CONTROLLED USER PILOT = NO-GO`). Esta missão cria uma etapa distinta e anterior ao staging — validação humana real da V1, em máquina local do Founder, usando exclusivamente infraestrutura local já suportada pelo produto. **Nenhuma implementação nesta missão** — apenas este documento.

---

## 0. Fronteira de preservação (registrada explicitamente, per mandato Seção 2)

`LOCAL V1 USER VALIDATION ≠ STAGING VALIDATION`. Nenhum resultado desta etapa poderá, sob nenhuma hipótese:

- fechar W7-1 (permanece `OPEN`);
- alterar Gate A/B/C/D (permanecem exatamente como em D-202: A/B/C `NOT AVAILABLE`, D `NOT APPROVED`);
- declarar Production AI Validation;
- declarar Enterprise Readiness;
- substituir staging;
- substituir o DR Drill do W7-3;
- autorizar dados corporativos reais.

---

## 1. Análise grounded — respostas às 8 perguntas mandatadas

**1. A V1 atual pode ser executada integralmente em localhost?** **SIM, via PostgreSQL — NÃO via SQLite.** Verificado empiricamente nesta missão (não presumido): rodando `alembic upgrade head` contra um banco SQLite limpo, a cadeia de migrations **falha na migration `0010_security_hardening.py`** (`ALTER TABLE analysis_records ALTER COLUMN organization_id SET NOT NULL` — sintaxe `ALTER COLUMN` não suportada pelo SQLite), muito antes mesmo de chegar à Knowledge Platform (migration `0016`, que adicionaria uma segunda falha via `CREATE EXTENSION IF NOT EXISTS vector`, sintaxe exclusiva do PostgreSQL). **Achado real, classificado como Documentation Defect, não Product Defect:** `demo/start-demo.sh` e `demo/README.md` ainda descrevem o caminho SQLite ("no Docker/Postgres needed") como viável — essa descrição está desatualizada desde a migration `0010` (Wave 2), nunca atualizada quando o produto evoluiu. O caminho real e único viável hoje é PostgreSQL (nativo ou via Docker) — exatamente o mesmo banco já usado durante toda a Wave 7 desta sessão (`postgresql://aipmo:aipmo@localhost:5432/aipmo`), sem qualquer alteração de código necessária.

**2. Quais funcionalidades podem ser validadas sem Anthropic e Voyage?** Login, Dashboard (dados de domínio), Navigation, Priorização, Projects/Program Management/Project Delivery (listagens), Actions/Decisions/Aprendizados (visualização de análises já persistidas), Documents (upload/listagem — mecanismo, não qualidade semântica), Mission Control (100% dado estático), Administration completa, Logout, Backup/Restore local. Ver Matriz (Seção 3).

**3. Quais dependem obrigatoriamente de Anthropic?** Qualquer geração NOVA de conteúdo via LLM: submissão de nova análise de projeto/risco/reunião (Workspace), Enterprise Advisors, Decision Support, Executive Narrative — **quando se exige que o CONTEÚDO da resposta seja um raciocínio real, não um placeholder**. Mecanicamente, nenhuma dessas rotas *exige* Anthropic para executar sem erro (ver pergunta 5) — mas o valor central da IA só é validável com Anthropic real.

**4. Quais dependem obrigatoriamente de Voyage?** Qualidade semântica real de Knowledge/RAG e do Document Advisor. Mecanicamente, a ingestão/indexação/recuperação funcionam sem Voyage (via `MockEmbeddingProvider`) — mas a fidelidade da busca semântica só é validável com Voyage real.

**5. Quais operam com mecanismos locais/mock já existentes, sem alterar arquitetura?** Todas as acima — confirmado por leitura direta: `parse_structured_output()` (`src/agents/shared/output_parser.py`) nunca lança exceção para texto não-JSON, retornando `{"structured": False, "raw_output": ...}` — ou seja, **toda a cadeia de rotas (Advisors/Decision Support/Executive Narrative/analistas) executa de ponta a ponta com `LLM_PROVIDER=mock` sem crash**, exercitando roteamento, RBAC, evidence-gating, persistência, e renderização de UI reais. `EMBEDDING_PROVIDER=mock` (`MockEmbeddingProvider`, determinístico, hash-based) já é o default de `dev` e permite todo o pipeline de Knowledge/RAG rodar mecanicamente.

**6. Quais NÃO devem ser consideradas validadas quando executadas com mock?** Qualidade de raciocínio dos Advisors; precisão de citações; coerência de síntese executiva; relevância semântica de busca em Documents/RAG; qualquer julgamento sobre "a IA está dando boas respostas". Mock prova **mecanismo**, nunca **conteúdo**.

**7. O Demo Mode/local RC existente é suficiente para esta validação?** **Parcialmente, e de forma mais direta do que o esperado — reverificado nesta missão, não assumido:** `make dev` (o "RC" documentado em `Makefile`) executa exatamente `setup → db-create → migrate → ./demo/start-demo.sh` — ou seja, **`make dev` e o Demo Mode do DPS-01 são o mesmo mecanismo**, não dois caminhos distintos. Isso já cobre login real, banco real, seed real (Organizations/Roles/Portfolios/Programs/Projects via migrations `0002`+`0008`), backend real, frontend real. **Limitação real encontrada:** `demo/seed_demo_data.py` e o mecanismo `MOCK_LLM_RESPONSE_FILE` (Demo Mode "com conteúdo realista") cobrem exclusivamente os 3 analistas originais (`project_status`/`risk_review`/`meeting_intelligence`) — não têm nenhuma cobertura para Advisors/Decision Support/Executive Narrative, que se rodados sem credencial real recebem o texto estático padrão do `MockLLMProvider` ("mock analysis output"), não conteúdo schema-conformant. Suficiente para Level 1 (mecanismo), insuficiente para demonstrar qualidade de conteúdo dessas 4 capabilities sem Anthropic real.

**8. Alguma alteração de código é realmente necessária?** **NÃO.** Nenhuma capability exige alteração de código para ser exercitada localmente no nível de fidelidade que cada uma permite hoje. O único gap real (item 1) é de **documentação desatualizada** (`demo/README.md`/`demo/start-demo.sh` sobre SQLite), classificado LOW, menor delta proposto na Seção 9 — **não implementado nesta missão, per mandato explícito**.

---

## 2. Matriz de Validação

Classificação: **A** = Validatable Locally — Real · **B** = Validatable Locally — Mock/Limited · **C** = Requires Anthropic · **D** = Requires Voyage · **E** = Requires Both · **F** = Requires Staging/External

| # | Funcionalidade | Classe | Mecanismo real | Dependência externa | Fidelidade | O que o teste comprova | O que NÃO comprova |
|---|---|---|---|---|---|---|---|
| 1 | Login | **A** | Argon2, brute-force guard, sessão HMAC — 100% local | Nenhuma | Total | Autenticação real de ponta a ponta | — |
| 2 | Dashboard | **B** | KPIs/grid = dado real de Postgres; painéis de Decision Support/Executive Narrative embutidos dependem de C | Nenhuma para KPIs; Anthropic para os painéis de IA | Alta para dados de domínio, Baixa para os painéis de IA | Renderização real, agregação real de KPIs | Qualidade do conteúdo dos painéis de IA embutidos |
| 3 | Navigation | **A** | 14 itens reais, roteamento client-side | Nenhuma | Total | Navegação completa, todos os breakpoints | — |
| 4 | Prioritização (Portfolio) | **A** | `usePortfolioSummary`/`useLatestRisks`, sem IA nova | Nenhuma | Total | Camadas de decisão executiva reais | — |
| 5 | Projects | **A** (listagem) / **B-C** (submissão de nova análise) | Listagem 100% real; análise nova (Workspace, TIP-005/006/007) chama o LLM configurado | Nenhuma para listar; Anthropic para nova análise com conteúdo real | Alta / Baixa-sem-Anthropic | Fluxo de listagem→Workspace real | Qualidade de uma análise nova gerada sem Anthropic |
| 6 | Program Management | **A** | Real, sem CRUD, sem IA | Nenhuma | Total | Agrupamento Program→Portfolio real | — |
| 7 | Project Delivery | **A** | Real, sem CRUD, sem IA | Nenhuma | Total | Agrupamento Project→Program real | — |
| 8 | Actions | **A** (visualização) / **B-C** (nova análise de reunião) | Agrega análises já persistidas | Nenhuma para visualizar | Alta | Action Intelligence real sobre dado seedado | Qualidade de uma nova extração de ação |
| 9 | Decisions | **A** (visualização) / **B-C** (nova análise de risco) | Executive Decision Queue real | Nenhuma para visualizar | Alta | Fila de decisão real sobre dado seedado | Qualidade de uma nova análise de risco |
| 10 | Learnings (Aprendizados) | **A** | Agrega os mesmos sinais de Portfolio/Actions | Nenhuma | Alta | Organizational Intelligence real | — |
| 11 | Documents | **B** | Upload/listagem/reindex 100% reais; indexação usa o embedding provider configurado | Nenhuma para o mecanismo; Voyage para qualidade semântica | Alta para o mecanismo, Baixa para semântica | Upload→persistência→status real | Qualidade da busca semântica sobre o conteúdo indexado |
| 12 | Knowledge/RAG | **B** (mecanismo) / **D** (qualidade) | `rag_pipeline.py` real contra Postgres+pgvector real | Voyage para embeddings reais | Alta para recuperação estrutural, Baixa para relevância semântica | Retrieval real, `chunk_id`/`document_id` rastreáveis | Se o contexto recuperado é o mais relevante semanticamente |
| 13 | Enterprise Advisors | **B** (mecanismo) / **C** (conteúdo) | `AdvisorFramework` real, 8 Advisors reais, evidence-gating real | Anthropic para raciocínio real | Alta para plumbing, Nula para conteúdo | RBAC, seleção, evidence-gating, resposta HTTP real | Qualidade de qualquer recomendação |
| 14 | Decision Support | **B** (mecanismo) / **C** (conteúdo) | `ExecutiveOrchestrator` real, `selection_rule` determinística | Anthropic para conteúdo | Alta para plumbing, Nula para conteúdo | Seleção de Advisors, evidence-gating (`insufficient_basis`) real | Qualidade da resposta/citações |
| 15 | Executive Narrative | **B** (mecanismo) / **C** (conteúdo) | Mesmo Orchestrator, catálogo completo de Advisors | Anthropic para conteúdo | Alta para plumbing, Nula para conteúdo | Composição real sobre escopo explícito | Qualidade da narrativa |
| 16 | Mission Control | **A** | 100% dado mock estático por design (não é uma limitação, é a arquitetura real) | Nenhuma | Total | Exatamente o comportamento de produção | — |
| 17 | Administration | **A** | Usuários/API Keys/Sessões/Convites — CRUD real, RBAC real | Nenhuma | Total | Fluxo administrativo completo real | — |
| 18 | Logout | **A** | Corrigido nesta Wave (D-200) — controle real, `DELETE /api/bff/session` | Nenhuma | Total | Ciclo completo de sessão real | — |
| 19 | Backup/Restore local | **A** | `src/database/backup.py`/`restore_validation.py`, já testados nesta sessão contra Postgres real | Nenhuma | Total | Backup/restore real, mesmo mecanismo de staging/produção | Um Disaster Recovery Drill real (fora de escopo, W7-3) |
| 20 | Composition Trace | **B** | Estrutura/seleção de Advisors é determinística e real (`selection_rule.py`), independente do LLM | Anthropic apenas para o conteúdo citado dentro do trace | Alta para estrutura, Baixa para conteúdo | Que o Orchestrator seleciona e registra Advisors corretamente | Se as citações registradas refletem raciocínio real |
| 21 | Citation Consolidation | **B** | Mesmo mecanismo — consolidação estrutural real, conteúdo depende do LLM | Anthropic para conteúdo | Alta para estrutura, Baixa para conteúdo | Consolidação/deduplicação real de citações | Precisão factual das citações |

---

## 3. AI Validation Levels (não confundir evidências entre eles)

**LEVEL 1 — LOCAL PRODUCT VALIDATION.** Sem credenciais externas. `LLM_PROVIDER=mock`, `EMBEDDING_PROVIDER=mock`. Prova: toda a arquitetura, roteamento, RBAC, persistência, UI, evidence-gating, Composition Trace estrutural. **Nunca prova:** qualidade de conteúdo de IA.

**LEVEL 2 — LOCAL REAL AI VALIDATION.** Localhost + Anthropic/Voyage reais, quando as credenciais forem disponibilizadas pelo Founder (mesmas variáveis já existentes: `LLM_PROVIDER=anthropic`+`ANTHROPIC_API_KEY`, `EMBEDDING_PROVIDER=voyage`+`VOYAGE_API_KEY`, em `demo/.env`, nunca commitadas). Prova: qualidade real de conteúdo, em ambiente local, com dado sintético. **Ainda não prova:** comportamento em ambiente de staging real, latência de rede real de um host remoto, ou qualquer característica exclusiva de um ambiente hospedado.

**LEVEL 3 — STAGING VALIDATION.** W7-1 formal — permanece futuro, independente, condicionado aos Gates A/B/C reais (D-202). Não relacionado a esta missão.

---

## 4. Local User Journey

Derivado da navegação real do produto (`web/components/shell/navigation.ts`, 14 itens), não inventado:

```
Iniciar ambiente (make dev)
→ Login (/entrar)
→ Dashboard (KPIs + painéis de IA, Level 1 ou 2 conforme credenciais)
→ Navegação (percorrer os 14 itens, confirmar breakpoints)
→ Priorização (Portfolio)
→ Projetos → Program Management → Project Delivery
→ Ações → Decisões → Aprendizados
→ Documents (upload de documento sintético → indexação → listagem)
→ Knowledge/RAG (implícito em Document Advisor/Decision Support, quando exposto)
→ Executive Intelligence (Decision Support no Dashboard + Executive Narrative)
→ Administração (Usuários/Chaves de API/Sessões/Convites — visualização mínima)
→ Mission Control
→ Logout
```

---

## 5. Dados (regra, não negociável)

Somente: dados demo já existentes (seed das migrations `0002`+`0008`, portfólio fictício SAP do DPS-01 via `seed_demo_data.py`), dados sintéticos adicionais criados especificamente para esta validação, documentos sintéticos para o upload em Documents. **Proibido:** dado corporativo real, documento real de cliente, informação confidencial, qualquer dado sujeito ao Gate D — sem exceção, em nenhum dos 2 níveis locais.

---

## 6. Requisitos da máquina (Windows do Founder)

Derivado de `scripts/prepare-env.sh` (checagem real de pré-requisitos), `.github/workflows/ci.yml` (versões exatas usadas em CI), e `scripts/rc2-db.sh` (que já documenta explicitamente o caminho Windows/Git Bash como suportado).

| Requisito | MINIMUM | RECOMMENDED |
|---|---|---|
| CPU | 2 cores | 4+ cores |
| RAM | 8 GB | 16 GB |
| Disco livre | 10 GB | 20 GB+ (Docker Desktop reserva espaço de VM próprio no Windows) |
| Docker Desktop | Necessário apenas se optar por PostgreSQL via container (recomendado no Windows, evita instalação nativa) | Idem, com backend WSL2 habilitado (padrão do Docker Desktop no Windows 10/11) |
| WSL2 | Não estritamente exigido pelos scripts (`scripts/prepare-env.sh`/`scripts/rc2-db.sh` já preveem Git Bash nativo) | Recomendado se Docker Desktop for usado (exigência do próprio Docker Desktop no Windows) |
| Git | Necessário (inclui Git Bash, o shell usado por `make`/scripts) | Última versão estável |
| Node.js | 22+ (verificado em `scripts/prepare-env.sh`, igual à CI) | 22 LTS |
| Python | 3.11+ (verificado em `scripts/prepare-env.sh`, igual à CI) | 3.11 |
| PostgreSQL 16 + pgvector | Obrigatório — **SQLite não é viável** (Seção 1, achado 1) | Via Docker (`pgvector/pgvector:pg16`, já usado em `docker-compose.yml`) — evita instalação nativa no Windows |
| Portas | 8000 (backend), 3000 (frontend), 5432 (Postgres, se local) | Mesmas — confirmar que nada mais as ocupa |
| Browser | Chrome/Chromium (único suportado pelo Controlled Pilot Browser Baseline, D-199) | Última versão estável |
| Conectividade | Nenhuma exigida para Level 1 | Acesso à internet para Level 2 (Anthropic/Voyage) |
| Variáveis de ambiente | `demo/.env` (gerado automaticamente na 1ª execução) | Mesmas, + `ANTHROPIC_API_KEY`/`EMBEDDING_PROVIDER=voyage`/`VOYAGE_API_KEY` apenas para Level 2 |

**Nenhum requisito inventado além do que os scripts/CI já exigem.**

---

## 7. Instalação limpa (derivada dos scripts reais, nenhum comando novo proposto)

```bash
# 1. Clone
git clone <repo> && cd ai-pmo-copilot

# 2. Dependências + ambiente (scripts/prepare-env.sh — checa Python 3.11+/Node 22+/psql)
make setup

# 3. Banco (scripts/rc2-db.sh create — ou usar o Postgres do docker-compose, ver nota abaixo)
make db-create

# 4. Migrations (Organizations/Roles/Portfolios/Programs/Projects já seedados por 0002+0008)
make migrate

# 5. Backend + Frontend juntos, Demo Mode por padrão (demo/start-demo.sh)
make dev
```

**Nota sobre o banco no Windows:** `make db-create` assume PostgreSQL nativo (peer/TCP auth, per `scripts/rc2-db.sh`). Alternativa mais simples no Windows, sem instalar Postgres nativamente: subir apenas o serviço `database` do `docker-compose.yml` (`docker compose up -d database`, já expõe a porta 5432 via `docker-compose.override.yml` em dev) e pular `make db-create` — a própria documentação do script já prevê essa alternativa.

```bash
# Validação
make health                    # GET /health
curl -sf http://localhost:8000/ready   # readiness real
# Login: http://localhost:3000/entrar (senha em demo/.env, WORKSPACE_PASSWORD)
python3 demo/seed_demo_data.py # opcional -- portfólio fictício SAP com conteúdo realista
```

```bash
# Encerrar
make stop
```

---

## 8. Pre-flight Check (executável, antes da sessão com usuário)

- [ ] `docker ps` (se Postgres via Docker) — container `database` `healthy`
- [ ] `psql`/`docker exec` — conexão ao banco confirmada
- [ ] `alembic current` — revisão de migration = head (21 migrations)
- [ ] `curl -sf http://localhost:8000/health` — 200, `release` presente
- [ ] `curl -sf http://localhost:8000/ready` — 200
- [ ] `curl -sf http://localhost:3000/entrar` — frontend respondendo
- [ ] Login manual bem-sucedido com o usuário de teste
- [ ] Dado demo/sintético confirmado visível (Dashboard mostra os projetos seedados)
- [ ] Browser = Chrome/Chromium, última versão
- [ ] Disco livre ≥ requisito mínimo
- [ ] Portas 8000/3000/5432 livres antes de iniciar (nenhum processo conflitante)
- [ ] `demo/logs/backend.log` e `demo/logs/frontend.log` sem erro na inicialização
- [ ] Um backup local executado e verificado (`src/database/backup.py`) antes da sessão
- [ ] Status do AI provider anunciado à sessão: Level 1 (mock) ou Level 2 (Anthropic/Voyage reais, se credenciais fornecidas) — nunca ambíguo para quem observa

---

## 9. Gaps encontrados (documentados, não corrigidos nesta missão)

| Gap | Severidade | Menor delta proposto (não implementado) |
|---|---|---|
| `demo/start-demo.sh`/`demo/README.md` descrevem SQLite como caminho viável ("no Docker/Postgres needed") — desatualizado desde a migration `0010` (confirmado empiricamente nesta missão) | LOW (Documentation Defect) | Atualizar o comentário/README para declarar PostgreSQL como único caminho suportado, removendo a alegação de SQLite — nenhuma mudança de comportamento, apenas texto |
| `demo/.env.example` não lista `EMBEDDING_PROVIDER`/`VOYAGE_API_KEY` como variáveis disponíveis para Level 2 | LOW (Documentation Defect) | Adicionar as 2 linhas comentadas ao exemplo, espelhando o padrão já usado para `ANTHROPIC_API_KEY` no mesmo arquivo |
| `demo/seed_demo_data.py`/Demo Mode não cobrem Advisors/Decision Support/Executive Narrative — apenas os 3 analistas originais | LOW (não bloqueante — Level 1 já prova o mecanismo sem precisar de conteúdo realista para essas 4 capabilities) | Nenhum proposto — expandiria escopo sem necessidade demonstrada para esta validação |
| Débito já registrado em sessões anteriores: `KnowledgeRepository.index()` não deleta chunks antigos antes de reindexar | LOW para esta validação (documento sintético único, reindex não é parte do roteiro mínimo) | Nenhum — já é dívida conhecida e registrada, fora de escopo aqui |

**Nenhuma alteração de código necessária para a validação em si (pergunta 8, Seção 1).**

---

## 10. Test Session Protocol (60–90 minutos)

| # | Etapa | Objetivo | Ação esperada do usuário | Evidência a observar | Severidade se FAIL |
|---|---|---|---|---|---|
| 1 | Login | Autenticação real | Inserir organização/e-mail/senha reais | Redirecionamento a `/dashboard` | BLOCKER |
| 2 | Dashboard | KPIs reais + painéis de IA | Observar a tela inicial | KPIs consistentes com o seed; painéis de IA mostram Level 1 ou 2 claramente | HIGH (dado) / UX-FEEDBACK (painel IA) |
| 3 | Navegação | 14 itens acessíveis | Clicar em cada item do menu | Página carrega, item ativo destacado | HIGH |
| 4 | Priorização/Projects/PM/PD | Domínio real | Explorar as listagens | Dados consistentes, sem erro | HIGH |
| 5 | Ações/Decisões/Aprendizados | Sinais agregados | Explorar | Sinais coerentes com o seed | MEDIUM |
| 6 | Documents | Upload sintético | Enviar um `.txt`/`.md` sintético | Documento aparece indexado | HIGH |
| 7 | Knowledge/RAG (via Document Advisor/Decision Support) | Recuperação | Fazer uma pergunta relacionada ao documento enviado | Contexto citado referencia o documento (Level 1: mecanismo; Level 2: relevância) | MEDIUM (Level1) / HIGH (Level2 se irrelevante) |
| 8 | Enterprise Advisors | Plumbing / conteúdo | Acionar um Advisor representativo | Resposta HTTP 200 com `structured`/citações (Level 1: placeholder esperado; Level 2: conteúdo real) | BLOCKER se erro; UX-FEEDBACK se conteúdo fraco em Level 2 |
| 9 | Decision Support | Composição multi-advisor | Fazer uma pergunta com escopo explícito | `insufficient_basis` ou resposta com Composition Trace visível | HIGH |
| 10 | Executive Narrative | Síntese executiva | Gerar narrativa para um escopo | Resposta com citações consolidadas | HIGH |
| 11 | Mission Control | Painel executivo | Acessar | Seções renderizam (dado estático por design) | LOW |
| 12 | Administração | CRUD básico | Visualizar Usuários/Chaves/Sessões | Dados reais, sem erro | MEDIUM |
| 13 | Logout | Encerramento real | Clicar em "Sair" | Retorno a `/entrar`, rota protegida exige login de novo | BLOCKER |

Para cada etapa registrar: PASS / FAIL, observações qualitativas, severidade (`BLOCKER`/`HIGH`/`MEDIUM`/`LOW`/`UX-FEEDBACK`).

---

## 11. Evidence Model

Capturar, sem criar infraestrutura de telemetria nova:

- Screenshot por Capability testada (ferramenta padrão do SO — nenhuma ferramenta nova)
- `release` de `GET /health` no início da sessão
- Resultado de `GET /health`/`GET /ready` capturado no pre-flight
- Browser + versão usados
- Resultado PASS/FAIL por linha do protocolo (Seção 10)
- Erros exatos copiados de `demo/logs/backend.log`/`demo/logs/frontend.log`, quando houver
- Feedback qualitativo do usuário humano, verbatim quando possível
- Duração real da sessão
- Nível de IA usado durante a sessão (Level 1 ou 2) — declarado explicitamente, nunca ambíguo

---

## 12. Exit Criteria

**`LOCAL V1 USER VALIDATION = PASSED`** — todas as etapas da Seção 10 = PASS, nenhum `BLOCKER`/`HIGH` encontrado.

**`LOCAL V1 USER VALIDATION = PASSED WITH FINDINGS`** — nenhum `BLOCKER`; um ou mais `MEDIUM`/`LOW`/`UX-FEEDBACK` encontrados e registrados.

**`LOCAL V1 USER VALIDATION = FAILED`** — qualquer `BLOCKER`, ou qualquer `HIGH` não explicado por uma limitação já conhecida e aceita desta Seção/matriz.

**Estes estados não alteram automaticamente o status da Wave 7, W7-1, ou qualquer Gate — cada um permanece exatamente como registrado em D-201/D-202 até uma Founder Decision explícita subsequente.**

---

## 13. Preservação

Nenhuma implementação nesta missão. Nenhum piloto iniciado. Nenhum staging iniciado. Nenhuma nova Wave/Epic iniciada. W7-1, W7-3, W7-4, W7-7 não alterados retroativamente.
