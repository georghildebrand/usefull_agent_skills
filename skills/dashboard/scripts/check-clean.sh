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

subs="$(mktemp)"
words="$(mktemp)"
trap 'rm -f "$subs" "$words"' EXIT
python3 "$here/presets.py" "$private" > "$subs" || { echo "cannot read private file" >&2; exit 2; }
python3 "$here/presets.py" "$private" --words > "$words" || { echo "cannot read private file" >&2; exit 2; }

targets=("$root/skills/dashboard")
for e in $extra; do
  [ -e "$root/$e" ] && targets+=("$root/$e")
done
# Substring patterns match anywhere; word patterns (preset names, tile ids,
# split source parts) match only as whole words, so "work" does not hit "network".
hits=""
for mode in sub word; do
  if [ "$mode" = sub ]; then file="$subs"; flags="-rnIiF"; else file="$words"; flags="-rnIiwF"; fi
  [ -s "$file" ] || continue
  raw="$(grep $flags -f "$file" "${targets[@]}")"
  rc=$?
  if [ "$rc" -gt 1 ]; then
    echo "grep failed (status $rc), check did not run" >&2
    exit 2
  fi
  [ "$rc" -eq 0 ] && hits="$hits$raw"$'\n'
done
if [ -n "$hits" ]; then
  printf '%s' "$hits" | sed '/^$/d' | cut -d: -f1,2 | sed "s#^$root/##" | sort -u
  exit 1
fi
echo clean
