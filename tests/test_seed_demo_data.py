"""demo/seed_demo_data.py -- Founder Decision "Local V1 Pilot Dataset
Completion".

The script is a standalone operational tool (demo/), not part of `src/`, so
it is loaded here by file path rather than as a package import -- same
principle as every other API test file: real Postgres (temp_database_url),
real Alembic migrations (seeds roles + the real RBAC/knowledge permission
catalog), real AuthService bootstrap, real TestClient. httpx.post is
monkeypatched inside the loaded module's namespace to route through
TestClient instead of a real socket -- the script's own HTTP call shape
(headers/json/files/data/timeout) is unchanged, only the transport is
in-process.

Covers exactly the 10 items the Founder mandated (A-J):
A/B/C: real login, correct organization, correct user.
D: tenant isolation preserved (the demo/viewer organization sees none of it).
E-H: Projects/Actions/Decisions(risks)/Learnings-eligible data available.
I: second-run behavior is predictable (documented, not silently changed).
J: no real credential is ever printed to stdout.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api import dependencies as dependencies_module
from src.api.routes import auth as auth_module
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.authorization.checker import SqlPermissionChecker
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.identity.auth_service import AuthService
from src.services.identity.password_hashing import Argon2PasswordHasher
from src.workflows import document_indexed_workflow
from src.workflows.execution_tracking import ExecutionTracker
from src.workflows.runtime import WorkflowRuntime
from tests.db import temp_database_url

SEED_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "demo" / "seed_demo_data.py"

ADMIN_EMAIL = "pilot-admin@example.com"
ADMIN_PASSWORD = "pilot-admin-correct-password"
VIEWER_PASSWORD = "demo-viewer-correct-password"
API_KEY = "seed-test-api-key"


def _alembic(env, *args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result


def _load_seed_module(monkeypatch, test_client, response_file, admin_password=ADMIN_PASSWORD):
    """Loads a fresh copy of demo/seed_demo_data.py (module-level constants
    are read from the environment at import time) with its HTTP transport
    swapped for the given TestClient -- no real socket, same app instance
    the fixture already wired to a real temp database."""
    monkeypatch.setenv("BACKEND_URL", "http://testserver")
    monkeypatch.setenv("API_KEY", API_KEY)
    # Read by the real provider factory (src/llm/providers/factory.py) on
    # every request -- same Demo Mode mechanism production uses, not a
    # test-only fake provider.
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("MOCK_LLM_RESPONSE_FILE", str(response_file))
    monkeypatch.setenv("STRATECH_ADMIN_EMAIL", ADMIN_EMAIL)
    monkeypatch.setenv("STRATECH_ADMIN_PASSWORD", admin_password)
    monkeypatch.setenv("ADMIN_ORGANIZATION_SLUG", "organizacao-principal")

    spec = importlib.util.spec_from_file_location("seed_demo_data_under_test", SEED_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.httpx, "post", test_client.post)
    return module


@pytest.fixture()
def env():
    """Real Postgres, real migrations (seeds "Organizacao Principal" +
    "Demo Organization" with the Enterprise Domain data, migrations
    0002+0008, plus the RBAC/knowledge permission catalog, migrations
    0006/0010/0020), real AuthService bootstrap for both identities the
    script needs to distinguish (write-capable admin vs read-only demo
    viewer) -- exactly what src/main.py's lifespan does at real boot."""
    with temp_database_url("seed_demo_data") as database_url:
        db_env = os.environ.copy()
        db_env["DATABASE_URL"] = database_url
        _alembic(db_env, "upgrade", "head")

        repo = AnalysisRepository(database_url=database_url)
        auth_service = AuthService(repo.SessionLocal, Argon2PasswordHasher())
        auth_service.bootstrap_administrator(ADMIN_EMAIL, ADMIN_PASSWORD)
        auth_service.bootstrap_demo_user(VIEWER_PASSWORD)

        dispatcher = EventDispatcher(repo.SessionLocal)
        runtime = WorkflowRuntime(ExecutionTracker(repo.SessionLocal))
        document_indexed_workflow.register(dispatcher, runtime)
        event_publisher = InProcessEventPublisher(repo.SessionLocal, dispatcher)

        app.dependency_overrides[dependencies_module.build_repository] = lambda: repo
        app.dependency_overrides[dependencies_module.build_event_publisher] = lambda: event_publisher
        app.dependency_overrides[auth_module.build_repository] = lambda: repo
        app.dependency_overrides[auth_module.build_auth_service] = lambda: auth_service
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        try:
            yield repo, TestClient(app)
        finally:
            app.dependency_overrides.pop(dependencies_module.build_repository, None)
            app.dependency_overrides.pop(dependencies_module.build_event_publisher, None)
            app.dependency_overrides.pop(auth_module.build_repository, None)
            app.dependency_overrides.pop(auth_module.build_auth_service, None)
            app.dependency_overrides.pop(authorization_module.build_permission_checker, None)


def _login_headers(test_client, organization: str, email: str, password: str) -> dict[str, str]:
    response = test_client.post(
        "/api/auth/login",
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
        json={"organization": organization, "email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    identity = response.json()
    return {
        "X-API-Key": API_KEY,
        "X-Stratech-User-Id": str(identity["user_id"]),
        "X-Stratech-Organization-Id": str(identity["organization_id"]),
        "X-Stratech-Session-Id": identity["session_id"],
    }


# A/B/C -- seed authenticates correctly, as the correct organization and user.
def test_seed_authenticates_as_the_bootstrapped_administrator(env, monkeypatch, tmp_path):
    repo, test_client = env
    module = _load_seed_module(monkeypatch, test_client, tmp_path / "mock-response.json")

    identity_headers = module._login()

    with repo.SessionLocal() as session:
        org = repo.enterprise.get_organization_by_slug(session, "organizacao-principal")
        admin = repo.enterprise.get_user_by_email(session, org.id, ADMIN_EMAIL)

    assert identity_headers["X-Stratech-Organization-Id"] == str(org.id)
    assert identity_headers["X-Stratech-User-Id"] == str(admin.id)
    assert identity_headers["X-Stratech-Session-Id"]


# D -- tenant isolation preserved: the seed never writes to, and the demo/viewer
# organization never sees, the pilot dataset it produces.
def test_seed_preserves_tenant_isolation_from_demo_organization(env, monkeypatch, tmp_path):
    _repo, test_client = env
    module = _load_seed_module(monkeypatch, test_client, tmp_path / "mock-response.json")

    failures = module.seed()
    assert failures == 0

    viewer_headers = _login_headers(
        test_client, "demo-organization", "demo@stratech.local", VIEWER_PASSWORD
    )
    actions_response = test_client.get("/api/action-items", headers=viewer_headers)
    documents_response = test_client.get("/api/documents", headers=viewer_headers)
    assert actions_response.status_code == 200
    assert documents_response.status_code == 200
    assert actions_response.json() == []
    assert documents_response.json() == []


# E-H -- Projects/Actions/Decisions(risks)/Learnings-eligible data available,
# verified through the real read APIs (not a direct database query).
def test_seed_populates_projects_actions_risks_and_learnings_threshold(env, monkeypatch, tmp_path):
    _repo, test_client = env
    module = _load_seed_module(monkeypatch, test_client, tmp_path / "mock-response.json")

    failures = module.seed()
    assert failures == 0

    admin_headers = _login_headers(
        test_client, "organizacao-principal", ADMIN_EMAIL, ADMIN_PASSWORD
    )

    projects = test_client.get("/api/portfolio/summary", headers=admin_headers).json()
    assert {p["project_name"] for p in projects} == {name for name, *_ in module.PROJECTS}

    actions = test_client.get("/api/action-items", headers=admin_headers).json()
    assert len(actions) > 0

    risks = test_client.get("/api/risks/latest", headers=admin_headers).json()
    assert len(risks) > 0
    # web/lib/decision-center/decision-queue.ts: red/yellow status always
    # queues a Decision -- both are present in the seed's own PROJECTS.
    statuses = {p["latest_health_status"] for p in projects}
    assert "red" in statuses
    assert "yellow" in statuses

    # web/lib/organizational-intelligence/organizational-learnings.ts
    # (MIN_OCCURRENCES=3): a Learning only appears when the exact same
    # description recurs across >=3 distinct projects. Verified here at the
    # data level so a future edit to PROJECTS/MEETINGS that silently drops
    # below the threshold fails this test, not a human noticing an empty
    # screen during the pilot session.
    risk_projects = {
        r["project_name"] for r in risks if r["description"] == module.RECURRING_RISK_DESCRIPTION
    }
    assert len(risk_projects) >= 3
    action_projects = {
        a["project_name"] for a in actions if a["description"] == module.RECURRING_ACTION_DESCRIPTION
    }
    assert len(action_projects) >= 3

    documents = test_client.get("/api/documents", headers=admin_headers).json()
    assert len(documents) == 1
    assert documents[0]["status"] == "indexed"


# I -- second-run behavior is predictable, not silently changed.
def test_seed_second_run_behavior_is_predictable(env, monkeypatch, tmp_path):
    _repo, test_client = env
    module = _load_seed_module(monkeypatch, test_client, tmp_path / "mock-response.json")

    assert module.seed() == 0
    admin_headers = _login_headers(
        test_client, "organizacao-principal", ADMIN_EMAIL, ADMIN_PASSWORD
    )
    actions_after_first = test_client.get("/api/action-items", headers=admin_headers).json()
    risks_after_first = test_client.get("/api/risks/latest", headers=admin_headers).json()
    documents_after_first = test_client.get("/api/documents", headers=admin_headers).json()

    assert module.seed() == 0
    actions_after_second = test_client.get("/api/action-items", headers=admin_headers).json()
    risks_after_second = test_client.get("/api/risks/latest", headers=admin_headers).json()
    documents_after_second = test_client.get("/api/documents", headers=admin_headers).json()

    # analysis_records is an append-only historical log by design (no
    # dedup in AnalysisRepository.save_analysis) -- Acoes accumulates...
    assert len(actions_after_second) == 2 * len(actions_after_first)
    # ...while Riscos/Decisoes stays stable: ProjectSummaryService.
    # list_latest_risks keeps only the most recent risk analysis per
    # project, by design.
    assert len(risks_after_second) == len(risks_after_first)
    # ...and Documents stays at one Document with a new DocumentVersion
    # (KnowledgeRepository.ingest reuses an existing Document by
    # source_name), never a duplicate Document row.
    assert len(documents_after_second) == len(documents_after_first) == 1


# J -- no real credential is ever persisted/printed by the script.
def test_seed_never_prints_the_admin_password(env, monkeypatch, tmp_path, capsys):
    _repo, test_client = env
    module = _load_seed_module(monkeypatch, test_client, tmp_path / "mock-response.json")

    module.seed()

    captured = capsys.readouterr()
    assert ADMIN_PASSWORD not in captured.out
    assert ADMIN_PASSWORD not in captured.err


def test_seed_fails_fast_without_admin_credentials(env, monkeypatch, tmp_path):
    _repo, _test_client = env
    monkeypatch.setenv("BACKEND_URL", "http://testserver")
    monkeypatch.setenv("API_KEY", API_KEY)
    monkeypatch.setenv("MOCK_LLM_RESPONSE_FILE", str(tmp_path / "mock-response.json"))
    monkeypatch.delenv("STRATECH_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("STRATECH_ADMIN_PASSWORD", raising=False)

    spec = importlib.util.spec_from_file_location("seed_demo_data_no_admin", SEED_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def _fail_if_called(*_args, **_kwargs):
        raise AssertionError("must not call the backend without admin credentials")

    monkeypatch.setattr(module.httpx, "post", _fail_if_called)

    with pytest.raises(SystemExit) as exc_info:
        module._login()
    assert exc_info.value.code == 1


# Pure data-shape regression guard (no network/DB): the Learnings trigger
# (MIN_OCCURRENCES=3, web/lib/organizational-intelligence/
# organizational-learnings.ts) depends on exact text recurring across >=3
# distinct projects -- catches a future edit to PROJECTS/MEETINGS that
# silently breaks it, without needing a live backend.
def test_recurring_descriptions_appear_in_at_least_three_projects():
    spec = importlib.util.spec_from_file_location("seed_demo_data_shape", SEED_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    risk_projects = {
        name
        for name, _context, _status, risk in module.PROJECTS
        if risk is not None
        for item in risk["risks"]
        if item["description"] == module.RECURRING_RISK_DESCRIPTION
    }
    assert len(risk_projects) >= 3

    action_projects = {
        name
        for name, _transcript, target in module.MEETINGS
        for item in target["action_items"]
        if item["description"] == module.RECURRING_ACTION_DESCRIPTION
    }
    assert len(action_projects) >= 3

    # Referential coherence (Section 4): every meeting must be about a
    # project the same script also analyzes -- no orphaned project name.
    project_names = {name for name, *_ in module.PROJECTS}
    meeting_names = {name for name, *_ in module.MEETINGS}
    assert meeting_names <= project_names
