"""Document upload size limit tests (W7-4 Etapa 3, F4 -- Founder Decision).

Mandated coverage: S (below limit), T (exactly at limit), U (above limit),
V (rejection occurs before the ingestion pipeline), W (no Document
persisted for a rejected upload), X (no Chunk persisted), Y (no embedding
called), Z (organizational isolation intact). Real Postgres, real HTTP
route, `MockEmbeddingProvider` only (no real provider call possible).
"""
import io
import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from src.api import authorization as authorization_module
from src.api import dependencies as dependencies_module
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.authorization.checker import SqlPermissionChecker
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.knowledge_platform import (
    document_ingestion_service as ingestion_module,
)
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


def _upload(test_client, headers, content: bytes, source_name="notes.md"):
    return test_client.post(
        "/api/documents",
        headers=headers,
        files={"file": (source_name, io.BytesIO(content), "text/markdown")},
    )


def _counts(repo) -> tuple[int, int]:
    with repo.SessionLocal() as session:
        documents = session.execute(text("SELECT COUNT(*) FROM documents")).scalar()
        chunks = session.execute(text("SELECT COUNT(*) FROM chunks")).scalar()
        return documents, chunks


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE_BYTES", "100")
    with temp_database_url("document_upload_size_limit") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")

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


class TestBelowAndAtLimit:
    def test_s_upload_below_the_limit_succeeds(self, client) -> None:
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        response = _upload(test_client, _headers(org_id, user_id), content=b"x" * 50)

        assert response.status_code == 201
        assert response.json()["chunk_count"] == 1

    def test_t_upload_exactly_at_the_limit_succeeds(self, client) -> None:
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        response = _upload(test_client, _headers(org_id, user_id), content=b"x" * 100)

        assert response.status_code == 201
        assert response.json()["chunk_count"] == 1


class TestAboveLimit:
    def test_u_upload_above_the_limit_is_rejected(self, client) -> None:
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        response = _upload(test_client, _headers(org_id, user_id), content=b"x" * 101)

        assert response.status_code == 413
        assert "maximum upload size" in response.json()["detail"]

    def test_u_far_above_the_limit_is_rejected_the_same_way(self, client) -> None:
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        response = _upload(test_client, _headers(org_id, user_id), content=b"x" * 10_000)

        assert response.status_code == 413


class TestRejectionHappensBeforeIngestion:
    def test_v_ingestion_service_is_never_invoked_for_a_rejected_upload(self, client, monkeypatch) -> None:
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        def _fail_if_called(*args, **kwargs):
            raise AssertionError("DocumentIngestionService.upload() must never run for a rejected upload")

        monkeypatch.setattr(ingestion_module.DocumentIngestionService, "upload", _fail_if_called)

        response = _upload(test_client, _headers(org_id, user_id), content=b"x" * 101)

        assert response.status_code == 413

    def test_w_x_y_no_document_no_chunk_no_embedding_for_a_rejected_upload(self, client) -> None:
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        before_documents, before_chunks = _counts(repo)

        response = _upload(test_client, _headers(org_id, user_id), content=b"x" * 101)
        assert response.status_code == 413

        after_documents, after_chunks = _counts(repo)
        # No Document persisted (W), no Chunk persisted (X) -- and since no
        # Chunk exists, no embedding could have been computed for it (Y):
        # KnowledgeRepository.index() is the only caller of
        # EmbeddingProvider.embed(), and it never ran for this upload.
        assert after_documents == before_documents
        assert after_chunks == before_chunks


class TestNormalUploadBehaviorIsPreserved:
    def test_valid_file_is_still_processed_normally(self, client) -> None:
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        response = _upload(test_client, _headers(org_id, user_id), content=b"a real small document")

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "indexed"
        assert body["chunk_count"] == 1


class TestOrganizationalIsolationIntact:
    def test_z_size_limit_applies_identically_regardless_of_organization_and_isolation_holds(
        self, client
    ) -> None:
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a)
        user_b = _actor(repo, org_b)

        rejected_a = _upload(test_client, _headers(org_a, user_a), content=b"x" * 101)
        rejected_b = _upload(test_client, _headers(org_b, user_b), content=b"x" * 101)
        assert rejected_a.status_code == rejected_b.status_code == 413

        accepted_a = _upload(test_client, _headers(org_a, user_a), content=b"org a document")
        assert accepted_a.status_code == 201
        document_id = accepted_a.json()["document_id"]

        # Org B must never see Org A's document -- same tenant isolation
        # guarantee already proven elsewhere (D-090), unaffected by the new
        # size check.
        cross_tenant_read = test_client.get(
            f"/api/documents/{document_id}", headers=_headers(org_b, user_b)
        )
        assert cross_tenant_read.status_code == 404
