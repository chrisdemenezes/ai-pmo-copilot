"""Backup Contract (W7-3 Resilience & Disaster Recovery, Etapa 1 --
Founder Decision, Technical Design `TECHNICAL-DESIGN-W7-3-RESILIENCE-DISASTER-RECOVERY.md`
Section 8): the smallest mechanism that makes the already-approved
`PostgreSQL -> pg_dump -> versioned backup` contract executable and
verifiable, reusing exactly the tools `PRI-008` already documents
(`pg_dump`/`pg_restore`, no new backup platform). `chunks` (text + vector +
provenance) is backed up like every other table -- no special handling,
per the Technical Design's explicit rejection of reconstruction as a
primary recovery path.

Execution context is deliberately left to the operator (same assumption
`PRI-008`/`PRI-009` already make): this module only requires `pg_dump`/
`pg_restore` to be on `PATH` wherever it runs -- inside the `database`
container (which already has them, being the official Postgres image) or
on an operator host with `postgresql-client` installed. No change to the
`api` image was made, since none is required for this module to be tested
or used.
"""
import argparse
import json
import logging
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger(__name__)


class BackupError(Exception):
    """Raised when `pg_dump` fails, or the resulting artifact cannot be
    objectively verified as a usable backup."""


def _redact_database_url(database_url: str) -> str:
    """Never persist credentials -- keeps only host/port/database name, the
    same non-secret identification `PRI-008`'s own commands already expose
    on an operator's screen, never the user/password portion."""
    parts = urlsplit(database_url)
    netloc = parts.hostname or ""
    if parts.port:
        netloc = f"{netloc}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


@dataclass(frozen=True)
class BackupMetadata:
    """Everything the Restore Contract (Etapa 2) and a real DR Drill
    (Etapa 5, not executed by this mission) need to identify a backup
    artifact without ever needing to open it first."""

    path: Path
    environment: str
    release_sha: str
    alembic_revision: str
    created_at: datetime
    size_bytes: int
    database: str  # redacted -- host/port/dbname only, never credentials

    def to_json_dict(self) -> dict:
        data = asdict(self)
        data["path"] = str(self.path)
        data["created_at"] = self.created_at.isoformat()
        return data


def create_backup(
    database_url: str,
    destination_dir: Path,
    environment: str,
    release_sha: str,
    alembic_revision: str,
) -> BackupMetadata:
    """`pg_dump -Fc` (custom format, the same choice `PRI-008` Section 1
    already made and justifies: portable across Postgres image versions,
    supports selective restore, no exclusive lock). Fails explicitly
    (`BackupError`) on any `pg_dump` failure, a missing binary, an empty
    artifact, or an artifact that fails its own integrity check -- never
    silently returns a backup that cannot be trusted.
    """
    destination_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"aipmo_{environment}_{timestamp}.dump"
    path = destination_dir / filename

    try:
        subprocess.run(
            ["pg_dump", "--dbname", database_url, "-Fc", "-f", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise BackupError("pg_dump binary not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        # A failed pg_dump can still leave a partial/empty file at `path` --
        # never leave a misleading artifact behind for a future restore to
        # discover.
        path.unlink(missing_ok=True)
        raise BackupError(f"pg_dump failed (exit {exc.returncode}): {exc.stderr}") from exc

    if not path.exists() or path.stat().st_size == 0:
        path.unlink(missing_ok=True)
        raise BackupError(f"pg_dump produced no usable artifact at {path}")

    # Objective verification that the backup was produced (mandated by the
    # Founder): `pg_restore --list` only reads the archive's table of
    # contents -- it never connects to or mutates any database -- so this
    # is a real integrity check of the artifact itself, not a restore.
    try:
        subprocess.run(
            ["pg_restore", "--list", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise BackupError("pg_restore binary not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        path.unlink(missing_ok=True)
        raise BackupError(f"backup artifact failed its integrity check: {exc.stderr}") from exc

    size_bytes = path.stat().st_size
    metadata = BackupMetadata(
        path=path,
        environment=environment,
        release_sha=release_sha,
        alembic_revision=alembic_revision,
        created_at=datetime.now(timezone.utc),
        size_bytes=size_bytes,
        database=_redact_database_url(database_url),
    )

    # Metadata/release identification (Founder mandate): a sidecar JSON next
    # to the dump so a real DR event can identify a backup from the
    # artifact alone, without needing the Python return value that produced
    # it -- never contains the database_url's credentials.
    metadata_path = path.with_suffix(path.suffix + ".json")
    metadata_path.write_text(json.dumps(metadata.to_json_dict(), indent=2))

    logger.info(
        "Backup created path=%s environment=%s release_sha=%s alembic_revision=%s size_bytes=%d",
        path,
        environment,
        release_sha,
        alembic_revision,
        size_bytes,
    )
    return metadata


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Backup Contract (W7-3): pg_dump the current DATABASE_URL to a "
            "versioned, verifiable artifact. Never run against production "
            "without an already-validated Backup/Restore Contract in place."
        )
    )
    parser.add_argument(
        "--destination",
        required=True,
        help="Directory to write the backup artifact and its metadata sidecar into.",
    )
    parser.add_argument(
        "--environment",
        required=True,
        help="Environment identifier embedded in the artifact name and metadata (e.g. staging, production).",
    )
    parser.add_argument(
        "--release-sha",
        default=os.getenv("RELEASE_SHA", "unknown"),
        help="Release identity to embed in the metadata sidecar. Defaults to RELEASE_SHA.",
    )
    parser.add_argument(
        "--alembic-revision",
        required=True,
        help="Schema/migration revision to embed in the metadata sidecar (e.g. from `alembic current`).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1
    try:
        metadata = create_backup(
            database_url=database_url,
            destination_dir=Path(args.destination),
            environment=args.environment,
            release_sha=args.release_sha,
            alembic_revision=args.alembic_revision,
        )
    except BackupError as exc:
        print(f"Backup failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(metadata.to_json_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
