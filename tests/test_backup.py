"""Backup Contract tests (W7-3 Etapa 1, Founder Decision).

Mandated coverage (Founder mandate letters, subset applicable to backup):
A. backup válido; B. falha explícita do backup; C. metadata/release
identificável; O. nenhuma credencial real persistida. All destructive/real
`pg_dump` runs happen exclusively against isolated, throwaway test
databases (`tests.db.temp_database_url`) -- never a shared or real
environment.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text

from src.database.backup import BackupError, create_backup
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


def _seed_organization(conn) -> int:
    return conn.execute(
        text("INSERT INTO organizations (name, slug, created_at) VALUES ('Org A', 'org-a', now()) RETURNING id")
    ).scalar()


class TestCreateBackup:
    def test_produces_a_valid_verifiable_artifact(self, tmp_path: Path) -> None:
        with temp_database_url("backup_valid") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "head")
            engine = create_engine(database_url)
            with engine.connect() as conn:
                _seed_organization(conn)
                conn.commit()
            engine.dispose()

            metadata = create_backup(
                database_url=database_url,
                destination_dir=tmp_path,
                environment="staging",
                release_sha="abc123",
                alembic_revision="0021",
            )

            assert metadata.path.exists()
            assert metadata.size_bytes > 0
            assert metadata.path.stat().st_size == metadata.size_bytes

    def test_metadata_sidecar_identifies_release_environment_and_schema(self, tmp_path: Path) -> None:
        with temp_database_url("backup_metadata") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "head")

            metadata = create_backup(
                database_url=database_url,
                destination_dir=tmp_path,
                environment="production",
                release_sha="deadbeef",
                alembic_revision="0021",
            )

            sidecar_path = metadata.path.with_suffix(metadata.path.suffix + ".json")
            assert sidecar_path.exists()
            sidecar = json.loads(sidecar_path.read_text())
            assert sidecar["environment"] == "production"
            assert sidecar["release_sha"] == "deadbeef"
            assert sidecar["alembic_revision"] == "0021"
            assert "created_at" in sidecar
            assert sidecar["size_bytes"] > 0

    def test_never_persists_credentials_in_metadata(self, tmp_path: Path) -> None:
        with temp_database_url("backup_no_creds") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "head")

            metadata = create_backup(
                database_url=database_url,
                destination_dir=tmp_path,
                environment="staging",
                release_sha="abc123",
                alembic_revision="0021",
            )

            # The redacted form must never contain the credential portion
            # that appears before "@" in the real connection string.
            assert "@" not in metadata.database
            credential_portion = database_url.split("://", 1)[1].split("@", 1)[0]
            assert credential_portion not in metadata.database

            sidecar_path = metadata.path.with_suffix(metadata.path.suffix + ".json")
            sidecar_text = sidecar_path.read_text()
            assert credential_portion not in sidecar_text

    def test_fails_explicitly_when_pg_dump_cannot_connect(self, tmp_path: Path) -> None:
        unreachable_url = "postgresql://aipmo:aipmo@localhost:1/does_not_exist"
        with pytest.raises(BackupError, match="pg_dump failed"):
            create_backup(
                database_url=unreachable_url,
                destination_dir=tmp_path,
                environment="staging",
                release_sha="abc123",
                alembic_revision="0021",
            )
        # A failed pg_dump must never leave a misleading partial artifact
        # behind for a future restore to discover.
        assert list(tmp_path.iterdir()) == []

    def test_fails_explicitly_when_pg_dump_binary_is_missing(self, tmp_path: Path) -> None:
        with (
            patch("src.database.backup.subprocess.run", side_effect=FileNotFoundError()),
            pytest.raises(BackupError, match="pg_dump binary not found"),
        ):
            create_backup(
                database_url="postgresql://aipmo:aipmo@localhost:5432/aipmo",
                destination_dir=tmp_path,
                environment="staging",
                release_sha="abc123",
                alembic_revision="0021",
            )

    def test_fails_explicitly_when_artifact_fails_integrity_check(self, tmp_path: Path) -> None:
        """A `pg_dump` that "succeeds" but writes an unusable artifact (e.g.
        truncated by disk pressure) must still be rejected -- `pg_restore
        --list` is the real, independent verification, not just "the
        command exited 0"."""
        with temp_database_url("backup_integrity") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "head")

            real_run = subprocess.run

            def _fake_run(cmd, *args, **kwargs):
                if cmd[0] == "pg_dump":
                    Path(cmd[-1]).write_bytes(b"not a real dump")
                    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
                return real_run(cmd, *args, **kwargs)

            with (
                patch("src.database.backup.subprocess.run", side_effect=_fake_run),
                pytest.raises(BackupError, match="integrity check"),
            ):
                create_backup(
                    database_url=database_url,
                    destination_dir=tmp_path,
                    environment="staging",
                    release_sha="abc123",
                    alembic_revision="0021",
                )
            assert list(tmp_path.iterdir()) == []
