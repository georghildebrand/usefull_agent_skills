#!/usr/bin/env bash
# Sandbox spike for local-llm-guard.
# Run it inside the same sandbox that Claude Code runs in (for example a terminal
# session started with nono). It prints only check results, never file content.
#
# Usage: spike_sandbox.sh <path-to-a-file-the-canary-blocks>

set -u

OLLAMA_URL="${OLLAMA_HOST:-http://127.0.0.1:11434}"
case "$OLLAMA_URL" in
  http://* | https://*) ;;
  *) OLLAMA_URL="http://$OLLAMA_URL" ;;
esac
BACKUP_DIR="$HOME/.local/state/local-llm-guard/backups"
FAILED=0

pass() { printf 'PASS  %s\n' "$1"; }
fail() {
  printf 'FAIL  %s: %s\n' "$1" "$2"
  FAILED=1
}

# 1. Ollama reachable
if out=$(curl -s --max-time 5 "$OLLAMA_URL/api/version" 2>&1) && [[ "$out" == *'"version"'* ]]; then
  pass "1 ollama reachable at $OLLAMA_URL ($out)"
else
  fail "1 ollama reachable at $OLLAMA_URL" "${out:-no answer}"
fi

# 2. osascript dialog
if out=$(osascript -e 'display dialog "local-llm-guard spike: click any button" buttons {"Cancel", "Write"} default button "Cancel" giving up after 30' 2>&1); then
  pass "2 osascript dialog ($out)"
else
  # Clicking Cancel makes osascript exit non-zero with error -128; the dialog still worked.
  if [[ "$out" == *"-128"* ]]; then
    pass "2 osascript dialog (Cancel clicked)"
  else
    fail "2 osascript dialog" "$out"
  fi
fi

# 3. write access to the backup folder
probe="$BACKUP_DIR/.spike-$$"
if out=$(mkdir -p "$BACKUP_DIR" 2>&1 && touch "$probe" 2>&1 && rm -f "$probe" 2>&1); then
  pass "3 write access to $BACKUP_DIR"
else
  fail "3 write access to $BACKUP_DIR" "$out"
fi

# 4. read access to a blocked file (content is never printed)
if [[ $# -lt 1 ]]; then
  fail "4 read access" "no path given (pass a file the canary blocks)"
elif [[ -r "$1" ]] && head -c 1 "$1" >/dev/null 2>&1; then
  pass "4 read access to $1"
else
  fail "4 read access to $1" "not readable (missing, or denied by the sandbox)"
fi

exit "$FAILED"
