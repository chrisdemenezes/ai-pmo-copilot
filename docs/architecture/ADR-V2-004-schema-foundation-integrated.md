# ADR-V2-004: Enterprise Foundation Schema Integrated into Main

- **Status:** Accepted
- **Date:** 2026-07-17
- **Context layer:** Implementação (per the 4-layer model of the Enterprise Architecture Blueprint v2.0)

## Contexto

O Blueprint v2.0 (commit `922b19e`) definiu o modelo canônico mínimo da STRATECH V2 (Organização → Usuário/Papel/Permissão → Projeto) e o Release-0.1-Macro-Backlog fracionou a Release 0.1 em 6 épicos, o primeiro dos quais é a fundação relacional (Épico 1). O Founder autorizou formalmente a abertura da Release 0.1 e a implementação exclusiva do Épico 1 (2026-07-17), com o ajuste explícito de que o modelo deveria ser multi-organização desde a fundação, operando inicialmente com uma organização principal por instalação.

## Problema

Sem esta fundação, `analysis_records.project_name` permanece texto livre, sem identidade real, sem organização, sem usuário individual e sem qualquer mecanismo de segregação — o que bloqueia toda evolução subsequente da V2 (RBAC, Portfólio/Programa, atores externos, Integration Hub).

## Alternativas consideradas

1. **Introduzir o schema incrementalmente junto com a UI/RBAC do Épico 2/3** — rejeitada: acoplaria a fundação de dados a decisões de produto ainda não aprovadas, e adiaria a prova de que a migração de `analysis_records` é segura.
2. **Modelo single-tenant simples (sem `organization_id`)**, adicionando multi-organização apenas quando fosse necessário — rejeitada pelo Founder explicitamente: exigiria retrofitting doloroso de segregação em todo o schema e em todos os testes já escritos.
3. **Modelo multi-organização estrutural desde o Épico 1, operando com uma organização principal** — **escolhida**. Reconcilia o requisito de simplicidade operacional imediata com a exigência de correção arquitetural de longo prazo.

## Decisão

Integrar à `main` (PR #39, merge commit `4dcf7e886467e86c37524bd0fb46f70b70a7778c`) o schema da Enterprise Foundation:

- Tabelas: `organizations`, `users`, `roles`, `permissions`, `role_permissions`, `user_roles`, `projects`, `user_project_memberships`.
- `organization_id` presente em `users` e `projects` desde o primeiro commit do schema, com unicidade escopada (`uq_users_org_email`, `uq_projects_org_name`).
- Migração 0002 (Alembic) migra todo o histórico de `analysis_records` para `project_id`, com regra determinística congelada (ADR-V2-002/003): strip de espaços nas bordas, sem case folding, sem merging por similaridade; NULL/vazio/só-espaços → projeto fallback único.
- `EnterpriseRepository` como única camada de escrita para as novas entidades, com guarda explícita contra vínculo cross-tenant (`CrossTenantViolationError`).

## Justificativa

- Cumpre a diretriz do Founder (multi-organização obrigatório, operação inicial com organização única) sem promessa de funcionalidade que não existe ainda (nenhuma UI multi-org, nenhum RBAC funcional).
- Preserva integralmente a V1: nenhum endpoint, nenhuma Capability, nenhum arquivo fora de `src/database/` foi tocado; regressão completa (backend + frontend + E2E) permaneceu verde antes e depois.
- Migração e downgrade comprovados por execução real (não apenas por leitura de código): contagem 1:1, zero órfãos, 7 edge cases (NULL/vazio/espaços/capitalização/duplicados/caracteres especiais) verificados individualmente.
- Passou por revisão arquitetural independente (Executive Pre-Merge Architecture Review) com decisão **APPROVED WITH OBSERVATIONS** antes do merge.

## Consequências

- **Positivas:** a Release 0.1 tem uma fundação de dados testada e auditada sobre a qual os Épicos 2-6 podem ser construídos sem retrabalho de schema. O padrão de revisão arquitetural independente antes de merge fica estabelecido como prática para os próximos épicos.
- **Negativas / dívida assumida:** a integridade referencial não é reforçada pelo motor SQLite (ver TD-001, TD-002 em `docs/architecture/TECHNICAL_DEBT.md`) — aceito conscientemente porque nenhuma funcionalidade de exclusão existe neste épico.
- **Impacto futuro:** qualquer épico que introduza exclusão (organização, usuário ou projeto) **deve** resolver TD-001/TD-002 antes de expor esse fluxo. O Épico 2 (identidade/autenticação) consome diretamente `users.password_hash` (já presente, nula) e `roles`/`permissions` (já semeados) sem necessidade de nova migração estrutural para os 4 papéis iniciais.
