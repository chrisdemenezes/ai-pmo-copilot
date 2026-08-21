#!/usr/bin/env bash
# Regression test for H2 (Local V1 Pilot Final Hardening): demo/start-demo.sh
# must load demo/.env without re-interpreting values as shell syntax.
#
# Root cause (Local V1 Human User Session #2, D-222): `source "$ENV_FILE"`
# executes each line as a bash command. An unquoted value containing a space
# -- e.g. PILOT_ORGANIZATION_NAME=Piloto Externo A, the exact example used by
# docs/operations/LOCAL-V1-PILOT-ORGANIZATION-PROVISIONING-RUNBOOK.md -- is
# parsed as "assign PILOT_ORGANIZATION_NAME=Piloto, then run a command named
# Externo with argument A". The variable is never exported, and (because the
# script runs under `set -e`) the resulting "command not found" aborts the
# entire script.
#
# This test extracts the actual env-loading block from demo/start-demo.sh
# (not a reimplementation) and exercises it against scenarios A-H from the
# Local V1 Pilot Final Hardening mandate.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$ROOT_DIR/demo/start-demo.sh"
FAILURES=0

fail() {
  echo "FAIL: $1" >&2
  FAILURES=$((FAILURES + 1))
}

pass() {
  echo "PASS: $1"
}

LOADER_BLOCK="$(sed -n '/^set -a$/,/^set +a$/p' "$SCRIPT")"
if [ -z "$LOADER_BLOCK" ]; then
  echo "FATAL: could not extract the env-loading block from $SCRIPT -- has the script changed shape?" >&2
  exit 1
fi

# Runs the extracted block against a synthetic demo/.env fixture, printing
# each requested variable as NAME=[value] (with -- and $? -- of the whole
# subshell, so a `set -e` abort inside the block is visible as a non-zero
# exit rather than silently producing empty output).
run_loader() {
  local env_file="$1"
  shift
  local print_lines=""
  for var_name in "$@"; do
    print_lines="$print_lines echo \"$var_name=[\${$var_name:-UNSET}]\";"
  done
  ( bash -c "
      set -euo pipefail
      ENV_FILE='$env_file'
      $LOADER_BLOCK
      $print_lines
    "
  )
}

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# --- A. simple name, no space ------------------------------------------------
printf 'PILOT_ORGANIZATION_NAME=Acme\n' > "$TMP_DIR/a.env"
OUT_A="$(run_loader "$TMP_DIR/a.env" PILOT_ORGANIZATION_NAME)"
if echo "$OUT_A" | grep -qF "PILOT_ORGANIZATION_NAME=[Acme]"; then
  pass "A. simple name without space is exported correctly"
else
  fail "A. simple name without space: $OUT_A"
fi

# --- B. one space, unquoted (the Runbook's own example) ----------------------
printf 'PILOT_ORGANIZATION_NAME=Piloto Externo A\n' > "$TMP_DIR/b.env"
OUT_B="$(run_loader "$TMP_DIR/b.env" PILOT_ORGANIZATION_NAME)"
if echo "$OUT_B" | grep -qF "PILOT_ORGANIZATION_NAME=[Piloto Externo A]"; then
  pass "B. Runbook's own example (unquoted, one space) is exported correctly, no abort"
else
  fail "B. one space (unquoted): $OUT_B"
fi

# --- C. multiple spaces -------------------------------------------------------
printf 'PILOT_ORGANIZATION_NAME=Piloto   Externo    A\n' > "$TMP_DIR/c.env"
OUT_C="$(run_loader "$TMP_DIR/c.env" PILOT_ORGANIZATION_NAME)"
if echo "$OUT_C" | grep -qF "PILOT_ORGANIZATION_NAME=[Piloto   Externo    A]"; then
  pass "C. multiple spaces preserved exactly, no abort"
else
  fail "C. multiple spaces: $OUT_C"
fi

# --- D. PT-BR characters ------------------------------------------------------
printf 'PILOT_ORGANIZATION_NAME=Organizacao com Acentuacao e Cedilha Apice Acao\n' > "$TMP_DIR/d1.env"
OUT_D1="$(run_loader "$TMP_DIR/d1.env" PILOT_ORGANIZATION_NAME)"
printf 'PILOT_ORGANIZATION_NAME="Piloto \xc3\x81cao \xc3\x87\xc3\xa3o"\n' > "$TMP_DIR/d2.env"
OUT_D2="$(run_loader "$TMP_DIR/d2.env" PILOT_ORGANIZATION_NAME)"
if echo "$OUT_D1" | grep -qF "PILOT_ORGANIZATION_NAME=[Organizacao com Acentuacao e Cedilha Apice Acao]" \
   && echo "$OUT_D2" | grep -qF "PILOT_ORGANIZATION_NAME=[Piloto Ácao Ção]"; then
  pass "D. PT-BR characters (accented and quoted) exported correctly"
else
  fail "D. PT-BR characters: unquoted=$OUT_D1 quoted=$OUT_D2"
fi

# --- E. configuration absent ---------------------------------------------------
printf 'OTHER_VAR=1\n' > "$TMP_DIR/e.env"
OUT_E="$(run_loader "$TMP_DIR/e.env" PILOT_ORGANIZATION_NAME)"
if echo "$OUT_E" | grep -qF "PILOT_ORGANIZATION_NAME=[UNSET]"; then
  pass "E. absent configuration leaves the variable unset (bootstrap skip logic unaffected)"
else
  fail "E. absent configuration: $OUT_E"
fi

# --- F. invalid configuration (mismatched quote) does not abort the script ----
printf 'PILOT_ORGANIZATION_NAME="Piloto Externo A\n' > "$TMP_DIR/f.env"
if OUT_F="$(run_loader "$TMP_DIR/f.env" PILOT_ORGANIZATION_NAME)"; then
  pass "F. mismatched quote does not abort the script (fails safely downstream, e.g. organization not found)"
else
  fail "F. mismatched quote aborted the script instead of failing safely: $OUT_F"
fi

# --- G. Linux behavior preserved for existing variables (URL with :, /, @) ---
printf 'DATABASE_URL=postgresql://aipmo:aipmo@localhost:5432/aipmo\nPILOT_ORGANIZATION_NAME=Piloto Externo A\n' > "$TMP_DIR/g.env"
OUT_G="$(run_loader "$TMP_DIR/g.env" DATABASE_URL PILOT_ORGANIZATION_NAME)"
if echo "$OUT_G" | grep -qF "DATABASE_URL=[postgresql://aipmo:aipmo@localhost:5432/aipmo]" \
   && echo "$OUT_G" | grep -qF "PILOT_ORGANIZATION_NAME=[Piloto Externo A]"; then
  pass "G. existing variables (URLs with :, /, @) continue to load correctly alongside the fix"
else
  fail "G. existing variable compatibility: $OUT_G"
fi

# --- H. Windows/Git Bash: CRLF line endings ----------------------------------
printf 'PILOT_ORGANIZATION_NAME=Piloto Externo A\r\n' > "$TMP_DIR/h.env"
OUT_H="$(run_loader "$TMP_DIR/h.env" PILOT_ORGANIZATION_NAME)"
if echo "$OUT_H" | grep -qF "PILOT_ORGANIZATION_NAME=[Piloto Externo A]"; then
  pass "H. Windows/Git Bash CRLF line endings do not corrupt the value"
else
  fail "H. CRLF line endings: $OUT_H"
fi

if [ "$FAILURES" -ne 0 ]; then
  echo "$FAILURES failure(s)." >&2
  exit 1
fi
echo "All H2 env-loader checks (A-H) passed."
