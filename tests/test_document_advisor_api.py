"""Document Advisor HTTP route (Wave 5, Epic W5-1), per
`TECHNICAL-DESIGN-DOCUMENT-ADVISOR.md` §6.

Same rigor already established for `/risk-advisor/ask`
(`test_intelligence_api.py::TestRiskAdvisor`) and for `/documents`
(`test_documents_api.py`) -- real Postgres, real migration-seeded
permissions, real institutional headers, real `KnowledgeRepository` for
ingestion (direct, not via the Ingestion HTTP route -- W5-0 is already
proven end to end elsewhere; this file's concern is the Advisor route
itself).
"""
import json
import os
import subprocess
import sys

import pytest

from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api import dependencies as dependencies_module
from src.api.routes import intelligence
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.authorization.checker import SqlPermissionChecker
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.knowledge_platform.embedding_provider import MockEmbeddingProvider
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.vector_repository import PgVectorRepository

from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"


def _alembic(env, *args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
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


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "document_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nChunks: $chunks_json"


class FakeProvider:
    def generate(self, prompt):
        return "not json at all"  # falls back to unstructured, matching test_intelligence_api.py's convention


@pytest.fixture()
def client():
    with temp_database_url("document_advisor_api") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")  # seeds roles + knowledge.read/write (migration 0020)

        repo = AnalysisRepository(database_url=database_url)
        dispatcher = EventDispatcher(repo.SessionLocal)
        event_publisher = InProcessEventPublisher(repo.SessionLocal, dispatcher)
        vector_repository = PgVectorRepository(repo.SessionLocal)
        knowledge_repository = KnowledgeRepository(
            repo.SessionLocal, MockEmbeddingProvider(), vector_repository, event_publisher
        )

        app.dependency_overrides[intelligence.build_prompt_registry] = lambda: FakePromptRegistry()
        app.dependency_overrides[intelligence.build_provider] = lambda: FakeProvider()
        app.dependency_overrides[intelligence.build_repository] = lambda: repo
        app.dependency_overrides[dependencies_module.build_event_publisher] = lambda: event_publisher
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        yield TestClient(app), repo, knowledge_repository
        app.dependency_overrides.pop(intelligence.build_prompt_registry, None)
        app.dependency_overrides.pop(intelligence.build_provider, None)
        app.dependency_overrides.pop(intelligence.build_repository, None)
        app.dependency_overrides.pop(dependencies_module.build_event_publisher, None)
        app.dependency_overrides.pop(authorization_module.build_permission_checker, None)


class TestNoEvidence:
    def test_returns_a_canned_answer_without_calling_the_llm_when_nothing_is_indexed(self, client):
        test_client, repo, _knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        class ExplodingProvider:
            def generate(self, prompt):
                raise AssertionError("LLM must not be called when there is no indexed evidence")

        app.dependency_overrides[intelligence.build_provider] = lambda: ExplodingProvider()

        response = test_client.post(
            "/api/document-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "O que os documentos dizem sobre o orçamento?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "Nenhum documento relevante foi encontrado para responder a esta pergunta."
        assert body["cited_chunks"] == []


class TestRealCitation:
    def test_answers_from_an_indexed_chunk_with_a_real_citation(self, client):
        test_client, repo, knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        document = knowledge_repository.ingest(
            org_id, "runbook.md", "the middleware vendor has a history of delayed delivery"
        )
        knowledge_repository.index(document.id, CORRELATION_ID)

        class AdvisorProvider:
            def generate(self, prompt):
                # chunk_id 1 is deterministic here: first Chunk row ever
                # created in this isolated per-test database.
                return json.dumps(
                    {"answer": "O fornecedor de middleware tem histórico de atraso.", "cited_analysis_ids": [1]}
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/document-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Há histórico de atraso no fornecedor?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "O fornecedor de middleware tem histórico de atraso."
        assert body["cited_chunks"] == [
            {"document_id": document.id, "chunk_id": 1, "source_label": f"Document {document.id} / Chunk 1"}
        ]

    def test_discards_a_citation_the_model_invented(self, client):
        test_client, repo, knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        document = knowledge_repository.ingest(org_id, "runbook.md", "the rollback procedure is documented here")
        knowledge_repository.index(document.id, CORRELATION_ID)

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps(
                    {"answer": "O procedimento de rollback está documentado.", "cited_analysis_ids": [1, 999999]}
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/document-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Existe um procedimento de rollback?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["cited_chunks"]) == 1
        assert body["cited_chunks"][0]["chunk_id"] == 1


class TestRbac:
    def test_user_with_no_role_is_denied(self, client):
        test_client, repo, _knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "norole@example.com", "No Role")

        response = test_client.post(
            "/api/document-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "missing permission: knowledge.read"

    def test_viewer_can_ask(self, client):
        test_client, repo, _knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, "viewer")

        response = test_client.post(
            "/api/document-advisor/ask",
            headers=_headers(org_id, viewer_id),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 200


class TestOrganizationalIsolation:
    def test_never_cites_a_chunk_from_another_organization(self, client):
        test_client, repo, knowledge_repository = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a, "organization_admin")
        document = knowledge_repository.ingest(org_b, "confidential.md", "Org B's confidential rollback plan")
        knowledge_repository.index(document.id, CORRELATION_ID)

        class ExplodingProvider:
            def generate(self, prompt):
                raise AssertionError("must not synthesize over another organization's documents")

        app.dependency_overrides[intelligence.build_provider] = lambda: ExplodingProvider()

        response = test_client.post(
            "/api/document-advisor/ask",
            headers=_headers(org_a, user_a),
            json={"question": "Existe um plano de rollback?"},
        )

        assert response.status_code == 200
        assert response.json()["answer"] == "Nenhum documento relevante foi encontrado para responder a esta pergunta."
        assert response.json()["cited_chunks"] == []


class TestMalformedResponse:
    def test_returns_502_for_a_malformed_advisor_response(self, client):
        test_client, repo, knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        document = knowledge_repository.ingest(org_id, "runbook.md", "the rollback procedure is documented here")
        knowledge_repository.index(document.id, CORRELATION_ID)

        class NotJsonProvider:
            def generate(self, prompt):
                return "not json at all"

        app.dependency_overrides[intelligence.build_provider] = lambda: NotJsonProvider()

        response = test_client.post(
            "/api/document-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Existe um procedimento de rollback?"},
        )

        assert response.status_code == 502


class TestAuditTrail:
    def test_records_an_audit_entry_without_the_llm_answer(self, client):
        test_client, repo, _knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        response = test_client.post(
            "/api/document-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Alguma pergunta sobre documentos?"},
        )
        assert response.status_code == 200

        entries = repo.administration.list_audit_log(org_id)
        matching = [e for e in entries if e.action == "document_advisor.question_asked"]
        assert len(matching) == 1
        assert matching[0].actor_user_id == user_id
        assert matching[0].organization_id == org_id
        assert matching[0].details["question"] == "Alguma pergunta sobre documentos?"
        assert "answer" not in matching[0].details
