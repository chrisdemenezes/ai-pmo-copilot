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
- **Status:** **RESOLVIDO** (2026-07-26 — D-061). Fase 3a (W3-1) + Fase 3b completa (Etapas 1, 2, 3, 5, 4a e 4b) — item 8 do Wave Completion Review retrospectivo. `project_id` é a única chave de acesso interno ao Project; a coluna legada `analysis_records.project_name` foi removida (migração 0015, Etapa 4b); `Project.name` é a única fonte do nome de exibição.
- **Descrição:** (1) o `Project` real do backend (`src/database/models.py`, Épico 1, persistido, hoje só usado para membership); (2) `ProjectSummary` (`web/lib/dashboard/types.ts`, dado real do V1/BFF, chaveado por `project_name` livre); (3) `Project` do domínio (`web/lib/domain/project.ts`, Capability 03, vinculado a Program). Nenhum compartilha ID.
- **Progresso:** per `DOMAIN-BLUEPRINT-PROJECT.md` (Opção A, faseada) — **Fase 1 concluída** (Sprint 1): os campos de domínio vivem na mesma tabela `projects` do Épico 1, não em uma `projects_delivery` separada. **Fase 2 concluída** (Sprint 5): o frontend lê da API real (arrays semeados deletados), e a migração `0008_domain_seed` executou a unificação in-place para os Projects legados com nome colidente ("Multilift"/"Aurora" — atualizados, nunca duplicados). **Fase 3a concluída** (Wave 3, Epic W3-1 — `DOMAIN-BLUEPRINT-PROJECT-IDENTITY-UNIFICATION.md`): `ProjectSummaryService.summarize_portfolio()` agrupa por `project_id` em vez do `project_name` bruto (corrige um bug real: nomes que diferem só por espaço em branco resolviam ao mesmo `project_id` mas apareciam como 2 entradas de portfólio); `ProjectSummaryResponse`/`ProjectSummary` ganham `project_id` aditivo. **Fase 3b (não iniciada, escopo grande):** migrar rotas/BFF/todo o consumo de frontend (Dashboard, Portfólio, Decision Center, Executive Focus, Workspace) de `project_name` para `project_id` como chave primária de fato, aposentando `ProjectSummary` por completo — raio de impacto abrange praticamente toda a experiência executiva; candidata a um Epic dedicado futuro da Wave 3.
- **Fase 3b (em execução, 5 etapas incrementais):** ver `TD-008-PHASE-3B-IMPACT-ASSESSMENT.md` (escopo/mapa de dependência/plano/riscos/validação, aprovado pelo Founder). **Etapa 1 concluída** (aditiva, zero remoção): as rotas de intelligence (`/analyses`, `/action-items`, `/risks/latest`, `/projects/summary`) aceitam `project_id` além de `project_name`, com resolução dual-key org-escopada (`EnterpriseRepository.resolve_project_reference`) que rejeita explicitamente id inexistente/cross-org (404), divergência id≠nome (409) e nome ambíguo (409); `AnalysisRecord.project_id` re-backfillado defensivamente (migração 0014, não-destrutiva, sem NOT NULL). **Achado da Etapa 1:** o constraint `uq_projects_org_name` já garante nome único por organização — a ambiguidade de nome que a migração temia é estruturalmente impossível hoje (o branch de ambiguidade do resolver é código defensivo à prova de futuro). **Etapa 2 concluída** (frontend-only, aditiva, zero remoção — D-057): as 4 rotas BFF de intelligence encaminham `project_id` opcional; `WorkspaceSummary` e os hooks escopados (`use-workspace-summary`/`use-latest-risks`/`use-action-items`/`use-workspace-latest`/`use-recent-analyses`/`use-workspace-timeline`) carregam `project_id` coexistindo com o nome; em `executive-brief.tsx` o `project_id` resolvido pelo summary é reaproveitado como chave exata nas leituras irmãs (independência de painéis preservada, fallback por nome enquanto o summary carrega). **Etapa 3 concluída** (frontend-only, aditiva, zero remoção — D-058): os consumidores escopados restantes do Workspace (`RisksPanel`, `CommunicationBrief`, `IntelligenceTimeline`, `AnalysisHistory`, `ActionsSection`, `ActionsContextLine`) passam a usar `project_id` como chave primária via o hook compartilhado `useResolvedProjectId` (reaproveita a resolução nome→id do summary, deduplicada pelo React Query — sem resolução redundante); `keepPreviousData` mantém a troca de chave sem flash; independência de painéis preservada e reflexo pós-mutação inalterado (invalidações casam por prefixo de chave). `project_name` permanece como atributo de exibição. **Etapa 5 concluída** (frontend-only, sem tocar no banco — D-059; **reordenada para antes da Etapa 4** por decisão do Founder): `ProjectSummary` (`lib/dashboard/types.ts`) e `WorkspaceSummary` (`lib/workspace/types.ts`) — dois espelhos duplicados do mesmo read-model de inteligência de um Project — foram consolidados no tipo canônico `ProjectIntelligenceSummary` (`lib/project/intelligence-summary.ts`), ancorado em `project_id` (`project_name` só exibição); todos os consumidores migrados, as definições antigas removidas. Rejeitada a fusão com a entidade de Entrega `Project` (`lib/domain/project.ts`) — bounded context distinto. Backend inalterado (`ProjectSummaryService`/`ProjectSummaryResponse` seguem como produtor da projeção). **Gate Final de Migração aprovado** (veredito NÃO-GO para a destrutiva estava correto — governança funcionou). **Etapa 4a concluída** (aditiva, reversível — D-060): `project_id` é a **única chave de escopo de leitura**; resolvidos os resíduos R1-R6 — `list_analyses` id-only (`AnalysisRepository.resolve_scope_id` reutilizado pelo serviço e pelo `AIContextEngine`); display derivado de `Project.name` via `AnalysisRecord.project`/`analysis_display_name` (sentinela→`None`); `list_latest_risks` dedup por `project_id`, `summarize_portfolio` agrupa por id; responses (`AnalysisSummary`/`ActionItemResponse`/`LatestRiskItemResponse`) e joins de frontend (`decision-queue`/`portfolio-view`) por `project_id`; `save_analysis` não grava mais a coluna. `ProjectSummaryResponse`/`ProjectSummaryService` mantidos e classificados como projeção de leitura/serviço de composição (`DOMAIN-MODEL.md`). **Etapa 4b concluída** (destrutiva — D-061): migração `0015` **ativada** (`alembic heads` = `0015`) — `SET NOT NULL` em `analysis_records.project_id` + `DROP COLUMN analysis_records.project_name` + drop do índice; campo `project_name` **removido do ORM**; `project_id` agora `nullable=False`. Nome preservado como apresentação (`Project.name`; o campo `project_name` permanece nas responses, derivado de `Project.name` — zero regressão de frontend). Downgrade **íntegro**: recria a coluna e **repopula `project_name` de `projects.name` via `project_id`**, provado em PostgreSQL real (`tests/test_migration_0015_drop_project_name.py`). **TD-008 RESOLVIDO** — todos os critérios de encerramento satisfeitos (0015 ativa; coluna removida; rollback íntegro comprovado; suíte verde: ruff/pytest 449/tsc/eslint/vitest 491/E2E 292; docs atualizadas; sem compatibilidade temporária desnecessária).
- **Resolver antes de:** Fase 3b em execução como item 8 do Wave Completion Review retrospectivo — cada etapa é um PR próprio, verde de ponta a ponta, com gate destrutivo (Etapa 4) exigindo nova aprovação explícita do Founder.
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

## TD-011 — Backend de embeddings de produção não escolhido (Enterprise Knowledge Platform)

- **Origem:** Wave 3, Fase 1 (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.4) — decisão explicitamente diferida à época, reafirmada nas Fases 2 e 4.
- **Classificação:** Baixo (sem consumidor real ainda).
- **Status:** Aberto.
- **Descrição:** `EmbeddingProvider` (Protocol) só tem uma implementação, `MockEmbeddingProvider` (determinística, hash-based) — nenhum backend de produção (modelo de embeddings real) foi escolhido ou integrado. O Risk Advisor migrado (Fase 4) já chama `RagPipeline`/`KnowledgeRepository` em produção, mas sobre embeddings mock, já que nenhum documento real é ingerido para o domínio de risco hoje.
- **Gatilho de resolução:** quando um Advisor real precisar de qualidade semântica de produção sobre conteúdo real ingerido — o candidato natural é o Document Advisor (Wave 5 — Enterprise Advisors, per a harmonização oficial do roadmap em D-071), o primeiro Advisor com dependência obrigatória de RAG.

## TD-012 — Document Ingestion real (parsing de formatos binários) não implementado

- **Origem:** Wave 3, Fase 1 (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.2) — escopo explicitamente reduzido a texto já normalizado (`str`).
- **Classificação:** Baixo (sem consumidor real ainda).
- **Status:** Aberto.
- **Descrição:** `KnowledgeRepository.ingest()` aceita apenas texto já normalizado — não há parser de PDF/DOCX/outros formatos binários.
- **Gatilho de resolução:** quando o Document Advisor (ou qualquer Advisor real) precisar ingerir um documento em formato binário real, não apenas texto.
- **Nota de atualização (D-090, Epic W5-0):** o Epic W5-0 (Document Ingestion) entregou um fluxo HTTP real (`POST /documents`) para texto/markdown já normalizado, exatamente o limite de escopo que este TD sempre documentou — não resolve TD-012, apenas confirma que o caminho de texto (já suportado por `ingest()`) agora tem um chamador real além dos testes. Gatilho de PDF/binário permanece não disparado.

## TD-014 — Evidence Confidence (campo `confidence`) não implementado

- **Origem:** AR-9 (`AR-9-DOCUMENT-ADVISOR-ARCHITECTURE-REVIEW.md` §8), Technical Design W5-0 (§8), Founder Decision — Technical Design W5-0 (D-090): postergação oficializada.
- **Classificação:** Baixo (sem consumidor real, semanticamente indefinido para `source_type="analysis_record"`).
- **Status:** Deferred.
- **Descrição:** o contrato definitivo de `Evidence` (`source_type`/`source_id`/`source_label`/`content`/`metadata`, aprovado em AR-9/D-088) não inclui um campo `confidence`. Tecnicamente aditivo e barato de adicionar (`confidence: float | None = None`), mas sem nenhum consumidor real hoje em `RecommendationEngine`/`ExplanationEngine`/qualquer Advisor, e seria semanticamente falso para evidência de `AnalysisRecord` (sem sinal de confiança natural equivalente ao `score` de similaridade do RAG).
- **Gatilho de resolução:** primeiro produtor real capaz de calcular confiança de maneira objetiva (ex.: Document Advisor filtrando/exibindo citações por `score` de similaridade do RAG) — nesse momento, extensão aditiva trivial ao dataclass já aprovado, populado a partir de `chunk.score` apenas para `source_type="document_chunk"`, permanecendo `None` para `analysis_record` até essa fonte também ganhar um sinal real.

## TD-015 — Chave literal `"cited_analysis_ids"` em `AdvisorFramework.run()` carrega vocabulário do Risk Advisor, não genérico

- **Origem:** Technical Design — Document Advisor (`TECHNICAL-DESIGN-DOCUMENT-ADVISOR.md` §5.2/§8.4), achado durante o desenho do prompt do `DocumentAdvisorAgent`.
- **Classificação:** Baixo (cosmético — nenhum impacto funcional).
- **Status:** Deferred (decisão explícita de AR-10, `AR-10-GOVERNANCE-ADVISOR-ARCHITECTURE-REVIEW.md` §2 — não uma nova postergação vaga).
- **Descrição:** `AdvisorFramework.run()` lê `model_output.get("cited_analysis_ids")` literalmente (`framework.py:98`) para popular `RecommendationEngine.build()` — nome herdado do Risk Advisor, anterior ao rename de `Evidence.source_analysis_id` → `source_id` (D-088). Para o Document/Governance Advisor, os valores retornados por essa chave são `chunk_id`, não `analysis_id` — funcionalmente correto (ambos `int`, compatíveis com `source_id`), mas o nome da chave é enganoso para quem lê o prompt/código sem o contexto histórico. Corrigir exigiria alterar `AdvisorFramework.run()`.
- **Avaliação do gatilho (AR-10):** o gatilho anterior ("segundo Advisor baseado em RAG") chegou com o Governance Advisor — avaliado explicitamente nesta Architecture Review, não ignorado. Decisão: **não resolver nesta Epic**, porque a mesma autorização do Founder que exigiu essa avaliação também determinou preservar `AdvisorFramework` integralmente nesta revisão — as duas exigências são estruturalmente incompatíveis dentro do mesmo Epic, e a preservação do Framework prevalece.
- **Gatilho de resolução (revisado, mais específico, per AR-10):** uma mudança de manutenção **isolada e explicitamente autorizada pelo Founder**, nunca bundlada à entrega funcional de um Advisor específico (nem deste Epic, nem de um terceiro Advisor futuro) — um rename em `AdvisorFramework.run()` afeta simultaneamente todos os Advisors já em produção (Risk, Document, Governance), e misturá-lo com a entrega de um Advisor aumentaria o raio de impacto de um commit sem necessidade.

## TD-013 — Enterprise Memory Model: Consolidação e Expiração automática não implementadas

- **Origem:** Wave 3, Fase 2 (`DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §4) — escopo explicitamente limitado a Captura+Classificação+Consulta.
- **Classificação:** Baixo (sem consumidor real ainda).
- **Status:** Aberto.
- **Descrição:** `EnterpriseMemoryService` implementa `classify()`/`list_by_category()`; a promoção a memória organizacional ("Consolidação") e a expiração automática de memória operacional/documental não existem.
- **Gatilho de resolução:** quando um Advisor real precisar consultar memória organizacional consolidada (padrões emergentes entre múltiplos projetos) ou depender de expiração automática para não reter memória operacional indefinidamente.

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
| TD-008 | Código + Documentação | ✅ **RESOLVIDO** (2026-07-26, D-061 — `project_id` é a única chave; coluna `project_name` removida) | — | — | — | NÃO |
| TD-009 | Documentação | Baixo | Baixa | N/A (lacuna de instrumentação, não um risco ativo) | Baixo (instalar `@vitest/coverage-v8`) | NÃO |

**Nenhum item bloqueia o início da Phase 2.** TD-007 é o único com prioridade que sobe de "não bloqueante" para "resolver antes de" no momento em que qualquer entidade deste domínio for persistida em banco — condição ainda não disparada.

---

## Classificação Final — Wave 2 Closure Review (2026-07-27)

Toda a Wave Completion Policy (D-048) exige que nenhum item deste registro permaneça sem classificação ao encerrar uma Wave. Classificação obrigatória em uma de quatro categorias — **Resolvido** / **Postergado** (gatilho definido, ainda não disparado) / **Business Pending** (aguarda decisão de negócio do Founder) / **Futuro Roadmap** (sem risco ativo, candidato a uma Wave futura):

| TD | Classificação | Justificativa |
|---|---|---|
| TD-001 (FK não aplicadas em SQLite) | **Postergado** | Gatilho ("qualquer DELETE exposto") auditado nesta revisão: os 4 `DELETE` reais hoje (`remove_role`, `revoke_api_key`, `revoke_session`, `cancel_invitation`) são revogações/soft-deletes de registros-folha sem filhos por FK — nenhum dispara o cenário de órfãos que o TD descreve. Adicionalmente, o ambiente oficial (Postgres, desde RC-2/D-037) já aplica FK por padrão; o risco real está isolado ao fallback SQLite zero-dependência (instalações locais sem `DATABASE_URL`). Gatilho não disparado. |
| TD-002 (Delete Policy indefinida) | **Postergado** | Mesma auditoria de TD-001: nenhum `DELETE` real de uma entidade com filhos por FK (Organization/User/Project) existe hoje. Decisão de produto (RESTRICT vs. CASCADE) continua pendente, mas sem urgência técnica. |
| TD-003 (convenção de sessão do Repository) | **Postergado** | `EnterpriseRepository` cresceu substancialmente ao longo da Wave 2 (RBAC, Administration, API Keys, Sessões, Convites) sem que a inconsistência de convenção (`_in_session` vs. sessão própria) tenha causado um bug real — nenhum incidente registrado em nenhuma Decision Log. Baixo risco, baixo esforço; sem gatilho novo disparado nesta revisão. |
| TD-004/005/006 (race de invalidação do React Query) | ✅ **Resolvido** | D-050 (item 2 do Wave Completion Review retrospectivo). `cancelQueries` antes de `invalidateQueries` nos 3 hooks de mutação. Verificado A/B, 3 breakpoints E2E. |
| TD-007 (Portfolio/Program/Project sem persistência) | ✅ **Resolvido** | Wave 2, Sprint 1 (D-032). Migração `0005_domain_persistence`; `CrossTenantViolationError` em toda escrita. |
| TD-008 (três conceitos "Project") | ✅ **Resolvido** | D-061. `project_id` é a única chave de acesso interno ao Project; coluna legada `analysis_records.project_name` removida (migração 0015); `Project.name` é a única fonte do nome de exibição. |
| TD-009 (cobertura de frontend não instrumentada) | **Futuro Roadmap** | Nenhum risco ativo — lacuna de instrumentação, não um defeito. Candidato natural para quando a Wave 5 (Enterprise Analytics/Observabilidade) ou um gate de qualidade mais rigoroso exigir métricas de cobertura do frontend; instalar `@vitest/coverage-v8` é o único trabalho pendente. |
| TD-010 (sem armazenamento server-side de sessão) | ✅ **Resolvido** | D-053 (item 5 do Wave Completion Review retrospectivo). Tabela `sessions`, revogação real, enforcement em `require_permission`. |

**Nenhum item permanece sem classificação.** 5 de 8 itens ativos estão **Resolvidos**; 3 (TD-001/002/003) são **Postergados** com gatilho explícito ainda não disparado (nenhum bloqueia a Wave 3); 1 (TD-009) é **Futuro Roadmap**, sem risco ativo. Nenhum item desta revisão é **Business Pending** — essa categoria se aplica aos itens de roadmap fora do TD Register (Tenant/System Settings, D-052) tratados no `WAVE-2-CLOSURE-REPORT.md`.

---

## Classificação Final — Wave 3 Closure Review (2026-07-27)

A mesma disciplina da Wave Completion Policy (D-048) aplicada ao fechamento da Wave 2 é reaplicada aqui: nenhum item deste registro pode permanecer sem classificação ao encerrar a Wave 3. Os itens TD-001/002/003/009 são reconfirmados sem alteração (nenhuma decisão desta Wave mudou seu gatilho ou seu risco); TD-004/005/006/007/008/010 seguem **Resolvidos**, como já registrado. Os três itens novos, abertos durante as Fases 1 e 2 desta Wave, recebem classificação final abaixo:

| TD | Classificação | Justificativa |
|---|---|---|
| TD-001 (FK não aplicadas em SQLite) | **Postergado** (reconfirmado) | Nenhum novo `DELETE` foi introduzido pela Wave 3 (Enterprise Knowledge Platform/Advisor Framework são exclusivamente `INSERT`/`SELECT`). Gatilho inalterado, não disparado. |
| TD-002 (Delete Policy indefinida) | **Postergado** (reconfirmado) | Mesma auditoria de TD-001 — nenhuma entidade da Wave 3 introduz um `DELETE` de registro com filhos por FK. |
| TD-003 (convenção de sessão do Repository) | **Postergado** (reconfirmado) | `KnowledgeRepository`/`EnterpriseMemoryService` (Wave 3) seguiram a convenção de sessão já estabelecida no `AnalysisRepository`/`EnterpriseRepository`, sem introduzir uma terceira convenção nem agravar a inconsistência existente. |
| TD-009 (cobertura de frontend não instrumentada) | **Futuro Roadmap** (reconfirmado) | Nenhuma mudança de frontend nesta Wave (Wave 3 foi inteiramente backend). Sem alteração de risco. |
| TD-011 (backend de embeddings de produção não escolhido) | **Postergado** | Gatilho explícito: primeiro Advisor real com dependência obrigatória de RAG sobre conteúdo semântico real (candidato natural: Document Advisor, Wave 5 — Enterprise Advisors, per D-071). Sem consumidor real hoje — `MockEmbeddingProvider` é suficiente para a validação arquitetural feita na Fase 4. Não bloqueia a Wave 4 (Enterprise Operations) nem a Wave 5 em si, apenas a entrega de um Advisor que dependa de qualidade semântica de produção. |
| TD-012 (Document Ingestion real não implementado) | **Postergado** | Gatilho explícito: quando o Document Advisor (ou qualquer Advisor real) precisar ingerir um documento binário real. Escopo foi deliberadamente reduzido a texto normalizado desde o Domain Blueprint da Fase 1 (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.2) — não é uma omissão, é um limite de escopo já documentado e agora reconfirmado no fechamento. |
| TD-013 (Memory Model: Consolidação/Expiração não implementadas) | **Postergado** | Gatilho explícito: primeiro Advisor real que precise de memória organizacional consolidada entre projetos ou dependa de expiração automática. Escopo reduzido a Captura+Classificação+Consulta desde o Domain Blueprint da Fase 2 — decisão consciente para evitar construir capacidade sem consumidor real (mesma disciplina anti-sobre-engenharia aplicada em toda a Wave 3). |

**Item avaliado e explicitamente descartado como débito técnico:** a suíte E2E (`web/e2e/*.spec.ts`) não foi re-executada contra a migração real do Risk Advisor (Fase 4). Isso **não** é registrado como débito porque é uma propriedade estrutural pré-existente e já aceita da arquitetura de testes: os testes E2E rodam contra um backend mockado em Node.js (`web/e2e/mock-backend.mjs`), nunca contra as rotas reais do FastAPI — logo, mudanças backend-only (como a migração da Fase 4) são estruturalmente invisíveis à regressão E2E por desenho, não uma lacuna nova introduzida por esta Wave. A prova de regressão funcional da Fase 4 veio da suíte de integração backend pré-existente e não modificada (`tests/test_intelligence_api.py::TestRiskAdvisor`), que é o mecanismo correto para essa camada.

**Nenhum item deste registro permanece sem classificação.** Dos 13 itens ativos: 6 (TD-004/005/006/007/008/010) estão **Resolvidos**; 6 (TD-001/002/003/011/012/013) são **Postergados**, todos com gatilho explícito ainda não disparado, nenhum bloqueando o início da Wave 4; 1 (TD-009) é **Futuro Roadmap**. Nenhum item é **Business Pending** nesta revisão.

**Nota de atualização (D-072):** a justificativa de TD-009 na "Classificação Final — Wave 2 Closure Review" acima cita "Wave 5 (Enterprise Analytics/Observabilidade)" — nomenclatura da estrutura de 6 Waves, já superada pela harmonização do roadmap (D-071/D-072). O texto original não foi reescrito (mesma disciplina de preservação de histórico já aplicada a D-034/D-035); para leitura corrente, o gatilho de TD-009 deve ser entendido como "quando Enterprise Analytics — hoje uma capacidade transversal construída ao longo das Waves 4, 5 e 6, per D-072 — ou um gate de qualidade mais rigoroso exigir métricas de cobertura do frontend", não uma Wave isolada.

---

## TD-016 — Captura de snapshot de performance (EVM) é manual, sem scheduler automático

- **Origem:** Wave 8 — Executive Analytics & Experience Completion, Founder Decision "EVM Temporal Baseline" (`docs/architecture/TECHNICAL-DESIGN-WAVE-8-EXECUTIVE-ANALYTICS.md` Seção 2.B).
- **Classificação:** Médio.
- **Status:** ✅ **Resolvido** (V1 Post-Completion Technical Closure — D-245).
- **Descrição:** `POST /projects-delivery/{id}/performance-snapshots` capturava um `ProjectPerformanceSnapshot` só quando explicitamente chamado (idempotente por dia) -- não existia scheduler/cron/Event Pipeline consumer que capturasse automaticamente.
- **Resolução:** nenhuma nova primitiva de agendamento criada (reconciliação confirmou, via grep, que não existe nenhum evento real de "campo alterado" para Project -- `actual_cost`/`progress_percentage`/`forecast_cost` nunca são reatribuídos fora da criação). Dois caminhos complementares, ambos sobre infraestrutura já existente: (1) `src/workflows/performance_snapshot_automation.py` registra um handler simples de `EventDispatcher` (não um workflow de `WorkflowRuntime`, que permanece reservado ao exemplo único do Epic W4-4) no evento real `project_performance_baseline.created`, capturando automaticamente o snapshot do dia da baseline recém-criada; (2) captura disparada por leitura (`_auto_capture_snapshot` em `project_delivery.py`, chamada de `list_projects_delivery`/`get_project_delivery`) substitui a necessidade de um scheduler periódico -- toda leitura de um Project gera uma tentativa idempotente de captura do dia corrente, cobrindo o caso "sem evento de baseline recente". Os 4 endpoints existentes (Wave 8/D-240) preservados integralmente; captura manual/on-demand continua disponível.
- **Testes:** `tests/test_performance_snapshot_automation.py` (11 casos: captura orientada a evento, checkpoint por leitura, idempotência, isolamento de tenant, escopo de projeto, ausência de baseline/dados, ordenação, timestamps, histórico append-only, endpoints preservados).

## TD-017 — Executive Signals/Analytics ainda não alimentam a Executive Intelligence (Wave 8, Fase F adiada)

- **Origem:** Wave 8 — Executive Analytics & Experience Completion, Fase F (Intelligence Integration).
- **Classificação:** Baixo (nenhum impacto funcional -- Signals/Analytics já funcionam standalone).
- **Status:** ✅ **Resolvido** (V1 Post-Completion Technical Closure — D-246).
- **Descrição:** o mandato Wave 8 autorizou integrar Signals/Analytics ao contexto de `AdvisorFramework`/`AIContextEngine` **somente se** de forma aditiva, rastreável e compatível com os contratos existentes -- deliberadamente adiado na própria Wave 8 (D-244) por prudência de escopo, não por impossibilidade técnica.
- **Resolução:** mesmo padrão já provado para Organizational Learnings em Package M (D-237) -- uma variável de prompt nova e separada (`analytics_context`, `src/agents/shared/executive_analytics_prompt.py`), nunca misturada a `evidence`/`cited_evidence`. `src/services/executive_analytics/executive_signal_engine.py` (novo) é o port server-side, puramente determinístico, do algoritmo já validado no frontend (`web/lib/domain/executive-signal.ts`) para os 2 sinais que dependem apenas do histórico EVM de um Project (cost/schedule performance trend, forecast deviation) -- zero cálculo feito pelo LLM. `AIContextEngine.gather_executive_analytics_context()` + passthrough em `AdvisorFramework` alimentam PMO Advisor e Executive Advisor (os 2 Advisors organization-wide já existentes, per preferência do mandato por "enriquecimento no nível de Executive Intelligence" em vez de tocar nos 8 Advisors individualmente) -- nenhum Advisor, Orchestrator ou Evidence Gate alterado estruturalmente. Sinais de concentração de portfólio/risco (que exigem agregação cross-project ainda não portada ao backend) permanecem fora de escopo, documentados, não fabricados.
- **Testes:** `tests/test_executive_analytics/test_executive_signal_engine.py` (10 casos determinísticos), `tests/test_ai_foundation/test_context_engine.py::TestGatherExecutiveAnalyticsContext` (ausência de sinal, cap-de-5 com ordenação por severidade/escopo, isolamento de tenant, campo de proveniência), `tests/test_pmo_advisor.py::TestTD017ExecutiveSignalsIntegration` e `tests/test_executive_advisor.py::TestTD017ExecutiveSignalsIntegration` (Evidence Gate preservado -- sinais nunca substituem a ausência de evidência de status/risco -- e sinal real aparecendo no prompt como contexto de apoio, nunca citável).

## Convenção de uso deste registro

- Novo débito identificado por qualquer revisão (arquitetural, de segurança, de código) ganha um ID sequencial `TD-NNN` aqui, com origem (PR/commit), status (`Aberto` / `Planejado` / `Resolvido`) e o gatilho explícito de resolução.
- Nenhum item é resolvido silenciosamente: a resolução de um TD é um commit/PR próprio que referencia o ID e atualiza o status para `Resolvido`, com a data e o PR de resolução.
- Este documento não substitui ADRs — um TD pode motivar um ADR futuro quando sua resolução envolver decisão arquitetural (como é o caso de TD-002).
- **Categoria "Baseline Defect"** (TD-004+): usada quando um Épico encontra uma falha de teste E2E/CI que uma reprodução contra o baseline anterior (antes das mudanças do próprio Épico) comprova já existir. Registrar aqui em vez de bloquear o Regression Gate do Épico — a evidência de reprodução (comando, resultado, commit de referência) fica descrita no próprio item, para que a falha nunca seja confundida com uma regressão introduzida por trabalho subsequente nem seja silenciosamente esquecida.
