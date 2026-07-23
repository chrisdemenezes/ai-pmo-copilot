#!/usr/bin/env bash
# STRATECH RC-2 -- one-time local environment preparation (Python venv +
# backend deps, frontend deps). Extracted from rc1-local-start.sh so both
# the V1 RC-1 demo flow and the RC-2 `make setup` target share the exact
# same preparation steps instead of duplicating them.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

echo "== STRATECH -- local environment preparation =="

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

if ! command -v psql > /dev/null 2>&1; then
  echo "WARNING: psql not found on PATH. PostgreSQL client tools are required" >&2
  echo "for 'make db-create' / 'make reset-db'. Install PostgreSQL 16+ before" >&2
  echo "continuing -- see docs/product/release-candidate/RC-2/Quick-Start.md." >&2
fi

# 2. Backend: venv + dependencies (skip if already installed -- fast re-run).
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating Python virtual environment at .venv ..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
# venv layout differs by platform: POSIX python puts the activate script in
# bin/, the Windows python.org/Store build puts it in Scripts/ -- including
# when driven from Git Bash on Windows, which is still a Windows-built venv.
if [ -f "$VENV_DIR/bin/activate" ]; then
  ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
  ACTIVATE_SCRIPT="$VENV_DIR/Scripts/activate"
else
  echo "ERROR: could not find an activate script under $VENV_DIR (checked bin/ and Scripts/)." >&2
  exit 1
fi
# shellcheck disable=SC1090,SC1091
source "$ACTIVATE_SCRIPT"
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

echo "== Preparation complete =="
