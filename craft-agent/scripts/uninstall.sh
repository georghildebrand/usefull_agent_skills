#!/bin/bash
# uninstall.sh: remove the symlinks install.sh created (only links that point into
# this folder). Keeps CRAFT_HOME, its data and the .craft-home link.
self=$(readlink -f "$0" 2>/dev/null)
[ -n "$self" ] || { echo "uninstall: cannot find its own folder (readlink -f failed)" >&2; exit 5; }
here=$(cd "$(dirname "$self")/.." && pwd -P) \
  || { echo "uninstall: cannot find the package folder" >&2; exit 5; }
claude=${CLAUDE_DIR:-$HOME/.claude}
lbin=${LOCAL_BIN:-$HOME/.local/bin}

remove_own() {
  if [ -L "$1" ]; then
    case $(readlink "$1") in
      "$here"/*) rm "$1" && echo "removed $1" ;;
    esac
  fi
}

for f in "$here"/agents/craft-*.md; do
  remove_own "$claude/agents/$(basename "$f")"
done
remove_own "$claude/skills/craft"
for b in craft-mcp craft-stage craft-app craft-guard; do
  remove_own "$lbin/$b"
done
