#!/usr/bin/env bash
# STRATECH V1 RC-1 -- single command to prepare AND start a local environment
# from a machine with no prior setup (no venv, no node_modules, no demo/.env).
#
# Preparation steps (venv + pip install, npm install) live in
# scripts/prepare-env.sh, shared with the RC-2 `make setup` target so neither
# flow duplicates the other's logic. This script only adds the demo hand-off
# on top -- never duplicates demo/start-demo.sh's process-management logic
# (env file creation, backend/frontend start, health checks). See
# docs/product/release-candidate/Local-Installation-Guide.html for the full
# walkthrough and troubleshooting.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source "$ROOT_DIR/scripts/prepare-env.sh"

echo "== Preparation complete -- handing off to demo/start-demo.sh =="
echo

# Delegate the actual bring-up (demo/.env creation, backend + frontend start,
# health checks) to the existing, already-documented script -- reused as-is,
# never duplicated.
exec "$ROOT_DIR/demo/start-demo.sh"
