# Technical Design — Security Hardening Gate (C-1 + C-2)

**Base:** `docs/product/governance/REPOSITORY-AUDIT-WAVE-3.md`, Decision Proposal `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §16, autorização do Founder ("AUTORIZAÇÃO — MERGE DA PR #45 E SECURITY HARDENING GATE").
**Escopo:** C-1 (RBAC em `intelligence.py`) e C-2 (Tenant Isolation em `AnalysisRecord`) — consolidados num único Technical Design por serem a mesma superfície de código e se resolverem melhor juntos (ambos exigem que as rotas de `intelligence.py` ganhem `get_request_context`).
**Nenhum impacto arquitetural fora do escopo aprovado** — ver Seção 6. Prossegue direto para implementação/testes/Executive Report, per autorização do Founder.

---

## 1. C-1 — RBAC em `intelligence.py`

### 1.1 Novo par de permissões (reaproveita o catálogo existente, nenhum registry novo)

Migração nova (`0010`), seguindo exatamente o padrão de `0006_rbac_permission_catalog.py`:

```
PERMISSIONS = [
    ("intelligence.read", "Ler análises de IA (meetings/risks/status) da organização"),
    ("intelligence.write", "Executar novas análises de IA (meetings/risks/status) da organização"),
]
```

**Atribuição de papéis** (mesma lógica já usada para `project_delivery.*`): `intelligence.read` para os 4 papéis seed (todo usuário que navega Workspace/Dashboard precisa ler análises); `intelligence.write` para `organization_admin`, `pmo`, `project_manager` (mesmos 3 que já têm `project_delivery.write`) — `viewer` fica somente leitura, consistente com seu papel em todo o resto da plataforma.

### 1.2 Rotas (`src/api/routes/intelligence.py`)

Cada uma das 8 rotas ganha `Depends(get_request_context)` + `Depends(require_permission(...))`, inserido exatamente como em `portfolio.py`/`program.py`/`project_delivery.py` — nenhuma mudança de assinatura além disso:

| Rota | Permissão |
|---|---|
| `POST /meetings/analyze` | `intelligence.write` |
| `POST /risks/analyze` | `intelligence.write` |
| `POST /projects/analyze` | `intelligence.write` |
| `GET /analyses` | `intelligence.read` |
| `GET /analyses/{id}` | `intelligence.read` |
| `GET /action-items` | `intelligence.read` |
| `GET /risks/latest` | `intelligence.read` |
| `GET /projects/summary` | `intelligence.read` |
| `GET /portfolio/summary` | `intelligence.read` |

## 2. C-2 — Tenant Isolation em `AnalysisRecord`

### 2.1 Migração (mesma `0010`, uma única migração para C-1+C-2 — mesma superfície, mesmo commit lógico)

1. `ALTER TABLE analysis_records ADD COLUMN organization_id INTEGER REFERENCES organizations(id)` — nullable inicialmente.
2. **Backfill seguro, sem exposição de dado histórico** (é uma atualização de metadado via SQL, nunca uma leitura/exposição de conteúdo): `UPDATE analysis_records SET organization_id = (SELECT organization_id FROM projects WHERE projects.id = analysis_records.project_id) WHERE project_id IS NOT NULL`. Toda linha existente já tem `project_id` populado (desde o Épico 1) e todo `Project` já tem `organization_id NOT NULL` (desde a Wave 1) — o backfill é determinístico e completo, sem ambiguidade.
3. Após o backfill, `ALTER COLUMN organization_id SET NOT NULL` — nenhuma linha deveria ficar nula; a migração falha ruidosamente se alguma ficar (não silenciosamente).
4. Índice: `CREATE INDEX ix_analysis_records_organization_id ON analysis_records (organization_id)` — toda consulta passa a filtrar por ele.
5. `downgrade()`: remove o índice, a constraint NOT NULL (volta a nullable), a FK, e a coluna — ordem inversa, simétrico.

### 2.2 Resolução de Project por organização real (corrige uma causa raiz mais profunda encontrada nesta Technical Design)

`EnterpriseRepository.get_or_create_project_for_name(session, raw_project_name)` hoje **sempre** resolve para a "Default Organization" hardcoded (`get_or_create_default_organization`), **independentemente de quem está chamando** — ou seja, mesmo um usuário da Demo Organization tem suas análises vinculadas a um Project da Default Organization hoje. Isto é uma manifestação mais profunda de C-2, encontrada ao desenhar a correção, não apenas a ausência da coluna.

**Correção:** `get_or_create_project_for_name(session, organization_id, raw_project_name)` ganha `organization_id` como parâmetro obrigatório, substituindo a resolução hardcoded — reaproveita o mesmo método, apenas estende a assinatura (único call site: `AnalysisRepository.save_analysis`, blast radius mínimo).

### 2.3 Camada de serviço/repositório

- `AnalysisRepository.save_analysis(kind, payload, organization_id, project_name=None)` — `organization_id` obrigatório, passado a `get_or_create_project_for_name` e gravado em `AnalysisRecord.organization_id`.
- `AnalysisRepository.list_analyses(organization_id, project_name=None, kind=None, ...)` — filtro `AnalysisRecord.organization_id == organization_id` obrigatório, sempre aplicado primeiro.
- `AnalysisRepository.get_analysis(analysis_id, organization_id)` — filtro por ambos; retorna `None` (→ 404) se o id existir mas pertencer a outra organização, mesmo padrão de `DomainRepository.get_portfolio`.
- `ProjectSummaryService.summarize(organization_id, project_name)`, `summarize_portfolio(organization_id)`, `list_action_items(organization_id, project_name=None)`, `list_latest_risks(organization_id, project_name=None)` — todos ganham `organization_id`, repassado a `list_analyses`.

### 2.4 Rotas

Cada rota (já modificada pela Seção 1.2 para ter `context: RequestContext`) passa `context.organization.organization_id` para o serviço/repositório — nenhum parâmetro de organização jamais aceito do cliente (mesma disciplina de `portfolio.py`).

## 3. Auditoria

Cada uma das 3 rotas de análise (`/meetings/analyze`, `/risks/analyze`, `/projects/analyze`) registra uma entrada via `AdministrationRepository.record_audit(organization_id, actor_user_id, action, entity_type="analysis", entity_id=<analysis_id>, details={"kind": ..., "project_id": ...})` — reaproveita a infraestrutura de auditoria já existente (`audit_logs`, usada por Administration), nenhuma tabela nova. `action` = `"analysis.meeting_created"` / `"analysis.risk_created"` / `"analysis.status_created"`.

## 4. Testes obrigatórios (per critérios de aceite do Founder)

- Nenhuma rota de `intelligence.py` acessível sem `require_permission` (teste 403 para ator sem a permissão, em cada uma das 8 rotas).
- Isolamento cross-tenant: criar 2 organizações, análises em cada uma, confirmar que o contexto da organização A nunca vê dados da organização B em nenhuma das 5 rotas GET (incluindo `list_analyses`, `get_analysis` por id de outra org → 404, `summarize_portfolio`).
- Migração: upgrade → downgrade → re-upgrade validado em Postgres real, incluindo o backfill (inserir dados pré-migração simulando o estado antigo, confirmar backfill correto).
- `get_or_create_project_for_name` com organização real (não mais hardcoded) — teste que 2 organizações com o mesmo nome de projeto (`"Projeto Alfa"`) resultam em 2 Projects distintos, um por organização.
- Auditoria: as 3 rotas de análise geram uma entrada em `audit_logs` com `organization_id`/`actor_user_id`/`entity_id` corretos.
- Regressão completa: toda a suíte existente (backend + frontend + E2E) permanece verde.

## 5. Fora de escopo (não incluído neste Gate)

Nenhuma mudança a `X-Stratech-User-Id`/`X-Stratech-Organization-Id` (M-2 do Repository Audit, defesa em profundidade, não bloqueante) — fora do escopo aprovado por este Gate, que cobre exclusivamente C-1/C-2.

## 6. Confirmação — nenhum impacto arquitetural fora do escopo aprovado

- Nenhum Bounded Context novo: `intelligence.py` e `AnalysisRecord` já existem.
- Nenhum registry/provider novo.
- Reaproveita 100% dos padrões já estabelecidos: `require_permission`/`get_request_context` (idêntico a `portfolio.py`), migração de catálogo de permissões (idêntico a `0006`), auditoria (`record_audit`, idêntico a `administration_service.py`), scoping por organização em repositório (idêntico a `DomainRepository`).
- Único ajuste além do escopo literal de C-1/C-2: `get_or_create_project_for_name` ganha `organization_id` — uma extensão de assinatura de um método já existente, único call site, não uma mudança de arquitetura.
- **Prossegue direto para implementação**, per autorização do Founder.
