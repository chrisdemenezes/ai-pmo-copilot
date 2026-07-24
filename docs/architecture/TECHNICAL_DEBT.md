# STRATECH — Technical Debt Register

Registro vivo de débitos arquiteturais conhecidos. Cada item tem origem, status e o gatilho que exige sua resolução — nenhum item aqui é corrigido automaticamente por esta entrada; a correção é um trabalho futuro separado, autorizado individualmente quando seu gatilho ocorrer.

**Referência cruzada por Wave:** `docs/product/ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §11 mapeia cada item abaixo a uma Wave do Enterprise Master Execution Program, sem duplicar ou alterar o conteúdo original deste registro.

---

## TD-001 — SQLite Foreign Keys não aplicadas pelo motor

- **Origem:** PR #39 (Épico 1 — Enterprise Foundation Schema)
- **Status:** Aberto
- **Descrição:** O SQLite não aplica constraints de FK por padrão; nenhuma conexão desta aplicação executa `PRAGMA foreign_keys=ON`. Todas as FKs declaradas nos modelos/migração (`organizations`, `users`, `projects`, etc.) são estruturalmente corretas mas não são impostas pelo motor em tempo de execução no caminho SQLite (o caminho Postgres, se usado em produção, aplica FKs por padrão).
- **Evidência:** comprovado por execução real durante a Executive Pre-Merge Architecture Review — um `DELETE FROM organizations` com usuários e projetos filhos executa sem erro.
- **Resolver antes de:** qualquer fluxo de exclusão (organização, usuário ou projeto) ser exposto por API ou UI.

## TD-002 — Delete Policy indefinida (RESTRICT vs. CASCADE)

- **Origem:** PR #39 (Épico 1 — Enterprise Foundation Schema)
- **Status:** Aberto
- **Descrição:** Nenhuma FK possui `ondelete` definido; nenhum `relationship()` ORM com cascade existe. Combinado com TD-001, uma exclusão real hoje produziria órfãos silenciosos em vez de RESTRICT (bloquear) ou CASCADE (propagar) — nenhuma das duas é a política atual; a política atual é "nenhuma".
- **Decisão pendente:** escolher RESTRICT ou CASCADE por relação (ex.: excluir Organização deveria bloquear se houver Projetos, ou excluir em cascata?) é uma decisão de produto/arquitetura, não apenas técnica.
- **Resolver antes de:** o primeiro endpoint `DELETE` de qualquer entidade da Enterprise Foundation (candidato natural: Épico 5 — Auditoria e administração mínima).

## TD-003 — Convenção de sessão do Repository inconsistente

- **Origem:** PR #39 (Épico 1 — Enterprise Foundation Schema)
- **Status:** Planejado
- **Descrição:** `EnterpriseRepository` mistura dois padrões: a maioria dos métodos abre sua própria sessão (`with self._session_factory() as session`), mas dois métodos (`get_or_create_default_organization`, `get_or_create_project_for_name`) recebem uma sessão externa para participar da transação do chamador. Funciona e está documentado via docstring, mas não há convenção de nome (ex.: sufixo `_in_session`) que distinga os dois grupos à primeira vista.
- **Resolver durante:** o Épico RBAC (Épico 3), quando a classe crescer com novos métodos de escrita e o risco de uso incorreto do padrão errado aumentar.

## TD-007 — Domínio Portfolio/Program/Project (Capabilities 01-03) ainda sem persistência, sem escopo multi-tenant

- **Origem:** Architecture Review AR-1 (Release 0.2), auditando as Capabilities 01-03.
- **Classificação:** Médio.
- **Status:** **Resolvido** (Wave 2, Sprint 1 — 2026-07-19).
- **Descrição:** `web/lib/domain/{portfolio,program,project}.ts` existiam apenas como domínio de frontend, sem tabela/model/migração em `src/database`.
- **Resolução:** migração `0005_domain_persistence` cria `portfolios`/`programs` (org-escopadas desde a primeira migração, per o plano original) e estende `projects` com os campos de domínio — `CrossTenantViolationError` aplicado em toda escrita (`src/database/domain_repository.py`), 16 testes de segregação/migração passando. **Pendente, não coberto por esta resolução:** o frontend (`web/lib/domain/*.ts`) ainda lê dos arrays semeados em memória, não desta persistência — a troca é a próxima Sprint (API + RBAC), rastreada como trabalho de Sprint, não mais como TD.

## TD-008 — Três conceitos "Project" coexistem no código, sem unificação

- **Origem:** Capability 03 (Decision Log D-019), confirmado na Architecture Review AR-1.
- **Classificação:** Médio.
- **Status:** Em progresso (Fase 3a de 3 concluída, Wave 3 Epic W3-1 — 2026-07-23).
- **Descrição:** (1) o `Project` real do backend (`src/database/models.py`, Épico 1, persistido, hoje só usado para membership); (2) `ProjectSummary` (`web/lib/dashboard/types.ts`, dado real do V1/BFF, chaveado por `project_name` livre); (3) `Project` do domínio (`web/lib/domain/project.ts`, Capability 03, vinculado a Program). Nenhum compartilha ID.
- **Progresso:** per `DOMAIN-BLUEPRINT-PROJECT.md` (Opção A, faseada) — **Fase 1 concluída** (Sprint 1): os campos de domínio vivem na mesma tabela `projects` do Épico 1, não em uma `projects_delivery` separada. **Fase 2 concluída** (Sprint 5): o frontend lê da API real (arrays semeados deletados), e a migração `0008_domain_seed` executou a unificação in-place para os Projects legados com nome colidente ("Multilift"/"Aurora" — atualizados, nunca duplicados). **Fase 3a concluída** (Wave 3, Epic W3-1 — `DOMAIN-BLUEPRINT-PROJECT-IDENTITY-UNIFICATION.md`): `ProjectSummaryService.summarize_portfolio()` agrupa por `project_id` em vez do `project_name` bruto (corrige um bug real: nomes que diferem só por espaço em branco resolviam ao mesmo `project_id` mas apareciam como 2 entradas de portfólio); `ProjectSummaryResponse`/`ProjectSummary` ganham `project_id` aditivo. **Fase 3b (não iniciada, escopo grande):** migrar rotas/BFF/todo o consumo de frontend (Dashboard, Portfólio, Decision Center, Executive Focus, Workspace) de `project_name` para `project_id` como chave primária de fato, aposentando `ProjectSummary` por completo — raio de impacto abrange praticamente toda a experiência executiva; candidata a um Epic dedicado futuro da Wave 3.
- **Resolver antes de:** Fase 3b não tem gatilho definido ainda — candidata a um Epic futuro da Wave 3, não urgente (nenhum bug ativo pendente após a Fase 3a).
- **Plano de resolução:** `docs/architecture/PHASE-2-FOUNDATION-ARCHITECTURE.md` §2 recomendava que Épico 4 e a persistência de `projects_delivery` fossem uma única Engineering Order — **premissa corrigida na AR-2** (`AR-2-WAVE-3-ARCHITECTURE-REVIEW.md` §2): `projects_delivery` nunca chegou a existir como tabela separada (Fase 1 já unificou os campos na própria `projects`), então esse gate específico não se aplica mais.

## TD-009 — Cobertura de testes do frontend não instrumentada

- **Origem:** RC-2 Enterprise Release Certification, Etapa 5 (Qualidade).
- **Classificação:** Baixo.
- **Status:** Aberto.
- **Descrição:** `web/` não tem `@vitest/coverage-v8` instalado — `vitest run --coverage` falha por dependência ausente. O backend (`src/`) já mede cobertura real (97%, via `pytest --cov`); o frontend não tem visibilidade equivalente. Consistente com o pilar "Observabilidade" do Product Maturity Model, hoje em 0%.
- **Resolver antes de:** nenhum gatilho específico — melhoria de visibilidade, não um risco ativo. Candidato natural para quando a Phase 2 exigir métricas de qualidade mais rigorosas.

## TD-010 — Nenhum armazenamento server-side de sessão (revogação real não é possível)

- **Origem:** Wave 2, Sprint 4 (Enterprise Administration) — encontrada ao tentar implementar "Sessões" per `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §2.
- **Classificação:** Médio (segurança/observabilidade prospectiva).
- **Status:** ✅ **RESOLVIDO — D-053** (item 5 do Wave Completion Review retrospectivo, 2026-07-24).
- **Descrição:** a sessão da STRATECH era um cookie HMAC-assinado, sem estado no servidor (`src/services/identity/auth_service.py`, `logout()`: "No server-side session store exists yet"). Não havia como listar sessões ativas nem revogar uma sessão antes da expiração natural (12h) — um logout era apenas o cliente descartando o cookie. O Blueprint de Administration assumiu incorretamente que isso já existia ("painel é só leitura+revogação sobre o que já existe").
- **Resolução (D-053):** nova tabela `sessions` (migração 0012, `revoked_at`), `session_id` cunhado pelo backend no login em vez do BFF, `AuthService.logout()` revoga a linha, e enforcement de revogação em `require_permission` (uma sessão revogada é rejeitada com 401 na requisição seguinte). Fail-open para ids não rastreados (não quebra sessões anteriores ao store). Painel `/administracao/sessoes` para listagem/revogação. Ver `TECHNICAL-DESIGN-SESSIONS.md`.

---

## Baseline Defects — falhas E2E pré-existentes, não introduzidas por Épicos

Categoria distinta de TD-001/002/003: não são débitos arquiteturais de uma decisão de design, mas defeitos de comportamento já presentes no baseline antes do Épico que os documenta, comprovados por reprodução contra esse baseline. Registrados aqui para que nunca sejam confundidos com uma regressão introduzida por um Épico subsequente, e para que não sejam silenciosamente esquecidos por não bloquearem o Regression Gate.

### TD-004 — Race de invalidação do React Query após "Analisar Projeto" (Avaliação de Riscos)

- **Categoria:** Baseline Defect
- **Origem confirmada:** pré-existente ao Épico 2 (Identity Foundation) e ao PR #39 (Épico 1). Não introduzida pela correção de escopo organizacional (EO-015).
- **Status:** **Resolvido** (Wave Completion Review retrospectivo, item 2 — ver D-050).
- **Teste afetado:** `web/e2e/workspace.spec.ts` › `Avaliação de Riscos (TIP-006)` › `runs a full risk analysis via the Avaliação de Riscos tab and reflects it in the Workspace and the Dashboard`
- **Sintoma:** após submeter uma nova Avaliação de Riscos, o Intelligence Timeline registra o novo evento (a mutação teve sucesso no backend/mock), mas o painel "Riscos" não é atualizado com o novo resultado — continua mostrando o risco anterior. Mesmo mecanismo documentado inline em `executive-memory.spec.ts:54-60`: se o fetch inicial de uma query ainda está em voo no instante em que a mutação invalida o cache, o React Query não dispara um novo fetch (já há um em voo) e a invalidação é "engolida" pela resolução do fetch obsoleto.
- **Evidência de reprodução no baseline:** `git stash push -u` (removendo as 36 alterações do Épico 2/EO-015 da árvore de trabalho) → `npx playwright test e2e/workspace.spec.ts -g "runs a full risk analysis via the Avaliação de Riscos tab" --project=md` → falha idêntica (mesmo locator, mesma mensagem, mesma linha relativa) contra o código anterior a esta correção → `git stash pop` restaura o trabalho do Épico 2 sem perda. Falha reproduzida de forma determinística em múltiplas execuções (3/3), antes e depois do stash.
- **Correção aplicada:** `useSubmitRiskReview` (`use-submit-risk-review.ts`) agora chama `queryClient.cancelQueries(...)` em `workspace-latest`/`workspace-recent` **antes** de `invalidateQueries` no `onSuccess` da mutação — força o fetch de volta a `idle` para que a invalidação sempre dispare um fetch genuinamente novo, mesmo quando o primeiro fetch da montagem ainda está em voo.
- **Verificação:** comparação controlada A/B no mesmo servidor (sem reiniciar): código-base falha 8/8 em execuções repetidas do teste isolado; com a correção, 20/20 (`--repeat-each=5`, TIP-006+TIP-007 juntos) e passes limpos nos 3 breakpoints (lg/md/mobile) da suíte completa.

### TD-005 — Mesmo race, painel de Comunicação (O que mudou na última reunião?)

- **Categoria:** Baseline Defect
- **Origem confirmada:** pré-existente ao Épico 2. Mesmo mecanismo de TD-004, painel diferente.
- **Status:** **Resolvido** (Wave Completion Review retrospectivo, item 2 — ver D-050).
- **Teste afetado:** `web/e2e/workspace.spec.ts` › `O que mudou na última reunião? (TIP-007)` › `runs a full meeting analysis via the 3rd tab and reflects it in the Workspace and the Dashboard`
- **Sintoma:** idêntico a TD-004, aplicado ao painel "Comunicação" após uma análise de reunião.
- **Evidência:** falha intermitente na mesma suíte completa (5/202 e 7/202 falhas em duas execuções completas), sempre restrita a este teste e aos de TD-004/TD-006 — nunca a testes fora desse padrão de "reflete mutação sem reload".
- **Correção aplicada:** `useSubmitMeetingIntelligence` (`use-submit-meeting-intelligence.ts`) ganha o mesmo `cancelQueries` antes de `invalidateQueries` em `workspace-latest` (esta análise nunca teve `workspace-recent`, então só a 1 chave).
- **Verificação:** mesma comparação A/B; passes limpos nos 3 breakpoints da suíte completa (81/81, 81/81, 82/82 -- lg/md/mobile).
- **Nota de infraestrutura de teste (não é o TD em si):** durante a verificação, `npx playwright test --repeat-each=N` neste mesmo teste mostrou falhas mesmo contra o código-base sem a correção, com um sintoma diferente (o próprio "Análise concluída" nunca aparece, não a invalidação silenciosa) -- isolado como um artefato do cache de build `.next` do servidor de desenvolvimento degradando sob uso muito intenso e prolongado de hot-reload dentro da mesma sessão (não reproduz após `rm -rf web/.next`); não é uma falha de produção nem está relacionado à correção de TD-004/005/006.

### TD-006 — Mesmo race, Executive Memory Insight "Mudou"

- **Categoria:** Baseline Defect
- **Origem confirmada:** pré-existente — já documentado inline no próprio teste (`executive-memory.spec.ts:54-60`) desde o Incremento 1 de Executive Memory, muito antes do Épico 2.
- **Status:** **Resolvido** (Wave Completion Review retrospectivo, item 2 — ver D-050).
- **Teste afetado:** `web/e2e/executive-memory.spec.ts` › `shows a Mudou Executive Memory Insight right after Analisar Projeto changes the health status`
- **Sintoma:** idêntico a TD-004/005, aplicado ao Executive Brief / Memory Insight.
- **Correção aplicada:** `useSubmitProjectStatus` (`use-submit-project-status.ts`) ganha o mesmo `cancelQueries` antes de `invalidateQueries`, em `workspace-latest` e `workspace-recent`.
- **Verificação:** comparação A/B controlada, mesmo servidor, sem reiniciar entre execuções -- código-base falha 8/8 em `--repeat-each=8`; com a correção, 8/8 aprovado. Prova direta de que a correção elimina a corrida (não apenas reduz sua frequência).

---

## RC-2 Classification Matrix (Etapa 6, Enterprise Release Certification)

Classificação por dimensão (Arquitetural/Código/Performance/UX/Segurança/Documentação), impacto, prioridade, probabilidade, esforço e se bloqueia a Phase 2 — Enterprise AI Platform.

| TD | Dimensão | Impacto | Prioridade | Probabilidade | Esforço | Bloqueia Phase 2? |
|---|---|---|---|---|---|---|
| TD-001 | Arquitetural | Alto | Média | Baixa (só se um DELETE for exposto) | Baixo | NÃO |
| TD-002 | Arquitetural | Alto | Média | Baixa (mesma condição de TD-001) | Médio (decisão de produto + implementação) | NÃO |
| TD-003 | Código | Baixo | Baixa | Baixa | Baixo | NÃO |
| TD-004/005/006 | Código | Médio (UX momentâneo, corrige em refetch) | Média | Média (intermitente, comprovado) | Médio (revisão de invalidação de queries) | NÃO |
| TD-007 | Arquitetural + Segurança (prospectivo) | Alto (se esquecido no dia da persistência) | Alta (quando o backend for wireado) | Baixa hoje (nada persistido ainda) | Baixo (padrão já estabelecido no Épico 1) | NÃO hoje — mas resolver antes de qualquer persistência real de Portfolio/Program/Project |
| TD-008 | Código + Documentação | Médio (risco de confusão para novo engenheiro) | Média | Média | Alto (unificação real é o Épico 4) | NÃO |
| TD-009 | Documentação | Baixo | Baixa | N/A (lacuna de instrumentação, não um risco ativo) | Baixo (instalar `@vitest/coverage-v8`) | NÃO |

**Nenhum item bloqueia o início da Phase 2.** TD-007 é o único com prioridade que sobe de "não bloqueante" para "resolver antes de" no momento em que qualquer entidade deste domínio for persistida em banco — condição ainda não disparada.

---

## Convenção de uso deste registro

- Novo débito identificado por qualquer revisão (arquitetural, de segurança, de código) ganha um ID sequencial `TD-NNN` aqui, com origem (PR/commit), status (`Aberto` / `Planejado` / `Resolvido`) e o gatilho explícito de resolução.
- Nenhum item é resolvido silenciosamente: a resolução de um TD é um commit/PR próprio que referencia o ID e atualiza o status para `Resolvido`, com a data e o PR de resolução.
- Este documento não substitui ADRs — um TD pode motivar um ADR futuro quando sua resolução envolver decisão arquitetural (como é o caso de TD-002).
- **Categoria "Baseline Defect"** (TD-004+): usada quando um Épico encontra uma falha de teste E2E/CI que uma reprodução contra o baseline anterior (antes das mudanças do próprio Épico) comprova já existir. Registrar aqui em vez de bloquear o Regression Gate do Épico — a evidência de reprodução (comando, resultado, commit de referência) fica descrita no próprio item, para que a falha nunca seja confundida com uma regressão introduzida por trabalho subsequente nem seja silenciosamente esquecida.
