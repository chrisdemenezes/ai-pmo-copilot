# TD-008 Fase 3b — Impact Assessment (migração `project_name` → `project_id`)

**Item:** 8 do Wave Completion Review retrospectivo (`WAVE-COMPLETION-REVIEW-RETROSPECTIVE.md` §6).
**Status:** **Fase 1 (Impact Assessment) + Fase 2 (Revisão) — concluídas. Nenhum código alterado.** Aguarda **Fase 3 (aprovação do Founder)** antes de qualquer implementação.
**Data:** 2026-07-24
**Natureza:** migração arquitetural controlada, incremental e auditável — não uma refatoração ampla em etapa única.

---

## 0. Onde estamos (contexto)

TD-008 tem 3 fases; **1, 2 e 3a já concluídas**:
- **Fase 1/2** (Waves 2): campos de domínio de Project unificados na tabela `projects`; frontend lê a API real; migração 0008 unificou os Projects legados colidentes.
- **Fase 3a** (Wave 3, Epic W3-1, D-040): `ProjectSummaryService` agrupa por `project_id` (corrigiu o bug de nomes que diferem só por espaço); `ProjectSummaryResponse`/`ProjectSummary` (frontend) ganharam `project_id` **aditivo** (opcional).

**O que resta (Fase 3b):** promover `project_id` a chave primária de fato em toda a superfície de Intelligence (Dashboard, Portfólio, Decision Center, Executive Focus, Workspace, Ações, Riscos, Aprendizados), aposentar o uso de `project_name` como chave, e eliminar o read model `ProjectSummary` como conceito separado.

**Estado atual do dado (fundamental para o plano):** `AnalysisRecord` (`src/database/repository.py:20`) **já possui ambas as colunas** — `project_name` (String, nullable, index) e `project_id` (FK `projects.id`, nullable, index, backfill pela migração 0002, vinculado no `save_analysis` via `get_or_create_project_for_name`). Ou seja, o dado de ligação já existe; a Fase 3b é sobre **trocar a chave de acesso**, não sobre criar o vínculo.

---

## 1. Inventário completo (Fase 1.1)

Contagem bruta de ocorrências do token `project_name`/`projectName` (grep, exclui `node_modules`/`.next`/`.pyc`):

| Área | Ocorrências | Arquivos | Classificação predominante |
|---|---|---|---|
| Backend `src/` (`.py`) | **97** | 12 | Chave de API/serviço/repositório + input do agente |
| Backend `tests/` (`.py`) | **208** | ~18 | Fixtures e asserções acopladas à chave atual |
| `alembic/` (`.py`) | **18** | 6 migrações | Schema histórico (imutável) + a nova migração da Fase 3b |
| Frontend `web/` (`.ts/.tsx/.mjs`) | **659** | ~55 | Rota, BFF, hooks, componentes, mock, tipos |
| Documentação `docs/` | **209** | ~20 | Blueprints/TDs/Decision Logs — atualização textual |
| **Total (bruto)** | **~1.191** | **~110** | — |

**Classificação por natureza (o que precisa migrar vs. o que permanece):**

| Natureza | O que é | Ação na Fase 3b |
|---|---|---|
| **(K) Chave de acesso** | `project_name` usado para *identificar/filtrar/rotear* um projeto (query param das rotas de intelligence; segmento de URL `/workspace/[projectName]`; chaves de React Query; filtros de repositório) | **Migrar para `project_id`** |
| **(A) Atributo de exibição** | `project_name` como *rótulo humano* de um projeto (título da tela, coluna de tabela, texto de brief) | **Permanece** — mas passa a ser `Project.name`, lido junto do `project_id`, não a chave |
| **(I) Input do usuário** | O texto que o usuário digita ao "Analisar Projeto" (resolvido para um Project via `get_or_create_project_for_name`) | **Permanece como entrada**; o backend resolve para `project_id` e persiste o id — o `project_name` deixa de ser a chave de `AnalysisRecord` |
| **(H) Schema histórico** | Colunas/migrações já aplicadas (0001–0010) | **Imutável** — nunca reescrever migração aplicada; a Fase 3b adiciona uma migração nova |
| **(D) Documentação** | Referências textuais em Blueprints/TDs | **Atualizar** ao final, refletindo o novo estado |

> **Observação crítica de escopo:** a maior parte das 659 ocorrências no frontend é **(A) atributo de exibição** (mostrar o nome do projeto) — essas **não somem**, apenas passam a ser lidas via `Project.name` acompanhando o `project_id`. O subconjunto que realmente muda é **(K) chave de acesso**: as rotas de intelligence, o segmento de URL do Workspace, e as chaves de cache. Isso reduz o risco real bem abaixo do que a contagem bruta sugere.

### 1.1 Inventário backend (`src/`) por arquivo

| Arquivo | Oc. | Papel | Natureza |
|---|---|---|---|
| `src/api/routes/intelligence.py` | 41 | Contrato da API: analyze (status/risk/meeting), list analyses, action-items, risks — todos recebem/filtram por `project_name` | **(K)** primária |
| `src/services/project_summary_service.py` | 23 | Agrega `AnalysisRecord` em `ProjectSummary`; já agrupa por `project_id` (3a) mas ainda expõe `project_name` como chave | **(K)+(A)** |
| `src/database/repository.py` | 11 | `AnalysisRecord.project_name`, `save_analysis`, `list_analyses(project_name=…)` | **(K)** + (H) coluna |
| `src/database/enterprise_repository.py` | 5 | `get_or_create_project_for_name` (resolução nome→Project) | **(I)** resolução |
| `src/agents/{risk_review,project_status,meeting_intelligence}/agent.py` | 3 cada | `project_name` como contexto textual passado ao LLM | **(A)** contexto |
| `src/services/ai_foundation/{context_engine,types,audit_integration}.py` | 1–2 | Foundation recebe `project_name` no `SessionContext` | **(K/A)** |
| `src/database/project_identity.py` | 2 | Normalização de nome (`DEFAULT_ORGANIZATION`/slug helpers) | (A) |
| `src/database/models.py` | 2 | Comentário/relacionamento | (H) |

### 1.2 Inventário frontend (`web/`) por área

| Área | Arquivos | Papel | Natureza |
|---|---|---|---|
| `app/workspace/[projectName]/` + `app/api/bff/workspace/[projectName]/**` (summary, analyses, analyses/[id], analyze/{status,risk,meeting}, risk-advisor) | ~9 rotas | **Segmento de URL = chave de roteamento**; BFF encaminha `project_name` para o backend | **(K)** primária — maior mudança de superfície |
| `lib/hooks/use-workspace-*.ts`, `use-*-by-kind.ts`, `use-action-items.ts`, `use-latest-risks.ts` (20 arquivos) | 20 | Chaves de React Query e parâmetros de fetch | **(K)** chaves de cache |
| `components/workspace/**` (16) | 16 | Renderizam painéis do Workspace; recebem `projectName` como prop | **(A/K)** — prop de roteamento + rótulo |
| `lib/dashboard/types.ts`, `components/dashboard/**` | ~7 | `ProjectSummary` type + tabela/cards do Dashboard (link para o Workspace) | **(K)** link + **(A)** exibição |
| `lib/decision-center/**`, `components/decision-center/**` | ~5 | Decision Queue por projeto | (A/K) |
| `lib/organizational-intelligence/**`, `lib/executive-memory/**`, `lib/portfolio-intelligence/**` | ~7 | Agregações por projeto | (A/K) |
| `app/{portfolio,projects,decisions,actions}/` | ~8 | Páginas que linkam para `/workspace/{name}` | **(K)** links |
| `e2e/*.spec.ts`, `e2e/mock-backend.mjs` | ~3 | Mock keyed por `project_name`; specs navegam por nome | **(K)** — mock + E2E |
| `lib/workspace/types.ts` | 3 | `WorkspaceSummary` (read model, keyed por `project_name`) | **(K)** |

### 1.3 Banco de dados

| Objeto | Estado hoje | Fase 3b |
|---|---|---|
| `analysis_records.project_name` | `String(255)`, nullable, index | Passa a **redundante** (o id é a chave); candidata a `DROP COLUMN` na Etapa 4, **após** `project_id` estar NOT NULL e 100% backfillado |
| `analysis_records.project_id` | FK nullable, index, backfill 0002 | Promover a **NOT NULL** (nova migração), após garantir zero linhas com id nulo |
| `projects.name` | Nome real do Project (entidade) | Torna-se a **única fonte** do rótulo humano |

---

## 2. Dependency Map (Fase 1.2)

Cadeia completa de dependência da chave, do dado à tela:

```
[DB] analysis_records.project_name (K, legado)  ──┐
[DB] analysis_records.project_id  (já existe) ────┤
                                                  ▼
[Repo] AnalysisRepository.list_analyses(project_name=…)  ◀── ainda filtra por name
[Svc]  ProjectSummaryService  ── já AGRUPA por project_id (3a) ── mas expõe project_name como chave
[API]  intelligence.py  ── recebe project_name (query/body) em: analyze×3, /analyses, /action-items, /risks/latest, /projects/summary
                                                  ▼
[BFF]  /api/bff/workspace/[projectName]/**  ── encaminha o name para o backend
[URL]  /workspace/[projectName]             ── name no segmento de rota
                                                  ▼
[Hooks] use-workspace-*/use-*-by-kind/use-action-items/use-latest-risks ── React Query keys = [..., projectName, ...]
[Comp]  components/workspace/**, dashboard/**, decision-center/**  ── projectName como prop + link
[Pages] dashboard/portfolio/projects/decisions/actions ── linkam para /workspace/{name}
```

**Quem já usa `project_id`:**
- `ProjectSummaryService.summarize_portfolio()` — agrupa por `project_id` (3a).
- `ProjectSummaryResponse`/`ProjectSummary` (FE) — carregam `project_id` aditivo (3a).
- `AnalysisRecord.project_id` — populado em toda escrita desde a migração 0002.
- Domínio Portfolio/Program/Project (`web/lib/domain/*`) — sempre por `id`.

**Onde coexistem ambos (o núcleo da migração):** `AnalysisRecord` (colunas), `ProjectSummaryService`/`ProjectSummaryResponse` (expõe os dois), e a fronteira API↔BFF↔URL do Workspace (o dado tem id, mas a chave de acesso ainda é o name).

**Onde haverá necessidade de adaptação:** rotas de intelligence (aceitar `project_id`), toda a árvore BFF `/workspace/[projectName]` → `[projectId]`, as ~20 hooks (chaves de cache), os links de página, o mock e os E2E, e as ~18 suítes de teste backend acopladas ao name.

---

## 3. Migration Plan (Fase 1.3) — incremental, sem quebra de compatibilidade

Cada etapa é **um PR próprio, verde de ponta a ponta antes da próxima** (nenhuma etapa quebra compatibilidade).

### Etapa 1 — Introdução completa de `project_id` (aditiva, zero remoção)
- Migração nova: garantir `project_id` populado em 100% das linhas de `analysis_records` (re-backfill defensivo por organização), **sem** ainda torná-lo NOT NULL.
- API: as rotas de intelligence passam a **aceitar `project_id`** (novo parâmetro opcional) **além** de `project_name`. Quando ambos vierem, `project_id` prevalece; quando só o name vier, comportamento idêntico ao de hoje.
- `ProjectSummaryResponse` já expõe `project_id` (3a) — nada a fazer.
- **Compatibilidade:** total. Nenhum consumidor existente muda.
- **Validação:** pytest backend + suíte E2E inalterada devem permanecer 100% verdes.

### Etapa 2 — Compatibilidade temporária (dual-key)
- BFF e hooks passam a **preferir `project_id`** quando disponível (o Portfolio já o recebe), mantendo o fallback por `project_name` para caminhos ainda não migrados.
- Novo padrão de rota do Workspace introduzido **em paralelo** (`/workspace/id/[projectId]` ou query `?projectId=`), coexistindo com `/workspace/[projectName]`. Nenhum link antigo quebra.
- **Compatibilidade:** total (dual-key).
- **Validação:** vitest + E2E (ambas as rotas navegáveis) verdes.

### Etapa 3 — Migração de todos os consumidores
- Trocar, um por vez, cada consumidor (Dashboard → Portfólio → Decision Center → Executive Focus → Workspace → Ações → Riscos → Aprendizados) para linkar/consultar por `project_id`.
- Cada consumidor migrado é um commit isolado com sua própria verificação verde.
- Mock backend e E2E migrados junto de cada consumidor.
- **Compatibilidade:** mantida enquanto ambos os caminhos existem; o name continua funcionando até a Etapa 4.
- **Validação:** por consumidor — vitest + o subconjunto E2E daquela superfície.

### Etapa 4 — Remoção definitiva de `project_name` como chave
- Quando nenhum consumidor depender mais do name como chave: remover o parâmetro `project_name` das rotas de intelligence (mantendo apenas o **input** de análise, que resolve para id); promover `analysis_records.project_id` a **NOT NULL** (migração); **`DROP COLUMN analysis_records.project_name`** (migração — o nome passa a viver só em `projects.name`).
- A rota `/workspace/[projectName]` é aposentada em favor de `/workspace/[projectId]` (redirect temporário do padrão antigo, se desejável).
- **Compatibilidade:** esta é a etapa que **intencionalmente** remove o caminho antigo — por isso vem por último, só depois de a Etapa 3 provar que ninguém mais o usa.
- **Validação:** suíte completa (pytest + vitest + E2E 3 breakpoints) 100% verde; migração testada upgrade **e** downgrade.

### Etapa 5 — Eliminação completa de `ProjectSummary`
- Com todos os consumidores por `project_id`, o read model `ProjectSummary`/`WorkspaceSummary` deixa de ser um conceito separado: consolidar sobre a entidade `Project` do domínio (que já existe), removendo o tipo `ProjectSummary` e o `ProjectSummaryService` como camada distinta (ou reduzindo-o a um método de projeção sobre `Project`).
- Atualização final de TD-008 no Technical Debt Register para **Resolvido**, e da documentação (Blueprints/TDs) para o novo estado.
- **Validação:** suíte completa verde + `grep` de confirmação de que `ProjectSummary` não é mais referenciado como chave.

---

## 4. Risk Assessment (Fase 1.4)

| Risco | Nível | Descrição | Mitigação / Rollback |
|---|---|---|---|
| **APIs críticas de intelligence** (analyze×3, /analyses, /action-items, /risks/latest, /projects/summary) | **Alto** | Toda a experiência executiva depende delas; mudar o contrato pode quebrar o Workspace inteiro | Aditivo primeiro (Etapa 1): `project_id` opcional coexiste com `project_name`; remoção só na Etapa 4 após prova de não-uso. Rollback = reverter o PR da etapa (contrato antigo intacto até a Etapa 4). |
| **`DROP COLUMN analysis_records.project_name`** | **Alto** | Operação destrutiva e irreversível em dado | Só na Etapa 4, após `project_id` NOT NULL + 100% backfill verificado; migração com downgrade que recria a coluna e re-deriva o name de `projects.name`; backup pré-migração (Production Backup Runbook, RB-002). |
| **Roteamento do Workspace** (`/workspace/[projectName]` → `[projectId]`) | **Médio** | Links salvos/externos e navegação por nome podem quebrar | Rotas coexistem na Etapa 2; redirect do padrão antigo; E2E cobre ambos os caminhos durante a transição. |
| **Chaves de React Query** (~20 hooks) | **Médio** | Trocar a chave de cache pode causar corrida de invalidação (ver TD-004/005/006, já resolvido) | Migrar hook a hook (Etapa 3), reaproveitando o padrão `cancelQueries`+`invalidateQueries` já corrigido (D-050). |
| **Nomes livres colidentes / históricos** | **Médio** | Registros antigos com `project_name` que resolve a mais de um id, ou a nenhum | O re-backfill da Etapa 1 resolve por organização com a mesma regra do `get_or_create_project_for_name`; linhas irresolvíveis são relatadas, nunca descartadas silenciosamente. |
| **Regressão E2E ampla** | **Médio** | ~292 testes E2E tocam a superfície executiva; o mock é keyed por name | Migrar mock+E2E junto de cada consumidor (Etapa 3); rodar a suíte 3-breakpoints por etapa. |
| **Suítes de teste backend acopladas ao name** (~18 arquivos, 208 oc.) | **Baixo** | Muitas asserções por `project_name` | Atualização mecânica por etapa; o dual-key da Etapa 1 mantém os testes atuais passando sem alteração. |
| **Documentação divergente** | **Baixo** | 209 oc. em docs | Atualização textual na Etapa 5, sem risco funcional. |

**Estratégia de rollback global:** cada etapa é um PR isolado e reversível; nenhuma etapa anterior à 4 remove um caminho existente, então reverter qualquer PR até a Etapa 3 restaura 100% do comportamento. As duas operações irreversíveis (NOT NULL + DROP COLUMN) ficam confinadas à Etapa 4, com backup prévio e migração de downgrade testada.

---

## 5. Validation Plan (Fase 1.5)

Gate por etapa — **nenhuma etapa avança sem 100% verde:**

| Verificação | Comando | Aplica-se a |
|---|---|---|
| Ruff | `ruff check src tests` | Toda etapa com mudança backend |
| Pytest (backend completo) | `python -m pytest -q` (PostgreSQL efêmero por teste) | Toda etapa backend; migração testada upgrade **e** downgrade |
| TypeScript | `npx tsc --noEmit` | Toda etapa frontend |
| ESLint | `npx eslint .` | Toda etapa frontend |
| Vitest (frontend) | `npx vitest run` | Toda etapa frontend |
| Playwright E2E (3 breakpoints) | `npx playwright test --project=lg --project=md --project=mobile` (após `rm -rf web/.next`) | Toda etapa que toca a superfície executiva; **obrigatório** nas Etapas 2, 3 (por consumidor), 4 e 5 |

A migração só é considerada concluída quando, na Etapa 5, a suíte completa (ruff + pytest + tsc + eslint + vitest + E2E 3 breakpoints) permanecer 100% verde **e** um `grep` confirmar que `project_name` não é mais usado como chave (só como atributo/entrada) e que `ProjectSummary` não é mais um conceito separado.

---

## 6. Fase 2 — Revisão (esforço, complexidade, arquivos, riscos, estratégia)

| Dimensão | Avaliação |
|---|---|
| **Estimativa de esforço** | **Grande** — 5 etapas, cada uma um PR verificado; realista distribuir em ~5 incrementos sequenciais. É, por desenho do próprio Blueprint W3-1, "escopo maior que o resto da Wave 3". |
| **Complexidade** | **Média-Alta** — a lógica é direta (o vínculo id já existe), mas o **raio de impacto** é a experiência executiva inteira e a superfície de teste/mock/E2E é ampla. A complexidade está na **coordenação incremental sem quebra**, não em algoritmo. |
| **Arquivos impactados** | ~**110 arquivos** com ocorrências; porém a maioria é **(A) exibição** (permanece) ou **(D) docs**. O subconjunto que muda comportamento — **(K) chave** — é da ordem de **~40–50 arquivos** (rotas de intelligence, árvore BFF do Workspace, ~20 hooks, links de página, mock+E2E, `ProjectSummaryService`, `AnalysisRecord`). |
| **Riscos identificados** | 2 de nível **Alto** (contrato das APIs de intelligence; `DROP COLUMN`), ambos confinados a etapas específicas com aditividade/backup/downgrade; demais **Médio/Baixo** mitigáveis por incremento. |
| **Estratégia recomendada** | **Migração incremental de 5 etapas, dual-key, aditiva-primeiro**, com a única etapa destrutiva (4) isolada por último, precedida de backup e migração de downgrade testada. Preferir 5 PRs pequenos e auditáveis a uma mudança ampla única — exatamente a preferência do Founder. Cada PR carrega seu próprio gate verde completo. |

**Benefício de governança:** este documento é o registro formal da migração arquitetural (escopo, mapa de dependência, plano, riscos, validação) — evidência para o Enterprise Readiness Program e para auditorias futuras da v1.0, conforme o objetivo estratégico do Founder.

---

## 7. Recomendação e ponto de decisão

**Recomendação:** aprovar a estratégia incremental de 5 etapas acima e autorizar o início pela **Etapa 1 (aditiva, zero remoção, risco baixo)**, que é reversível e não muda nenhum contrato existente.

**Decisão do Founder pendente (Fase 3):** esta migração **não inicia implementação** até aprovação explícita. Além do go/no-go, há um ponto de desenho a ratificar:

> Na Etapa 4, `project_name` deixa de ser chave de `AnalysisRecord`, mas o **input de análise** (o usuário digita um nome de projeto ao "Analisar Projeto") permanece — resolvido para um `project_id` via `get_or_create_project_for_name`, com o nome vivendo em `projects.name`. Isso preserva a UX atual ("digitar um projeto para analisar") sem forçar a seleção por id. Confirmar que esse é o end-state desejado (alternativa seria forçar seleção de um Project existente por id, o que **seria** uma mudança de UX e não é recomendado nesta migração).

**Nenhum código foi alterado nesta fase.** Aguardando aprovação para iniciar a Etapa 1.
