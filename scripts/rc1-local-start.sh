#!/usr/bin/env bash
# STRATECH V1 RC-1 -- single command to prepare AND start a local environment
# from a machine with no prior setup (no venv, no node_modules, no demo/.env).
#
# Adds only the missing preparation steps (Python venv + pip install, npm
# install) on top of the already-existing, already-documented bring-up in
# demo/start-demo.sh -- never duplicates that script's process-management
# logic (env file creation, backend/frontend start, health checks). See
# docs/product/release-candidate/Local-Installation-Guide.html for the full
# walkthrough and troubleshooting.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

echo "== STRATECH V1 RC-1 -- local environment preparation =="

# 1. Prerequisite check (fail fast with a clear message instead of a confusing
#    error later in pip/npm).
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" > /dev/null 2>&1; then
  echo "ERROR: $PYTHON_BIN not found. Install Python 3.11+ before continuing." >&2
  exit 1
fi
PYTHON_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
PYTHON_MAJOR="${PYTHON_VERSION%%.*}"
PYTHON_MINOR="${PYTHON_VERSION##*.}"
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
  echo "ERROR: Python $PYTHON_VERSION found, but 3.11+ is required." >&2
  exit 1
fi
echo "Python $PYTHON_VERSION found."

if ! command -v node > /dev/null 2>&1; then
  echo "ERROR: node not found. Install Node.js 22+ before continuing." >&2
  exit 1
fi
NODE_MAJOR="$(node -e 'console.log(process.versions.node.split(".")[0])')"
if [ "$NODE_MAJOR" -lt 22 ]; then
  echo "ERROR: Node.js $(node -v) found, but 22+ is required." >&2
  exit 1
fi
echo "Node.js $(node -v) found."

# 2. Backend: venv + dependencies (skip if already installed -- fast re-run).
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating Python virtual environment at .venv ..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "Installing backend dependencies (requirements.txt) ..."
pip install --quiet --upgrade pip
pip install --quiet -r "$ROOT_DIR/requirements.txt"

# 3. Frontend: npm install (skip if node_modules already present).
if [ ! -d "$ROOT_DIR/web/node_modules" ]; then
  echo "Installing frontend dependencies (npm install) ..."
  (cd "$ROOT_DIR/web" && npm install)
else
  echo "Frontend dependencies already installed (web/node_modules present)."
fi

echo "== Preparation complete -- handing off to demo/start-demo.sh =="
echo

# 4. Delegate the actual bring-up (demo/.env creation, backend + frontend
#    start, health checks) to the existing, already-documented script --
#    reused as-is, never duplicated.
exec "$ROOT_DIR/demo/start-demo.sh"
