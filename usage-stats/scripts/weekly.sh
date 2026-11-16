#!/usr/bin/env bash
# Daily run: index new transcripts, name topics, write the weekly snapshot once.
#
# Run it every day. Indexing and classifying only touch sessions that are new, so
# a daily run costs about the same in total as a weekly one, and a missed day is
# caught up by the next run. The snapshot covers the previous completed ISO week
# and is written only when its file does not exist yet, so the first run after
# the week ends writes it and every later run leaves it alone.
#
# Prefer a launchd job over cron on macOS. Cron skips a run when the Mac sleeps at
# the scheduled time. launchd (StartCalendarInterval) runs it after the wake-up.
# Example for cron, every day at 18:00:
#   0 18 * * * /path/to/usage-stats/scripts/weekly.sh >> ~/.claude/usage-stats/weekly.log 2>&1
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${CLAUDE_USAGE_STATS_HOME:-$HOME/.claude/usage-stats}"
mkdir -p "$STATE"

# cron runs with a minimal PATH and would not find python3 or claude.
export PATH="$HOME/.local/bin:$HOME/.local/wrappers:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

# cron does not set USER, and claude cannot find its login without it
# ("Not logged in"), so every classification call failed.
export USER="${USER:-$(id -un)}"

PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "$(date -u +%FT%TZ) python3 not found on PATH" >&2
  exit 1
fi

echo "=== $(date -u +%FT%TZ) daily usage-stats run"

"$PY" "$HERE/extract.py" || echo "extract failed, continuing with what is stored" >&2

# Skip classification when the model cannot be reached, so the report still runs.
if command -v claude >/dev/null 2>&1; then
  "$PY" "$HERE/classify.py" || echo "classify failed, topics may be incomplete" >&2
  "$PY" "$HERE/classify.py" --label-gaps || echo "label-gaps failed" >&2
  "$PY" "$HERE/classify.py" --categorize || echo "categorize failed" >&2
else
  echo "claude CLI not found, skipping classification" >&2
fi

"$PY" "$HERE/report.py" --write-snapshot --if-missing
