#!/bin/bash
# check-confidentiality.sh: fail (exit 1) if files contain absolute home paths or
# ticket keys. Checks tracked and untracked (not ignored) files in local-llm-guard/
# plus the plan and the spec. Skips tests/fixtures/.
self=$(readlink -f "$0" 2>/dev/null)
[ -n "$self" ] || { echo "check-confidentiality: cannot resolve own path" >&2; exit 5; }
here=$(cd "$(dirname "$self")/.." && pwd -P)
repo=$(git -C "$here" rev-parse --show-toplevel) || exit 2

# Built from two parts so this script does not match its own pattern.
home_re='/(Us'"ers|ho"'me)/[A-Za-z0-9._-]+'
ticket_re='\b[A-Z]{2,6}-[0-9]+\b'
allow_re=':(UTF-8|SHA-256|ISO-8601)$'

listing=$(git -C "$repo" ls-files -co --exclude-standard -- local-llm-guard \
  docs/superpowers/plans/2026-11-09-local-llm-guard.md \
  docs/superpowers/specs/2026-11-09-local-llm-guard-design.md) || exit 2

files=()
while IFS= read -r f; do
  case "$f" in local-llm-guard/tests/fixtures/*) continue ;; esac
  [ -n "$f" ] && [ -f "$repo/$f" ] && files+=("$repo/$f")
done <<<"$listing"
[ ${#files[@]} -gt 0 ] || { echo "check-confidentiality: no files to check" >&2; exit 2; }

status=0
for f in "${files[@]}"; do
  while IFS= read -r hit; do
    echo "home path: $hit"
    status=1
  done < <(grep -nHE "$home_re" "$f")
  while IFS= read -r hit; do
    echo "ticket key: $hit"
    status=1
  done < <(grep -noHE "$ticket_re" "$f" | grep -vE "$allow_re")
done
[ $status -eq 0 ] && echo "confidentiality check: ${#files[@]} files clean"
exit $status
