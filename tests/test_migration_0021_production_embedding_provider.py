"""Migration 0021 -- Production Embedding Provider (Founder Decision D-177).

`chunks.embedding` moves from vector(16) (Mock placeholder) to
vector(1024) (Voyage AI `voyage-4`), and gains minimal provenance
(`embedding_provider`/`embedding_model`). Proven on real PostgreSQL:
existing 16-dim rows are deleted (no lossless 16->1024 conversion exists),
the new column accepts a real 1024-dim vector, provenance persists, and
downgrade restores the vector(16) shape.
"""
import os
import subprocess
import sys

from sqlalchemy import create_engine, text

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


def _column_type(conn, table_name: str, column_name: str) -> str | None:
    return conn.execute(
        text(
            "SELECT udt_name FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table_name, "c": column_name},
    ).scalar()


def _vector_dimension(conn, table_name: str, column_name: str) -> int | None:
    return conn.execute(
        text(
            "SELECT atttypmod FROM pg_attribute "
            "JOIN pg_class ON pg_attribute.attrelid = pg_class.oid "
            "WHERE pg_class.relname = :t AND attname = :c"
        ),
        {"t": table_name, "c": column_name},
    ).scalar()


def _seed_document_version(conn) -> tuple[int, int]:
    org_id = conn.execute(
        text(
            "INSERT INTO organizations (name, slug, created_at) "
            "VALUES ('Org A', 'org-a', now()) RETURNING id"
        )
    ).scalar()
    document_id = conn.execute(
        text(
            "INSERT INTO documents (organization_id, source_name, created_at) "
            "VALUES (:o, 'runbook.md', now()) RETURNING id"
        ),
        {"o": org_id},
    ).scalar()
    version_id = conn.execute(
        text(
            "INSERT INTO document_versions (document_id, content, created_at) "
            "VALUES (:d, 'hello world', now()) RETURNING id"
        ),
        {"d": document_id},
    ).scalar()
    return org_id, version_id


def test_0021_upgrade_replaces_dimension_and_downgrade_restores_it():
    with temp_database_url("migration_0021") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        engine = create_engine(database_url)

        _alembic(env, "upgrade", "0020")
        with engine.connect() as conn:
            assert _vector_dimension(conn, "chunks", "embedding") == 16
            org_id, version_id = _seed_document_version(conn)
            old_vector = "[" + ",".join(["0"] * 16) + "]"
            conn.execute(
                text(
                    "INSERT INTO chunks "
                    "(document_version_id, organization_id, chunk_index, text, embedding) "
                    "VALUES (:v, :o, 0, 'hello world', :e)"
                ),
                {"v": version_id, "o": org_id, "e": old_vector},
            )
            conn.commit()
            existing_count = conn.execute(text("SELECT COUNT(*) FROM chunks")).scalar()
            assert existing_count == 1

        _alembic(env, "upgrade", "0021")
        with engine.connect() as conn:
            # Old 16-dim mock rows carried zero semantic value (no real
            # production RAG was ever validated against them) -- deleted
            # by the migration itself, not preserved, since no lossless
            # conversion from 16 to 1024 dimensions exists.
            remaining_count = conn.execute(text("SELECT COUNT(*) FROM chunks")).scalar()
            assert remaining_count == 0

            assert _vector_dimension(conn, "chunks", "embedding") == 1024
            assert _column_type(conn, "chunks", "embedding_provider") == "varchar"
            assert _column_type(conn, "chunks", "embedding_model") == "varchar"

            # document_versions.content is never touched -- the document
            # can be reindexed against the new provider.
            content = conn.execute(
                text("SELECT content FROM document_versions WHERE id = :v"), {"v": version_id}
            ).scalar()
            assert content == "hello world"

            new_vector = "[" + ",".join(["0.1"] * 1024) + "]"
            chunk_id = conn.execute(
                text(
                    "INSERT INTO chunks "
                    "(document_version_id, organization_id, chunk_index, text, embedding, "
                    "embedding_provider, embedding_model) "
                    "VALUES (:v, :o, 0, 'hello world', :e, 'voyage', 'voyage-4') RETURNING id"
                ),
                {"v": version_id, "o": org_id, "e": new_vector},
            ).scalar()
            conn.commit()
            provider, model = conn.execute(
                text("SELECT embedding_provider, embedding_model FROM chunks WHERE id = :c"),
                {"c": chunk_id},
            ).one()
            assert provider == "voyage"
            assert model == "voyage-4"

        _alembic(env, "downgrade", "0020")
        with engine.connect() as conn:
            assert _vector_dimension(conn, "chunks", "embedding") == 16
            assert _column_type(conn, "chunks", "embedding_provider") is None
            assert _column_type(conn, "chunks", "embedding_model") is None
            remaining_count = conn.execute(text("SELECT COUNT(*) FROM chunks")).scalar()
            assert remaining_count == 0

        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            assert _vector_dimension(conn, "chunks", "embedding") == 1024

        engine.dispose()
