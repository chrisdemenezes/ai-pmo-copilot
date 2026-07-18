# STRATECH — Technical Debt Register

Registro vivo de débitos arquiteturais conhecidos. Cada item tem origem, status e o gatilho que exige sua resolução — nenhum item aqui é corrigido automaticamente por esta entrada; a correção é um trabalho futuro separado, autorizado individualmente quando seu gatilho ocorrer.

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
- **Status:** Aberto (aceito conscientemente — decisão explícita do Founder, ver ADR-V2-009).
- **Descrição:** `web/lib/domain/{portfolio,program,project}.ts` existem apenas como domínio de frontend, sem tabela/model/migração em `src/database`. Quando forem persistidos, precisarão de `organization_id` desde a primeira migração, seguindo exatamente o padrão já estabelecido pela Enterprise Foundation (Épico 1) — hoje não há esse campo porque não há persistência, então não há risco de vazamento cross-tenant ainda (nada é gravado). O risco é apenas prospectivo: nasce no dia em que a Release 0.2 wireener um backend real para essas 3 entidades.
- **Resolver antes de:** qualquer migração de banco que persista Portfolio/Program/Project.
- **Plano de resolução:** `docs/architecture/PHASE-2-FOUNDATION-ARCHITECTURE.md` §2-3 (Persistence Strategy + Organizational Scoping) — proposta, pendente de aprovação.

## TD-008 — Três conceitos "Project" coexistem no código, sem unificação

- **Origem:** Capability 03 (Decision Log D-019), confirmado na Architecture Review AR-1.
- **Classificação:** Médio.
- **Status:** Aberto (aceito conscientemente até o Épico 4).
- **Descrição:** (1) o `Project` real do backend (`src/database/models.py`, Épico 1, persistido, hoje só usado para membership); (2) `ProjectSummary` (`web/lib/dashboard/types.ts`, dado real do V1/BFF, chaveado por `project_name` livre); (3) `Project` do domínio (`web/lib/domain/project.ts`, Capability 03, vinculado a Program). Nenhum compartilha ID. Risco real: um novo engenheiro pode importar o `Project` errado para uma nova feature sem perceber a diferença — mitigado hoje por documentação explícita (docstrings + Decision Log), não por um mecanismo que impeça o erro em tempo de compilação.
- **Resolver antes de:** Épico 4 (unificação de `Project`) — candidato natural a também resolver este item.
- **Plano de resolução:** `docs/architecture/PHASE-2-FOUNDATION-ARCHITECTURE.md` §2 (Persistence Strategy) recomenda que Épico 4 e a persistência de `projects_delivery` sejam uma única Engineering Order — proposta, pendente de aprovação.

## TD-009 — Cobertura de testes do frontend não instrumentada

- **Origem:** RC-2 Enterprise Release Certification, Etapa 5 (Qualidade).
- **Classificação:** Baixo.
- **Status:** Aberto.
- **Descrição:** `web/` não tem `@vitest/coverage-v8` instalado — `vitest run --coverage` falha por dependência ausente. O backend (`src/`) já mede cobertura real (97%, via `pytest --cov`); o frontend não tem visibilidade equivalente. Consistente com o pilar "Observabilidade" do Product Maturity Model, hoje em 0%.
- **Resolver antes de:** nenhum gatilho específico — melhoria de visibilidade, não um risco ativo. Candidato natural para quando a Phase 2 exigir métricas de qualidade mais rigorosas.

---

## Baseline Defects — falhas E2E pré-existentes, não introduzidas por Épicos

Categoria distinta de TD-001/002/003: não são débitos arquiteturais de uma decisão de design, mas defeitos de comportamento já presentes no baseline antes do Épico que os documenta, comprovados por reprodução contra esse baseline. Registrados aqui para que nunca sejam confundidos com uma regressão introduzida por um Épico subsequente, e para que não sejam silenciosamente esquecidos por não bloquearem o Regression Gate.

### TD-004 — Race de invalidação do React Query após "Analisar Projeto" (Avaliação de Riscos)

- **Categoria:** Baseline Defect
- **Origem confirmada:** pré-existente ao Épico 2 (Identity Foundation) e ao PR #39 (Épico 1). Não introduzida pela correção de escopo organizacional (EO-015).
- **Status:** Aberto
- **Teste afetado:** `web/e2e/workspace.spec.ts` › `Avaliação de Riscos (TIP-006)` › `runs a full risk analysis via the Avaliação de Riscos tab and reflects it in the Workspace and the Dashboard`
- **Sintoma:** após submeter uma nova Avaliação de Riscos, o Intelligence Timeline registra o novo evento (a mutação teve sucesso no backend/mock), mas o painel "Riscos" não é atualizado com o novo resultado — continua mostrando o risco anterior. Mesmo mecanismo documentado inline em `executive-memory.spec.ts:54-60`: se o fetch inicial de uma query ainda está em voo no instante em que a mutação invalida o cache, o React Query não dispara um novo fetch (já há um em voo) e a invalidação é "engolida" pela resolução do fetch obsoleto.
- **Evidência de reprodução no baseline:** `git stash push -u` (removendo as 36 alterações do Épico 2/EO-015 da árvore de trabalho) → `npx playwright test e2e/workspace.spec.ts -g "runs a full risk analysis via the Avaliação de Riscos tab" --project=md` → falha idêntica (mesmo locator, mesma mensagem, mesma linha relativa) contra o código anterior a esta correção → `git stash pop` restaura o trabalho do Épico 2 sem perda. Falha reproduzida de forma determinística em múltiplas execuções (3/3), antes e depois do stash.
- **Resolver antes de:** qualquer trabalho que dependa da confiabilidade dessa suíte E2E específica para novas features de Riscos; candidato natural ao Épico de Risk Intelligence ou a uma revisão dedicada dos hooks `use-workspace-latest`/invalidação de queries.

### TD-005 — Mesmo race, painel de Comunicação (O que mudou na última reunião?)

- **Categoria:** Baseline Defect
- **Origem confirmada:** pré-existente ao Épico 2. Mesmo mecanismo de TD-004, painel diferente.
- **Status:** Aberto
- **Teste afetado:** `web/e2e/workspace.spec.ts` › `O que mudou na última reunião? (TIP-007)` › `runs a full meeting analysis via the 3rd tab and reflects it in the Workspace and the Dashboard`
- **Sintoma:** idêntico a TD-004, aplicado ao painel "Comunicação" após uma análise de reunião.
- **Evidência:** falha intermitente na mesma suíte completa (5/202 e 7/202 falhas em duas execuções completas), sempre restrita a este teste e aos de TD-004/TD-006 — nunca a testes fora desse padrão de "reflete mutação sem reload".
- **Resolver:** junto com TD-004 (mesma causa raiz).

### TD-006 — Mesmo race, Executive Memory Insight "Mudou"

- **Categoria:** Baseline Defect
- **Origem confirmada:** pré-existente — já documentado inline no próprio teste (`executive-memory.spec.ts:54-60`) desde o Incremento 1 de Executive Memory, muito antes do Épico 2.
- **Status:** Aberto
- **Teste afetado:** `web/e2e/executive-memory.spec.ts` › `shows a Mudou Executive Memory Insight right after Analisar Projeto changes the health status`
- **Sintoma:** idêntico a TD-004/005, aplicado ao Executive Brief / Memory Insight.
- **Resolver:** junto com TD-004 (mesma causa raiz).

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
