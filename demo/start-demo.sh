#!/usr/bin/env bash
# DPS-01 Sprint 1 — single command to bring up the demo environment.
#
# Starts the real backend (uvicorn) and the real frontend (next dev) exactly
# as documented in README.md / web/README.md. Creates no new architecture:
# this is orchestration only, reusing the same commands a developer already
# runs by hand.
#
# PostgreSQL + pgvector is required -- confirmed empirically (Local V1 User
# Validation Plan, D-203): the migration chain fails against SQLite at
# 0010_security_hardening.py, well before the Knowledge Platform's pgvector
# requirement (0016). Set DATABASE_URL to a real PostgreSQL instance before
# running this script (`make dev` already does, via db-create + migrate).
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$DEMO_DIR")"
ENV_FILE="$DEMO_DIR/.env"

# Prefer the project venv (uvicorn, alembic) regardless of whether the
# caller already activated it -- covers both direct invocation and
# `make dev`, which calls this script in its own subshell. venv layout
# differs by platform: POSIX python puts binaries in bin/, Windows
# (including Git Bash on Windows, still a Windows-built venv) puts them in
# Scripts/ and names the interpreter python.exe, never python3.exe -- so
# PYTHON_BIN must be resolved explicitly rather than assuming `python3`.
if [ -f "$ROOT_DIR/.venv/bin/python3" ]; then
  PATH="$ROOT_DIR/.venv/bin:$PATH"
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python3"
elif [ -f "$ROOT_DIR/.venv/Scripts/python.exe" ]; then
  PATH="$ROOT_DIR/.venv/Scripts:$PATH"
  PYTHON_BIN="$ROOT_DIR/.venv/Scripts/python.exe"
else
  PYTHON_BIN="python3"
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "demo/.env not found -- creating one from demo/.env.example with a generated SESSION_SECRET."
  cp "$DEMO_DIR/.env.example" "$ENV_FILE"
  GENERATED_SECRET="$(openssl rand -base64 32)"
  # Portable in-place edit (works on both GNU and BSD sed).
  sed -i.bak "s#^SESSION_SECRET=.*#SESSION_SECRET=${GENERATED_SECRET}#" "$ENV_FILE"
  rm -f "$ENV_FILE.bak"
  echo "Created $ENV_FILE (Demo Mode: mock provider, no external credential needed)."
fi

# Load demo/.env line-by-line instead of `source`-ing it as a bash script.
# `source` previously executed each line as a shell command: an unquoted
# value containing a space (e.g. PILOT_ORGANIZATION_NAME=Piloto Externo A --
# the exact example used by the Pilot Organization Provisioning Runbook) is
# parsed by bash as "assign PILOT_ORGANIZATION_NAME=Piloto, then run a
# command named Externo with argument A" -- the variable was never exported
# at all, and (because this script runs under `set -e`) the "command not
# found" aborted the whole script. This loader reads each line as literal
# data (no re-interpretation as shell syntax), so values with spaces work
# whether or not they are quoted; one matching pair of surrounding quotes is
# stripped if present, for compatibility with already-quoted values.
set -a
while IFS= read -r line || [ -n "$line" ]; do
  line="${line%$'\r'}"
  case "$line" in
    ''|'#'*) continue ;;
  esac
  case "$line" in
    *=*) ;;
    *) continue ;;
  esac
  key="${line%%=*}"
  value="${line#*=}"
  first_char="${value:0:1}"
  last_char="${value: -1}"
  if { [ "$first_char" = '"' ] && [ "$last_char" = '"' ]; } || { [ "$first_char" = "'" ] && [ "$last_char" = "'" ]; }; then
    if [ "${#value}" -ge 2 ]; then
      value="${value:1:${#value}-2}"
    fi
  fi
  export "$key=$value"
done < "$ENV_FILE"
set +a

if [ "${LLM_PROVIDER:-}" = "anthropic" ] && [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "WARNING: LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is empty."
  echo "The backend will start, but any /api/*/analyze call will fail with a 503"
  echo "(provider_config_error) until a real key is set in demo/.env."
fi

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
LOG_DIR="$DEMO_DIR/logs"
mkdir -p "$LOG_DIR"

case "${DATABASE_URL:-}" in
  postgresql://*|postgres://*) DB_LABEL="PostgreSQL" ;;
  ""|sqlite://*) DB_LABEL="SQLite (unsupported since migration 0010 -- set DATABASE_URL to PostgreSQL)" ;;
  *) DB_LABEL="DATABASE_URL=${DATABASE_URL}" ;;
esac

# Migrations run here unconditionally so this script alone is a complete
# bring-up regardless of entry point (direct call or `make dev`, which also
# runs this as its last step) -- alembic upgrade head is idempotent, and
# this is also where the Enterprise Domain seed (migrations 0002 + 0008:
# Organizations, Roles, Portfolios, Programs, Projects) is applied.
echo "Applying database migrations ($DB_LABEL) ..."
(cd "$ROOT_DIR" && DATABASE_URL="${DATABASE_URL:-}" "$PYTHON_BIN" -m alembic upgrade head)

echo "Starting backend on :$BACKEND_PORT ($DB_LABEL) ..."
(
  cd "$ROOT_DIR"
  API_KEY="$API_KEY" LLM_PROVIDER="$LLM_PROVIDER" ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
    MOCK_LLM_RESPONSE_FILE="${MOCK_LLM_RESPONSE_FILE:-}" \
    uvicorn src.main:app --host 0.0.0.0 --port "$BACKEND_PORT" \
    > "$LOG_DIR/backend.log" 2>&1 &
  echo $! > "$DEMO_DIR/backend.pid"
)

echo "Starting frontend on :$FRONTEND_PORT ..."
(
  cd "$ROOT_DIR/web"
  BACKEND_URL="http://localhost:$BACKEND_PORT" API_KEY="$API_KEY" \
    WORKSPACE_PASSWORD="$WORKSPACE_PASSWORD" SESSION_SECRET="$SESSION_SECRET" \
    ./node_modules/.bin/next dev -p "$FRONTEND_PORT" \
    > "$LOG_DIR/frontend.log" 2>&1 &
  echo $! > "$DEMO_DIR/frontend.pid"
)

echo "Waiting for backend health check ..."
for _ in $(seq 1 30); do
  if curl -sf "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
    echo "Backend is up: http://localhost:$BACKEND_PORT"
    break
  fi
  sleep 1
done

echo "Waiting for frontend ..."
for _ in $(seq 1 60); do
  if curl -sf "http://localhost:$FRONTEND_PORT/entrar" > /dev/null 2>&1; then
    echo "Frontend is up: http://localhost:$FRONTEND_PORT/entrar"
    break
  fi
  sleep 1
done

cat <<EOF

Demo environment ready.

  Login:     http://localhost:$FRONTEND_PORT/entrar  (password: $WORKSPACE_PASSWORD)
  Dashboard: http://localhost:$FRONTEND_PORT/dashboard
  Backend:   http://localhost:$BACKEND_PORT/health

Enterprise Domain data (Organizations, Roles, Portfolios, Programs, Projects)
is already seeded by the migrations (0002 + 0008) that ran on startup.

Optional: python3 demo/seed_demo_data.py adds a fictitious SAP portfolio
via the AI analysis endpoints -- a separate, additive demo capability.

Logs:  $LOG_DIR/backend.log, $LOG_DIR/frontend.log
Stop:  demo/stop-demo.sh
EOF
