#!/usr/bin/env bash
# Focused regression test for the stop-demo.sh Windows finding (Founder
# Decision -- Local V1 Pilot Navigation Blocker, D-212): the port-based
# fallback in demo/stop-demo.sh used `lsof`, which does not exist on
# Windows/Git Bash, so it silently found nothing to kill there (masked by
# `2>/dev/null || true`) -- confirmed live during the Local Windows
# Revalidation, worked around manually via PowerShell Stop-Process.
#
# This test extracts the actual port-fallback block from the script (not a
# reimplementation) and exercises it against 3 scenarios: lsof present
# (Linux/macOS, unchanged behavior), lsof absent but netstat present
# (Windows, the new branch), and neither present (safe no-op, no crash).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$ROOT_DIR/demo/stop-demo.sh"
FAILURES=0

fail() {
  echo "FAIL: $1" >&2
  FAILURES=$((FAILURES + 1))
}

pass() {
  echo "PASS: $1"
}

# Extract the actual for-loop block verbatim from the script.
PORT_FALLBACK_BLOCK="$(sed -n '/^for port in "\$BACKEND_PORT" "\$FRONTEND_PORT"; do$/,/^done$/p' "$SCRIPT")"
if [ -z "$PORT_FALLBACK_BLOCK" ]; then
  echo "FATAL: could not extract the port-fallback block from $SCRIPT -- has the script changed shape?" >&2
  exit 1
fi

TMP_BIN="$(mktemp -d)"
trap 'rm -rf "$TMP_BIN"' EXIT

BASH_BIN="$(command -v bash)"

# Real lsof/netstat may already be reachable on this test machine's normal
# PATH -- a scenario bin dir alone is not enough to make either "absent" if
# PATH still falls through to the system's own directories. Each scenario
# gets an isolated bin dir containing only the real external tools the
# block actually needs (awk, sort, xargs, ...), so `command -v lsof`/
# `command -v netstat` can only ever find what the scenario itself stubs
# in -- never a real system binary.
#
# Thin exec wrapper scripts, not symlinks: on Windows/Git Bash, a symlink to
# an MSYS binary breaks its shared-library (DLL) resolution, which is
# relative to the executable's own real directory -- confirmed live during
# the Local Windows Revalidation ("awk: error while loading shared
# libraries"). A wrapper script has no such dependency; it just execs the
# real binary by its original absolute path.
make_isolated_bin() {
  local dir="$1"
  mkdir -p "$dir"
  for tool in awk sort xargs env bash cat; do
    local real_path
    real_path="$(command -v "$tool")"
    # Absolute-path shebang (not `#!/usr/bin/env bash`): env is itself one
    # of the wrapped tools here, and Git Bash resolves a shebang's
    # interpreter via its own PATH search, which would otherwise chase its
    # own tail through this directory's env wrapper.
    printf '#!%s\nexec "%s" "$@"\n' "$BASH_BIN" "$real_path" > "$dir/$tool"
    chmod +x "$dir/$tool"
  done
}

# Runs the extracted block with BACKEND_PORT/FRONTEND_PORT set to a single
# probe port and a fully isolated PATH. `xargs kill` execs `kill` as an
# external command (a shell function would not be inherited by xargs's
# child), so the stub must be a real executable on PATH ahead of anything
# else.
#
# The block is written to a temp *file* and executed with `bash file`, not
# interpolated into a `bash -c "...block..."` string: the block's own awk
# script contains single-quoted $2/$NF, and nesting that inside an outer
# double-quoted string would let this test's shell expand $2/$NF itself
# before awk ever saw them. A temp file sidesteps that quoting hazard
# entirely.
run_block() {
  local bin_dir="$1"
  local kill_log="$2"
  cat > "$bin_dir/kill" <<EOF
#!/usr/bin/env bash
echo "\$*" >> "$kill_log"
EOF
  chmod +x "$bin_dir/kill"
  local block_file="$bin_dir/block.sh"
  {
    echo 'set -uo pipefail'
    echo "$PORT_FALLBACK_BLOCK"
  } > "$block_file"
  PATH="$bin_dir" BACKEND_PORT="8000" FRONTEND_PORT="__no_such_port__" "$BASH_BIN" "$block_file"
}

# --- A. lsof present (Linux/macOS): unchanged behavior ----------------------
FIXTURE_A="$TMP_BIN/scenario-a"
make_isolated_bin "$FIXTURE_A"
cat > "$FIXTURE_A/lsof" <<'EOF'
#!/usr/bin/env bash
# Mimics `lsof -ti tcp:$port`: terse, PID-only output.
echo "4242"
EOF
chmod +x "$FIXTURE_A/lsof"
KILL_LOG_A="$TMP_BIN/kill-log-a"
: > "$KILL_LOG_A"
run_block "$FIXTURE_A" "$KILL_LOG_A" || true
if grep -q "4242" "$KILL_LOG_A"; then
  pass "A. lsof present: extracted PID passed to kill"
else
  fail "A. lsof present: expected PID 4242 was not killed. Log: $(cat "$KILL_LOG_A")"
fi

# --- B. lsof absent, netstat present (Windows): new fallback ----------------
FIXTURE_B="$TMP_BIN/scenario-b"
make_isolated_bin "$FIXTURE_B"
cat > "$FIXTURE_B/netstat" <<'EOF'
#!/usr/bin/env bash
# Realistic sample of `netstat -ano -p tcp` output on Windows: Proto,
# Local Address, Foreign Address, State, PID -- includes an IPv6 row, an
# unrelated port (must NOT match), and a suffix-similar port (80000 must
# not match the 8000 probe).
cat <<'NETSTAT_OUTPUT'
  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       15228
  TCP    127.0.0.1:8000         127.0.0.1:54321        ESTABLISHED     15228
  TCP    0.0.0.0:3000           0.0.0.0:0              LISTENING       22264
  TCP    [::]:8000              [::]:0                 LISTENING       15228
  TCP    0.0.0.0:80000          0.0.0.0:0              LISTENING       99999
NETSTAT_OUTPUT
EOF
chmod +x "$FIXTURE_B/netstat"
KILL_LOG_B="$TMP_BIN/kill-log-b"
: > "$KILL_LOG_B"
run_block "$FIXTURE_B" "$KILL_LOG_B" || true
if grep -q "15228" "$KILL_LOG_B"; then
  pass "B. netstat fallback: correct PID (15228) extracted for port 8000"
else
  fail "B. netstat fallback: expected PID 15228 was not killed. Log: $(cat "$KILL_LOG_B")"
fi
if grep -q "22264\|99999" "$KILL_LOG_B"; then
  fail "B. netstat fallback: an unrelated port's PID leaked into the kill list. Log: $(cat "$KILL_LOG_B")"
else
  pass "B. netstat fallback: unrelated ports (3000, 80000) correctly excluded"
fi

# --- C. neither lsof nor netstat present: safe no-op, no crash --------------
FIXTURE_C="$TMP_BIN/scenario-c"
make_isolated_bin "$FIXTURE_C"
KILL_LOG_C="$TMP_BIN/kill-log-c"
: > "$KILL_LOG_C"
if run_block "$FIXTURE_C" "$KILL_LOG_C"; then
  if [ ! -s "$KILL_LOG_C" ]; then
    pass "C. neither lsof nor netstat: no-op, no crash, nothing killed"
  else
    fail "C. neither lsof nor netstat: unexpectedly attempted a kill: $(cat "$KILL_LOG_C")"
  fi
else
  fail "C. neither lsof nor netstat: block exited non-zero instead of a safe no-op"
fi

if [ "$FAILURES" -ne 0 ]; then
  echo "$FAILURES failure(s)." >&2
  exit 1
fi
echo "All stop-demo.sh port-fallback checks (A-C) passed."
