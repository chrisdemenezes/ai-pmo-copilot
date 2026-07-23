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
        )
        assert result.returncode == 0, result.stderr

        engine = create_engine(database_url)
        inspector = inspect(engine)

        assert "analysis_records" in inspector.get_table_names()

        columns = {col["name"]: col for col in inspector.get_columns("analysis_records")}
        assert set(columns) == {"id", "kind", "project_name", "project_id", "payload", "created_at"}
        assert not columns["id"]["nullable"]
        assert not columns["kind"]["nullable"]
        assert columns["project_name"]["nullable"]
        # Nullable during the Release 0.1 transition; NOT NULL lands in Épico 4.
        assert columns["project_id"]["nullable"]
        assert not columns["payload"]["nullable"]

        index_names = {idx["name"] for idx in inspector.get_indexes("analysis_records")}
        assert "ix_analysis_records_project_name" in index_names
        assert "ix_analysis_records_project_id" in index_names
