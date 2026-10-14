#!/bin/bash
# mark-reviewed.sh <tool>: record the current commit of the tool's repository as
# reviewed, so build.sh may build it. Run it only after you have read a safety
# review of exactly this commit.
self=$(readlink -f "$0" 2>/dev/null)
[ -n "$self" ] || { echo "mark-reviewed: cannot find its own folder (readlink -f failed)" >&2; exit 5; }
CRAFT_BIN=$(cd "$(dirname "$self")/../bin" && pwd -P) \
  || { echo "mark-reviewed: cannot find the bin folder" >&2; exit 5; }
# shellcheck source=../bin/lib/craft-common.sh
. "$CRAFT_BIN/lib/craft-common.sh"

[ $# -eq 1 ] || craft_fail 2 "usage: mark-reviewed.sh <tool>"
craft_load_config || exit 5
craft_read_row "$1" || craft_fail 2 "mark-reviewed: unknown tool '$1' (known: $(craft_tool_keys))"
[ -n "${ARTCRAFT_DIR:-}" ] || craft_fail 5 "mark-reviewed: ARTCRAFT_DIR is not set in config.env"
src="$ARTCRAFT_DIR/$TOOL_REPO"
git -C "$src" rev-parse --git-dir >/dev/null 2>&1 || craft_fail 5 "mark-reviewed: not a git clone: $src"
changes=$(git -C "$src" status --porcelain) || craft_fail 5 "mark-reviewed: git status failed in $src"
[ -z "$changes" ] || craft_fail 6 "mark-reviewed: $src has uncommitted changes"
head=$(git -C "$src" rev-parse HEAD) || craft_fail 5 "mark-reviewed: git rev-parse failed in $src"
mkdir -p "$CRAFT_HOME/reviewed"
printf '%s\n' "$head" >"$CRAFT_HOME/reviewed/$TOOL_REPO"
echo "recorded $TOOL_REPO $head as reviewed"
