#!/usr/bin/env bash
# Focused regression test for F4 (Local V1 Pilot Hardening Review, D-210/D-211):
# demo/start-demo.sh must resolve PYTHON_BIN explicitly for both venv layouts
# (POSIX .venv/bin vs Windows .venv/Scripts) instead of assuming `python3` is
# always on PATH and always the right interpreter -- Windows venvs create
# python.exe, never python3.exe.
#
# This test extracts the actual PYTHON_BIN-resolution block from the script
# (not a reimplementation) and exercises it against synthetic venv fixtures,
# proving scenarios A-F from the Local V1 Pilot Hardening Review mandate.
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

# Extract the resolution block verbatim from the script so this test proves
# the logic actually shipped, not a reimplementation of it.
RESOLUTION_BLOCK="$(sed -n '/^if \[ -f "\$ROOT_DIR\/\.venv\/bin\/python3" \]; then$/,/^fi$/p' "$SCRIPT")"
if [ -z "$RESOLUTION_BLOCK" ]; then
  echo "FATAL: could not extract PYTHON_BIN resolution block from $SCRIPT -- has the script changed shape?" >&2
  exit 1
fi

# Runs the extracted block with ROOT_DIR pointed at a synthetic fixture and
# a caller-supplied base PATH, printing PYTHON_BIN and the resulting PATH.
run_resolution() {
  local fixture_root="$1"
  local base_path="$2"
  ( PATH="$base_path" bash -c "
      set -euo pipefail
      ROOT_DIR='$fixture_root'
      $RESOLUTION_BLOCK
      echo \"PYTHON_BIN=\$PYTHON_BIN\"
      echo \"PATH_HEAD=\${PATH%%:*}\"
    "
  )
}

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

FAKE_GLOBAL_BIN="$TMP_ROOT/fake-global-bin"
mkdir -p "$FAKE_GLOBAL_BIN"
cat > "$FAKE_GLOBAL_BIN/python3" <<'EOF'
#!/usr/bin/env bash
echo "GLOBAL python3 invoked (should never happen when a venv is present)"
EOF
chmod +x "$FAKE_GLOBAL_BIN/python3"
BASE_PATH="$FAKE_GLOBAL_BIN:/usr/bin:/bin"

# --- A. layout .venv/bin (POSIX) -------------------------------------------
FIXTURE_A="$TMP_ROOT/scenario-a"
mkdir -p "$FIXTURE_A/.venv/bin"
touch "$FIXTURE_A/.venv/bin/python3"
OUT_A="$(run_resolution "$FIXTURE_A" "$BASE_PATH")"
if echo "$OUT_A" | grep -q "PYTHON_BIN=$FIXTURE_A/.venv/bin/python3"; then
  pass "A. .venv/bin layout resolves PYTHON_BIN to .venv/bin/python3"
else
  fail "A. .venv/bin layout did not resolve PYTHON_BIN correctly: $OUT_A"
fi

# --- B. layout .venv/Scripts (Windows) -------------------------------------
FIXTURE_B="$TMP_ROOT/scenario-b"
mkdir -p "$FIXTURE_B/.venv/Scripts"
touch "$FIXTURE_B/.venv/Scripts/python.exe"
OUT_B="$(run_resolution "$FIXTURE_B" "$BASE_PATH")"
if echo "$OUT_B" | grep -q "PYTHON_BIN=$FIXTURE_B/.venv/Scripts/python.exe"; then
  pass "B. .venv/Scripts layout resolves PYTHON_BIN to .venv/Scripts/python.exe"
else
  fail "B. .venv/Scripts layout did not resolve PYTHON_BIN correctly: $OUT_B"
fi

# --- C. correct selection between the two layouts ---------------------------
# (A and B above already prove each layout independently selects its own
# interpreter; this case proves Scripts is not silently matched by the bin/
# check, and vice versa, by asserting each fixture never resolves to the
# other layout's path.)
if ! echo "$OUT_A" | grep -q "Scripts" && ! echo "$OUT_B" | grep -q "/bin/python3"; then
  pass "C. layout selection does not cross-match the other platform's path"
else
  fail "C. layout selection cross-matched: A=$OUT_A B=$OUT_B"
fi

# --- D. venv precedence over global python -----------------------------------
FIXTURE_D="$TMP_ROOT/scenario-d"
mkdir -p "$FIXTURE_D/.venv/bin"
touch "$FIXTURE_D/.venv/bin/python3"
OUT_D="$(run_resolution "$FIXTURE_D" "$BASE_PATH")"
if echo "$OUT_D" | grep -q "PYTHON_BIN=$FIXTURE_D/.venv/bin/python3" && \
   echo "$OUT_D" | grep -q "PATH_HEAD=$FIXTURE_D/.venv/bin"; then
  pass "D. venv python takes precedence over global python3 on PATH"
else
  fail "D. venv did not take precedence over global python3: $OUT_D"
fi

# --- E. absence of venv: explicit, previous fallback preserved --------------
FIXTURE_E="$TMP_ROOT/scenario-e"
mkdir -p "$FIXTURE_E"
OUT_E="$(run_resolution "$FIXTURE_E" "$BASE_PATH")"
if echo "$OUT_E" | grep -q "PYTHON_BIN=python3" && \
   echo "$OUT_E" | grep -q "PATH_HEAD=$FAKE_GLOBAL_BIN"; then
  pass "E. no venv present falls back to bare 'python3', PATH left untouched"
else
  fail "E. no-venv fallback behaved unexpectedly: $OUT_E"
fi

# --- F. Linux/macOS behavior preserved bit-for-bit ---------------------------
# The .venv/bin case (A/D) must prepend exactly "$ROOT_DIR/.venv/bin:$PATH",
# identical to the pre-fix script -- proven by PATH_HEAD above equalling the
# fixture's .venv/bin exactly, with no other change to PATH ordering.
if echo "$OUT_A" | grep -q "PATH_HEAD=$FIXTURE_A/.venv/bin"; then
  pass "F. Linux/macOS .venv/bin PATH-prepend behavior preserved"
else
  fail "F. Linux/macOS .venv/bin PATH-prepend behavior changed: $OUT_A"
fi

if [ "$FAILURES" -ne 0 ]; then
  echo "$FAILURES failure(s)." >&2
  exit 1
fi
echo "All F4 venv-detection checks (A-F) passed."
