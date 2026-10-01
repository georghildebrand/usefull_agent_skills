#!/usr/bin/env bash
# Weekly run: index new transcripts, name topics, write the snapshot.
#
# Install as a cron entry, for example every Friday at 18:00:
#   0 18 * * 5 /path/to/usage-stats/scripts/weekly.sh >> ~/.claude/usage-stats/weekly.log 2>&1
#
# The report covers the previous completed ISO week, so a Friday run reports the
# week that ended on the preceding Sunday. Change --week if you want the running
# week instead.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${CLAUDE_USAGE_STATS_HOME:-$HOME/.claude/usage-stats}"
mkdir -p "$STATE"

# cron runs with a minimal PATH and would not find python3 or claude.
export PATH="$HOME/.local/bin:$HOME/.local/wrappers:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "$(date -u +%FT%TZ) python3 not found on PATH" >&2
  exit 1
fi

echo "=== $(date -u +%FT%TZ) weekly usage-stats run"

"$PY" "$HERE/extract.py" || echo "extract failed, continuing with what is stored" >&2

# Skip classification when the model cannot be reached, so the report still runs.
if command -v claude >/dev/null 2>&1; then
  "$PY" "$HERE/classify.py" || echo "classify failed, topics may be incomplete" >&2
else
  echo "claude CLI not found, skipping classification" >&2
fi

"$PY" "$HERE/report.py" --write-snapshot
