# STRATECH V2 — Release 0.1: Enterprise Foundation

- **Status:** Épico 1 (Schema Foundation) e Épico 2 (Identity Foundation) integrados à `main`. Épicos 3-6 pendentes.
- **Merge commit do Épico 1:** `4dcf7e886467e86c37524bd0fb46f70b70a7778c` (PR #39)
- **Merge commit do Épico 2:** `ef760ee426f58eb3dad48f7d3eb3ed248308107d` (PR #41)
- **Referência arquitetural:** Enterprise Architecture Blueprint v2.0 (`922b19e`), Release-0.1-Macro-Backlog

## Objetivo da Release

Estabelecer progressivamente a fundação de identidade, organização e projeto real como pré-requisito da STRATECH V2, evoluindo do modelo baseado em `project_name` para um modelo relacional multi-organização, operando inicialmente com uma organização principal por instalação. O Épico 1 entrega a fundação e a migração inicial preservando compatibilidade — `project_name` permanece preservado durante a transição e `project_id` permanece nullable; a conclusão do vínculo obrigatório (`project_id` NOT NULL) ocorrerá no Épico 4.

## Escopo (6 épicos, per Macro Backlog)

| Épico | Descrição | Status |
|---|---|---|
| 1 | Schema relacional e migração para Postgres/Alembic | ✅ Integrado (PR #39) |
| 2 | Identidade e autenticação individual | ✅ Integrado (PR #41) |
| 3 | Organização e RBAC inicial | Não iniciado |
| 4 | Projeto como entidade real (vínculo completo com `analysis_records`, `project_id` NOT NULL) | Não iniciado |
| 5 | Auditoria e administração mínima | Não iniciado |
| 6 | Validação e documentação | Não iniciado |

## Épico 1 — Schema Foundation (concluído)

- **Entidades:** `organizations`, `users`, `roles`, `permissions`, `role_permissions`, `user_roles`, `projects`, `user_project_memberships`.
- **Migração 0002:** cria as tabelas, semeia a organização padrão ("Organização Principal") e os 4 papéis iniciais (organization_admin, pmo, project_manager, viewer), adiciona `analysis_records.project_id` e migra todo o histórico de análises com regra determinística (ver ADR-V2-002/003 e ADR-V2-004).
- **Validação:** contagem 1:1 pré/pós-migração, zero órfãos, downgrade lossless comprovado, 12 testes novos (100% de cobertura nos módulos novos), regressão V1 completa verde (backend + frontend + E2E).
- **Revisão:** Executive Pre-Merge Architecture Review independente — decisão `APPROVED WITH OBSERVATIONS`.
- **Débitos assumidos conscientemente:** TD-001 (FK não aplicada pelo SQLite) e TD-002 (política de exclusão indefinida) — ambos sem impacto neste épico porque nenhuma funcionalidade de exclusão é exposta; devem ser resolvidos antes do primeiro endpoint `DELETE`.

## Épico 2 — Identity Foundation (concluído)

- **Entidades/colunas:** `users.identity_type` (migração 0003), `organizations.slug` (migração 0004).
- **Identity Layer:** `src/services/identity/` — autenticação individual escopada por organização + e-mail + senha (nunca busca global de e-mail), bootstrap transacional do Administrator e do usuário Demo.
- **Validação:** 165 testes de backend (97% cobertura) + 398 testes de frontend, round-trip completo de migration, regressão E2E com 3 falhas classificadas como Baseline Defect (TD-004/005/006, comprovadamente pré-existentes).
- **Revisão:** AR-001 (Rev. 1, CHANGES REQUESTED) → AR-002 (Rev. 2, APPROVED) → AR-003 (PR #41, `APPROVED WITH OBSERVATIONS`).
- **Merge:** autorizado por EO-MERGE-001.
- Ver `docs/architecture/technical-design-specs/TDS-EPIC-02.md` para a especificação técnica completa.

## Critérios de aceite da Release 0.1 (referência completa, Blueprint Seção 20)

2 usuários autenticados de forma independente · 2 perfis com permissão distinta · 2 organizações sem acesso cruzado · criação real de projeto · associação usuário↔projeto · restrição por papel · análise de IA vinculada ao projeto real · dashboard com entidades reais · histórico de auditoria · instalação limpa · testes automatizados · documentação atualizada. **Satisfeitos até aqui:** segregação entre organizações (testada no Épico 1); autenticação individual (Épico 2). Os demais dependem dos Épicos 3-6.

## Fora de escopo desta release

Portfólio, Programa, atores externos, SSO, qualquer Acelerador de IA novo, Integration Hub, Orquestração — todos fora de escopo até Release 0.2+ (Blueprint Seção 20).

## Governança aplicada durante esta release

Branch protection na `main` (PR obrigatório, checks `validate`+`frontend` obrigatórios, branch atualizada obrigatória, force push bloqueado, Merge Commit único método permitido), `.github/CODEOWNERS`, revisão arquitetural independente antes de cada merge estrutural. Ver `docs/governance/LESSONS_LEARNED.md` para o registro do incidente de configuração de ruleset encontrado e corrigido durante este épico.

## Ver também (EO-018 — governança institucionalizada)

- `docs/governance/ENGINEERING_ORDERS.md` — registro cronológico das Engineering Orders desta release.
- `docs/governance/ARCHITECTURE_REVIEWS.md` — registro das Architecture Reviews (Épico 1 e Épico 2).
- `docs/governance/GOVERNANCE_MODEL.md` — modelo de papéis e fluxo de estágios.
- `docs/architecture/technical-design-specs/TDS-EPIC-02.md` — especificação técnica consolidada do Épico 2.
