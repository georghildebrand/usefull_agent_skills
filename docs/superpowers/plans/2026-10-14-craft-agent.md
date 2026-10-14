# craft-agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `/craft` skill plus 11 `craft-<tool>` Claude Code subagents that edit files with the ArtCraft desktop applications through their MCP servers, on copies of the inputs in a job folder.

**Architecture:** One table (`tools.toml`) holds every per-tool difference. A generator turns it into `bin/tools.tsv` (read by the bash scripts) and 11 agent files. Bash scripts start the MCP servers (`craft-mcp`), copy inputs into job folders (`craft-stage`), start desktop apps (`craft-app`) and block tool calls that name paths outside the jobs folder (`craft-guard`, a `PreToolUse` hook declared in each agent file).

**Tech Stack:** bash 3.2 (`/bin/bash` on macOS), `/usr/bin/jq`, Python 3.11+ (generator and tests, standard library only, `unittest`), Make, shellcheck, Claude Code subagents.

**Spec:** `docs/superpowers/specs/2026-10-14-craft-agent-design.md`

## Global Constraints

- All new files live in `craft-agent/` of this repository, except the repository `README.md` row (Task 7) and this plan and the spec.
- Runtime scripts (`bin/*`, `scripts/*.sh`) run under `/bin/bash` 3.2: no associative arrays, no `mapfile`, no `set -u`, no `${var,,}`.
- Python: `scripts/generate.py` and `tests/test_*.py` need Python 3.11+ (`tomllib`). `tests/fake_mcp_server.py` and `tests/mcp_client.py` must also run under Python 3.9 (`/usr/bin/python3`).
- Tests use `unittest` only (repository convention, see `usage-stats/tests`). No pytest dependency.
- Ports: `CRAFT_PORT_BASE` default `7901`; offsets cad 0, design 1, fig 2, film 3, grid 4, light 5, pdf 6, photo 7, sound 8, vector 9, word 10.
- Secret file names: any path component that contains `.env`, or is `credentials`, `.databrickscfg` or `.netrc`.
- Exit codes for all scripts: 0 ok, 2 usage error or refused/blocked, 3 live app not reachable, 4 binary not built, 5 config or folder missing, 6 commit not reviewed, 7 build failed.
- `craft-mcp` in server mode prints nothing on stdout before `exec`: stdout belongs to the MCP JSON-RPC stream.
- `CRAFT_HOME` comes from the gitignored symlink `craft-agent/.craft-home`; a `CRAFT_HOME` environment variable overrides it (tests use this). `config.env` must not set `CRAFT_HOME`.
- Agents use `model: sonnet`.
- Confidentiality: no absolute home paths (`/Users/<name>`, `/home/<name>`), no company or person names, no ticket keys in any committed file. Examples use synthetic names (`report.pdf`, `photo.jpg`).
- **No commits.** The repository owner reviews the diff and commits. Each task ends with a checkpoint that lists the changed files.
- Work in a git worktree of this repository on branch `craft-agent`. The spec and this plan are untracked files in the main checkout; Task 1 copies them into the worktree.

## Review Focus

1. **Spaces and non-ASCII characters in paths** (`My Report ä.pdf`, a `CRAFT_HOME` that contains a space): every script must quote correctly. Pinned by the test home folder `craft home` (with a space) used in all script tests, and by a staging test with `Bericht ä.pdf` (Task 5).
2. **Output on stdout from the launcher** before it starts the server would corrupt the MCP stream and show up as a confusing "server failed" in Claude Code. Pinned by an empty-stdout assertion in all 21 launcher cases (Task 4).
3. **Paths hidden in tool arguments**: `file://` URLs, `~/...`, a path inside a JSON-string parameter, `..` after an existing folder, `..` into a missing folder, a symlink inside the job. Pinned by guard tests (Task 1).
4. **Name collisions in a job**: staging a file whose name already exists in `in/`, or two inputs with the same name, must not overwrite anything. Pinned by staging tests (Task 5).
5. **Broken hook input or environment** (not JSON, no `tool_name`, `jq` missing, config missing) must block the call, not allow it. Pinned by guard tests (Task 1).

---

### Task 1: Shared library and the `craft-guard` hook

**Files:**
- Create: `craft-agent/.gitignore`
- Create: `craft-agent/bin/lib/craft-common.sh`
- Create: `craft-agent/bin/craft-guard`
- Create: `craft-agent/tests/helpers.py`
- Create: `craft-agent/tests/test_guard.py`
- Copy: spec and plan from the main checkout into the worktree (same paths)

**Interfaces:**
- Produces (bash, in `craft-common.sh`; callers set `CRAFT_BIN` to the real folder of `bin/` before sourcing):
  - `craft_fail <code> <message>`: print to stderr, exit with code.
  - `craft_resolve_link <path>`: print the real path, following symlinks.
  - `craft_real_path <abs-path>`: print the real path; the path may not exist yet; return 1 if the missing part contains `.` or `..`.
  - `craft_is_under <path> <root>`: return 0 if path is root or inside it.
  - `craft_is_secret_name <path>`: return 0 if any component is a secret file name.
  - `craft_load_config`: set and export `CRAFT_HOME`, `CRAFT_JOBS`; set `CRAFT_PORT_BASE`, `CRAFT_READ_ROOT` and all values from `config.env`; return 5 on failure.
  - `craft_read_row <tool>`: set `TOOL_KEY TOOL_REPO TOOL_CLI TOOL_APP TOOL_OFFSET TOOL_HEADLESS TOOL_LIVE TOOL_APP_ARGS TOOL_TOKEN` from `bin/tools.tsv`; return 1 if unknown.
  - `craft_tool_keys`: print the known tool keys, space-separated.
  - `craft_expand_args <template> <port>`: fill the array `CRAFT_ARGS`; `-` means empty.
- Produces (Python, `tests/helpers.py`): `ROOT`, `BIN`, `CraftHome(read_root=None, port_base=7901, extra="")` with `.home`, `.jobs`, `.base`, `.read_root`, `.write_config(port_base=7901, extra="")`, `.run(script, *args, stdin=None, env_extra=None, cwd=None)`, `.cleanup()`; `write_exe(path, body)`; `Listener()` with `.port` and `.close()`.

- [ ] **Step 1: Copy the spec and the plan into the worktree**

Run from the worktree root (`MAIN` = the main checkout of this repository):
```bash
mkdir -p docs/superpowers/specs docs/superpowers/plans
cp "$MAIN/docs/superpowers/specs/2026-10-14-craft-agent-design.md" docs/superpowers/specs/
cp "$MAIN/docs/superpowers/plans/2026-10-14-craft-agent.md" docs/superpowers/plans/
```

- [ ] **Step 2: Create `craft-agent/.gitignore`**

```gitignore
# Local link to this machine's CRAFT_HOME, created by `make install`.
.craft-home
__pycache__/
```

- [ ] **Step 3: Write the test helpers**

`craft-agent/tests/helpers.py`:
```python
"""Shared helpers for the craft-agent tests.

Every test gets its own CRAFT_HOME in a temporary folder. The folder name
contains a space on purpose: all scripts must quote paths correctly.
"""
import os
import shutil
import socket
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")


def write_exe(path, body):
    with open(path, "w") as f:
        f.write(body)
    os.chmod(path, 0o755)


class CraftHome:
    """A throwaway CRAFT_HOME with config.env, bin/, jobs/, logs/, state/."""

    def __init__(self, read_root=None, port_base=7901, extra=""):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix="craft-test-"))
        self.home = os.path.join(self.base, "craft home")
        for d in ("bin", "jobs", "logs", "state", "reviewed"):
            os.makedirs(os.path.join(self.home, d))
        self.read_root = read_root or os.path.join(self.base, "workspace")
        os.makedirs(self.read_root, exist_ok=True)
        self.write_config(port_base, extra)

    @property
    def jobs(self):
        return os.path.join(self.home, "jobs")

    def write_config(self, port_base=7901, extra=""):
        with open(os.path.join(self.home, "config.env"), "w") as f:
            f.write('CRAFT_READ_ROOT="%s"\n' % self.read_root)
            f.write("CRAFT_PORT_BASE=%d\n" % port_base)
            f.write(extra)

    def env(self, env_extra=None):
        e = dict(os.environ)
        e["CRAFT_HOME"] = self.home
        e.pop("CRAFT_JQ", None)
        if env_extra:
            e.update(env_extra)
        return e

    def run(self, script, *args, stdin=None, env_extra=None, cwd=None):
        path = script if os.path.isabs(script) else os.path.join(BIN, script)
        return subprocess.run(
            [path, *args], input=stdin, capture_output=True, text=True,
            env=self.env(env_extra), cwd=cwd, timeout=60,
        )

    def cleanup(self):
        shutil.rmtree(self.base, ignore_errors=True)


class Listener:
    """An open TCP port on 127.0.0.1, standing in for a running desktop app."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]

    def close(self):
        self.sock.close()
```

- [ ] **Step 4: Write the failing guard tests**

`craft-agent/tests/test_guard.py`:
```python
"""Tests for bin/craft-guard, the PreToolUse hook of the craft agents.

Run: python3 -m unittest discover -s tests -p 'test_guard.py' -v
"""
import json
import os
import unittest

from helpers import CraftHome


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.h = CraftHome()
        self.job = os.path.join(self.h.jobs, "2026-01-01-test")
        os.makedirs(os.path.join(self.job, "in"))
        os.makedirs(os.path.join(self.job, "out"))
        with open(os.path.join(self.job, "in", "a.pdf"), "w") as f:
            f.write("x")

    def tearDown(self):
        self.h.cleanup()

    def hook(self, tool, tool_input, raw=None, env_extra=None):
        stdin = raw if raw is not None else json.dumps(
            {"tool_name": tool, "tool_input": tool_input})
        return self.h.run("craft-guard", stdin=stdin, env_extra=env_extra)

    def assertAllowed(self, r):
        self.assertEqual(r.returncode, 0, r.stderr)

    def assertBlocked(self, r, text):
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn(text, r.stderr)

    # allowed
    def test_path_in_job_folder_allowed(self):
        self.assertAllowed(self.hook("mcp__craft-pdf__open",
                                     {"path": os.path.join(self.job, "in", "a.pdf")}))

    def test_new_output_path_allowed(self):
        self.assertAllowed(self.hook("mcp__craft-pdf__save",
                                     {"path": os.path.join(self.job, "out", "new.pdf")}))

    def test_relative_path_allowed(self):
        self.assertAllowed(self.hook("mcp__craft-pdf__open",
                                     {"path": "2026-01-01-test/in/a.pdf"}))

    def test_plain_text_allowed(self):
        self.assertAllowed(self.hook("mcp__craft-word__run_command",
                                     {"command": "text.insert", "text": "Hello world", "n": 3}))

    def test_other_tool_not_checked(self):
        self.assertAllowed(self.hook("Bash", {"command": "cat /etc/hosts"}))

    def test_read_inside_home_allowed(self):
        self.assertAllowed(self.hook("Read",
                                     {"file_path": os.path.join(self.h.home, "logs", "pdf.log")}))

    # blocked: paths
    def test_absolute_path_outside_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": "/etc/hosts"}), "outside")

    def test_dotdot_escape_blocked(self):
        p = os.path.join(self.job, "..", "..", "..", "etc", "hosts")
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": p}), "outside")

    def test_dotdot_into_missing_folder_blocked(self):
        p = self.job + "/missing/../../../../etc/passwd"
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": p}), "cannot be resolved")

    def test_bare_dotdot_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": ".."}), "outside")

    def test_tilde_path_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": "~/notes.txt"}), "outside")

    def test_file_url_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"url": "file:///etc/hosts"}), "outside")

    def test_path_inside_json_string_blocked(self):
        params = json.dumps({"path": "/etc/hosts"})
        self.assertBlocked(self.hook("mcp__craft-fig__run_command",
                                     {"command": "file.open", "params": params}), "outside")

    def test_nested_list_path_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__combine",
                                     {"files": [os.path.join(self.job, "in", "a.pdf"), "/etc/hosts"]}),
                           "outside")

    def test_symlink_in_job_pointing_outside_blocked(self):
        os.symlink("/etc", os.path.join(self.job, "in", "etc-link"))
        p = os.path.join(self.job, "in", "etc-link", "hosts")
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": p}), "outside")

    def test_read_outside_home_blocked(self):
        self.assertBlocked(self.hook("Read", {"file_path": "/etc/hosts"}), "outside")

    # blocked: secret names
    def test_secret_name_in_job_blocked(self):
        p = os.path.join(self.job, "in", ".env")
        open(p, "w").close()
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": p}), "secret")

    def test_secret_suffix_blocked(self):
        p = os.path.join(self.job, "in", "prod.env")
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": p}), "secret")

    def test_bare_secret_name_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"name": "credentials"}), "secret")

    def test_read_netrc_in_home_blocked(self):
        r = self.hook("Read", {"file_path": os.path.join(self.h.home, ".netrc")})
        self.assertBlocked(r, "secret")

    # blocked: broken input or environment (fail closed)
    def test_invalid_json_blocked(self):
        self.assertBlocked(self.hook(None, None, raw="not json"), "not JSON")

    def test_missing_tool_name_blocked(self):
        self.assertBlocked(self.hook(None, None, raw='{"tool_input": {}}'), "no tool_name")

    def test_missing_jq_blocked(self):
        r = self.hook("mcp__craft-pdf__open", {"path": "/etc/hosts"},
                      env_extra={"CRAFT_JQ": "/nonexistent/jq"})
        self.assertBlocked(r, "jq not found")

    def test_missing_config_blocked(self):
        os.remove(os.path.join(self.h.home, "config.env"))
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": "x"}), "config")

    def test_decisions_are_logged(self):
        self.hook("mcp__craft-pdf__open", {"path": "/etc/hosts"})
        with open(os.path.join(self.h.home, "logs", "guard.log")) as f:
            log = f.read()
        self.assertIn("mcp__craft-pdf__open\tdeny", log)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5: Run the tests to verify they fail**

Run: `cd craft-agent && python3 -m unittest discover -s tests -p 'test_guard.py'`
Expected: errors (`FileNotFoundError` for `bin/craft-guard`).

- [ ] **Step 6: Write the shared library**

`craft-agent/bin/lib/craft-common.sh`:
```bash
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

craft_resolve_link() {
  # Print the real path of $1, following every symlink in the chain.
  local p=$1 t d
  while [ -L "$p" ]; do
    t=$(readlink "$p")
    case $t in
      /*) p=$t ;;
      *) p=$(dirname "$p")/$t ;;
    esac
  done
  d=$(cd "$(dirname "$p")" 2>/dev/null && pwd -P) || return 1
  if [ "$d" = "/" ]; then
    printf '/%s\n' "$(basename "$p")"
  else
    printf '%s/%s\n' "$d" "$(basename "$p")"
  fi
}

craft_real_path() {
  # Print the real path of the absolute path $1. The path may not exist yet:
  # the longest existing part is resolved and the missing rest is appended.
  # Returns 1 if $1 is not absolute or the missing rest contains . or .. parts.
  local p=$1 rest=""
  case $p in /*) ;; *) return 1 ;; esac
  while [ ! -e "$p" ] && [ ! -L "$p" ]; do
    [ "$p" = "/" ] && break
    rest="/$(basename "$p")$rest"
    p=$(dirname "$p")
  done
  case "$rest/" in */../*|*/./*) return 1 ;; esac
  if [ -d "$p" ]; then
    p=$(cd "$p" 2>/dev/null && pwd -P) || return 1
  else
    p=$(craft_resolve_link "$p") || return 1
    if [ -d "$p" ]; then
      p=$(cd "$p" 2>/dev/null && pwd -P) || return 1
    fi
  fi
  [ "$p" = "/" ] && p=""
  printf '%s%s\n' "$p" "$rest"
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
  # ".databrickscfg" or ".netrc".
  case "/$1/" in
    */*.env*/*|*/credentials/*|*/.databrickscfg/*|*/.netrc/*) return 0 ;;
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
  (cd "$link" && pwd -P)
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
```

- [ ] **Step 7: Write the hook**

`craft-agent/bin/craft-guard`:
```bash
#!/bin/bash
# craft-guard: PreToolUse hook for the craft-<tool> agents.
#
# Claude Code sends the planned tool call as JSON on stdin. The hook blocks the
# call (exit 2; the reason on stderr is shown to the model) when
#   - a craft MCP tool (mcp__craft-*) receives a path outside $CRAFT_HOME/jobs,
#   - Read receives a path outside $CRAFT_HOME,
#   - any path or name is a secret file name.
# Strings that look like paths are checked; strings that hold JSON are parsed and
# their strings checked too. Anything unexpected blocks the call (fail closed).
# Every decision is appended to $CRAFT_HOME/logs/guard.log.
CRAFT_BIN=$(dirname "$(readlink -f "$0")")
# shellcheck source=lib/craft-common.sh
. "$CRAFT_BIN/lib/craft-common.sh"

tool_name="-"

log_decision() {
  [ -n "${CRAFT_HOME:-}" ] || return 0
  mkdir -p "$CRAFT_HOME/logs" 2>/dev/null
  printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$tool_name" "$1" "$2" \
    >>"$CRAFT_HOME/logs/guard.log" 2>/dev/null
}

deny() {
  log_decision deny "$1"
  echo "craft-guard blocked this call: $1" >&2
  exit 2
}

craft_load_config 2>/dev/null || deny "craft config not found (run make install)"

if [ -n "${CRAFT_JQ:-}" ]; then
  JQ=$CRAFT_JQ
else
  JQ=/usr/bin/jq
  [ -x "$JQ" ] || JQ=$(command -v jq)
fi
{ [ -n "$JQ" ] && [ -x "$JQ" ]; } || deny "jq not found"

input=$(cat)
tool_name=$(printf '%s' "$input" | "$JQ" -r '.tool_name // empty' 2>/dev/null) \
  || deny "hook input is not JSON"
[ -n "$tool_name" ] || deny "hook input has no tool_name"

case $tool_name in
  Read) root=$(craft_real_path "$CRAFT_HOME") || deny "cannot resolve CRAFT_HOME" ;;
  mcp__craft-*) root=$(craft_real_path "$CRAFT_JOBS") || deny "cannot resolve the jobs folder" ;;
  *) log_decision allow "not a craft tool"; exit 0 ;;
esac

check_string() {
  local s=$1 p real
  case $s in file://*) s=${s#file://} ;; esac
  case $s in
    /*) p=$s ;;
    "~"|"~/"*) p=$HOME${s#"~"} ;;
    ..|../*|./*|*/*) p=$CRAFT_JOBS/$s ;;
    *)
      if craft_is_secret_name "$s"; then deny "secret file name: $s"; fi
      return 0
      ;;
  esac
  if craft_is_secret_name "$p"; then deny "secret file name: $s"; fi
  real=$(craft_real_path "$p") || deny "path cannot be resolved safely: $s"
  if craft_is_secret_name "$real"; then deny "secret file name: $s"; fi
  craft_is_under "$real" "$root" || deny "path outside the allowed folder: $s"
}

strings=$(mktemp) || deny "mktemp failed"
trap 'rm -f "$strings"' EXIT
filter='[.tool_input | .. | strings] + [.tool_input | .. | strings | (try fromjson catch empty) | .. | strings] | .[]'
printf '%s' "$input" | "$JQ" --raw-output0 "$filter" >"$strings" 2>/dev/null \
  || deny "cannot read tool_input"
while IFS= read -r -d '' s; do
  check_string "$s"
done <"$strings"

log_decision allow "paths ok"
exit 0
```

Make it executable: `chmod +x craft-agent/bin/craft-guard`

- [ ] **Step 8: Run the tests to verify they pass**

Run: `cd craft-agent && python3 -m unittest discover -s tests -p 'test_guard.py' -v`
Expected: all 26 tests pass.

- [ ] **Step 9: Checkpoint (no commit)**

Run: `git status --short`
Expected: `craft-agent/` and `docs/superpowers/` listed as untracked. Leave them for the owner's review.

---

### Task 2: Prove that a subagent file can declare its own MCP server and hook

This task decides where the hook lives. It runs a real Claude Code subagent against a fake MCP server. It costs two short `claude -p` runs.

**Files:**
- Create: `craft-agent/tests/fake_mcp_server.py`
- Create: `craft-agent/tests/mcp_client.py`
- Create: `craft-agent/tests/test_mcp_client.py`
- Temporary, not in the repository: `~/.claude/agents/craft-probe.md` (deleted in Step 7)

**Interfaces:**
- Consumes: `bin/craft-guard` (Task 1).
- Produces: `McpClient(argv, env=None, timeout=30)` with `.initialize()`, `.list_tools() -> list`, `.call(name, arguments) -> dict`, `.close()`; exception `McpError`. The fake server's tool `touch_path(path)` appends `path` to `$CRAFT_HOME/logs/probe-called`.
- Produces: a recorded decision (Step 6) that Task 3 uses: `HOOK_IN_AGENT_FILE` = yes/no, `SERVER_SYNTAX` = map/list.

- [ ] **Step 1: Write the fake MCP server**

`craft-agent/tests/fake_mcp_server.py`:
```python
#!/usr/bin/env python3
"""A minimal stdio MCP server for tests. Python 3.9 compatible.

One tool, touch_path(path): appends the path to $CRAFT_HOME/logs/probe-called
and returns "touched <path>". It never opens the path itself.
"""
import json
import os
import sys

TOOL = {
    "name": "touch_path",
    "description": "Record a path. Used to test the craft-guard hook.",
    "inputSchema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
}


def reply(msg_id, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        method, msg_id = msg.get("method"), msg.get("id")
        if msg_id is None:
            continue  # notification
        if method == "initialize":
            version = msg.get("params", {}).get("protocolVersion", "2025-06-18")
            reply(msg_id, {"protocolVersion": version, "capabilities": {"tools": {}},
                           "serverInfo": {"name": "fake-craft", "version": "1"}})
        elif method == "tools/list":
            reply(msg_id, {"tools": [TOOL]})
        elif method == "tools/call":
            path = msg["params"]["arguments"]["path"]
            log = os.path.join(os.environ["CRAFT_HOME"], "logs", "probe-called")
            with open(log, "a") as f:
                f.write(path + "\n")
            reply(msg_id, {"content": [{"type": "text", "text": "touched " + path}]})
        else:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "error": {
                "code": -32601, "message": "unknown method " + str(method)}}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write the failing client test**

`craft-agent/tests/test_mcp_client.py`:
```python
"""Tests for tests/mcp_client.py against tests/fake_mcp_server.py."""
import os
import sys
import unittest

from helpers import HERE, CraftHome
from mcp_client import McpClient


class McpClientTest(unittest.TestCase):
    def setUp(self):
        self.h = CraftHome()
        self.c = McpClient([sys.executable, os.path.join(HERE, "fake_mcp_server.py")],
                           env=self.h.env(), timeout=10)

    def tearDown(self):
        self.c.close()
        self.h.cleanup()

    def test_initialize_list_call(self):
        info = self.c.initialize()
        self.assertEqual(info["serverInfo"]["name"], "fake-craft")
        tools = self.c.list_tools()
        self.assertEqual([t["name"] for t in tools], ["touch_path"])
        result = self.c.call("touch_path", {"path": "x.txt"})
        self.assertEqual(result["content"][0]["text"], "touched x.txt")
        with open(os.path.join(self.h.home, "logs", "probe-called")) as f:
            self.assertEqual(f.read(), "x.txt\n")


if __name__ == "__main__":
    unittest.main()
```

Run: `cd craft-agent && python3 -m unittest discover -s tests -p 'test_mcp_client.py'`
Expected: `ModuleNotFoundError: No module named 'mcp_client'`.

- [ ] **Step 3: Write the client**

`craft-agent/tests/mcp_client.py`:
```python
#!/usr/bin/env python3
"""A minimal stdio MCP client for smoke tests. Python 3.9 compatible.

    python3 tests/mcp_client.py list <tool>                  list tools and schemas
    python3 tests/mcp_client.py call <tool> <name> '<json>'  call one tool

<tool> is a craft tool key (pdf, grid, ...); the server is started with
bin/craft-mcp <tool>.
"""
import json
import os
import queue
import subprocess
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTOCOL_VERSION = "2025-06-18"


class McpError(Exception):
    pass


class McpClient:
    def __init__(self, argv, env=None, timeout=30):
        self.timeout = timeout
        self.next_id = 1
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, env=env)
        self.lines = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.proc.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def _send(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def _read(self):
        try:
            line = self.lines.get(timeout=self.timeout)
        except queue.Empty:
            raise TimeoutError("no answer within %ss" % self.timeout)
        if line is None:
            err = self.proc.stderr.read() if self.proc.poll() is not None else ""
            raise EOFError("server closed stdout (exit %s) %s" % (self.proc.poll(), err[-500:]))
        return json.loads(line)

    def request(self, method, params=None):
        msg_id = self.next_id
        self.next_id += 1
        self._send({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}})
        while True:
            msg = self._read()
            if msg.get("id") != msg_id:
                continue  # notification or log message
            if "error" in msg:
                raise McpError("%s: %s" % (method, msg["error"]))
            return msg["result"]

    def notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def initialize(self):
        result = self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION, "capabilities": {},
            "clientInfo": {"name": "craft-smoke", "version": "1"}})
        self.notify("notifications/initialized")
        return result

    def list_tools(self):
        tools, cursor = [], None
        while True:
            result = self.request("tools/list", {"cursor": cursor} if cursor else {})
            tools.extend(result.get("tools", []))
            cursor = result.get("nextCursor")
            if not cursor:
                return tools

    def call(self, name, arguments):
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def main(argv):
    if len(argv) < 2 or argv[0] not in ("list", "call"):
        print(__doc__)
        return 2
    client = McpClient([os.path.join(ROOT, "bin", "craft-mcp"), argv[1]])
    try:
        client.initialize()
        if argv[0] == "list":
            for tool in client.list_tools():
                print(json.dumps({"name": tool["name"], "inputSchema": tool.get("inputSchema")}))
        else:
            print(json.dumps(client.call(argv[2], json.loads(argv[3])), indent=2))
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Run: `cd craft-agent && python3 -m unittest discover -s tests -p 'test_mcp_client.py' -v`
Expected: 1 test passes.

- [ ] **Step 4: Create the probe home and the probe agent**

Run (from the worktree root):
```bash
REPO_AGENT="$(pwd -P)/craft-agent"
PROBE="$(mktemp -d)/probe"
mkdir -p "$PROBE/jobs" "$PROBE/logs"
printf 'CRAFT_READ_ROOT="%s"\n' "$PROBE" > "$PROBE/config.env"
cat > "$HOME/.claude/agents/craft-probe.md" <<EOF
---
name: craft-probe
description: Temporary probe for the craft-agent plan. Calls touch_path when asked.
model: sonnet
tools: mcp__craft-probe__*
mcpServers:
  craft-probe:
    type: stdio
    command: /usr/bin/python3
    args: ["$REPO_AGENT/tests/fake_mcp_server.py"]
    env:
      CRAFT_HOME: "$PROBE"
hooks:
  PreToolUse:
    - matcher: "mcp__craft-.*|Read"
      hooks:
        - type: command
          command: "CRAFT_HOME='$PROBE' '$REPO_AGENT/bin/craft-guard'"
---
Call the touch_path tool exactly as the task says, once per path, and report each result word for word.
EOF
echo "$PROBE"
```
Expected: the probe folder path is printed. Keep it for Step 5.

- [ ] **Step 5: Run the probe through a real subagent**

Run:
```bash
claude -p "Use the craft-probe subagent. Ask it to call touch_path with path /etc/hosts, then with path probe-ok.txt. Report what happened for each call." \
  --model sonnet --allowedTools Agent mcp__craft-probe__touch_path
cat "$PROBE/logs/guard.log"; echo ---; cat "$PROBE/logs/probe-called"
```

- [ ] **Step 6: Record the outcome**

| Outcome | What you see | Decision |
|---|---|---|
| **A (expected)** | `guard.log` has a `deny` line with `/etc/hosts` and an `allow` line; `probe-called` contains only `probe-ok.txt` | `HOOK_IN_AGENT_FILE=yes`, `SERVER_SYNTAX=map`. Continue with Task 3 unchanged. |
| **B** | `probe-called` contains `/etc/hosts`; `guard.log` is missing or empty | The frontmatter hook did not run. `HOOK_IN_AGENT_FILE=no`. Do Step 6b. |
| **C** | Neither file exists; the subagent says it has no `touch_path` tool | The `mcpServers` map form was not accepted. Change the probe file's `mcpServers` block to the list form below, run Step 5 again, then decide A or B. If it still fails, stop and report to the owner: the design needs per-agent MCP servers. |

List form for outcome C:
```yaml
mcpServers:
  - craft-probe:
      type: stdio
      command: /usr/bin/python3
      args: ["<same path as before>"]
      env:
        CRAFT_HOME: "<same probe path>"
```
With the list form, record `SERVER_SYNTAX=list`.

Write the decision into the spec's "Open points" item 1, for example: `Verified 2026-10-14: frontmatter hooks run in subagents (outcome A).`

- [ ] **Step 6b: Only for outcome B: move the hook to the user settings**

`templates/agent.md.tmpl` (Task 3) then has no `hooks:` block, and `scripts/install.sh` (Task 6) must add this entry to `$CLAUDE_DIR/settings.json`, after copying the file to `settings.json.bak`:
```bash
jq '.hooks.PreToolUse = ((.hooks.PreToolUse // []) | map(select(.hooks[0].command != "craft-guard")) + [{"matcher": "mcp__craft-.*|Read", "hooks": [{"type": "command", "command": "craft-guard"}]}])' \
  "$settings.bak" > "$settings"
```
`craft-guard` then also runs for `Read` in every session. It allows `Read` only inside `$CRAFT_HOME`, which would block normal reads, so in this case change the `Read)` branch in `craft-guard` to: `Read) log_decision allow "Read outside craft agents"; exit 0 ;;` and drop `Read` from the agents' `tools` (the agents then check results only through their MCP tools). Note the change in the spec.

- [ ] **Step 7: Remove the probe**

Run: `rm "$HOME/.claude/agents/craft-probe.md"; rm -rf "$(dirname "$PROBE")"`

- [ ] **Step 8: Checkpoint (no commit)**

Run: `git status --short`
Expected: new files `craft-agent/tests/fake_mcp_server.py`, `mcp_client.py`, `test_mcp_client.py`; the spec is modified (Step 6).

---

### Task 3: `tools.toml`, the agent template and the generator

**Files:**
- Create: `craft-agent/tools.toml`
- Create: `craft-agent/templates/agent.md.tmpl`
- Create: `craft-agent/scripts/generate.py`
- Create: `craft-agent/tests/test_generate.py`
- Generated: `craft-agent/bin/tools.tsv`, `craft-agent/agents/craft-*.md` (11 files)

**Interfaces:**
- Consumes: the Task 2 decision (`HOOK_IN_AGENT_FILE`, `SERVER_SYNTAX`).
- Produces: `bin/tools.tsv` with 9 tab-separated columns: `key repo cli app port_offset headless live app_args token_file` (`-` = empty); one comment line starting with `#`.
- Produces (Python, `scripts/generate.py`): `load_tools(path) -> dict`, `validate(tools)` (raises `ValueError`), `tsv_row(key, t) -> str`, `render_tsv(tools) -> str`, `render_agent(key, t, template) -> str`, `main(argv) -> int` with `--check`.
- Produces: agent names `craft-cad craft-design craft-fig craft-film craft-sheet craft-light craft-pdf craft-photo craft-sound craft-vector craft-word`; MCP server names `<agent>` and `<agent>-live`.

- [ ] **Step 1: Write `tools.toml`**

`craft-agent/tools.toml`:
```toml
# One table per ArtCraft tool. `make generate` turns this file into
# bin/tools.tsv (read by the bash scripts) and agents/craft-<tool>.md.
#
# Argument lists hold tokens without spaces. The scripts replace:
#   {jobs}  -> $CRAFT_HOME/jobs      {state} -> $CRAFT_HOME/state
#   {home}  -> $CRAFT_HOME           {port}  -> CRAFT_PORT_BASE + port_offset
# An empty `live` list means the tool has no live MCP mode; then `app_args`
# must be empty too. Flags come from each tool's CLI source (apps/<repo>-cli).

[tool.cad]
repo = "cadcraft"
cli = "cadcraft-cli"
app = "cadcraft"
agent = "craft-cad"
title = "CADCraft"
port_offset = 0
headless = ["mcp"]
live = ["mcp", "--connect", "127.0.0.1:{port}"]
app_args = ["--control", "{port}"]
token_file = ""
description = "Edits and converts CAD drawings (DXF, DWG) with CADCraft: draw, change, inspect, export to PNG or SVG."
notes = """
- CADCraft has no folder limit of its own. Use only paths inside the job folder.
- Commands use AutoCAD-style names. Look them up before you use them.
"""

[tool.design]
repo = "designcraft"
cli = "designcraft-cli"
app = "designcraft"
agent = "craft-design"
title = "DesignCraft"
port_offset = 1
headless = ["mcp"]
live = ["mcp", "--connect", "127.0.0.1:{port}"]
app_args = ["--control", "{port}"]
token_file = ""
description = "Lays out pages with DesignCraft (InDesign-style): documents, text frames, images, IDML, EPUB and PDF export."
notes = """
- DesignCraft has no folder limit of its own. Use only paths inside the job folder.
"""

[tool.fig]
repo = "figcraft"
cli = "figcraft-cli"
app = "figcraft"
agent = "craft-fig"
title = "FigCraft"
port_offset = 2
headless = ["mcp"]
live = ["mcp", "--attach", "127.0.0.1:{port}"]
app_args = ["--control", "{port}"]
token_file = ""
description = "Designs user interfaces with FigCraft (Figma-style): frames, auto layout, components, render to PNG, export SVG."
notes = """
- FigCraft files use the `.figcraft` format.
- FigCraft has no folder limit of its own. Use only paths inside the job folder.
"""

[tool.film]
repo = "filmcraft"
cli = "filmcraft-cli"
app = "filmcraft"
agent = "craft-film"
title = "FilmCraft"
port_offset = 3
headless = ["mcp"]
live = ["mcp", "--bridge", "127.0.0.1:{port}"]
app_args = ["--control", "{port}"]
token_file = ""
description = "Edits video with FilmCraft (Premiere Pro-style): cut, trim, color, sound, captions, export."
notes = """
- FilmCraft has more than 650 commands. Search for the one you need.
- Exports can take minutes. Wait until the export has finished before you check the file.
- FilmCraft has no folder limit of its own. Use only paths inside the job folder.
"""

[tool.grid]
repo = "gridcraft"
cli = "gridcraft-cli"
app = "gridcraft"
agent = "craft-sheet"
title = "GridCraft"
port_offset = 4
headless = ["mcp"]
live = ["mcp", "--connect", "127.0.0.1:{port}"]
app_args = ["--control", "{port}"]
token_file = ""
description = "Works with spreadsheets in GridCraft (Excel-style): read and write cells, formulas, charts, XLSX files."
notes = """
- Tools include read_range, write_range, set_cell and evaluate_formula.
- GridCraft has no folder limit of its own. Use only paths inside the job folder.
"""

[tool.light]
repo = "lightcraft"
cli = "lightcraft-cli"
app = "lightcraft"
agent = "craft-light"
title = "LightCraft"
port_offset = 5
headless = ["mcp", "--headless", "--compact", "--library", "{state}/light"]
live = ["mcp", "--connect", "127.0.0.1:{port}", "--compact"]
app_args = ["--control", "{port}"]
token_file = ""
description = "Develops and exports photos with LightCraft: raw files, exposure, color, batches of photos."
notes = """
- `import` scans folders recursively. Import only `<job>/in` or files inside it.
- The server runs with --compact: commands that are not listed are reachable through run_command.
- LightCraft has no folder limit of its own. Use only paths inside the job folder.
"""

[tool.pdf]
repo = "pdfcraft"
cli = "pdfcraft-cli"
app = "pdfcraft"
agent = "craft-pdf"
title = "PdfCraft"
port_offset = 6
headless = ["mcp", "--root", "{jobs}", "--compact"]
live = []
app_args = []
token_file = ""
description = "Edits PDF files with PdfCraft (Acrobat-style): pages, merge, split, comments, forms, passwords, text search, pages to PNG."
notes = """
- The server runs with --compact: core tools are listed; find others with tool_search and call them with tool_call.
- doc_batch walks folders recursively. Use it only on folders inside the job.
- PdfCraft's own --root flag limits it to the jobs folder.
"""

[tool.photo]
repo = "photocraft"
cli = "photocraft-cli"
app = "photocraft"
agent = "craft-photo"
title = "PhotoCraft"
port_offset = 7
headless = ["mcp", "--automation-read-root", "{jobs}", "--automation-write-root", "{jobs}"]
live = ["mcp", "--bridge", "127.0.0.1:{port}", "--control-token-file", "{home}/photo.token"]
app_args = ["--control", "{port}", "--control-token-file", "{home}/photo.token"]
token_file = "photo.token"
description = "Edits images with PhotoCraft (Photoshop-style): layers, masks, adjustments, text, PSD files."
notes = """
- In headless mode PhotoCraft's own read and write roots limit it to the jobs folder.
"""

[tool.sound]
repo = "soundcraft"
cli = "soundcraft-cli"
app = "soundcraft"
agent = "craft-sound"
title = "SoundCraft"
port_offset = 8
headless = ["mcp", "--automation-read-root", "{jobs}", "--automation-write-root", "{jobs}"]
live = ["mcp", "--connect", "127.0.0.1:{port}"]
app_args = ["--control", "{port}"]
token_file = ""
description = "Records, edits and mixes audio with SoundCraft (Pro Tools-style): tracks, effects, mixing, bounce to a file."
notes = """
- In headless mode SoundCraft's own read and write roots limit it to the jobs folder.
"""

[tool.vector]
repo = "vectorcraft"
cli = "vectorcraft-cli"
app = "vectorcraft"
agent = "craft-vector"
title = "VectorCraft"
port_offset = 9
headless = ["mcp", "--automation-read-root", "{jobs}", "--automation-write-root", "{jobs}"]
live = ["mcp", "--connect", "127.0.0.1:{port}"]
app_args = ["--control", "{port}"]
token_file = ""
description = "Creates and edits vector graphics with VectorCraft (Illustrator-style): paths, shapes, text, SVG, AI and EPS files."
notes = """
- VectorCraft is alpha software. Check every export.
- In headless mode VectorCraft's own read and write roots limit it to the jobs folder.
"""

[tool.word]
repo = "wordcraft"
cli = "wordcraft-cli"
app = "wordcraft"
agent = "craft-word"
title = "WordCraft"
port_offset = 10
headless = ["mcp", "--automation-read-root", "{jobs}", "--automation-write-root", "{jobs}"]
live = ["mcp", "--connect", "127.0.0.1:{port}"]
app_args = ["--control", "{port}"]
token_file = ""
description = "Writes and edits documents with WordCraft (Word-style): text, styles, tables, DOCX files, PDF export."
notes = """
- inspect_document shows the document structure. Use it to check your work without screenshots.
- In headless mode WordCraft's own read and write roots limit it to the jobs folder.
"""
```

- [ ] **Step 2: Write the agent template**

`craft-agent/templates/agent.md.tmpl` (for Task 2 outcome B, leave out the five `hooks:` lines and replace `, Read` handling as described in Task 2 Step 6b):
```markdown
---
name: {{agent}}
description: {{description}} Use it through the /craft skill, which prepares the job folder.
model: sonnet
tools: {{tools}}
mcpServers:
{{servers}}
hooks:
  PreToolUse:
    - matcher: "mcp__craft-.*|Read"
      hooks:
        - type: command
          command: craft-guard
---

<!-- GENERATED by scripts/generate.py from tools.toml and templates/agent.md.tmpl. Edit those files, then run `make generate`. -->

You edit files with {{title}}, an open-source desktop application, through its MCP
server.

## Job folder

The task gives you a job folder `<job>`. Inputs are in `<job>/in`. Write results to
`<job>/out`. You can only reach paths inside the jobs folder: a hook blocks every
other path before the call runs.

## Rules

1. Never open files whose name contains `.env`, or is `credentials`,
   `.databrickscfg` or `.netrc`.
2. Before you call a command, find it with the server's list or search tool and
   read its parameters. Do not guess command ids or parameter names.
3. Write results only to `<job>/out`. Never change files in `<job>/in`.
4. Check your result: render it or inspect it, and compare it with the task. If it
   is wrong, try one fix. If it is still wrong, save it under `<job>/out/_failed/`
   and say what is wrong. Never report a failed result as done.
5. If {{title}} has no command for the task, say so. Do not build a rough
   substitute from other commands without saying so.
6. If the hook blocks a call, report the block. Do not try to reach the file in
   another way.
7. If the server stops responding, report the last command and the log file
   `<job>/../../logs/{{key}}.log`. Try once more, then stop.
{{live_rule}}

## Report

End with the output paths, what you checked and how, and what you could not do.

## {{title}} notes

{{notes}}
```

- [ ] **Step 3: Write the failing generator tests**

`craft-agent/tests/test_generate.py`:
```python
"""Tests for scripts/generate.py."""
import copy
import importlib.util
import os
import subprocess
import sys
import unittest

from helpers import ROOT

_spec = importlib.util.spec_from_file_location("generate", os.path.join(ROOT, "scripts", "generate.py"))
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


class GenerateTest(unittest.TestCase):
    def setUp(self):
        self.tools = gen.load_tools(os.path.join(ROOT, "tools.toml"))
        with open(os.path.join(ROOT, "templates", "agent.md.tmpl")) as f:
            self.template = f.read()

    def test_committed_files_match_generator(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "generate.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_eleven_valid_tools(self):
        self.assertEqual(len(self.tools), 11)
        gen.validate(self.tools)

    def test_duplicate_port_offset_rejected(self):
        tools = copy.deepcopy(self.tools)
        tools["pdf"]["port_offset"] = tools["cad"]["port_offset"]
        with self.assertRaises(ValueError):
            gen.validate(tools)

    def test_token_with_space_rejected(self):
        tools = copy.deepcopy(self.tools)
        tools["cad"]["headless"] = ["mcp", "--x y"]
        with self.assertRaises(ValueError):
            gen.validate(tools)

    def test_unknown_placeholder_rejected(self):
        tools = copy.deepcopy(self.tools)
        tools["cad"]["headless"] = ["mcp", "{nope}"]
        with self.assertRaises(ValueError):
            gen.validate(tools)

    def test_live_without_app_args_rejected(self):
        tools = copy.deepcopy(self.tools)
        tools["cad"]["app_args"] = []
        with self.assertRaises(ValueError):
            gen.validate(tools)

    def test_headless_only_agent(self):
        text = gen.render_agent("pdf", self.tools["pdf"], self.template)
        self.assertIn("  craft-pdf:\n", text)
        self.assertNotIn("craft-pdf-live", text)
        self.assertIn("tools: mcp__craft-pdf__*, Read", text)
        self.assertNotIn("{{", text)

    def test_live_agent_has_two_servers(self):
        text = gen.render_agent("vector", self.tools["vector"], self.template)
        self.assertIn("  craft-vector-live:\n", text)
        self.assertIn('args: ["vector", "--live"]', text)
        self.assertIn("craft-app vector", text)

    def test_grid_agent_is_named_craft_sheet(self):
        text = gen.render_agent("grid", self.tools["grid"], self.template)
        self.assertIn("name: craft-sheet\n", text)
        self.assertIn('args: ["grid"]', text)

    def test_tsv_row(self):
        row = gen.tsv_row("pdf", self.tools["pdf"]).split("\t")
        self.assertEqual(row, ["pdf", "pdfcraft", "pdfcraft-cli", "pdfcraft", "6",
                               "mcp --root {jobs} --compact", "-", "-", "-"])


if __name__ == "__main__":
    unittest.main()
```

Run: `cd craft-agent && python3 -m unittest discover -s tests -p 'test_generate.py'`
Expected: error, `scripts/generate.py` not found.

- [ ] **Step 4: Write the generator**

`craft-agent/scripts/generate.py` (for `SERVER_SYNTAX=list` from Task 2, change `server_block` to the list form recorded there):
```python
#!/usr/bin/env python3
"""Generate bin/tools.tsv and agents/craft-<tool>.md from tools.toml.

    python3 scripts/generate.py           write the files
    python3 scripts/generate.py --check   exit 1 if a committed file differs

Needs Python 3.11+ (tomllib). The bash scripts read bin/tools.tsv because the
macOS system Python (3.9) has no TOML parser.
"""
import argparse
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_TOML = ROOT / "tools.toml"
TEMPLATE = ROOT / "templates" / "agent.md.tmpl"
TSV = ROOT / "bin" / "tools.tsv"
AGENTS = ROOT / "agents"

REQUIRED = ("repo", "cli", "app", "agent", "title", "port_offset", "headless", "live",
            "app_args", "token_file", "description", "notes")
ONE_LINE = ("repo", "cli", "app", "agent", "title", "token_file", "description")
PLACEHOLDER = re.compile(r"\{([a-z]+)\}")
KNOWN_PLACEHOLDERS = {"jobs", "home", "state", "port"}

LIVE_RULE = """8. You have two servers. `{agent}` works on files without a window. `{agent}-live`
   controls the open {title} window. Use `{agent}-live` only when the task says
   "Mode: live". If it is not reachable, tell the user to run `craft-app {key}`,
   then continue with `{agent}` and say that you did."""

HEADLESS_RULE = """8. You have one server, `{agent}`. It works on files without a window.
   {title} has no live mode."""


def load_tools(path=TOOLS_TOML):
    with open(path, "rb") as f:
        return tomllib.load(f)["tool"]


def validate(tools):
    offsets, agents = {}, {}
    for key, t in tools.items():
        if not re.fullmatch(r"[a-z]+", key):
            raise ValueError(f"tool key {key!r}: use lowercase letters only")
        missing = [k for k in REQUIRED if k not in t]
        if missing:
            raise ValueError(f"{key}: missing {', '.join(missing)}")
        if t["port_offset"] in offsets:
            raise ValueError(f"{key}: port_offset {t['port_offset']} is also used by {offsets[t['port_offset']]}")
        offsets[t["port_offset"]] = key
        if t["agent"] in agents:
            raise ValueError(f"{key}: agent {t['agent']} is also used by {agents[t['agent']]}")
        agents[t["agent"]] = key
        for field in ONE_LINE:
            if "\t" in t[field] or "\n" in t[field]:
                raise ValueError(f"{key}.{field}: must be one line without tabs")
        if not t["headless"]:
            raise ValueError(f"{key}: headless must not be empty")
        if bool(t["live"]) != bool(t["app_args"]):
            raise ValueError(f"{key}: set live and app_args together, or leave both empty")
        for field in ("headless", "live", "app_args"):
            for tok in t[field]:
                if not tok or tok == "-" or re.search(r"\s", tok):
                    raise ValueError(f"{key}.{field}: bad token {tok!r} (no spaces, not empty, not '-')")
                for name in PLACEHOLDER.findall(tok):
                    if name not in KNOWN_PLACEHOLDERS:
                        raise ValueError(f"{key}.{field}: unknown placeholder {{{name}}}")


def tsv_row(key, t):
    def args(tokens):
        return " ".join(tokens) or "-"
    return "\t".join([key, t["repo"], t["cli"], t["app"], str(t["port_offset"]),
                      args(t["headless"]), args(t["live"]), args(t["app_args"]),
                      t["token_file"] or "-"])


def render_tsv(tools):
    lines = ["# GENERATED by scripts/generate.py from tools.toml. Columns: "
             "key repo cli app port_offset headless live app_args token_file"]
    lines += [tsv_row(key, t) for key, t in tools.items()]
    return "\n".join(lines) + "\n"


def server_block(name, args):
    quoted = ", ".join(f'"{a}"' for a in args)
    return f"  {name}:\n    type: stdio\n    command: craft-mcp\n    args: [{quoted}]"


def render_agent(key, t, template):
    agent = t["agent"]
    servers = [server_block(agent, [key])]
    tools = [f"mcp__{agent}__*"]
    rule = HEADLESS_RULE
    if t["live"]:
        servers.append(server_block(f"{agent}-live", [key, "--live"]))
        tools.append(f"mcp__{agent}-live__*")
        rule = LIVE_RULE
    tools.append("Read")
    values = {
        "agent": agent,
        "key": key,
        "title": t["title"],
        "description": t["description"],
        "tools": ", ".join(tools),
        "servers": "\n".join(servers),
        "live_rule": rule.format(agent=agent, key=key, title=t["title"]),
        "notes": t["notes"].strip(),
    }
    text = template
    for name, value in values.items():
        text = text.replace("{{" + name + "}}", value)
    leftover = re.findall(r"\{\{[a-z_]+\}\}", text)
    if leftover:
        raise ValueError(f"{key}: template placeholders left: {leftover}")
    return text


def outputs(tools):
    template = TEMPLATE.read_text()
    files = {TSV: render_tsv(tools)}
    for key, t in tools.items():
        files[AGENTS / f"{t['agent']}.md"] = render_agent(key, t, template)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only report out-of-date files")
    args = parser.parse_args(argv)
    tools = load_tools()
    validate(tools)
    files = outputs(tools)
    stale = [p for p, text in files.items() if not p.exists() or p.read_text() != text]
    extra = [p for p in AGENTS.glob("craft-*.md") if p not in files]
    if args.check:
        for p in stale + extra:
            print(f"out of date: {p.relative_to(ROOT)} (run make generate)")
        return 1 if stale or extra else 0
    AGENTS.mkdir(exist_ok=True)
    for p in stale:
        p.write_text(files[p])
        print(f"wrote {p.relative_to(ROOT)}")
    for p in extra:
        p.unlink()
        print(f"removed {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Generate and run the tests**

Run:
```bash
cd craft-agent && python3 scripts/generate.py && python3 -m unittest discover -s tests -p 'test_generate.py' -v
```
Expected: `wrote bin/tools.tsv` and 11 `wrote agents/craft-*.md` lines; 10 tests pass.

- [ ] **Step 6: Read one generated agent file**

Run: `cat craft-agent/agents/craft-photo.md | head -30`
Expected: frontmatter with `name: craft-photo`, two servers (`craft-photo`, `craft-photo-live`), `tools: mcp__craft-photo__*, mcp__craft-photo-live__*, Read`, the `hooks:` block, and rule 8 with `craft-app photo`.

- [ ] **Step 7: Checkpoint (no commit)**

Run: `git status --short`
Expected: new `tools.toml`, `templates/`, `scripts/generate.py`, `bin/tools.tsv`, `agents/` (11 files), `tests/test_generate.py`.

---

### Task 4: The `craft-mcp` launcher

**Files:**
- Create: `craft-agent/bin/craft-mcp`
- Create: `craft-agent/tests/expected_argv.txt`
- Create: `craft-agent/tests/test_mcp.py`

**Interfaces:**
- Consumes: `craft-common.sh` (Task 1), `bin/tools.tsv` (Task 3).
- Produces: `craft-mcp <tool> [--live]` (execs the server; cwd `$CRAFT_HOME/jobs`; stderr to `$CRAFT_HOME/logs/<tool>.log`); `craft-mcp --check <tool>` (exit 0 or 4). Exit 3 with `craft-app <tool>` in the message when the live port is closed.

- [ ] **Step 1: Write the expected command lines by hand**

`craft-agent/tests/expected_argv.txt`:
```text
# <tool> <mode> | <expected command line>
# {J} = $CRAFT_HOME/jobs, {H} = $CRAFT_HOME, {P} = the port the test opened.
# Written by hand from the CLI source review. Do NOT generate this file from
# tools.toml: it exists to catch a wrong flag in tools.toml.
cad headless | cadcraft-cli mcp
cad live | cadcraft-cli mcp --connect 127.0.0.1:{P}
design headless | designcraft-cli mcp
design live | designcraft-cli mcp --connect 127.0.0.1:{P}
fig headless | figcraft-cli mcp
fig live | figcraft-cli mcp --attach 127.0.0.1:{P}
film headless | filmcraft-cli mcp
film live | filmcraft-cli mcp --bridge 127.0.0.1:{P}
grid headless | gridcraft-cli mcp
grid live | gridcraft-cli mcp --connect 127.0.0.1:{P}
light headless | lightcraft-cli mcp --headless --compact --library {H}/state/light
light live | lightcraft-cli mcp --connect 127.0.0.1:{P} --compact
pdf headless | pdfcraft-cli mcp --root {J} --compact
photo headless | photocraft-cli mcp --automation-read-root {J} --automation-write-root {J}
photo live | photocraft-cli mcp --bridge 127.0.0.1:{P} --control-token-file {H}/photo.token
sound headless | soundcraft-cli mcp --automation-read-root {J} --automation-write-root {J}
sound live | soundcraft-cli mcp --connect 127.0.0.1:{P}
vector headless | vectorcraft-cli mcp --automation-read-root {J} --automation-write-root {J}
vector live | vectorcraft-cli mcp --connect 127.0.0.1:{P}
word headless | wordcraft-cli mcp --automation-read-root {J} --automation-write-root {J}
word live | wordcraft-cli mcp --connect 127.0.0.1:{P}
```

- [ ] **Step 2: Write the failing launcher tests**

`craft-agent/tests/test_mcp.py`:
```python
"""Tests for bin/craft-mcp. Fake *-cli binaries record the arguments they get."""
import os
import unittest

from helpers import HERE, CraftHome, Listener, write_exe

OFFSETS = {"cad": 0, "design": 1, "fig": 2, "film": 3, "grid": 4, "light": 5,
           "pdf": 6, "photo": 7, "sound": 8, "vector": 9, "word": 10}

FAKE_CLI = """#!/bin/bash
{ pwd -P; printf '%s\\n' "$(basename "$0")" "$@"; } > "$CRAFT_HOME/argv.out"
"""


def expected_cases():
    with open(os.path.join(HERE, "expected_argv.txt")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                head, cmd = line.split(" | ")
                tool, mode = head.split()
                yield tool, mode, cmd.split(" ")


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.h = CraftHome()

    def tearDown(self):
        self.h.cleanup()

    def fake(self, cli):
        write_exe(os.path.join(self.h.home, "bin", cli), FAKE_CLI)

    def recorded(self):
        with open(os.path.join(self.h.home, "argv.out")) as f:
            return f.read().splitlines()

    def test_all_21_command_lines(self):
        cases = list(expected_cases())
        self.assertEqual(len(cases), 21)
        for tool, mode, expected in cases:
            with self.subTest(tool=tool, mode=mode):
                self.fake(expected[0])
                port = 0
                listener = None
                if mode == "live":
                    listener = Listener()
                    port = listener.port
                    self.h.write_config(port_base=port - OFFSETS[tool])
                try:
                    args = [tool] + (["--live"] if mode == "live" else [])
                    r = self.h.run("craft-mcp", *args)
                finally:
                    if listener:
                        listener.close()
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout, "", "launcher must print nothing on stdout")
                fill = {"{J}": self.h.jobs, "{H}": self.h.home, "{P}": str(port)}
                want = []
                for tok in expected:
                    for k, v in fill.items():
                        tok = tok.replace(k, v)
                    want.append(tok)
                got = self.recorded()
                self.assertEqual(got[0], os.path.realpath(self.h.jobs), "cwd must be the jobs folder")
                self.assertEqual(got[1:], want)

    def test_live_port_closed(self):
        self.fake("vectorcraft-cli")
        listener = Listener()
        port = listener.port
        listener.close()
        self.h.write_config(port_base=port - OFFSETS["vector"])
        r = self.h.run("craft-mcp", "vector", "--live")
        self.assertEqual(r.returncode, 3)
        self.assertIn("craft-app vector", r.stderr)
        with open(os.path.join(self.h.home, "logs", "vector.log")) as f:
            self.assertIn("not reachable", f.read())

    def test_pdf_has_no_live_mode(self):
        self.fake("pdfcraft-cli")
        r = self.h.run("craft-mcp", "pdf", "--live")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no live mode", r.stderr)

    def test_unknown_tool(self):
        r = self.h.run("craft-mcp", "excel")
        self.assertEqual(r.returncode, 2)
        self.assertIn("known: cad design", r.stderr)

    def test_missing_binary(self):
        r = self.h.run("craft-mcp", "pdf")
        self.assertEqual(r.returncode, 4)
        self.assertIn("make build TOOL=pdf", r.stderr)

    def test_check(self):
        self.assertEqual(self.h.run("craft-mcp", "--check", "pdf").returncode, 4)
        self.fake("pdfcraft-cli")
        r = self.h.run("craft-mcp", "--check", "pdf")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_usage(self):
        self.assertEqual(self.h.run("craft-mcp").returncode, 2)
        self.assertEqual(self.h.run("craft-mcp", "pdf", "--other").returncode, 2)

    def test_missing_config(self):
        os.remove(os.path.join(self.h.home, "config.env"))
        self.assertEqual(self.h.run("craft-mcp", "pdf").returncode, 5)


if __name__ == "__main__":
    unittest.main()
```

Run: `cd craft-agent && python3 -m unittest discover -s tests -p 'test_mcp.py'`
Expected: errors, `bin/craft-mcp` not found.

- [ ] **Step 3: Write the launcher**

`craft-agent/bin/craft-mcp`:
```bash
#!/bin/bash
# craft-mcp: start the MCP server of one ArtCraft tool for the craft-<tool> agents.
#
#   craft-mcp <tool> [--live]   run the server on stdio
#   craft-mcp --check <tool>    exit 0 if the tool's CLI binary is built
#
# The server runs with $CRAFT_HOME/jobs as working directory; its stderr goes to
# $CRAFT_HOME/logs/<tool>.log. In server mode this script prints nothing on
# stdout: stdout carries the MCP messages.
# Exit codes: 2 usage, 3 live app not reachable, 4 binary missing, 5 config missing.
CRAFT_BIN=$(dirname "$(readlink -f "$0")")
# shellcheck source=lib/craft-common.sh
. "$CRAFT_BIN/lib/craft-common.sh"

usage() { craft_fail 2 "usage: craft-mcp <tool> [--live] | craft-mcp --check <tool>"; }

check=0
mode=headless
if [ "${1:-}" = "--check" ]; then
  check=1
  shift
fi
[ $# -ge 1 ] || usage
tool=$1
shift
if [ "${1:-}" = "--live" ]; then
  mode=live
  shift
fi
[ $# -eq 0 ] || usage
if [ $check -eq 1 ] && [ $mode = live ]; then usage; fi

craft_load_config || exit 5
craft_read_row "$tool" || craft_fail 2 "craft-mcp: unknown tool '$tool' (known: $(craft_tool_keys))"

bin="$CRAFT_HOME/bin/$TOOL_CLI"
[ -x "$bin" ] || craft_fail 4 "$TOOL_CLI not built: run make build TOOL=$tool"
if [ $check -eq 1 ]; then
  echo "$TOOL_CLI is built: $bin"
  exit 0
fi

port=$((CRAFT_PORT_BASE + TOOL_OFFSET))
mkdir -p "$CRAFT_JOBS" "$CRAFT_HOME/logs" "$CRAFT_HOME/state/$tool" || exit 5
log="$CRAFT_HOME/logs/$tool.log"

if [ $mode = live ]; then
  [ "$TOOL_LIVE" != "-" ] || craft_fail 2 "craft-mcp: $tool has no live mode"
  if ! (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
    msg="craft-mcp: the $tool app is not reachable on 127.0.0.1:$port. Start it with: craft-app $tool"
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $msg" >>"$log"
    craft_fail 3 "$msg"
  fi
  template=$TOOL_LIVE
else
  template=$TOOL_HEADLESS
fi

craft_expand_args "$template" "$port"
cd "$CRAFT_JOBS" || exit 5
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) start $mode: $TOOL_CLI ${CRAFT_ARGS[*]}" >>"$log"
exec "$bin" "${CRAFT_ARGS[@]}" 2>>"$log"
```

Make it executable: `chmod +x craft-agent/bin/craft-mcp`

- [ ] **Step 4: Run the tests**

Run: `cd craft-agent && python3 -m unittest discover -s tests -p 'test_mcp.py' -v`
Expected: 8 tests pass (the first one runs 21 subtests).

- [ ] **Step 5: Checkpoint (no commit)**

Run: `git status --short`
Expected: new `bin/craft-mcp`, `tests/expected_argv.txt`, `tests/test_mcp.py`.

---

### Task 5: `craft-stage`

**Files:**
- Create: `craft-agent/bin/craft-stage`
- Create: `craft-agent/tests/test_stage.py`

**Interfaces:**
- Consumes: `craft-common.sh` (Task 1).
- Produces: `craft-stage <job-slug> [file-or-folder...]`; prints the job folder; creates `in/`, `out/`, `out/_failed/`; exit 2 when refused (nothing copied), 5 on config or copy failure.

- [ ] **Step 1: Write the failing tests**

`craft-agent/tests/test_stage.py`:
```python
"""Tests for bin/craft-stage."""
import os
import unittest

from helpers import CraftHome


class StageTest(unittest.TestCase):
    def setUp(self):
        self.h = CraftHome()
        self.ws = self.h.read_root

    def tearDown(self):
        self.h.cleanup()

    def make(self, rel, text="data"):
        path = os.path.join(self.ws, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
        return path

    def stage(self, *args):
        return self.h.run("craft-stage", *args)

    def job(self, slug="2026-01-01-test"):
        return os.path.join(self.h.jobs, slug)

    def test_copies_file_and_prints_job(self):
        src = self.make("docs/report.pdf", "pdf-bytes")
        r = self.stage("2026-01-01-test", src)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), self.job())
        with open(os.path.join(self.job(), "in", "report.pdf")) as f:
            self.assertEqual(f.read(), "pdf-bytes")
        self.assertTrue(os.path.isdir(os.path.join(self.job(), "out", "_failed")))

    def test_relative_path_and_folder(self):
        self.make("photos/a.jpg")
        self.make("photos/b.jpg")
        r = self.h.run("craft-stage", "2026-01-01-test", "photos", cwd=self.ws)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.job(), "in", "photos", "b.jpg")))

    def test_no_inputs_creates_empty_job(self):
        r = self.stage("2026-01-01-new-file")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isdir(os.path.join(self.job("2026-01-01-new-file"), "in")))

    def test_space_and_umlaut_in_name(self):
        src = self.make("Bericht ä.pdf")
        r = self.stage("2026-01-01-test", src)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.job(), "in", "Bericht ä.pdf")))

    def assertRefused(self, r, text):
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn(text, r.stderr)

    def test_refuses_secret_names(self):
        for name in (".env", "prod.env", ".env.local", "credentials", ".netrc", ".databrickscfg"):
            with self.subTest(name=name):
                self.assertRefused(self.stage("2026-01-01-test", self.make(name)), "secret")
        self.assertFalse(os.path.exists(self.job()))

    def test_refuses_path_outside_read_root(self):
        outside = os.path.join(self.h.base, "elsewhere.pdf")
        with open(outside, "w") as f:
            f.write("x")
        self.assertRefused(self.stage("2026-01-01-test", outside), "outside CRAFT_READ_ROOT")

    def test_refuses_symlink_pointing_outside(self):
        link = os.path.join(self.ws, "hosts-link")
        os.symlink("/etc/hosts", link)
        self.assertRefused(self.stage("2026-01-01-test", link), "outside CRAFT_READ_ROOT")

    def test_refuses_folder_with_secret_or_symlink(self):
        self.make("proj/a.txt")
        self.make("proj/sub/.netrc")
        self.assertRefused(self.stage("2026-01-01-test", os.path.join(self.ws, "proj")), "secret")
        self.make("proj2/a.txt")
        os.symlink("/etc", os.path.join(self.ws, "proj2", "etc"))
        self.assertRefused(self.stage("2026-01-01-test", os.path.join(self.ws, "proj2")), "symlink")

    def test_no_overwrite_in_existing_job(self):
        src = self.make("a/report.pdf", "first")
        self.assertEqual(self.stage("2026-01-01-test", src).returncode, 0)
        src2 = self.make("b/report.pdf", "second")
        self.assertRefused(self.stage("2026-01-01-test", src2), "already in the job")
        with open(os.path.join(self.job(), "in", "report.pdf")) as f:
            self.assertEqual(f.read(), "first")

    def test_two_inputs_with_same_name(self):
        a = self.make("a/report.pdf")
        b = self.make("b/report.pdf")
        self.assertRefused(self.stage("2026-01-01-test", a, b), "two inputs named report.pdf")
        self.assertFalse(os.path.exists(self.job()))

    def test_bad_slugs(self):
        src = self.make("report.pdf")
        for slug in ("../x", "a/b", ".hidden", "a..b", ""):
            with self.subTest(slug=slug):
                self.assertRefused(self.stage(slug, src), "job slug")

    def test_missing_file(self):
        self.assertRefused(self.stage("2026-01-01-test", os.path.join(self.ws, "nope.pdf")), "not found")


if __name__ == "__main__":
    unittest.main()
```

Run: `cd craft-agent && python3 -m unittest discover -s tests -p 'test_stage.py'`
Expected: errors, `bin/craft-stage` not found.

- [ ] **Step 2: Write `craft-stage`**

`craft-agent/bin/craft-stage`:
```bash
#!/bin/bash
# craft-stage: copy input files into a job folder for the craft-<tool> agents.
#
#   craft-stage <job-slug> [file-or-folder...]
#
# Creates $CRAFT_HOME/jobs/<job-slug>/{in,out,out/_failed}, copies the inputs into
# in/ (APFS clone with cp -c when possible) and prints the job folder.
# Refuses (exit 2, nothing copied): secret file names, paths outside
# CRAFT_READ_ROOT, folders that contain secret files or symlinks, names that
# already exist in in/, and two inputs with the same name.
CRAFT_BIN=$(dirname "$(readlink -f "$0")")
# shellcheck source=lib/craft-common.sh
. "$CRAFT_BIN/lib/craft-common.sh"

refuse() { craft_fail 2 "craft-stage: $1"; }

[ $# -ge 1 ] || craft_fail 2 "usage: craft-stage <job-slug> [file-or-folder...]"
slug=$1
shift
printf '%s\n' "$slug" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$' \
  || refuse "bad job slug '$slug' (letters, digits, '.', '_', '-'; not starting with '.')"
case $slug in *..*) refuse "bad job slug '$slug' (no '..')" ;; esac

craft_load_config || exit 5
read_root=$(craft_real_path "$CRAFT_READ_ROOT") || refuse "cannot resolve CRAFT_READ_ROOT ($CRAFT_READ_ROOT)"
job=$CRAFT_JOBS/$slug

seen="/"
srcs=()
dests=()
for src in "$@"; do
  case $src in
    /*) abs=$src ;;
    *) abs=$PWD/$src ;;
  esac
  { [ -e "$abs" ] || [ -L "$abs" ]; } || refuse "not found: $src"
  real=$(craft_real_path "$abs") || refuse "cannot resolve: $src"
  if craft_is_secret_name "$abs" || craft_is_secret_name "$real"; then
    refuse "secret file name: $src"
  fi
  craft_is_under "$real" "$read_root" || refuse "outside CRAFT_READ_ROOT ($CRAFT_READ_ROOT): $src"
  if [ -d "$real" ]; then
    hit=$(find "$real" \( -name '*.env*' -o -name credentials -o -name .databrickscfg -o -name .netrc \) -print -quit)
    [ -z "$hit" ] || refuse "folder contains a secret file: $hit"
    hit=$(find "$real" -type l -print -quit)
    [ -z "$hit" ] || refuse "folder contains a symlink: $hit"
  fi
  name=$(basename "$abs")
  case $seen in *"/$name/"*) refuse "two inputs named $name" ;; esac
  seen="$seen$name/"
  [ ! -e "$job/in/$name" ] || refuse "already in the job: $job/in/$name"
  srcs+=("$real")
  dests+=("$job/in/$name")
done

mkdir -p "$job/in" "$job/out/_failed" || craft_fail 5 "craft-stage: cannot create $job"
i=0
while [ $i -lt ${#srcs[@]} ]; do
  s=${srcs[$i]}
  d=${dests[$i]}
  if ! cp -c -R "$s" "$d" 2>/dev/null; then
    rm -rf "$d"
    cp -R "$s" "$d" || craft_fail 5 "craft-stage: copy failed: $s"
  fi
  i=$((i + 1))
done
printf '%s\n' "$job"
```

Make it executable: `chmod +x craft-agent/bin/craft-stage`

- [ ] **Step 3: Run the tests**

Run: `cd craft-agent && python3 -m unittest discover -s tests -p 'test_stage.py' -v`
Expected: 12 tests pass.

- [ ] **Step 4: Checkpoint (no commit)**

Run: `git status --short`
Expected: new `bin/craft-stage`, `tests/test_stage.py`.

---

### Task 6: `craft-app`, build gate, install and job cleanup

**Files:**
- Create: `craft-agent/bin/craft-app`
- Create: `craft-agent/scripts/build.sh`
- Create: `craft-agent/scripts/mark-reviewed.sh`
- Create: `craft-agent/scripts/install.sh`
- Create: `craft-agent/scripts/uninstall.sh`
- Create: `craft-agent/scripts/clean-jobs.sh`
- Create: `craft-agent/Makefile`
- Create: `craft-agent/tests/test_app.py`
- Create: `craft-agent/tests/test_build.py`
- Create: `craft-agent/tests/test_install.py`

**Interfaces:**
- Consumes: `craft-common.sh`, `bin/tools.tsv`, `config.example.env` (created in Task 7; `test_install.py` creates a stand-in if it is missing — see Step 1).
- Produces: `craft-app <tool>`; `scripts/build.sh <tool> [cli|app]` (exit 6 not reviewed or dirty, 7 cargo failed); `scripts/mark-reviewed.sh <tool>`; `scripts/install.sh <craft-home>` (env `CLAUDE_DIR`, `LOCAL_BIN`, `FORCE`); `scripts/uninstall.sh`; `scripts/clean-jobs.sh <days>`; Make targets `help check test generate build build-app mark-reviewed smoke install uninstall clean-jobs`.

- [ ] **Step 1: Write the failing tests**

`craft-agent/tests/test_app.py`:
```python
"""Tests for bin/craft-app."""
import os
import re
import stat
import time
import unittest

from helpers import CraftHome, write_exe

FAKE_APP = """#!/bin/bash
printf '%s\\n' "$@" > "$CRAFT_HOME/app-argv.out"
"""


class AppTest(unittest.TestCase):
    def setUp(self):
        self.h = CraftHome(port_base=7901)

    def tearDown(self):
        self.h.cleanup()

    def wait_argv(self):
        path = os.path.join(self.h.home, "app-argv.out")
        for _ in range(50):
            if os.path.exists(path):
                with open(path) as f:
                    return f.read().splitlines()
            time.sleep(0.1)
        self.fail("fake app did not run")

    def test_photo_gets_port_and_token(self):
        write_exe(os.path.join(self.h.home, "bin", "photocraft"), FAKE_APP)
        r = self.h.run("craft-app", "photo")
        self.assertEqual(r.returncode, 0, r.stderr)
        token = os.path.join(self.h.home, "photo.token")
        self.assertEqual(self.wait_argv(), ["--control", "7908", "--control-token-file", token])
        self.assertEqual(stat.S_IMODE(os.stat(token).st_mode), 0o600)
        with open(token) as f:
            self.assertRegex(f.read(), re.compile(r"^[0-9a-f]{64}$"))

    def test_vector_gets_port(self):
        write_exe(os.path.join(self.h.home, "bin", "vectorcraft"), FAKE_APP)
        self.assertEqual(self.h.run("craft-app", "vector").returncode, 0)
        self.assertEqual(self.wait_argv(), ["--control", "7910"])

    def test_pdf_has_no_live_mode(self):
        r = self.h.run("craft-app", "pdf")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no live mode", r.stderr)

    def test_missing_app(self):
        r = self.h.run("craft-app", "word")
        self.assertEqual(r.returncode, 4)
        self.assertIn("make build-app TOOL=word", r.stderr)


if __name__ == "__main__":
    unittest.main()
```

`craft-agent/tests/test_build.py`:
```python
"""Tests for scripts/build.sh and scripts/mark-reviewed.sh with a fake cargo."""
import os
import subprocess
import unittest

from helpers import ROOT, CraftHome, write_exe

FAKE_CARGO = """#!/bin/bash
# fake cargo: `cargo build --release -p <pkg>` creates target/release/<pkg>
[ -f "$PWD/fail-build" ] && exit 101
mkdir -p target/release
printf '#!/bin/bash\\necho built-%s\\n' "$5" > "target/release/$5"
chmod +x "target/release/$5"
"""


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.art = None
        self.h = CraftHome()
        self.art = os.path.join(self.h.base, "artcraft")
        self.repo = os.path.join(self.art, "gridcraft")
        os.makedirs(self.repo)
        git = ["git", "-C", self.repo]
        subprocess.run(git + ["init", "-q"], check=True)
        with open(os.path.join(self.repo, ".gitignore"), "w") as f:
            f.write("target/\nfail-build\n")
        subprocess.run(git + ["add", "."], check=True)
        subprocess.run(git + ["-c", "user.name=t", "-c", "user.email=t@example.invalid",
                              "commit", "-qm", "init"], check=True)
        self.head = subprocess.run(git + ["rev-parse", "HEAD"], capture_output=True,
                                   text=True, check=True).stdout.strip()
        self.h.write_config(extra='ARTCRAFT_DIR="%s"\n' % self.art)
        fakebin = os.path.join(self.h.base, "fakebin")
        os.makedirs(fakebin)
        write_exe(os.path.join(fakebin, "cargo"), FAKE_CARGO)
        self.path = fakebin + os.pathsep + os.environ["PATH"]

    def tearDown(self):
        self.h.cleanup()

    def script(self, name, *args):
        return self.h.run(os.path.join(ROOT, "scripts", name), *args,
                          env_extra={"PATH": self.path})

    def test_refuses_unreviewed_commit(self):
        r = self.script("build.sh", "grid")
        self.assertEqual(r.returncode, 6)
        self.assertIn("make mark-reviewed TOOL=grid", r.stderr)

    def test_builds_after_review(self):
        self.assertEqual(self.script("mark-reviewed.sh", "grid").returncode, 0)
        with open(os.path.join(self.h.home, "reviewed", "gridcraft")) as f:
            self.assertEqual(f.read().strip(), self.head)
        r = self.script("build.sh", "grid")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.access(os.path.join(self.h.home, "bin", "gridcraft-cli"), os.X_OK))

    def test_refuses_dirty_tree(self):
        self.script("mark-reviewed.sh", "grid")
        with open(os.path.join(self.repo, "build.rs"), "w") as f:
            f.write("fn main() {}")
        r = self.script("build.sh", "grid")
        self.assertEqual(r.returncode, 6)
        self.assertIn("uncommitted", r.stderr)

    def test_failed_build_keeps_old_binary(self):
        self.script("mark-reviewed.sh", "grid")
        old = os.path.join(self.h.home, "bin", "gridcraft-cli")
        write_exe(old, "#!/bin/bash\necho old\n")
        open(os.path.join(self.repo, "fail-build"), "w").close()
        r = self.script("build.sh", "grid")
        self.assertEqual(r.returncode, 7)
        with open(old) as f:
            self.assertIn("echo old", f.read())

    def test_app_kind_builds_app_package(self):
        self.script("mark-reviewed.sh", "grid")
        r = self.script("build.sh", "grid", "app")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.h.home, "bin", "gridcraft")))


if __name__ == "__main__":
    unittest.main()
```

`craft-agent/tests/test_install.py`:
```python
"""Tests for scripts/install.sh, uninstall.sh and clean-jobs.sh in temporary folders."""
import os
import subprocess
import tempfile
import time
import unittest
import shutil

from helpers import ROOT, CraftHome


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix="craft-install-"))
        self.home = os.path.join(self.base, "craft home")
        self.claude = os.path.join(self.base, "claude")
        self.lbin = os.path.join(self.base, "localbin")
        self.link = os.path.join(ROOT, ".craft-home")
        self.saved_link = os.readlink(self.link) if os.path.islink(self.link) else None
        if self.saved_link:
            os.remove(self.link)

    def tearDown(self):
        if os.path.islink(self.link):
            os.remove(self.link)
        if self.saved_link:
            os.symlink(self.saved_link, self.link)
        shutil.rmtree(self.base, ignore_errors=True)

    def run_script(self, name, *args, **env):
        e = dict(os.environ, CLAUDE_DIR=self.claude, LOCAL_BIN=self.lbin, **env)
        e.pop("CRAFT_HOME", None)
        return subprocess.run([os.path.join(ROOT, "scripts", name), *args],
                              capture_output=True, text=True, env=e)

    def test_install_creates_links_and_config(self):
        r = self.run_script("install.sh", self.home)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(os.path.realpath(self.link), os.path.realpath(self.home))
        self.assertTrue(os.path.isfile(os.path.join(self.home, "config.env")))
        agents = sorted(os.listdir(os.path.join(self.claude, "agents")))
        self.assertEqual(len(agents), 11)
        self.assertTrue(os.path.islink(os.path.join(self.claude, "skills", "craft")))
        for b in ("craft-mcp", "craft-stage", "craft-app", "craft-guard"):
            self.assertTrue(os.path.islink(os.path.join(self.lbin, b)))
        # second run is a no-op and keeps an edited config
        with open(os.path.join(self.home, "config.env"), "a") as f:
            f.write("# edited\n")
        self.assertEqual(self.run_script("install.sh", self.home).returncode, 0)
        with open(os.path.join(self.home, "config.env")) as f:
            self.assertIn("# edited", f.read())

    def test_install_refuses_to_replace_real_file(self):
        os.makedirs(os.path.join(self.claude, "agents"))
        with open(os.path.join(self.claude, "agents", "craft-pdf.md"), "w") as f:
            f.write("mine")
        r = self.run_script("install.sh", self.home)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not a symlink", r.stderr)

    def test_install_refuses_other_home_without_force(self):
        self.run_script("install.sh", self.home)
        other = os.path.join(self.base, "other")
        r = self.run_script("install.sh", other)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FORCE=1", r.stderr)
        self.assertEqual(self.run_script("install.sh", other, FORCE="1").returncode, 0)

    def test_uninstall_removes_only_own_links(self):
        self.run_script("install.sh", self.home)
        foreign = os.path.join(self.lbin, "other-tool")
        os.symlink("/bin/ls", foreign)
        r = self.run_script("uninstall.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.lbin, "craft-mcp")))
        self.assertTrue(os.path.islink(foreign))
        self.assertTrue(os.path.isdir(self.home), "uninstall keeps CRAFT_HOME data")


class CleanJobsTest(unittest.TestCase):
    def test_deletes_only_old_jobs(self):
        h = CraftHome()
        try:
            old = os.path.join(h.jobs, "2020-01-01-old")
            new = os.path.join(h.jobs, "2026-01-01-new")
            os.makedirs(old)
            os.makedirs(new)
            past = time.time() - 40 * 86400
            os.utime(old, (past, past))
            r = h.run(os.path.join(ROOT, "scripts", "clean-jobs.sh"), "30")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(os.path.exists(old))
            self.assertTrue(os.path.exists(new))
            self.assertEqual(h.run(os.path.join(ROOT, "scripts", "clean-jobs.sh"), "x").returncode, 2)
        finally:
            h.cleanup()


if __name__ == "__main__":
    unittest.main()
```

If `craft-agent/config.example.env` does not exist yet, create it now with the content from Task 7 Step 1 (Task 7 then only reviews it).

Run: `cd craft-agent && python3 -m unittest discover -s tests -p 'test_app.py' && python3 -m unittest discover -s tests -p 'test_build.py' && python3 -m unittest discover -s tests -p 'test_install.py'`
Expected: errors, scripts not found.

- [ ] **Step 2: Write `craft-app`**

`craft-agent/bin/craft-app`:
```bash
#!/bin/bash
# craft-app: start an ArtCraft desktop app with the control port that
# `craft-mcp <tool> --live` connects to.
#
#   craft-app <tool>
#
# For tools that need a control token (photocraft), creates the token file
# (64 hex characters, mode 0600) on first use. App output goes to
# $CRAFT_HOME/logs/<tool>-app.log.
CRAFT_BIN=$(dirname "$(readlink -f "$0")")
# shellcheck source=lib/craft-common.sh
. "$CRAFT_BIN/lib/craft-common.sh"

[ $# -eq 1 ] || craft_fail 2 "usage: craft-app <tool>"
tool=$1
craft_load_config || exit 5
craft_read_row "$tool" || craft_fail 2 "craft-app: unknown tool '$tool' (known: $(craft_tool_keys))"
[ "$TOOL_APP_ARGS" != "-" ] || craft_fail 2 "craft-app: $tool has no live mode"

app="$CRAFT_HOME/bin/$TOOL_APP"
[ -x "$app" ] || craft_fail 4 "$TOOL_APP not built: run make build-app TOOL=$tool"

if [ "$TOOL_TOKEN" != "-" ]; then
  token="$CRAFT_HOME/$TOOL_TOKEN"
  if [ ! -s "$token" ]; then
    (umask 077 && od -An -tx1 -N32 /dev/urandom | tr -d ' \n' >"$token") \
      || craft_fail 5 "craft-app: cannot write $token"
  fi
  chmod 600 "$token" || craft_fail 5 "craft-app: cannot chmod $token"
fi

port=$((CRAFT_PORT_BASE + TOOL_OFFSET))
craft_expand_args "$TOOL_APP_ARGS" "$port"
mkdir -p "$CRAFT_HOME/logs" "$CRAFT_JOBS" || exit 5
cd "$CRAFT_JOBS" || exit 5
nohup "$app" "${CRAFT_ARGS[@]}" >>"$CRAFT_HOME/logs/$tool-app.log" 2>&1 &
echo "$TOOL_APP started (pid $!), control port 127.0.0.1:$port"
```

Make it executable: `chmod +x craft-agent/bin/craft-app`

- [ ] **Step 3: Write the build gate scripts**

`craft-agent/scripts/build.sh`:
```bash
#!/bin/bash
# build.sh <tool> [cli|app]: build one ArtCraft binary with cargo and copy it to
# $CRAFT_HOME/bin.
#
# Refuses (exit 6) unless the repository has no uncommitted changes and its
# current commit was recorded by mark-reviewed.sh after a safety review: build
# scripts and proc macros run code on this machine during `cargo build`.
# Exit 7: cargo or the copy failed; the previous binary is kept.
CRAFT_BIN=$(cd "$(dirname "$(readlink -f "$0")")/../bin" && pwd -P)
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

[ -z "$(git -C "$src" status --porcelain)" ] \
  || craft_fail 6 "build: $src has uncommitted changes; build only reviewed commits"
head=$(git -C "$src" rev-parse HEAD)
reviewed=$(cat "$CRAFT_HOME/reviewed/$TOOL_REPO" 2>/dev/null)
if [ "$reviewed" != "$head" ]; then
  craft_fail 6 "build: $TOOL_REPO is at $head, reviewed: ${reviewed:-none}. Review this commit (repo-install-safety-check), then run: make mark-reviewed TOOL=$tool"
fi

echo "building $pkg in $src"
(cd "$src" && cargo build --release -p "$pkg") \
  || craft_fail 7 "build: cargo build failed for $pkg; kept the previous binary"
mkdir -p "$CRAFT_HOME/bin"
{ cp "$src/target/release/$pkg" "$CRAFT_HOME/bin/$pkg.new" \
  && mv -f "$CRAFT_HOME/bin/$pkg.new" "$CRAFT_HOME/bin/$pkg"; } \
  || craft_fail 7 "build: copy of $pkg failed; kept the previous binary"
echo "installed $CRAFT_HOME/bin/$pkg (commit $head)"
```

`craft-agent/scripts/mark-reviewed.sh`:
```bash
#!/bin/bash
# mark-reviewed.sh <tool>: record the current commit of the tool's repository as
# reviewed, so build.sh may build it. Run it only after you have read a safety
# review of exactly this commit.
CRAFT_BIN=$(cd "$(dirname "$(readlink -f "$0")")/../bin" && pwd -P)
# shellcheck source=../bin/lib/craft-common.sh
. "$CRAFT_BIN/lib/craft-common.sh"

[ $# -eq 1 ] || craft_fail 2 "usage: mark-reviewed.sh <tool>"
craft_load_config || exit 5
craft_read_row "$1" || craft_fail 2 "mark-reviewed: unknown tool '$1' (known: $(craft_tool_keys))"
[ -n "${ARTCRAFT_DIR:-}" ] || craft_fail 5 "mark-reviewed: ARTCRAFT_DIR is not set in config.env"
src="$ARTCRAFT_DIR/$TOOL_REPO"
git -C "$src" rev-parse --git-dir >/dev/null 2>&1 || craft_fail 5 "mark-reviewed: not a git clone: $src"
[ -z "$(git -C "$src" status --porcelain)" ] || craft_fail 6 "mark-reviewed: $src has uncommitted changes"
head=$(git -C "$src" rev-parse HEAD)
mkdir -p "$CRAFT_HOME/reviewed"
printf '%s\n' "$head" >"$CRAFT_HOME/reviewed/$TOOL_REPO"
echo "recorded $TOOL_REPO $head as reviewed"
```

- [ ] **Step 4: Write install, uninstall and clean-jobs**

`craft-agent/scripts/install.sh`:
```bash
#!/bin/bash
# install.sh <craft-home>: create the local folders, the .craft-home link and the
# symlinks Claude Code and the shell need.
#
# Env: CLAUDE_DIR (default ~/.claude), LOCAL_BIN (default ~/.local/bin),
#      FORCE=1 to point an existing .craft-home link to another folder.
# Never replaces a file that is not a symlink, or a symlink that points outside
# this folder. Copies config.example.env only when config.env does not exist.
here=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd -P)
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
```

`craft-agent/scripts/uninstall.sh`:
```bash
#!/bin/bash
# uninstall.sh: remove the symlinks install.sh created (only links that point into
# this folder). Keeps CRAFT_HOME, its data and the .craft-home link.
here=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd -P)
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
```

`craft-agent/scripts/clean-jobs.sh`:
```bash
#!/bin/bash
# clean-jobs.sh <days>: delete job folders created more than <days> days ago
# (by folder modification time). Runs only when called; nothing calls it
# automatically.
CRAFT_BIN=$(cd "$(dirname "$(readlink -f "$0")")/../bin" && pwd -P)
# shellcheck source=../bin/lib/craft-common.sh
. "$CRAFT_BIN/lib/craft-common.sh"

[ $# -eq 1 ] || craft_fail 2 "usage: clean-jobs.sh <days>"
case $1 in ''|*[!0-9]*) craft_fail 2 "clean-jobs: days must be a number" ;; esac
craft_load_config || exit 5
[ -d "$CRAFT_JOBS" ] || exit 0
find "$CRAFT_JOBS" -mindepth 1 -maxdepth 1 -type d -mtime +"$1" -print \
  | while IFS= read -r d; do
      echo "deleting $d"
      rm -rf "$d"
    done
```

Make them executable: `chmod +x craft-agent/scripts/*.sh`

- [ ] **Step 5: Write the Makefile**

`craft-agent/Makefile` (recipe lines start with a tab):
```make
# craft-agent. Run `make help`.
SHELL := /bin/bash
PYTHON ?= python3
DAYS ?= 30
TOOL ?=
ALL_TOOLS := cad design fig film grid light pdf photo sound vector word
TOOLS = $(if $(filter all,$(TOOL)),$(ALL_TOOLS),$(TOOL))

.PHONY: help check test generate build build-app mark-reviewed smoke install uninstall clean-jobs

help:
	@echo "make install CRAFT_HOME=<dir>     set up folders and symlinks (default dir: ~/craft)"
	@echo "make mark-reviewed TOOL=<tool>    record the reviewed commit of a tool's repository"
	@echo "make build TOOL=<tool>|all        build the *-cli binary (needs a reviewed commit)"
	@echo "make build-app TOOL=<tool>|all    build the desktop app for live mode"
	@echo "make smoke [TOOL=<tool>]          start built servers and run one call each"
	@echo "make test | check | generate      development"
	@echo "make clean-jobs DAYS=30           delete old job folders"
	@echo "make uninstall                    remove the symlinks (keeps CRAFT_HOME)"

generate:
	$(PYTHON) scripts/generate.py

check:
	$(PYTHON) scripts/generate.py --check
	shellcheck -x bin/craft-mcp bin/craft-stage bin/craft-app bin/craft-guard bin/lib/craft-common.sh scripts/*.sh
	scripts/check-confidentiality.sh

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

build:
	@test -n "$(TOOL)" || { echo "usage: make build TOOL=<tool>|all"; exit 2; }
	@for t in $(TOOLS); do scripts/build.sh $$t cli || exit $$?; done

build-app:
	@test -n "$(TOOL)" || { echo "usage: make build-app TOOL=<tool>|all"; exit 2; }
	@for t in $(TOOLS); do scripts/build.sh $$t app || exit $$?; done

mark-reviewed:
	@test -n "$(TOOL)" || { echo "usage: make mark-reviewed TOOL=<tool>"; exit 2; }
	scripts/mark-reviewed.sh $(TOOL)

smoke:
	$(PYTHON) tests/smoke.py $(TOOL)

install:
	scripts/install.sh "$(if $(CRAFT_HOME),$(CRAFT_HOME),$(HOME)/craft)"

uninstall:
	scripts/uninstall.sh

clean-jobs:
	scripts/clean-jobs.sh $(DAYS)
```

- [ ] **Step 6: Run the tests**

Run: `cd craft-agent && python3 -m unittest discover -s tests -p 'test_app.py' -v && python3 -m unittest discover -s tests -p 'test_build.py' -v && python3 -m unittest discover -s tests -p 'test_install.py' -v`
Expected: 4 + 5 + 5 tests pass.

Before the install tests run, check that no real `.craft-home` link exists in this worktree (`ls -la craft-agent/.craft-home` → "No such file"). The test saves and restores it anyway.

- [ ] **Step 7: Checkpoint (no commit)**

Run: `git status --short`
Expected: new `bin/craft-app`, `scripts/*.sh`, `Makefile`, three test files.

---

### Task 7: `/craft` skill, README, config template and `make check`

**Files:**
- Create: `craft-agent/config.example.env`
- Create: `craft-agent/skill/craft/SKILL.md`
- Create: `craft-agent/README.md`
- Create: `craft-agent/scripts/check-confidentiality.sh`
- Create: `craft-agent/tests/test_confidentiality.py`
- Modify: `README.md` (repository root): new "Agents" section before `## Contributing`

**Interfaces:**
- Consumes: everything above.
- Produces: `scripts/check-confidentiality.sh [file...]` (exit 1 on a finding; with no arguments it checks every tracked and untracked file under `craft-agent/` plus the spec and this plan).

- [ ] **Step 1: Write the config template**

`craft-agent/config.example.env`:
```bash
# craft-agent local settings. `make install` copies this file to
# $CRAFT_HOME/config.env once. Do not set CRAFT_HOME here: it comes from the
# .craft-home link that `make install` creates.

# Folder that holds the ArtCraft repositories, one subfolder per repository
# (cadcraft, pdfcraft, ...).
ARTCRAFT_DIR="$HOME/src/artcraft"

# craft-stage copies input files only from inside this folder.
CRAFT_READ_ROOT="$HOME"

# Control ports for live mode: cad = base + 0 ... word = base + 10.
CRAFT_PORT_BASE=7901

# Comma-separated words that must never appear in committed files of this
# folder, for example names of your organisation. `make check` searches for them.
CRAFT_DENY_WORDS=""
```

- [ ] **Step 2: Write the failing confidentiality test**

`craft-agent/tests/test_confidentiality.py`:
```python
"""Tests for scripts/check-confidentiality.sh."""
import os
import unittest

from helpers import ROOT, CraftHome

SCRIPT = os.path.join(ROOT, "scripts", "check-confidentiality.sh")


class ConfidentialityTest(unittest.TestCase):
    def setUp(self):
        self.h = CraftHome(extra='CRAFT_DENY_WORDS="examplecorp,Jane Roe"\n')

    def tearDown(self):
        self.h.cleanup()

    def check(self, text):
        path = os.path.join(self.h.base, "sample.md")
        with open(path, "w") as f:
            f.write(text)
        return self.h.run(SCRIPT, path)

    def test_clean_text_passes(self):
        r = self.check("Use $HOME/craft and UTF-8, SHA-256, ISO-8601.\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_home_path_found(self):
        r = self.check("see " + "/Us" + "ers/alice/notes\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("home path", r.stdout)

    def test_ticket_key_found(self):
        r = self.check("fixed in " + "ABC" + "-123\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("ticket key", r.stdout)

    def test_deny_word_found_case_insensitive(self):
        r = self.check("Built at ExampleCorp.\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("deny word", r.stdout)

    def test_repository_files_are_clean(self):
        r = self.h.run(SCRIPT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
```

Run: `cd craft-agent && python3 -m unittest discover -s tests -p 'test_confidentiality.py'`
Expected: errors, script not found.

- [ ] **Step 3: Write the confidentiality check**

`craft-agent/scripts/check-confidentiality.sh`:
```bash
#!/bin/bash
# check-confidentiality.sh [file...]: fail (exit 1) if files contain personal or
# internal data: absolute home paths, ticket-key patterns, or the words in
# CRAFT_DENY_WORDS from the local config.env. The deny list stays local, because
# a committed list of names would publish those names.
#
# Without arguments it checks every tracked and untracked (not ignored) file in
# craft-agent/ plus the craft-agent spec and plan.
CRAFT_BIN=$(cd "$(dirname "$(readlink -f "$0")")/../bin" && pwd -P)
# shellcheck source=../bin/lib/craft-common.sh
. "$CRAFT_BIN/lib/craft-common.sh"
here=$(dirname "$CRAFT_BIN")
repo=$(cd "$here/.." && pwd -P)

files=()
if [ $# -gt 0 ]; then
  files=("$@")
else
  while IFS= read -r f; do
    [ -f "$repo/$f" ] && files+=("$repo/$f")
  done < <(git -C "$repo" ls-files -co --exclude-standard -- craft-agent \
    docs/superpowers/specs/2026-10-14-craft-agent-design.md \
    docs/superpowers/plans/2026-10-14-craft-agent.md)
fi

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

if craft_load_config 2>/dev/null && [ -n "${CRAFT_DENY_WORDS:-}" ]; then
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

[ $status -eq 0 ] && echo "confidentiality check: ${#files[@]} files clean"
exit $status
```

Notes: the grep pattern `/(Users|home)/[A-Za-z0-9._-]+` does not match its own source line, because the line contains `/(Users`, not `/Users/`. The allowlist holds `PDF-1` (from `%PDF-1.4` in `tests/smoke.py`) and `Z0-9` (from the character class `[A-Z0-9]` in this script); both are matched by the ticket-key pattern but are not ticket keys.

Make it executable: `chmod +x craft-agent/scripts/check-confidentiality.sh`

Run: `cd craft-agent && python3 -m unittest discover -s tests -p 'test_confidentiality.py' -v`
Expected: 5 tests pass. If `test_repository_files_are_clean` fails, fix the reported file, not the check.

- [ ] **Step 4: Write the `/craft` skill**

`craft-agent/skill/craft/SKILL.md`:
```markdown
---
name: craft
description: Edit, convert or create files with the ArtCraft desktop tools (PDF, Word documents, spreadsheets, photos, raw photos, vector graphics, UI designs, CAD drawings, page layouts, video, audio). Use when the user types /craft or asks to do such a task with ArtCraft. Picks the matching craft-<tool> agent, copies the inputs into a job folder and reports the result files.
---

# /craft

One entry point for 11 `craft-<tool>` agents. Each agent controls one ArtCraft
application through its MCP server. An agent can only reach files inside a job
folder; a hook blocks every other path.

## Steps

### 1. Pick the agent

Match the input file type first, then the task. If two agents fit, ask the user
one question. If none fits, say so and stop.

| Input or task | Agent | Tool key |
|---|---|---|
| `.pdf`: pages, merge, split, comments, forms, passwords, redact | `craft-pdf` | `pdf` |
| `.docx` `.odt` `.rtf` `.md`: write, edit, convert documents | `craft-word` | `word` |
| `.xlsx` `.csv` `.ods`: data, formulas, charts | `craft-sheet` | `grid` |
| `.psd`, or one image: layers, masks, retouch, text | `craft-photo` | `photo` |
| raw files, `.dng`, many photos: exposure, color, batch export | `craft-light` | `light` |
| `.svg` `.ai` `.eps`: vector drawing, logos, icons | `craft-vector` | `vector` |
| `.figcraft`, UI screens, components, prototypes | `craft-fig` | `fig` |
| `.dxf` `.dwg`: technical drawings | `craft-cad` | `cad` |
| `.idml`, page layout, brochures, `.epub` | `craft-design` | `design` |
| `.mp4` `.mov` `.mkv`: cut, color, captions, export | `craft-film` | `film` |
| `.wav` `.mp3` `.flac`, several tracks: record, edit, mix | `craft-sound` | `sound` |

Cases that need a question:
- `.jpg` `.png` `.tif`: one image with pixel work goes to `craft-photo`; many photos
  or exposure and color work goes to `craft-light`.
- A `.pdf` the user wants to rewrite as a document: `craft-pdf` (edit the PDF) or
  `craft-word` (new document).

### 2. Check that the tool is built

Run `craft-mcp --check <tool key>`. On exit 4, show its message to the user (it
names the `make build` command) and stop. Do not start the agent.

### 3. Create the job

Slug: `YYYY-MM-DD-<2 to 4 words of the task, kebab-case>`, with today's date.
Run `craft-stage <slug> <input files>`. It prints the job folder. Without input
files (create a new file), run `craft-stage <slug>`.

On exit 2, show the message and stop. Never copy a refused file in another way,
and never put files into the job folder yourself.

### 4. Hand over to the agent

Use the Agent tool with `subagent_type: craft-<tool>` and this prompt:

    Task: <the user's task, with the file names as they are in <job>/in>
    Job folder: <the absolute path craft-stage printed>
    Inputs: <job>/in/<name> (one line per input)
    Results: write to <job>/out
    Mode: headless

Write `Mode: live` only when the user asked to watch the app or said "live". The
user must start the app first with `craft-app <tool key>`.

### 5. Report

Tell the user each output path, what the agent checked, and what it could not
do. If the agent saved anything under `out/_failed/`, say that first. Offer to
open a result with `open <path>`.

## A task that needs two tools

Run the agents one after another with the same job folder. Hand the first
agent's output files to the second agent as its inputs (they are already in
`<job>/out`; name them in the prompt). Do this only when the task clearly needs
two tools.

## Do not

- Do not call `craft-mcp` or the ArtCraft CLIs yourself to do the task.
- Do not give the agent paths outside the job folder.
- Do not retry a refused or blocked file with a different path.
```

- [ ] **Step 5: Write the craft-agent README**

`craft-agent/README.md`:
```markdown
# craft-agent

`/craft` plus 11 Claude Code subagents that edit files with the
[ArtCraft](https://getartcraft.com/) desktop applications through their MCP
servers. ArtCraft is a set of open-source, clean-room reimplementations of
well-known desktop applications, written in Rust.

| Agent | ArtCraft tool | Tool key | Replaces |
|---|---|---|---|
| `craft-cad` | CADCraft | `cad` | AutoCAD |
| `craft-design` | DesignCraft | `design` | InDesign |
| `craft-fig` | FigCraft | `fig` | Figma |
| `craft-film` | FilmCraft | `film` | Premiere Pro |
| `craft-sheet` | GridCraft | `grid` | Excel |
| `craft-light` | LightCraft | `light` | photo development (Lightroom-style) |
| `craft-pdf` | PdfCraft | `pdf` | Acrobat |
| `craft-photo` | PhotoCraft | `photo` | Photoshop |
| `craft-sound` | SoundCraft | `sound` | Pro Tools |
| `craft-vector` | VectorCraft | `vector` | Illustrator |
| `craft-word` | WordCraft | `word` | Word |

## How it works

1. You type `/craft <task>` and name the input files.
2. The skill picks the agent, checks that the tool is built, and copies the
   inputs into a job folder with `craft-stage`.
3. The agent starts its MCP server through `craft-mcp`, does the work, checks its
   result and writes to `<job>/out`.
4. A `PreToolUse` hook, `craft-guard`, runs before every tool call of the agent.
   It blocks calls that name a path outside the jobs folder or a secret file.

The agents are standalone subagent files, not a plugin. Claude Code starts the
MCP servers that a subagent file declares only while that subagent runs. In a
plugin agent, Claude Code ignores that field, and plugin MCP servers start in
every session.

## Requirements

- macOS. The scripts use `/bin/bash` 3.2, `/usr/bin/jq` and `cp -c`.
- Claude Code.
- Rust and cargo, to build the ArtCraft binaries.
- Python 3.11 or newer, for `make generate` and `make test`.
- shellcheck, for `make check`.
- `~/.local/bin` on `PATH`.

## Install

1. Clone the ArtCraft repositories you want into one folder:
   `git clone https://github.com/storytold/pdfcraft.git <ARTCRAFT_DIR>/pdfcraft`
2. `make install CRAFT_HOME=<folder for jobs, binaries and logs>`
   (default `~/craft`).
3. Edit `<CRAFT_HOME>/config.env`: `ARTCRAFT_DIR`, `CRAFT_READ_ROOT`.
4. For each tool you want:
   1. Review the code that runs during the build (build scripts, proc macros) for
      the current commit, for example with the `repo-install-safety-check` skill.
   2. `make mark-reviewed TOOL=pdf`
   3. `make build TOOL=pdf` (and `make build-app TOOL=pdf` for live mode)
   4. `make smoke TOOL=pdf`
5. Start a new Claude Code session, so it loads the agents.

## Commands

| Command | What it does |
|---|---|
| `/craft <task>` | the entry point in Claude Code |
| `craft-stage <slug> [files]` | copy inputs into `<CRAFT_HOME>/jobs/<slug>/in` |
| `craft-mcp <tool> [--live]` | start a tool's MCP server (used by the agents) |
| `craft-mcp --check <tool>` | exit 0 if the tool is built |
| `craft-app <tool>` | start the desktop app with its control port, for live mode |
| `make clean-jobs DAYS=30` | delete job folders older than 30 days |
| `make uninstall` | remove the symlinks; keeps `CRAFT_HOME` |

## Folders and what the agents can reach

```
<CRAFT_HOME>/
├── config.env      your settings (not in git)
├── bin/            built binaries
├── jobs/<slug>/    in/ (copies of inputs), out/ (results), out/_failed/
├── state/          per-tool state, for example the LightCraft library
├── reviewed/       reviewed commit per repository
└── logs/           server logs, guard.log (every hook decision)
```

- The ArtCraft tools see only copies in `jobs/`. Your original files are never
  opened by an ArtCraft tool.
- `craft-stage` copies only from inside `CRAFT_READ_ROOT`, and refuses secret
  file names: any name that contains `.env`, and `credentials`, `.databrickscfg`,
  `.netrc`.
- `craft-guard` checks every string in a tool call that looks like a path: it
  starts with `/`, `~`, `./`, `../` or `file://`, or it contains `/`. Strings that
  hold JSON are parsed and checked too.

### Limits

- Six tools have no folder limit of their own: cadcraft, designcraft, figcraft,
  filmcraft, gridcraft, lightcraft. For them, `craft-guard` is the only check.
- In live mode, no tool has a folder limit of its own. The desktop app may also
  use folders from its own settings (recent files, default export folder). The
  hook cannot see those.
- The hook also blocks normal text that contains `.env` or `../`. Rephrase the
  task in that case.
- The ArtCraft tools are young software. The agents check their results, but
  read the output before you use it.

## Development

- Edit `tools.toml` or `templates/agent.md.tmpl`, then `make generate`. Never
  edit `agents/*.md` or `bin/tools.tsv` by hand; `make test` fails when they
  differ from the generator output.
- `make test`: all tests, no ArtCraft binaries needed.
- `make check`: generator drift, shellcheck, confidentiality check.
- `make smoke [TOOL=<tool>]`: starts built servers and runs one real call per
  tool that has a case in `tests/smoke_cases.json`.

## Manual end-to-end check

Run these in a new Claude Code session after `make install` and one built tool:

1. `/craft split <some folder>/sample.pdf into single pages`: files appear in
   `jobs/<slug>/out/`, and the agent says how it checked them.
2. `/craft open <some folder>/.env`: refused by `craft-stage`.
3. `/craft ... live` with the app closed: the agent reports the `craft-app` hint
   and continues headless.
```

- [ ] **Step 6: Add the agent to the repository README**

Edit `README.md` at the repository root. Insert before the line `## Contributing`:
```markdown
## Agents

Standalone subagents with their own MCP servers. They are not plugins, because a
plugin agent cannot start its own MCP servers. Each one has its own `make install`.

| Agent | What it does | Use when |
|---|---|---|
| [`craft-agent`](craft-agent/) | `/craft` plus 11 `craft-<tool>` agents that drive the open-source ArtCraft desktop apps (PDF, documents, spreadsheets, photos, vector, CAD, layout, video, audio) over MCP, on copies of your files in a job folder | You want an agent to edit or convert a file with an open-source desktop tool |

```

- [ ] **Step 7: Run all tests and the checks**

Run: `cd craft-agent && make test && make check`
Expected: all tests pass; `make check` prints no `out of date` line, no shellcheck finding and `confidentiality check: <n> files clean` (plus the note that deny words were not checked, because this worktree has no `.craft-home` yet). Fix every shellcheck finding in the script it names.

- [ ] **Step 8: Checkpoint (no commit)**

Run: `git status --short`
Expected: new `config.example.env`, `skill/`, `README.md`, `scripts/check-confidentiality.sh`, `tests/test_confidentiality.py` in `craft-agent/`; modified root `README.md`.

---

### Task 8: Smoke test runner and the real install

**Files:**
- Create: `craft-agent/tests/smoke.py`
- Create: `craft-agent/tests/smoke_cases.json`
- Local only (not in the repository): `<CRAFT_HOME>/config.env`, symlinks

**Interfaces:**
- Consumes: `tests/mcp_client.py` (Task 2), `bin/craft-mcp` (Task 4), `scripts/install.sh` (Task 6).
- Produces: `python3 tests/smoke.py [tool]` prints one line per tool: `PASS`, `SKIP` or `FAIL` with a reason; exit 1 if any `FAIL`. `write_min_pdf(path, pages)` for synthetic PDFs.

- [ ] **Step 1: Write the smoke runner**

`craft-agent/tests/smoke.py`:
```python
#!/usr/bin/env python3
"""Smoke-test the built ArtCraft MCP servers through bin/craft-mcp.

    python3 tests/smoke.py [tool]

For every tool (or the one given): SKIP if its binary is not built. Otherwise
start `craft-mcp <tool>`, run initialize and tools/list, and run the tool's case
from smoke_cases.json if there is one. Uses the real CRAFT_HOME (the
.craft-home link or the CRAFT_HOME environment variable).

Case format: {"<tool>": {"setup": "<setup name or null>", "steps": [
  {"tool": "<mcp tool>", "arguments": {...}, "expect": "<text in result>",
   "expect_files": ["out/<file>"]}]}}
In arguments, "{job}", "{in}" and "{out}" are replaced with the job paths.
"""
import json
import os
import subprocess
import sys
import time

from mcp_client import McpClient, McpError

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CRAFT_MCP = os.path.join(ROOT, "bin", "craft-mcp")


def write_min_pdf(path, pages=2):
    """Write a valid PDF with empty 200x200 pages."""
    kids = " ".join("%d 0 R" % (3 + i) for i in range(pages))
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, pages)]
    objs += ["<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>"] * pages
    out = b"%PDF-1.4\n"
    offsets = []
    for n, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += ("%d 0 obj\n%s\nendobj\n" % (n, obj)).encode()
    xref = len(out)
    out += ("xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)).encode()
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, xref)).encode()
    with open(path, "wb") as f:
        f.write(out)


SETUPS = {
    "pdf2": lambda in_dir: write_min_pdf(os.path.join(in_dir, "two-pages.pdf"), 2),
}


def craft_home():
    if os.environ.get("CRAFT_HOME"):
        return os.environ["CRAFT_HOME"]
    return os.path.realpath(os.path.join(ROOT, ".craft-home"))


def tool_keys():
    with open(os.path.join(ROOT, "bin", "tools.tsv")) as f:
        return [line.split("\t")[0] for line in f if line.strip() and not line.startswith("#")]


def fill(value, job):
    if isinstance(value, str):
        return (value.replace("{job}", job).replace("{in}", os.path.join(job, "in"))
                .replace("{out}", os.path.join(job, "out")))
    if isinstance(value, list):
        return [fill(v, job) for v in value]
    if isinstance(value, dict):
        return {k: fill(v, job) for k, v in value.items()}
    return value


def text_of(result):
    return "\n".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")


def smoke(key, cases, home):
    check = subprocess.run([CRAFT_MCP, "--check", key], capture_output=True, text=True)
    if check.returncode == 4:
        return "SKIP", check.stderr.strip()
    if check.returncode != 0:
        return "FAIL", check.stderr.strip()
    client = McpClient([CRAFT_MCP, key], timeout=60)
    try:
        client.initialize()
        tools = client.list_tools()
        if not tools:
            return "FAIL", "tools/list is empty"
        case = cases.get(key)
        if case is None:
            return "PASS", "%d tools (no call case)" % len(tools)
        job = os.path.join(home, "jobs", "smoke-%s-%s" % (key, time.strftime("%Y%m%d-%H%M%S")))
        os.makedirs(os.path.join(job, "in"))
        os.makedirs(os.path.join(job, "out"))
        if case.get("setup"):
            SETUPS[case["setup"]](os.path.join(job, "in"))
        for step in case["steps"]:
            result = client.call(step["tool"], fill(step["arguments"], job))
            text = text_of(result)
            if result.get("isError"):
                return "FAIL", "%s: %s" % (step["tool"], text[:300])
            if step.get("expect") and step["expect"] not in text:
                return "FAIL", "%s: %r not in %r" % (step["tool"], step["expect"], text[:300])
            for rel in step.get("expect_files", []):
                if not os.path.exists(os.path.join(job, rel)):
                    return "FAIL", "%s: missing %s" % (step["tool"], rel)
        return "PASS", "%d tools, %d call(s), job %s" % (len(tools), len(case["steps"]), job)
    except (McpError, TimeoutError, EOFError) as e:
        return "FAIL", str(e)
    finally:
        client.close()


def main(argv):
    with open(os.path.join(HERE, "smoke_cases.json")) as f:
        cases = json.load(f)
    keys = argv or tool_keys()
    home = craft_home()
    failed = False
    for key in keys:
        status, detail = smoke(key, cases, home)
        failed = failed or status == "FAIL"
        print("%-4s %-7s %s" % (status, key, detail))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

`craft-agent/tests/smoke_cases.json` (the argument name `formula` is checked in Task 9 Step 4):
```json
{
  "grid": {
    "setup": null,
    "steps": [
      {"tool": "evaluate_formula", "arguments": {"formula": "=SUM(1,2)"}, "expect": "3"}
    ]
  }
}
```

- [ ] **Step 2: Add a unit test for the PDF writer**

Append to `craft-agent/tests/test_mcp_client.py`, before `if __name__`:
```python
class MinPdfTest(unittest.TestCase):
    def test_min_pdf_structure(self):
        import tempfile
        from smoke import write_min_pdf
        path = os.path.join(tempfile.mkdtemp(), "t.pdf")
        write_min_pdf(path, 2)
        with open(path, "rb") as f:
            data = f.read()
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertIn(b"/Count 2", data)
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))
        xref = int(data.rsplit(b"startxref\n", 1)[1].split(b"\n")[0])
        self.assertTrue(data[xref:].startswith(b"xref"))
```

Run: `cd craft-agent && make test`
Expected: all tests pass.

- [ ] **Step 3: Install for real**

Ask the owner for the `CRAFT_HOME` folder they chose and the folder that holds their ArtCraft clones. Then run, with those values:
```bash
cd craft-agent && make install CRAFT_HOME=<chosen folder>
```
Edit `<chosen folder>/config.env`: set `ARTCRAFT_DIR`, `CRAFT_READ_ROOT` (the owner's choice) and `CRAFT_DENY_WORDS` (ask the owner which words to list).

Expected: `linked ...` lines for `.craft-home`, 11 agents, the skill and 4 binaries; no `not on PATH` note.

- [ ] **Step 4: Run the checks with the real config**

Run: `cd craft-agent && make check`
Expected: `confidentiality check: <n> files clean` without the "deny words not checked" note.

- [ ] **Step 5: Checkpoint (no commit)**

Run: `git status --short`
Expected: new `tests/smoke.py`, `tests/smoke_cases.json`; `test_mcp_client.py` changed. `.craft-home` does not appear (it is ignored).

---

### Task 9: Review, build and smoke-test the first two tools; end-to-end check

This task runs code from third-party repositories on the owner's machine. Every build needs the owner's explicit approval after a safety review of the exact commit.

**Files:**
- Modify: `craft-agent/tests/smoke_cases.json` (add a `pdf` case; fix the `grid` case if needed)

**Interfaces:**
- Consumes: everything above; the `repo-install-safety-check` skill.

- [ ] **Step 1: Safety review of gridcraft and pdfcraft**

Invoke the `repo-install-safety-check` skill on `<ARTCRAFT_DIR>/gridcraft` and `<ARTCRAFT_DIR>/pdfcraft`. Show the owner both reports. **Stop and wait for the owner's approval of each repository.**

- [ ] **Step 2: Record the reviewed commits**

Only for approved repositories:
```bash
cd craft-agent && make mark-reviewed TOOL=grid && make mark-reviewed TOOL=pdf
```
Expected: `recorded gridcraft <hash> as reviewed`, same for pdfcraft.

- [ ] **Step 3: Build**

Run in the background (release builds can take several minutes each):
```bash
cd craft-agent && make build TOOL=grid && make build TOOL=pdf
```
Expected: `installed <CRAFT_HOME>/bin/gridcraft-cli (commit ...)`, same for `pdfcraft-cli`. On exit 7, read the cargo output and report it; do not change the ArtCraft repositories.

- [ ] **Step 4: Check the grid case against the real tool list**

Run: `cd craft-agent && python3 tests/mcp_client.py list grid | grep evaluate_formula`
Expected: one line with the input schema. If the formula parameter has another name than `formula`, change it in `tests/smoke_cases.json`. If there is no `evaluate_formula` tool, pick the tool from the list that evaluates a formula and use it.

Run: `make smoke TOOL=grid`
Expected: `PASS grid ...`.

- [ ] **Step 5: Write and run the pdf case**

Run: `python3 tests/mcp_client.py list pdf`
From the listed tools and their input schemas, write a `pdf` case in `tests/smoke_cases.json` with `"setup": "pdf2"` that (1) opens `{in}/two-pages.pdf`, (2) splits it or extracts page 2 into `{out}`, and (3) lists `expect_files` for the output file. Use only tool and parameter names that the list shows; with `--compact`, tools outside the core set are called through `tool_call` with the name found by `tool_search`.

Run: `make smoke TOOL=pdf`
Expected: `PASS pdf ...`, and the expected output file exists in the job's `out/`.

Run: `make smoke`
Expected: `PASS` for grid and pdf, `SKIP` for the other 9 tools, exit 0.

- [ ] **Step 6: Manual end-to-end check in Claude Code**

Prepare the inputs (inside `CRAFT_READ_ROOT`):
```bash
E2E="<a folder inside CRAFT_READ_ROOT>/craft-e2e"
mkdir -p "$E2E"
python3 -c "import sys; sys.path.insert(0, 'craft-agent/tests'); from smoke import write_min_pdf; write_min_pdf('$E2E/sample.pdf', 3)"
printf 'X=1\n' > "$E2E/.env"
```
Ask the owner to start a new Claude Code session and run:
1. `/craft split <E2E>/sample.pdf into single pages` → three files in the job's `out/`; the agent says how it checked them; `logs/guard.log` shows only `allow` lines for `mcp__craft-pdf__*`.
2. `/craft open <E2E>/.env` → refused by `craft-stage` with `secret file name`.
3. `/craft put 42 in cell A1 of a new spreadsheet, live` with the GridCraft app not running → the agent reports `craft-app grid` and continues headless (the result file lands in `out/`).

Record the results in the owner's chat. Then remove the inputs: `rm -rf "$E2E"`.

- [ ] **Step 7: Final checks**

Run: `cd craft-agent && make test && make check`
Expected: all tests pass, all checks clean.

- [ ] **Step 8: Hand over (no commit)**

Run: `git status --short` and `git diff --stat`
Report the list to the owner. The owner reviews and commits.
