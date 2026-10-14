#!/bin/bash
# clean-jobs.sh <days>: delete job folders created more than <days> days ago
# (by folder modification time). Runs only when called; nothing calls it
# automatically.
self=$(readlink -f "$0" 2>/dev/null)
[ -n "$self" ] || { echo "clean-jobs: cannot find its own folder (readlink -f failed)" >&2; exit 5; }
CRAFT_BIN=$(cd "$(dirname "$self")/../bin" && pwd -P) \
  || { echo "clean-jobs: cannot find the bin folder" >&2; exit 5; }
# shellcheck source=../bin/lib/craft-common.sh
. "$CRAFT_BIN/lib/craft-common.sh"

[ $# -eq 1 ] || craft_fail 2 "usage: clean-jobs.sh <days>"
case $1 in ''|*[!0-9]*) craft_fail 2 "clean-jobs: days must be a number" ;; esac
craft_load_config || exit 5
[ -d "$CRAFT_JOBS" ] || exit 0
# find passes each folder to rm as one argument, so a name with a newline in it
# cannot turn into a second path.
echo "deleting job folders older than $1 days:"
find "$CRAFT_JOBS" -mindepth 1 -maxdepth 1 -type d -mtime +"$1" -print -exec rm -rf {} +
