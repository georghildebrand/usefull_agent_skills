#!/bin/bash
# install.sh <craft-home>: create the local folders, the .craft-home link and the
# symlinks Claude Code and the shell need.
#
# Env: CLAUDE_DIR (default ~/.claude), LOCAL_BIN (default ~/.local/bin),
#      FORCE=1 to point an existing .craft-home link to another folder.
# Never replaces a file that is not a symlink, or a symlink that points outside
# this folder. Copies config.example.env only when config.env does not exist.
self=$(readlink -f "$0" 2>/dev/null)
[ -n "$self" ] || { echo "install: cannot find its own folder (readlink -f failed)" >&2; exit 5; }
here=$(cd "$(dirname "$self")/.." && pwd -P) \
  || { echo "install: cannot find the package folder" >&2; exit 5; }
claude=${CLAUDE_DIR:-$HOME/.claude}
lbin=${LOCAL_BIN:-$HOME/.local/bin}

fail() {
  echo "install: $1" >&2
  exit 1
}

[ $# -eq 1 ] || fail "usage: install.sh <craft-home>"
mkdir -p "$1/bin" "$1/jobs" "$1/logs" "$1/state" "$1/reviewed" || fail "cannot create $1"
home=$(cd "$1" && pwd -P)

link="$here/.craft-home"
if [ -L "$link" ]; then
  current=$(readlink "$link")
  if [ "$current" != "$home" ] && [ "${FORCE:-}" != 1 ]; then
    fail ".craft-home points to $current; run with FORCE=1 to change it to $home"
  fi
elif [ -e "$link" ]; then
  fail "$link exists and is not a symlink"
fi
ln -sfn "$home" "$link" || fail "cannot create $link"
echo "linked $link -> $home"

if [ ! -f "$home/config.env" ]; then
  cp "$here/config.example.env" "$home/config.env" || fail "cannot copy config.example.env"
  echo "created $home/config.env: edit ARTCRAFT_DIR and CRAFT_READ_ROOT"
fi

link_one() {
  # link_one <target> <link>
  if [ -L "$2" ]; then
    case $(readlink "$2") in
      "$here"/*) ;;
      *) fail "$2 is a symlink to $(readlink "$2"), not to this folder; not replacing it" ;;
    esac
  elif [ -e "$2" ]; then
    fail "$2 exists and is not a symlink; not replacing it"
  fi
  mkdir -p "$(dirname "$2")" || fail "cannot create $(dirname "$2")"
  ln -sfn "$1" "$2" || fail "cannot link $2"
  echo "linked $2"
}

for f in "$here"/agents/craft-*.md; do
  link_one "$f" "$claude/agents/$(basename "$f")"
done
link_one "$here/skill/craft" "$claude/skills/craft"
for b in craft-mcp craft-stage craft-app craft-guard; do
  link_one "$here/bin/$b" "$lbin/$b"
done

case ":$PATH:" in
  *":$lbin:"*) ;;
  *) echo "note: $lbin is not on PATH. Claude Code must find craft-mcp and craft-guard there." ;;
esac
echo "done. Start a new Claude Code session to load the agents."
