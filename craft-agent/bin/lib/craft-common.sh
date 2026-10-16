# shellcheck shell=bash
# craft-common.sh: helpers shared by the craft-* scripts.
#
# Bash 3.2 compatible: macOS runs these scripts with /bin/bash.
# The caller sets CRAFT_BIN (the real path of the bin/ folder) before sourcing.

craft_fail() {
  # craft_fail <exit-code> <message>
  echo "$2" >&2
  exit "$1"
}

# The path helpers below run no subshell or external command (except readlink
# for a symlink): craft-guard calls them for every path in a tool call, and a
# fork costs several milliseconds on macOS.

craft_strip_slashes() {
  # Set CRAFT_REAL to $1 without trailing slashes ("/" stays "/").
  CRAFT_REAL=$1
  while [ "$CRAFT_REAL" != "/" ] && [ "${CRAFT_REAL%/}" != "$CRAFT_REAL" ]; do
    CRAFT_REAL=${CRAFT_REAL%/}
  done
}

craft_resolve_link_var() {
  # Set CRAFT_REAL to the real path of the absolute path $1, following every
  # symlink in the chain. Changes the working directory of the shell.
  local p=$1 t d hops=0
  craft_strip_slashes "$p"
  p=$CRAFT_REAL
  while [ -L "$p" ]; do
    hops=$((hops + 1))
    [ "$hops" -le 40 ] || return 1
    t=$(readlink "$p") || return 1
    case $t in
      /*) p=$t ;;
      *) p=${p%/*}/$t ;;
    esac
    craft_strip_slashes "$p"
    p=$CRAFT_REAL
  done
  d=${p%/*}
  [ -n "$d" ] || d=/
  cd -P -- "$d" 2>/dev/null || return 1
  if [ "$PWD" = "/" ]; then
    CRAFT_REAL=/${p##*/}
  else
    CRAFT_REAL=$PWD/${p##*/}
  fi
}

craft_resolve_link() {
  # Print the real path of $1, following every symlink in the chain.
  (craft_resolve_link_var "$1" && printf '%s\n' "$CRAFT_REAL")
}

craft_real_path_var() {
  # Set CRAFT_REAL to the real path of the absolute path $1. The path may not
  # exist yet: the longest existing part is resolved and the missing rest is
  # appended. Returns 1 if $1 is not absolute or the missing rest contains . or
  # .. parts. Changes the working directory of the shell.
  local p=$1 rest=""
  case $p in /*) ;; *) return 1 ;; esac
  while :; do
    craft_strip_slashes "$p"
    p=$CRAFT_REAL
    if [ "$p" = "/" ] || [ -e "$p" ] || [ -L "$p" ]; then
      break
    fi
    rest="/${p##*/}$rest"
    p=${p%/*}
    [ -n "$p" ] || p=/
  done
  case "$rest/" in */../*|*/./*) return 1 ;; esac
  if [ -d "$p" ]; then
    cd -P -- "$p" 2>/dev/null || return 1
    p=$PWD
  else
    craft_resolve_link_var "$p" || return 1
    p=$CRAFT_REAL
    if [ -d "$p" ]; then
      cd -P -- "$p" 2>/dev/null || return 1
      p=$PWD
    fi
  fi
  [ "$p" = "/" ] && p=""
  CRAFT_REAL=$p$rest
}

craft_real_path() {
  # Print the real path of the absolute path $1 (see craft_real_path_var).
  (craft_real_path_var "$1" && printf '%s\n' "$CRAFT_REAL")
}

craft_is_under() {
  # craft_is_under <path> <root>: true if path is root or inside it.
  case "$1/" in
    "$2"/*) return 0 ;;
  esac
  return 1
}

craft_is_secret_name() {
  # True if any part of path $1 contains ".env", or is "credentials",
  # ".databrickscfg" or ".netrc". Letters match in both cases (ASCII only):
  # APFS ignores case, so ".ENV" opens ".env".
  case "/$1/" in
    */*.[Ee][Nn][Vv]*/* \
    | */[Cc][Rr][Ee][Dd][Ee][Nn][Tt][Ii][Aa][Ll][Ss]/* \
    | */.[Dd][Aa][Tt][Aa][Bb][Rr][Ii][Cc][Kk][Ss][Cc][Ff][Gg]/* \
    | */.[Nn][Ee][Tt][Rr][Cc]/*) return 0 ;;
  esac
  return 1
}

craft_home() {
  # CRAFT_HOME from the environment wins (the tests use it). Otherwise follow
  # the .craft-home symlink that `make install` creates next to bin/.
  if [ -n "${CRAFT_HOME:-}" ]; then
    printf '%s\n' "$CRAFT_HOME"
    return 0
  fi
  local link
  link="$(dirname "$CRAFT_BIN")/.craft-home"
  [ -e "$link" ] || return 1
  (cd -P "$link" && pwd -P)
}

craft_load_config() {
  # Set CRAFT_HOME, CRAFT_JOBS, CRAFT_PORT_BASE, CRAFT_READ_ROOT and the values
  # in $CRAFT_HOME/config.env. Returns 5 when something is missing.
  local home
  home=$(craft_home) || { echo "craft: no CRAFT_HOME: run make install" >&2; return 5; }
  if [ ! -f "$home/config.env" ]; then
    echo "craft: missing $home/config.env: run make install" >&2
    return 5
  fi
  # shellcheck disable=SC1091
  . "$home/config.env"
  CRAFT_HOME=$home
  CRAFT_JOBS="$CRAFT_HOME/jobs"
  CRAFT_PORT_BASE=${CRAFT_PORT_BASE:-7901}
  CRAFT_READ_ROOT=${CRAFT_READ_ROOT:-$HOME}
  export CRAFT_HOME CRAFT_JOBS
}

craft_tool_row() {
  awk -F '\t' -v k="$1" '$1 == k { print; f = 1 } END { exit f ? 0 : 1 }' "$CRAFT_BIN/tools.tsv"
}

craft_tool_keys() {
  awk -F '\t' '$1 !~ /^#/ { printf "%s%s", s, $1; s = " " } END { print "" }' "$CRAFT_BIN/tools.tsv"
}

craft_read_row() {
  # craft_read_row <tool>: set the TOOL_* variables from bin/tools.tsv.
  local row
  row=$(craft_tool_row "$1") || return 1
  # Tab is white space for IFS, so read joins two tabs in a row. No column may be
  # empty: generate.py writes "-" for an empty value and rejects empty names.
  # shellcheck disable=SC2034
  IFS=$'\t' read -r TOOL_KEY TOOL_REPO TOOL_CLI TOOL_APP TOOL_OFFSET \
    TOOL_HEADLESS TOOL_LIVE TOOL_APP_ARGS TOOL_TOKEN <<EOF
$row
EOF
}

craft_expand_args() {
  # craft_expand_args <template> <port>: fill the array CRAFT_ARGS. The template
  # is a space-separated token list ("-" = empty). Placeholders are replaced per
  # token, so paths with spaces stay one argument.
  CRAFT_ARGS=()
  [ "$1" = "-" ] && return 0
  local tok
  set -f
  for tok in $1; do
    tok=${tok//\{jobs\}/$CRAFT_JOBS}
    tok=${tok//\{state\}/$CRAFT_HOME/state}
    tok=${tok//\{home\}/$CRAFT_HOME}
    tok=${tok//\{port\}/$2}
    CRAFT_ARGS+=("$tok")
  done
  set +f
}
