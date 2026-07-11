#!/usr/bin/env bash
# Stops the processes started by start-demo.sh.
#
# Kills by recorded PID first (covers the common case), then by listening port
# as a safety net -- `next dev` forks a separate next-server child that a plain
# `kill` on the parent PID does not always reach.
set -uo pipefail
DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

for name in backend frontend; do
  pid_file="$DEMO_DIR/$name.pid"
  if [ -f "$pid_file" ]; then
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null
      echo "Stopped $name (pid $pid)"
    fi
    rm -f "$pid_file"
  fi
done

for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
  pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "$pids" | xargs kill 2>/dev/null
    echo "Stopped remaining process(es) on port $port"
  fi
done
