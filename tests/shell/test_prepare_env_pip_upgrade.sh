#!/usr/bin/env bash
# Focused regression test for F3 (Local V1 Pilot Hardening Review, D-210/D-211):
# scripts/prepare-env.sh must upgrade pip via `python -m pip`, never a bare
# `pip` call -- Windows cannot overwrite its own running executable, so
# `pip install --upgrade pip` fails there with "To modify pip, please run
# ...python.exe -m pip install...". This proves (a) the vulnerable literal
# pattern is gone from the script and (b) the line actually present in the
# script succeeds against a pip stub that fails exactly the way Windows does.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$ROOT_DIR/scripts/prepare-env.sh"
FAILURES=0

fail() {
  echo "FAIL: $1" >&2
  FAILURES=$((FAILURES + 1))
}

pass() {
  echo "PASS: $1"
}

# 1. Regression guard: the old vulnerable exact invocation must not return.
if grep -qE '^\s*pip install --quiet --upgrade pip\s*$' "$SCRIPT"; then
  fail "scripts/prepare-env.sh still calls bare 'pip install --upgrade pip' (Windows-incompatible)"
else
  pass "no bare 'pip install --upgrade pip' call in scripts/prepare-env.sh"
fi

# 2. The fixed line must be present, invoked via the Python interpreter.
PIP_UPGRADE_LINE="$(grep -E 'pip install --quiet --upgrade pip' "$SCRIPT" || true)"
if [ -z "$PIP_UPGRADE_LINE" ]; then
  fail "no pip upgrade line found at all in scripts/prepare-env.sh"
elif ! echo "$PIP_UPGRADE_LINE" | grep -qE '^\s*python -m pip install --quiet --upgrade pip\s*$'; then
  fail "pip upgrade line is not 'python -m pip install --quiet --upgrade pip': got: $PIP_UPGRADE_LINE"
else
  pass "pip upgrade line uses 'python -m pip'"
fi

# 3. Behavioral proof: stub `pip` to fail exactly like Windows does when
#    called directly, and stub `python` to only succeed via `-m pip`. Execute
#    the literal line extracted from the script against these stubs.
TMP_BIN="$(mktemp -d)"
trap 'rm -rf "$TMP_BIN"' EXIT

cat > "$TMP_BIN/pip" <<'EOF'
#!/usr/bin/env bash
echo "ERROR: To modify pip, please run the following command instead:" >&2
echo "C:\\path\\to\\.venv\\Scripts\\python.exe -m pip install --quiet --upgrade pip" >&2
exit 1
EOF
chmod +x "$TMP_BIN/pip"

cat > "$TMP_BIN/python" <<'EOF'
#!/usr/bin/env bash
if [ "$1" = "-m" ] && [ "$2" = "pip" ]; then
  echo "OK: python -m pip $*"
  exit 0
fi
echo "unexpected python invocation: $*" >&2
exit 1
EOF
chmod +x "$TMP_BIN/python"

if [ -n "$PIP_UPGRADE_LINE" ]; then
  if PATH="$TMP_BIN:$PATH" bash -c "$PIP_UPGRADE_LINE" > /dev/null 2>&1; then
    pass "extracted pip-upgrade line succeeds against a Windows-style pip stub"
  else
    fail "extracted pip-upgrade line failed against a Windows-style pip stub (still depends on bare 'pip')"
  fi
fi

if [ "$FAILURES" -ne 0 ]; then
  echo "$FAILURES failure(s)." >&2
  exit 1
fi
echo "All F3 pip-upgrade checks passed."
