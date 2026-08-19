"""Document Ingestion API (Wave 5, Epic W5-0), per
`TECHNICAL-DESIGN-W5-0-DOCUMENT-INGESTION.md`.

Includes the two tests mandated by "Founder Decision — Technical Design
W5-0" (D-090): Teste A (isolamento organizacional completo -- documentos de
uma organizacao nunca aparecem para outra, em nenhuma rota) and Teste B
(fluxo ponta a ponta upload->ingest->index->document.indexed->Workflow
Runtime->Execution Tracking, comprovado sem intervencao manual -- exercised
here through the real HTTP route, exactly what a caller would do).
"""
import io
import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.api import authorization as authorization_module
from src.api import dependencies as dependencies_module
from src.database.models import WorkflowExecution
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.authorization.checker import SqlPermissionChecker
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.vector_repository import PgVectorRepository
from src.workflows import document_indexed_workflow
from src.workflows.execution_tracking import ExecutionTracker
from src.workflows.runtime import WorkflowRuntime
from tests.db import temp_database_url


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


def _headers(organization_id: int, user_id: int) -> dict:
    return {
        "X-Stratech-User-Id": str(user_id),
        "X-Stratech-Organization-Id": str(organization_id),
        "X-Stratech-Session-Id": "session-1",
    }


def _actor(repo, organization_id: int, role: str = "organization_admin") -> int:
    user_id = repo.enterprise.create_user(organization_id, f"{role}@example.com", "Actor")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, user_id, role)
        session.commit()
    return user_id


def _upload(test_client, headers, source_name="notes.md", content=b"hello world rollback plan"):
    return test_client.post(
        "/api/documents",
        headers=headers,
        files={"file": (source_name, io.BytesIO(content), "text/markdown")},
    )


@pytest.fixture()
def client():
    with temp_database_url("documents_api") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")  # seeds roles + migration 0020 knowledge.read/write

        repo = AnalysisRepository(database_url=database_url)
        dispatcher = EventDispatcher(repo.SessionLocal)
        runtime = WorkflowRuntime(ExecutionTracker(repo.SessionLocal))
        document_indexed_workflow.register(dispatcher, runtime)
        event_publisher = InProcessEventPublisher(repo.SessionLocal, dispatcher)

        app.dependency_overrides[dependencies_module.build_repository] = lambda: repo
        app.dependency_overrides[dependencies_module.build_event_publisher] = lambda: event_publisher
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        yield TestClient(app), repo
        app.dependency_overrides.pop(dependencies_module.build_repository, None)
        app.dependency_overrides.pop(dependencies_module.build_event_publisher, None)
        app.dependency_overrides.pop(authorization_module.build_permission_checker, None)


class TestUploadAndStatus:
    def test_upload_returns_indexed_status(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        response = _upload(test_client, _headers(org_id, user_id))

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "indexed"
        assert body["chunk_count"] == 1
        assert body["source_name"] == "notes.md"

    def test_upload_rejects_empty_file(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        response = _upload(test_client, _headers(org_id, user_id), content=b"   ")
        assert response.status_code == 422

    def test_viewer_cannot_upload_but_can_read(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id, "organization_admin")
        viewer_id = _actor(repo, org_id, "viewer")

        upload_response = _upload(test_client, _headers(org_id, viewer_id))
        assert upload_response.status_code == 403

        uploaded = _upload(test_client, _headers(org_id, admin_id))
        document_id = uploaded.json()["document_id"]

        read_response = test_client.get(
            f"/api/documents/{document_id}", headers=_headers(org_id, viewer_id)
        )
        assert read_response.status_code == 200

    def test_get_document_includes_versions(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        document_id = _upload(test_client, _headers(org_id, user_id)).json()["document_id"]

        response = test_client.get(f"/api/documents/{document_id}", headers=_headers(org_id, user_id))
        assert response.status_code == 200
        body = response.json()
        assert len(body["versions"]) == 1
        assert body["versions"][0]["chunk_count"] == 1


class _BrokenEmbeddingProvider:
    """Simulates an EmbeddingProvider backend outage (Technical Design §6:
    the indexing exception must never be swallowed)."""

    def embed(self, text: str) -> list:
        raise RuntimeError("backend unavailable")


class TestIndexingFailureAndReindex:
    def test_indexing_failure_returns_502_with_retry_pointer(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        from src.api.routes import intelligence as intelligence_module

        dispatcher = EventDispatcher(repo.SessionLocal)
        broken_repository = KnowledgeRepository(
            repo.SessionLocal,
            _BrokenEmbeddingProvider(),
            PgVectorRepository(repo.SessionLocal),
            InProcessEventPublisher(repo.SessionLocal, dispatcher),
        )

        app.dependency_overrides[intelligence_module.build_knowledge_repository] = (
            lambda: broken_repository
        )
        try:
            response = _upload(test_client, _headers(org_id, user_id))
        finally:
            app.dependency_overrides.pop(intelligence_module.build_knowledge_repository, None)

        assert response.status_code == 502
        detail = response.json()["detail"]
        assert detail["status"] == "failed"
        document_id = detail["document_id"]

        status_response = test_client.get(
            f"/api/documents/{document_id}", headers=_headers(org_id, user_id)
        )
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "failed"
        assert status_response.json()["chunk_count"] == 0

        # Error is audited, sanitized -- type + message, never a traceback
        # (src.workflows.execution_tracking.sanitize_error, reused as-is).
        entries = repo.administration.list_audit_log(
            org_id, entity_type="document", entity_id=document_id
        )
        failed_entry = next(e for e in entries if e.action == "document.index_failed")
        assert failed_entry.details["error"] == "RuntimeError: backend unavailable"
        assert "Traceback" not in failed_entry.details["error"]

        # Retry via reindex succeeds once the transient failure is gone.
        reindex_response = test_client.post(
            f"/api/documents/{document_id}/reindex", headers=_headers(org_id, user_id)
        )
        assert reindex_response.status_code == 200
        assert reindex_response.json()["status"] == "indexed"


class TestOrganizationalIsolation:
    """Teste A (Founder Decision -- Technical Design W5-0, D-090): documentos
    de uma organizacao nunca aparecem para outra, em nenhuma rota."""

    def test_document_of_org_a_never_visible_to_org_b(self, client):
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a, "organization_admin")
        user_b = _actor(repo, org_b, "organization_admin")

        document_id = _upload(
            test_client, _headers(org_a, user_a), source_name="confidential-a.md"
        ).json()["document_id"]

        # GET detail: org B never confirms existence of org A's document.
        detail_response = test_client.get(
            f"/api/documents/{document_id}", headers=_headers(org_b, user_b)
        )
        assert detail_response.status_code == 404

        # GET list: org B's listing never contains org A's document.
        list_response = test_client.get("/api/documents", headers=_headers(org_b, user_b))
        assert list_response.status_code == 200
        assert all(doc["document_id"] != document_id for doc in list_response.json())

        # reindex: org B can never trigger a reindex of org A's document.
        reindex_response = test_client.post(
            f"/api/documents/{document_id}/reindex", headers=_headers(org_b, user_b)
        )
        assert reindex_response.status_code == 404

        # org A's own view is unaffected and still sees its document.
        own_list = test_client.get("/api/documents", headers=_headers(org_a, user_a))
        assert any(doc["document_id"] == document_id for doc in own_list.json())


class TestEndToEndChain:
    def test_upload_flows_through_event_pipeline_to_workflow_execution_tracking(self, client):
        """Teste B (Founder Decision -- Technical Design W5-0, D-090): a
        real HTTP upload flows upload->ingest->index->document.indexed->
        Workflow Runtime->Execution Tracking with zero manual intervention
        -- no direct call to EventDispatcher/WorkflowRuntime in this test."""
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        response = _upload(test_client, _headers(org_id, user_id), source_name="runbook.md")
        assert response.status_code == 201

        with repo.SessionLocal() as session:
            execution = session.execute(
                select(WorkflowExecution).where(
                    WorkflowExecution.workflow_name == document_indexed_workflow.WORKFLOW_NAME,
                    WorkflowExecution.organization_id == org_id,
                )
            ).scalar_one()

        assert execution.status == "completed"
        assert execution.error is None
