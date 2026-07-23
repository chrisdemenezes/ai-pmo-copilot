"""domain seed -- move the Capability 01-03 seed data from frontend to DB

STRATECH V2 Wave 2, Sprint 5 (frontend migration to the real API).
Executes Foundation Technical Design §2.16 step 2: the Portfolio/Program/
Project rows that lived hardcoded in web/lib/domain/{portfolio,program,
project}.ts since Capabilities 01-03 become real rows, so swapping the
frontend's list*() bodies to fetch() preserves exactly what every page
showed before -- no behavior change, only the data's home moves.

Seeded into BOTH organizations that exist by design ("Organização
Principal" from migration 0002 and "Demo Organization" from the Épico-2
bootstrap -- created here idempotently if the bootstrap hasn't run yet),
because the frontend previously showed this data to every logged-in user
regardless of organization; seeding only one org would silently blank the
other's dashboard.

Project unification note (DOMAIN-BLUEPRINT-PROJECT.md §3, Fase 2): where a
seed Project's name already exists in the org (e.g. "Multilift"/"Aurora",
created by migration 0002 from legacy analysis_records names), the
existing row is UPDATED in place (attach_project_to_program semantics) --
never duplicated, so uq_projects_org_name can't be violated and TD-008's
concept count shrinks instead of growing.

Idempotent throughout (existence checks by org+code / org+name).
Downgrade removes only rows this migration created or the domain fields
it attached (matching by the seed codes), never legacy data.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-20

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_ORGANIZATIONS = [
    ("Organização Principal", "organizacao-principal"),
    ("Demo Organization", "demo-organization"),
]

PORTFOLIOS = [
    {
        "code": "PF-001",
        "name": "Portfólio Corporativo",
        "description": "Iniciativas estratégicas corporativas de maior visibilidade executiva.",
        "category": "Corporativo",
        "executive_owner": "Diretoria de Estratégia",
        "strategic_objective": "Sustentar o crescimento consolidado do grupo nos próximos 3 anos.",
        "status": "Ativo",
        "health": "yellow",
        "priority": "Alta",
        "start_date": "2025-02-01",
        "planned_end_date": "2027-02-01",
        "progress_percentage": 58,
        "program_count": 4,
        "project_count": 14,
        "linked_demands": 6,
        "linked_risks": 9,
        "linked_issues": 4,
        "pending_decisions": 2,
        "sponsor": "Diretoria de Estratégia",
        "pmo_owner": "PMO Corporativo",
        "last_updated": "2026-07-10",
        "next_review": "2026-08-01",
    },
    {
        "code": "PF-002",
        "name": "Portfólio de Transformação Digital",
        "description": "Modernização de plataformas e processos digitais.",
        "category": "Transformação Digital",
        "executive_owner": "CIO",
        "strategic_objective": "Modernizar a base tecnológica e reduzir débito técnico crítico.",
        "status": "Ativo",
        "health": "green",
        "priority": "Alta",
        "start_date": "2025-06-01",
        "planned_end_date": "2026-12-01",
        "progress_percentage": 74,
        "program_count": 3,
        "project_count": 8,
        "linked_demands": 3,
        "linked_risks": 4,
        "linked_issues": 2,
        "pending_decisions": 1,
        "sponsor": "CIO",
        "pmo_owner": "PMO de Tecnologia",
        "last_updated": "2026-07-12",
        "next_review": "2026-07-25",
    },
    {
        "code": "PF-003",
        "name": "Portfólio de Expansão Regional",
        "description": "Entrada em novos mercados regionais.",
        "category": "Expansão",
        "executive_owner": "VP de Operações",
        "strategic_objective": "Estabelecer presença operacional em 2 novos mercados até o fim da Release 0.2.",
        "status": "Ativo",
        "health": "red",
        "priority": "Alta",
        "start_date": "2026-01-15",
        "planned_end_date": "2026-11-30",
        "progress_percentage": 31,
        "program_count": 1,
        "project_count": 2,
        "linked_demands": 2,
        "linked_risks": 5,
        "linked_issues": 1,
        "pending_decisions": 1,
        "sponsor": "VP de Operações",
        "pmo_owner": "PMO Regional",
        "last_updated": "2026-07-15",
        "next_review": "2026-07-22",
    },
]

PROGRAMS = [
    {
        "code": "PG-001",
        "portfolio_code": "PF-001",
        "name": "Eficiência Operacional",
        "description": "Redução de custo operacional e simplificação de processos internos.",
        "sponsor": "Diretoria de Estratégia",
        "program_manager": "Bruno Castro",
        "status": "Ativo",
        "health": "yellow",
        "priority": "Alta",
        "objective": "Reduzir custo operacional em 12% mantendo nível de serviço.",
        "start_date": "2025-08-01",
        "planned_end_date": "2026-10-01",
        "progress_percentage": 52,
        "project_count": 5,
        "linked_demands": 3,
        "linked_risks": 4,
        "linked_issues": 2,
        "pending_decisions": 1,
        "pending_actions": 2,
        "pmo_owner": "PMO Corporativo",
        "last_updated": "2026-07-11",
        "next_review": "2026-07-28",
    },
    {
        "code": "PG-002",
        "portfolio_code": "PF-001",
        "name": "Governança e Compliance Corporativa",
        "description": "Padronização de controles de governança entre unidades de negócio.",
        "sponsor": "Diretoria de Estratégia",
        "program_manager": "Diego Souza",
        "status": "Ativo",
        "health": "yellow",
        "priority": "Média",
        "objective": "Unificar o modelo de controles internos até o fim da Release 0.2.",
        "start_date": "2026-02-01",
        "planned_end_date": "2026-12-15",
        "progress_percentage": 45,
        "project_count": 2,
        "linked_demands": 1,
        "linked_risks": 2,
        "linked_issues": 0,
        "pending_decisions": 1,
        "pending_actions": 1,
        "pmo_owner": "PMO Corporativo",
        "last_updated": "2026-07-09",
        "next_review": "2026-08-05",
    },
    {
        "code": "PG-003",
        "portfolio_code": "PF-002",
        "name": "Modernização de Plataformas",
        "description": "Modernização das plataformas tecnológicas centrais.",
        "sponsor": "CIO",
        "program_manager": "Ana Ribeiro",
        "status": "Ativo",
        "health": "green",
        "priority": "Alta",
        "objective": "Migrar as 3 plataformas legadas mais críticas para a nova arquitetura.",
        "start_date": "2025-07-01",
        "planned_end_date": "2026-09-01",
        "progress_percentage": 80,
        "project_count": 3,
        "linked_demands": 2,
        "linked_risks": 2,
        "linked_issues": 1,
        "pending_decisions": 0,
        "pending_actions": 1,
        "pmo_owner": "PMO de Tecnologia",
        "last_updated": "2026-07-13",
        "next_review": "2026-07-27",
    },
    {
        "code": "PG-004",
        "portfolio_code": "PF-003",
        "name": "Entrada em Novos Mercados",
        "description": "Estruturação operacional para entrada em 2 novos mercados regionais.",
        "sponsor": "VP de Operações",
        "program_manager": "Carla Mendes",
        "status": "Ativo",
        "health": "red",
        "priority": "Alta",
        "objective": "Estabelecer operação local nos 2 mercados-alvo até o fim da Release 0.2.",
        "start_date": "2026-02-01",
        "planned_end_date": "2026-11-01",
        "progress_percentage": 28,
        "project_count": 2,
        "linked_demands": 2,
        "linked_risks": 5,
        "linked_issues": 1,
        "pending_decisions": 1,
        "pending_actions": 1,
        "pmo_owner": "PMO Regional",
        "last_updated": "2026-07-14",
        "next_review": "2026-07-21",
    },
]

PROJECTS = [
    {
        "code": "PJ-001",
        "program_code": "PG-001",
        "name": "Multilift",
        "description": "Modernização da linha de elevadores industriais.",
        "sponsor": "Diretoria de Estratégia",
        "project_manager": "Fernanda Lima",
        "objective": "Reduzir tempo de parada não planejada em 30%.",
        "start_date": "2025-09-01",
        "planned_end_date": "2026-06-01",
        "progress_percentage": 30,
        "health": "red",
        "status": "Ativo",
        "priority": "Alta",
        "last_updated": "2026-07-15",
        "next_review": "2026-07-20",
        "owner": {"name": "Bruno Castro", "role": "Product Owner"},
        "milestones": [
            {"name": "Diagnóstico concluído", "dueDate": "2025-11-01", "status": "Concluído"},
            {"name": "Piloto em planta 1", "dueDate": "2026-07-01", "status": "Atrasado"},
        ],
        "team": {"size": 8, "leadName": "Fernanda Lima"},
    },
    {
        "code": "PJ-002",
        "program_code": "PG-001",
        "name": "Automação de Faturamento",
        "description": "Automação do ciclo de faturamento corporativo.",
        "sponsor": "Diretoria de Estratégia",
        "project_manager": "Rafael Nunes",
        "objective": "Eliminar retrabalho manual no faturamento mensal.",
        "start_date": "2026-01-15",
        "planned_end_date": "2026-09-01",
        "progress_percentage": 55,
        "health": "yellow",
        "status": "Ativo",
        "priority": "Média",
        "last_updated": "2026-07-12",
        "next_review": "2026-07-26",
        "owner": {"name": "Bruno Castro", "role": "Product Owner"},
        "milestones": [{"name": "MVP em produção", "dueDate": "2026-08-01", "status": "Pendente"}],
        "team": {"size": 5, "leadName": "Rafael Nunes"},
    },
    {
        "code": "PJ-003",
        "program_code": "PG-002",
        "name": "Revisão de Controles Internos",
        "description": "Padronização de controles internos entre unidades.",
        "sponsor": "Diretoria de Estratégia",
        "project_manager": "Diego Souza",
        "objective": "Unificar o checklist de controles até o fim da Release 0.2.",
        "start_date": "2026-02-15",
        "planned_end_date": "2026-10-01",
        "progress_percentage": 70,
        "health": "green",
        "status": "Ativo",
        "priority": "Média",
        "last_updated": "2026-07-10",
        "next_review": "2026-08-02",
        "owner": {"name": "Diego Souza", "role": "Product Owner"},
        "milestones": [
            {"name": "Checklist unificado publicado", "dueDate": "2026-09-01", "status": "Pendente"}
        ],
        "team": {"size": 4, "leadName": "Diego Souza"},
    },
    {
        "code": "PJ-004",
        "program_code": "PG-003",
        "name": "Implantação SAP S/4HANA",
        "description": "Migração da plataforma ERP legada para SAP S/4HANA.",
        "sponsor": "CIO",
        "project_manager": "Ana Ribeiro",
        "objective": "Migrar os módulos financeiro e de suprimentos.",
        "start_date": "2025-08-01",
        "planned_end_date": "2026-08-01",
        "progress_percentage": 62,
        "health": "yellow",
        "status": "Ativo",
        "priority": "Alta",
        "last_updated": "2026-07-13",
        "next_review": "2026-07-27",
        "owner": {"name": "Ana Ribeiro", "role": "Product Owner"},
        "milestones": [
            {"name": "Go-live financeiro", "dueDate": "2026-06-01", "status": "Atrasado"},
            {"name": "Go-live suprimentos", "dueDate": "2026-08-01", "status": "Pendente"},
        ],
        "team": {"size": 10, "leadName": "Ana Ribeiro"},
    },
    {
        "code": "PJ-005",
        "program_code": "PG-003",
        "name": "Migração de Data Center",
        "description": "Migração da infraestrutura on-premise para a nuvem.",
        "sponsor": "CIO",
        "project_manager": "Ana Ribeiro",
        "objective": "Descomissionar o data center físico até o fim da Release 0.2.",
        "start_date": "2025-07-01",
        "planned_end_date": "2026-07-01",
        "progress_percentage": 88,
        "health": "green",
        "status": "Ativo",
        "priority": "Alta",
        "last_updated": "2026-07-14",
        "next_review": "2026-07-24",
        "owner": {"name": "Ana Ribeiro", "role": "Product Owner"},
        "milestones": [
            {"name": "Corte final de tráfego", "dueDate": "2026-07-15", "status": "Pendente"}
        ],
        "team": {"size": 6, "leadName": "Ana Ribeiro"},
    },
    {
        "code": "PJ-006",
        "program_code": "PG-004",
        "name": "Aurora",
        "description": "Estruturação da operação comercial no novo mercado.",
        "sponsor": "VP de Operações",
        "project_manager": "Carla Mendes",
        "objective": "Abrir a primeira unidade comercial no mercado-alvo.",
        "start_date": "2026-02-01",
        "planned_end_date": "2026-10-01",
        "progress_percentage": 74,
        "health": "green",
        "status": "Ativo",
        "priority": "Alta",
        "last_updated": "2026-07-11",
        "next_review": "2026-07-25",
        "owner": {"name": "Carla Mendes", "role": "Product Owner"},
        "milestones": [{"name": "Unidade inaugurada", "dueDate": "2026-09-01", "status": "Pendente"}],
        "team": {"size": 7, "leadName": "Carla Mendes"},
    },
    {
        "code": "PJ-007",
        "program_code": "PG-004",
        "name": "Abertura Operação LATAM",
        "description": "Estruturação regulatória e operacional para entrada na LATAM.",
        "sponsor": "VP de Operações",
        "project_manager": "Carla Mendes",
        "objective": "Obter licenças operacionais nos 2 países-alvo.",
        "start_date": "2026-03-01",
        "planned_end_date": "2026-11-01",
        "progress_percentage": 22,
        "health": "red",
        "status": "Ativo",
        "priority": "Alta",
        "last_updated": "2026-07-14",
        "next_review": "2026-07-21",
        "owner": {"name": "Carla Mendes", "role": "Product Owner"},
        "milestones": [
            {"name": "Licenças protocoladas", "dueDate": "2026-06-01", "status": "Atrasado"}
        ],
        "team": {"size": 4, "leadName": "Carla Mendes"},
    },
]


def _get_or_create_organization(conn, name: str, slug: str) -> int:
    org_id = conn.execute(
        sa.text("SELECT id FROM organizations WHERE name = :n"), {"n": name}
    ).scalar()
    if org_id is None:
        conn.execute(
            sa.text(
                "INSERT INTO organizations (name, slug, created_at) "
                "VALUES (:n, :s, CURRENT_TIMESTAMP)"
            ),
            {"n": name, "s": slug},
        )
        org_id = conn.execute(
            sa.text("SELECT id FROM organizations WHERE name = :n"), {"n": name}
        ).scalar()
    return org_id


def _seed_organization(conn, org_id: int) -> None:
    portfolio_ids: dict[str, int] = {}
    for portfolio in PORTFOLIOS:
        existing = conn.execute(
            sa.text("SELECT id FROM portfolios WHERE organization_id = :o AND code = :c"),
            {"o": org_id, "c": portfolio["code"]},
        ).scalar()
        if existing is None:
            conn.execute(
                sa.text(
                    "INSERT INTO portfolios (organization_id, name, code, description, "
                    "category, executive_owner, strategic_objective, status, health, "
                    "priority, start_date, planned_end_date, progress_percentage, "
                    "program_count, project_count, linked_demands, linked_risks, "
                    "linked_issues, pending_decisions, sponsor, pmo_owner, last_updated, "
                    "next_review, created_at) VALUES (:o, :name, :code, :description, "
                    ":category, :executive_owner, :strategic_objective, :status, :health, "
                    ":priority, :start_date, :planned_end_date, :progress_percentage, "
                    ":program_count, :project_count, :linked_demands, :linked_risks, "
                    ":linked_issues, :pending_decisions, :sponsor, :pmo_owner, "
                    ":last_updated, :next_review, CURRENT_TIMESTAMP)"
                ),
                {"o": org_id, **portfolio},
            )
            existing = conn.execute(
                sa.text("SELECT id FROM portfolios WHERE organization_id = :o AND code = :c"),
                {"o": org_id, "c": portfolio["code"]},
            ).scalar()
        portfolio_ids[portfolio["code"]] = existing

    program_ids: dict[str, int] = {}
    for program in PROGRAMS:
        portfolio_id = portfolio_ids[program["portfolio_code"]]
        existing = conn.execute(
            sa.text("SELECT id FROM programs WHERE portfolio_id = :p AND code = :c"),
            {"p": portfolio_id, "c": program["code"]},
        ).scalar()
        if existing is None:
            params = {k: v for k, v in program.items() if k != "portfolio_code"}
            conn.execute(
                sa.text(
                    "INSERT INTO programs (portfolio_id, name, code, description, sponsor, "
                    "program_manager, status, health, priority, objective, start_date, "
                    "planned_end_date, progress_percentage, project_count, linked_demands, "
                    "linked_risks, linked_issues, pending_decisions, pending_actions, "
                    "pmo_owner, last_updated, next_review, created_at) VALUES (:p, :name, "
                    ":code, :description, :sponsor, :program_manager, :status, :health, "
                    ":priority, :objective, :start_date, :planned_end_date, "
                    ":progress_percentage, :project_count, :linked_demands, :linked_risks, "
                    ":linked_issues, :pending_decisions, :pending_actions, :pmo_owner, "
                    ":last_updated, :next_review, CURRENT_TIMESTAMP)"
                ),
                {"p": portfolio_id, **params},
            )
            existing = conn.execute(
                sa.text("SELECT id FROM programs WHERE portfolio_id = :p AND code = :c"),
                {"p": portfolio_id, "c": program["code"]},
            ).scalar()
        program_ids[program["code"]] = existing

    domain_fields = (
        "program_id = :program_id, code = :code, description = :description, "
        "objective = :objective, sponsor = :sponsor, project_manager = :project_manager, "
        "status = :status, health = :health, priority = :priority, "
        "start_date = :start_date, planned_end_date = :planned_end_date, "
        "progress_percentage = :progress_percentage, last_updated = :last_updated, "
        "next_review = :next_review, owner_json = :owner_json, "
        "milestones_json = :milestones_json, team_json = :team_json"
    )
    for project in PROJECTS:
        params = {k: v for k, v in project.items() if k not in ("program_code", "owner", "milestones", "team")}
        params["program_id"] = program_ids[project["program_code"]]
        params["owner_json"] = json.dumps(project["owner"], ensure_ascii=False)
        params["milestones_json"] = json.dumps(project["milestones"], ensure_ascii=False)
        params["team_json"] = json.dumps(project["team"], ensure_ascii=False)

        existing = conn.execute(
            sa.text("SELECT id, program_id FROM projects WHERE organization_id = :o AND name = :n"),
            {"o": org_id, "n": project["name"]},
        ).first()
        if existing is None:
            conn.execute(
                sa.text(
                    "INSERT INTO projects (organization_id, name, created_at, program_id, "
                    "code, description, objective, sponsor, project_manager, status, "
                    "health, priority, start_date, planned_end_date, progress_percentage, "
                    "last_updated, next_review, owner_json, milestones_json, team_json) "
                    "VALUES (:o, :name, CURRENT_TIMESTAMP, :program_id, :code, "
                    ":description, :objective, :sponsor, :project_manager, :status, "
                    ":health, :priority, :start_date, :planned_end_date, "
                    ":progress_percentage, :last_updated, :next_review, :owner_json, "
                    ":milestones_json, :team_json)"
                ),
                {"o": org_id, **params},
            )
        elif existing.program_id is None:
            # Fase 2 unification (DOMAIN-BLUEPRINT-PROJECT.md §3): a legacy
            # Épico-1 Project with this name gains the domain fields in
            # place -- never a duplicate row. Rows already attached are
            # left untouched (idempotency).
            conn.execute(
                sa.text(f"UPDATE projects SET {domain_fields} WHERE id = :id"),
                {"id": existing.id, **params},
            )


def upgrade() -> None:
    conn = op.get_bind()
    for name, slug in SEED_ORGANIZATIONS:
        org_id = _get_or_create_organization(conn, name, slug)
        _seed_organization(conn, org_id)


def downgrade() -> None:
    conn = op.get_bind()
    seed_project_codes = [p["code"] for p in PROJECTS]
    seed_program_codes = [p["code"] for p in PROGRAMS]
    seed_portfolio_codes = [p["code"] for p in PORTFOLIOS]

    for name, _slug in SEED_ORGANIZATIONS:
        org_id = conn.execute(
            sa.text("SELECT id FROM organizations WHERE name = :n"), {"n": name}
        ).scalar()
        if org_id is None:
            continue
        for code in seed_project_codes:
            # Legacy rows that were attached (not created) keep existing --
            # only their domain fields are cleared; rows with no legacy
            # name (created by this migration) are deleted.
            row = conn.execute(
                sa.text(
                    "SELECT id, legacy_project_name FROM projects "
                    "WHERE organization_id = :o AND code = :c"
                ),
                {"o": org_id, "c": code},
            ).first()
            if row is None:
                continue
            if row.legacy_project_name is not None:
                conn.execute(
                    sa.text(
                        "UPDATE projects SET program_id = NULL, code = NULL, "
                        "description = NULL, objective = NULL, sponsor = NULL, "
                        "project_manager = NULL, status = NULL, health = NULL, "
                        "priority = NULL, start_date = NULL, planned_end_date = NULL, "
                        "progress_percentage = NULL, last_updated = NULL, "
                        "next_review = NULL, owner_json = NULL, milestones_json = NULL, "
                        "team_json = NULL WHERE id = :id"
                    ),
                    {"id": row.id},
                )
            else:
                conn.execute(sa.text("DELETE FROM projects WHERE id = :id"), {"id": row.id})
        for code in seed_program_codes:
            conn.execute(
                sa.text(
                    "DELETE FROM programs WHERE code = :c AND portfolio_id IN "
                    "(SELECT id FROM portfolios WHERE organization_id = :o)"
                ),
                {"c": code, "o": org_id},
            )
        for code in seed_portfolio_codes:
            conn.execute(
                sa.text("DELETE FROM portfolios WHERE organization_id = :o AND code = :c"),
                {"o": org_id, "c": code},
            )
