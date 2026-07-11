#!/usr/bin/env bash
# DPS-01 Sprint 1 — single command to bring up the demo environment.
#
# Starts the real backend (uvicorn, SQLite, no Docker/Postgres needed) and the
# real frontend (next dev) exactly as documented in README.md / web/README.md.
# Creates no new architecture: this is orchestration only, reusing the same
# commands a developer already runs by hand.
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$DEMO_DIR")"
ENV_FILE="$DEMO_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "demo/.env not found -- creating one from demo/.env.example with a generated SESSION_SECRET."
  cp "$DEMO_DIR/.env.example" "$ENV_FILE"
  GENERATED_SECRET="$(openssl rand -base64 32)"
  # Portable in-place edit (works on both GNU and BSD sed).
  sed -i.bak "s#^SESSION_SECRET=.*#SESSION_SECRET=${GENERATED_SECRET}#" "$ENV_FILE"
  rm -f "$ENV_FILE.bak"
  echo "Created $ENV_FILE (Demo Mode: mock provider, no external credential needed)."
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
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

echo "Starting backend on :$BACKEND_PORT (SQLite, no Docker) ..."
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

Next step: python3 demo/seed_demo_data.py   (populates the fictitious SAP portfolio)

Logs:  $LOG_DIR/backend.log, $LOG_DIR/frontend.log
Stop:  demo/stop-demo.sh
EOF
