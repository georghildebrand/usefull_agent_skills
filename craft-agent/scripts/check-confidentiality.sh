#!/bin/bash
# check-confidentiality.sh [file...]: fail (exit 1) if files contain personal or
# internal data: absolute home paths, ticket-key patterns, or the words in
# CRAFT_DENY_WORDS from the local config.env. The deny list stays local, because
# a committed list of names would publish those names.
#
# Without arguments it checks every tracked and untracked (not ignored) file in
# craft-agent/ plus the craft-agent spec and plan.
self=$(readlink -f "$0" 2>/dev/null)
[ -n "$self" ] || { echo "check-confidentiality: cannot find its own folder (readlink -f failed)" >&2; exit 5; }
CRAFT_BIN=$(cd "$(dirname "$self")/../bin" && pwd -P) \
  || { echo "check-confidentiality: cannot find the bin folder" >&2; exit 5; }
# shellcheck source-path=SCRIPTDIR source=../bin/lib/craft-common.sh
. "$CRAFT_BIN/lib/craft-common.sh"
here=$(dirname "$CRAFT_BIN")
repo=$(cd "$here/.." && pwd -P)

files=()
if [ $# -gt 0 ]; then
  for f in "$@"; do
    [ -f "$f" ] || { echo "check-confidentiality: no such file: $f" >&2; exit 2; }
  done
  files=("$@")
else
  listing=$(git -C "$repo" ls-files -co --exclude-standard -- craft-agent \
    docs/superpowers/specs/2026-10-14-craft-agent-design.md \
    docs/superpowers/plans/2026-10-14-craft-agent.md) \
    || { echo "check-confidentiality: cannot list files" >&2; exit 2; }
  while IFS= read -r f; do
    [ -n "$f" ] && [ -f "$repo/$f" ] && files+=("$repo/$f")
  done <<<"$listing"
fi
[ ${#files[@]} -gt 0 ] || { echo "check-confidentiality: no files to check" >&2; exit 2; }

status=0
report() {
  echo "$1: $2"
  status=1
}

for f in "${files[@]}"; do
  while IFS= read -r hit; do
    report "home path" "$hit"
  done < <(grep -nHE '/(Users|home)/[A-Za-z0-9._-]+' "$f")
  while IFS= read -r hit; do
    report "ticket key" "$hit"
  done < <(grep -noHE '\b[A-Z][A-Z0-9]{1,9}-[0-9]+\b' "$f" \
    | grep -vE ':(UTF|SHA|ISO|AES|RFC|NFC|NFD|TLS|PDF)-[0-9]+$|:Z0-9$')
done

deny_note=" (deny words not checked)"
if craft_load_config 2>/dev/null && [ -n "${CRAFT_DENY_WORDS:-}" ]; then
  deny_note=""
  IFS=',' read -r -a words <<<"$CRAFT_DENY_WORDS"
  for w in "${words[@]}"; do
    w=$(printf '%s' "$w" | sed 's/^ *//; s/ *$//')
    [ -n "$w" ] || continue
    for f in "${files[@]}"; do
      while IFS= read -r hit; do
        report "deny word" "$hit"
      done < <(grep -niHF -- "$w" "$f")
    done
  done
else
  echo "note: no config.env or empty CRAFT_DENY_WORDS; deny words not checked" >&2
fi

[ $status -eq 0 ] && echo "confidentiality check: ${#files[@]} files clean$deny_note"
exit $status
