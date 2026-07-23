#!/usr/bin/env bash
# STRATECH RC-2 -- idempotent PostgreSQL app role/database management.
#
# Used by `make db-create` / `make reset-db`. Connects as a Postgres
# superuser to create/drop the app role and database -- how that
# connection authenticates varies by install:
#   - Native Linux install (apt/dnf): the "postgres" OS account has peer
#     auth trust over the unix socket. Run: sudo -u postgres make db-create
#   - Homebrew/Postgres.app (Mac), the official Windows installer, Docker,
#     or a managed/cloud instance: usually TCP + password auth. Set
#     PGHOST/PGPORT/PGPASSWORD (standard libpq env vars) and run plain
#     `make db-create`.
#   - Using the bundled docker-compose Postgres instead? Skip this script --
#     the container creates POSTGRES_DB/POSTGRES_USER on first boot.
#
# Usage: rc2-db.sh {create|reset|drop}
set -euo pipefail

APP_DB="${POSTGRES_DB:-aipmo}"
APP_USER="${POSTGRES_USER:-aipmo}"
APP_PASSWORD="${POSTGRES_PASSWORD:-aipmo}"

export PGUSER="${PG_ADMIN_USER:-postgres}"
export PGDATABASE="${PG_ADMIN_DATABASE:-postgres}"

ACTION="${1:-create}"

if ! command -v psql > /dev/null 2>&1; then
  echo "ERROR: psql not found. Install the PostgreSQL client tools before continuing." >&2
  exit 1
fi

_admin_psql() {
  # Try the current OS user first (works out of the box wherever the admin
  # connection uses password/TCP auth -- Mac, Windows, Docker, managed
  # Postgres). Falls back to `sudo -u postgres`, which is what a native
  # Linux install's peer-auth "postgres" OS account requires, so `make
  # db-create` stays a single hands-off command on the most common local
  # dev setup instead of demanding the caller remember to prefix sudo.
  if psql -v ON_ERROR_STOP=1 -tAc "$1" 2>/tmp/rc2-db-admin-psql.err; then
    return 0
  fi
  if command -v sudo > /dev/null 2>&1 && id postgres > /dev/null 2>&1; then
    sudo -u postgres env PGUSER="$PGUSER" PGDATABASE="$PGDATABASE" \
      psql -v ON_ERROR_STOP=1 -tAc "$1"
    return $?
  fi
  cat /tmp/rc2-db-admin-psql.err >&2
  return 1
}

_terminate_connections() {
  # backend_type = 'client backend' excludes autovacuum/background workers,
  # which a non-superuser admin role cannot terminate even on a database it owns.
  _admin_psql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$APP_DB' AND pid <> pg_backend_pid() AND backend_type = 'client backend'" > /dev/null
}

case "$ACTION" in
  create)
    echo "Ensuring role '$APP_USER' exists ..."
    _admin_psql "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$APP_USER') THEN CREATE ROLE $APP_USER LOGIN PASSWORD '$APP_PASSWORD' CREATEDB; END IF; END \$\$;" > /dev/null
    echo "Ensuring database '$APP_DB' exists ..."
    EXISTS="$(_admin_psql "SELECT 1 FROM pg_database WHERE datname='$APP_DB'")"
    if [ "$EXISTS" != "1" ]; then
      _admin_psql "CREATE DATABASE $APP_DB OWNER $APP_USER" > /dev/null
    fi
    echo "Database '$APP_DB' ready (role '$APP_USER')."
    ;;
  reset)
    echo "Dropping and recreating '$APP_DB' (all data will be lost) ..."
    _terminate_connections
    _admin_psql "DROP DATABASE IF EXISTS $APP_DB" > /dev/null
    _admin_psql "CREATE DATABASE $APP_DB OWNER $APP_USER" > /dev/null
    echo "Database '$APP_DB' reset."
    ;;
  drop)
    _terminate_connections
    _admin_psql "DROP DATABASE IF EXISTS $APP_DB" > /dev/null
    echo "Database '$APP_DB' dropped."
    ;;
  *)
    echo "Usage: $0 {create|reset|drop}" >&2
    exit 1
    ;;
esac
