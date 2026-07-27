# Architecture Delta — Wave 2 (Enterprise Platform)

**Data:** 2026-07-27 · Comparação da arquitetura da STRATECH imediatamente antes e depois da Wave 2 (baseline: Wave 1/Épicos 1-2 concluídos; estado final: Wave 2 encerrada, `WAVE-2-CLOSURE-REPORT.md`).

---

## 1. O que mudou

### 1.1 Persistência real substitui domínio de frontend em memória
Antes: `Portfolio`/`Program`/`Project` viviam como classes DDD em `web/lib/domain/*.ts`, consumindo arrays semeados em memória — nenhuma tabela própria além do `Project` mínimo do Épico 1 (organização/membership).
Depois: `portfolios`/`programs` são tabelas reais (migração `0005_domain_persistence`); `projects` estendido com os campos de domínio na mesma tabela (não uma `projects_delivery` separada); API REST completa (9 rotas) com RBAC fino; frontend consome a API real via BFF — os arrays semeados foram deletados (D-036).

### 1.2 RBAC de "tabelas existentes, nunca aplicadas" para enforcement real
Antes: `roles`/`permissions`/`role_permissions`/`user_roles` existiam desde o Épico 1, sem nenhuma rota verificando permissão.
Depois: `require_permission(...)` (Protocol `PermissionChecker` + `SqlPermissionChecker`) aplicado a toda rota de Enterprise Domain, Administration, Intelligence — permission catalog semeado por migração, papéis já existentes ganham as permissões corretas sem reestruturar o schema (D-034).

### 1.3 Administration nasce como Nível 1 mínimo e cresce por correção de premissa, nunca por especulação
Antes: nenhum endpoint administrativo existia.
Depois: Organizações/Usuários/Papéis/Auditoria/Logs/Segurança (Nível 1+2, D-035), User Management completo (D-038), API Keys (D-051, reclassificado de Nível 3 para Nível 1), Sessões server-side (D-053, resolve TD-010), Convites (D-054, domínio desacoplado de e-mail). Cada extensão corrigiu uma premissa equivocada de um Blueprint anterior em vez de expandir escopo por suposição.

### 1.4 Sessão deixa de ser um cookie stateless
Antes: sessão = cookie HMAC-assinado, sem estado no servidor; `logout()` era um no-op documentado.
Depois: tabela `sessions` (backend cunha o `session_id` no login), revogação real, enforcement de revogação em `require_permission` (fail-open para ids não rastreados, D-053).

### 1.5 `project_id` torna-se a única chave de identidade do Project (TD-008 resolvido)
Antes: três conceitos "Project" coexistiam sem unificação — o `Project` real do backend (organização/membership), `ProjectSummary` do V1 (chaveado por `project_name` livre), e o `Project` de domínio (Capability 03, vinculado a Program).
Depois: `project_id` é a única chave de acesso interno ao Project em toda a superfície de Intelligence; a coluna legada `analysis_records.project_name` foi removida do banco e do ORM (migração 0015); `Project.name` é a única fonte do nome de exibição — nunca mais uma chave, join ou identidade.

### 1.6 Event Foundation nasce como seam, não como infraestrutura
Antes: nenhum mecanismo de evento de domínio existia, apesar de já especificado na Foundation Technical Design.
Depois: `EventEmitter` Protocol + `NoOpEventEmitter` (loga, nenhum efeito); `DomainService` emite 5 eventos nomeados nas 3 operações mutantes (D-049) — "o seam existe, o barramento ainda não", mesmo padrão depois reaproveitado por Convites (`NotificationProvider`/`NoOp`).

### 1.7 PostgreSQL torna-se o banco oficial
Antes: SQLite era o único banco usado, inclusive pela suíte de testes.
Depois: PostgreSQL é o ambiente oficial de desenvolvimento e testes desde RC-2 (D-037); SQLite permanece só como fallback zero-dependência para instalações locais sem `DATABASE_URL` — nunca um alvo de deploy.

---

## 2. O que permaneceu

- **Nenhuma segunda arquitetura de autorização.** Policies/Claims permanecem não adotados — RBAC relacional (roles→permissions) continua sendo o único mecanismo, por proibição explícita de CLAUDE.md contra criar um segundo provider/registry.
- **A cadeia de consolidação transitiva** Project → Program → Portfolio (`consolidateFromChildren()`, `shared.ts`) — inalterada desde a Capability 03, reaproveitada por todo o Executive Cockpit.
- **`AnalysisRepository`/`EnterpriseRepository`/`DomainRepository`/`AdministrationRepository` como a única camada de acesso a dados** — toda extensão da Wave 2 (API Keys, Sessões, Convites) estendeu `AdministrationRepository`/`AdministrationService` em vez de criar um repositório paralelo.
- **O padrão 404-nunca-403 para escopo cross-organization** — estabelecido na Sprint 2 (D-033) e reaproveitado sem exceção por toda rota subsequente (nunca confirma a existência de um id de outra organização).
- **Playwright E2E contra o mock backend, não o backend Python real** — decisão de arquitetura de teste pré-existente, reafirmada em D-037 como não alterada (determinismo/velocidade, cobertura real vem da suíte pytest).

---

## 3. Quais simplificações ocorreram

- **`ProjectSummary`/`WorkspaceSummary` (dois espelhos duplicados do mesmo read-model de inteligência) consolidados em um único tipo canônico** — `ProjectIntelligenceSummary`, ancorado em `project_id` (D-059).
- **O dual-key coexistente de TD-008 (Etapas 1-4a) foi temporário por desenho** — cada etapa aditiva preparou o terreno para que a etapa destrutiva final (4b) fosse uma mudança pequena e comprovadamente reversível, não uma migração monolítica arriscada.
- **`get_or_create_project_for_name` continua sendo o único ponto de resolução nome→Project** — nenhuma segunda rotina de normalização de nome foi criada em nenhuma extensão da Wave 2.

## 4. Quais conceitos foram eliminados

- **`ProjectSummary` e `WorkspaceSummary`** (tipos de frontend) — removidos, consolidados em `ProjectIntelligenceSummary` (D-059).
- **A coluna `analysis_records.project_name`** — removida do banco e do ORM (migração 0015, D-061). Era, até a Wave 2, a última chave de acesso ao Project que não passava por `project_id`.
- **"Workspace" como candidato a entidade de domínio** — nunca existiu como código, mas era um item de roadmap em aberto; eliminado como possibilidade arquitetural (D-055), reservado permanentemente ao vocabulário de apresentação.
- **A premissa de que "Sessões" e "API Keys" dependiam de infraestrutura futura** — ambas eram dependências artificiais de decisões arquiteturais anteriores, corrigidas e eliminadas (D-051, D-053).

## 5. Quais novos padrões passam a existir

1. **Padrão de migração dual-key aditiva-primeiro/destrutiva-por-último**, com gate explícito do Founder antes de qualquer operação irreversível — estabelecido por TD-008 Fase 3b, candidato a referência para toda futura remoção de coluna/chave em produção.
2. **Padrão "seam antes de infraestrutura"** — `NoOpEventEmitter`/`NoOpNotificationProvider`: o contrato existe e é exercido de ponta a ponta antes de qualquer implementação real do mecanismo por trás dele.
3. **Padrão "auditar a dependência antes de aceitá-la"** — toda vez que um item pareceu bloqueado por uma dependência (API Keys→Integration Hub; Sessões→"já existe"; Tenant Settings→arquitetura), a resposta obrigatória passou a ser auditar se a dependência é real (decisão de negócio genuinamente pendente) ou artificial (resultado de uma decisão arquitetural anterior, corrigível).
4. **Wave Completion Policy (D-048)** como critério permanente de encerramento de qualquer Wave futura: 100% do escopo original, Executive Reports publicados, testes verdes, zero placeholder — nenhuma Wave se encerra com Decision Proposal em aberto tratado como "não bloqueia".
5. **PostgreSQL como único ambiente de teste/produção oficial**, com SQLite explicitamente relegado a fallback de instalação zero-dependência — nunca mais um alvo de deploy ou de suíte de CI.
