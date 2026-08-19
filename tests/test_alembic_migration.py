import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect

from tests.db import temp_database_url


def test_alembic_upgrade_head_matches_sqlalchemy_model():
    with temp_database_url("alembic_test") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url

        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=os.getcwd(),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

        engine = create_engine(database_url)
        inspector = inspect(engine)

        assert "analysis_records" in inspector.get_table_names()

        columns = {col["name"]: col for col in inspector.get_columns("analysis_records")}
        # TD-008 Fase 3b, Etapa 4b: the legacy project_name column was dropped
        # by migration 0015; project_id is the sole, mandatory identity key.
        assert set(columns) == {
            "id",
            "kind",
            "project_id",
            "organization_id",
            "payload",
            "created_at",
        }
        assert not columns["id"]["nullable"]
        assert not columns["kind"]["nullable"]
        # project_id is NOT NULL since migration 0015 (Etapa 4b).
        assert not columns["project_id"]["nullable"]
        # NOT NULL since migration 0010 (Security Hardening Gate, C-2).
        assert not columns["organization_id"]["nullable"]
        assert not columns["payload"]["nullable"]

        index_names = {idx["name"] for idx in inspector.get_indexes("analysis_records")}
        # ix_analysis_records_project_name dropped with the column (0015).
        assert "ix_analysis_records_project_name" not in index_names
        assert "ix_analysis_records_project_id" in index_names
        assert "ix_analysis_records_organization_id" in index_names
