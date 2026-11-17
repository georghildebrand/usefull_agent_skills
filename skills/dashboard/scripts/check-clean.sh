#!/usr/bin/env bash
# Fail when a value from the private presets file appears in the repo files.
# Prints file:line only, never the value.
# Usage: check-clean.sh [private_path]
# Test overrides: DASHBOARD_CHECK_ROOT (repo root), DASHBOARD_CHECK_EXTRA (space-separated paths; empty = none).
set -u
here="$(cd "$(dirname "$0")" && pwd)"
private="${1:-$HOME/.config/claude-dashboard/presets.json}"
root="${DASHBOARD_CHECK_ROOT:-$(cd "$here/../../.." && pwd)}"
extra_default="docs/superpowers/specs/2026-11-17-dashboard-design.md docs/superpowers/plans/2026-11-17-dashboard.md docs/superpowers/specs/2026-11-17-dashboard-prototype"
extra="${DASHBOARD_CHECK_EXTRA-$extra_default}"

if [ ! -f "$private" ]; then
  echo "no private file, nothing to check"
  exit 0
fi

patterns="$(mktemp)"
trap 'rm -f "$patterns"' EXIT
python3 "$here/presets.py" "$private" > "$patterns"

targets=("$root/skills/dashboard")
for e in $extra; do
  [ -e "$root/$e" ] && targets+=("$root/$e")
done
[ -s "$patterns" ] || { echo clean; exit 0; }

hits="$(grep -rnIiF -f "$patterns" "${targets[@]}" 2>/dev/null | cut -d: -f1,2)"
if [ -n "$hits" ]; then
  echo "$hits" | sed "s#^$root/##"
  exit 1
fi
echo clean
