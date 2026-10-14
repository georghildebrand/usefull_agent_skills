#!/bin/bash
# build.sh <tool> [cli|app]: build one ArtCraft binary with cargo and copy it to
# $CRAFT_HOME/bin.
#
# Refuses (exit 6) unless the repository has no uncommitted changes and its
# current commit was recorded by mark-reviewed.sh after a safety review: build
# scripts and proc macros run code on this machine during `cargo build`.
# --locked: cargo uses only the reviewed Cargo.lock; CRAFT_FONTS_DIR is unset so no fonts are embedded.
# Exit 7: cargo or the copy failed; the previous binary is kept.
self=$(readlink -f "$0" 2>/dev/null)
[ -n "$self" ] || { echo "build: cannot find its own folder (readlink -f failed)" >&2; exit 5; }
CRAFT_BIN=$(cd "$(dirname "$self")/../bin" && pwd -P) \
  || { echo "build: cannot find the bin folder" >&2; exit 5; }
# shellcheck source=../bin/lib/craft-common.sh
. "$CRAFT_BIN/lib/craft-common.sh"

{ [ $# -ge 1 ] && [ $# -le 2 ]; } || craft_fail 2 "usage: build.sh <tool> [cli|app]"
tool=$1
kind=${2:-cli}
craft_load_config || exit 5
craft_read_row "$tool" || craft_fail 2 "build: unknown tool '$tool' (known: $(craft_tool_keys))"
case $kind in
  cli) pkg=$TOOL_CLI ;;
  app) pkg=$TOOL_APP ;;
  *) craft_fail 2 "build: kind must be cli or app" ;;
esac
[ -n "${ARTCRAFT_DIR:-}" ] || craft_fail 5 "build: ARTCRAFT_DIR is not set in $CRAFT_HOME/config.env"
src="$ARTCRAFT_DIR/$TOOL_REPO"
git -C "$src" rev-parse --git-dir >/dev/null 2>&1 || craft_fail 5 "build: not a git clone: $src"

changes=$(git -C "$src" status --porcelain) || craft_fail 5 "build: git status failed in $src"
[ -z "$changes" ] || craft_fail 6 "build: $src has uncommitted changes; build only reviewed commits"
head=$(git -C "$src" rev-parse HEAD) || craft_fail 5 "build: git rev-parse failed in $src"
reviewed=$(cat "$CRAFT_HOME/reviewed/$TOOL_REPO" 2>/dev/null)
if [ "$reviewed" != "$head" ]; then
  craft_fail 6 "build: $TOOL_REPO is at $head, reviewed: ${reviewed:-none}. Review this commit (repo-install-safety-check), then run: make mark-reviewed TOOL=$tool"
fi

echo "building $pkg in $src"
# --target-dir and no CARGO_TARGET_DIR: the binary copied below is the one this
# build wrote.
(cd "$src" && env -u CARGO_TARGET_DIR -u CRAFT_FONTS_DIR \
  cargo build --release --locked --target-dir "$src/target" -p "$pkg") \
  || craft_fail 7 "build: cargo build failed for $pkg; kept the previous binary"
mkdir -p "$CRAFT_HOME/bin"
{ cp "$src/target/release/$pkg" "$CRAFT_HOME/bin/$pkg.new" \
  && mv -f "$CRAFT_HOME/bin/$pkg.new" "$CRAFT_HOME/bin/$pkg"; } \
  || craft_fail 7 "build: copy of $pkg failed; kept the previous binary"
echo "installed $CRAFT_HOME/bin/$pkg (commit $head)"
