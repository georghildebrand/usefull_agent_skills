# Design: `craft-agent`

Date: 2026-10-14
Status: design approved in chat, spec waiting for review

## Problem

ArtCraft is a set of 11 open-source desktop applications, written in Rust. Each one
is a clean-room reimplementation of a well-known commercial application:

| ArtCraft tool | Replaces | Agent name |
|---|---|---|
| cadcraft | AutoCAD | `craft-cad` |
| designcraft | InDesign | `craft-design` |
| figcraft | Figma | `craft-fig` |
| filmcraft | Premiere Pro | `craft-film` |
| gridcraft | Excel | `craft-sheet` |
| lightcraft | Lightroom-style photo development | `craft-light` |
| pdfcraft | Acrobat | `craft-pdf` |
| photocraft | Photoshop | `craft-photo` |
| soundcraft | Pro Tools | `craft-sound` |
| vectorcraft | Illustrator | `craft-vector` |
| wordcraft | Word | `craft-word` |

A user wants **one entry point in Claude Code** for all 11 tools: "make this PDF
smaller", "remove the background of this photo". Most tasks need one tool. The agent
picks the tool, does the work on a copy of the input, checks the result and reports
where the output is.

## Key findings

All facts below come from reading each tool's CLI source (`apps/<tool>-cli`), not its
README.

**Every tool already has an MCP server.** `<tool>-cli mcp` speaks MCP over stdio.
Most servers expose a small set of generic tools (a list tool and a command tool)
that reach every command of the application, so the tool lists stay small (about
5-40 tools per server). The names of these generic tools differ per tool (for
example, gridcraft calls its command tool `execute_command`); the agents find them
with the server's list or search tool. lightcraft and pdfcraft have a `--compact` flag that hides
per-command tools.

**The flags differ per tool.**

| Tool | Live-app flag | Folder limit | Live server when the app is not running |
|---|---|---|---|
| cadcraft | `--connect HOST:PORT` | none | fails at startup |
| designcraft | `--connect PORT\|HOST:PORT` | none | fails at startup |
| figcraft | `--attach PORT\|HOST:PORT` | none | fails at startup |
| filmcraft | `--bridge 127.0.0.1:PORT` | none | starts, fails per call |
| gridcraft | `--connect PORT\|HOST:PORT` | none | fails at startup |
| lightcraft | `--connect [ADDR]` | none | starts, retries per call |
| pdfcraft | no live MCP mode | `--root DIR` (one folder, read and write) | n/a |
| photocraft | `--bridge 127.0.0.1:PORT` + token file | `--automation-read-root`, `--automation-write-root` (one each) | starts, fails per call |
| soundcraft | `--connect PORT\|HOST:PORT` | read/write root, one each, not with `--connect` | starts, fails per call |
| vectorcraft | `--connect ADDR` | read/write root, one each, not with `--connect` | fails at startup |
| wordcraft | `--connect HOST:PORT` + key file (found automatically) | read/write root, one each, not with `--connect` | fails at startup |

Consequences:

- Six tools have no folder limit, pdfcraft has one folder for read and write, and no
  tool has a folder limit in live mode. A folder limit can therefore not be enforced
  through the tools' own flags. It must be enforced outside the tools.
- Four apps use port 7979 in their examples. Running two of them with defaults fails.
- vectorcraft started with no flags silently attaches to an app on 7979 if one runs.
  Headless mode must always pass explicit flags.
- No server reads files on its own. lightcraft `import` and pdfcraft `doc_batch` scan
  folders recursively, but only folders the client names.

**Claude Code behavior** (from the Claude Code docs, to be confirmed by task 1 of the
plan):

- A subagent file in `~/.claude/agents/` may declare `mcpServers`. They start when
  the subagent starts and stop when it ends. A subagent shipped in a plugin may not:
  Claude Code ignores the field there. Plugin MCP servers start in every session.
  This is why `craft-agent` is not a plugin.
- A subagent file may declare `hooks` (`PreToolUse`), active only while it runs.
- Tool names are `mcp__<server>__<tool>`; hyphens are kept.
- The subagent `tools` field takes tool names and MCP wildcards, not Bash patterns.

## Confidentiality boundary

This folder lives in a shared skills repository. Everything committed must be safe to
publish.

- No absolute home paths. Committed files use `$HOME`, `PATH` lookups and
  placeholders. The agent files call `craft-mcp` and `craft-guard` by name.
- All user-specific values (folders, ports, forbidden words) live in a local
  `config.env` outside the repository. The repository ships `config.example.env`
  with generic defaults.
- Examples use synthetic file names (`report.pdf`, `photo.jpg`).
- ArtCraft and its repositories are public open-source projects and may be named.
- `make check` searches committed files for absolute home paths, ticket-key patterns
  and the words in the local `CRAFT_DENY_WORDS`. The deny list stays local, because a
  committed list of forbidden names would itself publish them.

## Architecture

### Repository layout

```
craft-agent/
├── README.md                  install, config, limits, manual end-to-end checklist
├── Makefile                   check | test | generate | build | smoke | install | clean-jobs
├── tools.toml                 one row per tool: repo, cli, port offset, flag mapping, notes
├── config.example.env         template for the local config
├── bin/
│   ├── craft-mcp              launcher (bash): craft-mcp <tool> [--live] | --check <tool>
│   ├── craft-stage            copies inputs into a job folder (bash)
│   ├── craft-app              starts a desktop app with its control port (bash)
│   ├── craft-guard            PreToolUse hook (bash + /usr/bin/jq, which ships with macOS)
│   └── tools.tsv              GENERATED from tools.toml
├── scripts/generate.py        tools.toml -> agents/*.md + bin/tools.tsv
├── templates/agent.md.tmpl    one template for all 11 agents
├── agents/craft-<tool>.md     11 GENERATED, committed
├── skill/craft/SKILL.md       the /craft entry point
└── tests/
```

Runtime code is bash, because Claude Code starts the launcher and the hook as plain
processes. The macOS system `python3` is 3.9 (no `tomllib`) and no conda environment
is active there. Python runs only in `make generate` and in tests.

### Local layout (not committed)

```
$CRAFT_HOME/                   default in config.example.env: $HOME/craft
├── config.env                 ARTCRAFT_DIR, CRAFT_READ_ROOT, CRAFT_PORT_BASE, CRAFT_DENY_WORDS
├── bin/                       the 11 *-cli binaries, copied by `make build`
├── jobs/<YYYY-MM-DD-slug>/
│   ├── in/                    copies of the inputs
│   └── out/                   results; out/_failed/ for results that failed their check
├── state/                     per-tool state, e.g. the lightcraft library
├── reviewed/<repo>            commit hash that passed repo-install-safety-check
├── photo.token                photocraft control token (mode 0600)
└── logs/<tool>.log            launcher stderr
```

`make install` creates these symlinks; nothing else outside `$CRAFT_HOME` changes:

- `~/.claude/agents/craft-<tool>.md` -> `craft-agent/agents/`
- `~/.claude/skills/craft` -> `craft-agent/skill/craft`
- `~/.local/bin/{craft-mcp,craft-stage,craft-app,craft-guard}` -> `craft-agent/bin/`

`make install CRAFT_HOME=<dir>` (default `$HOME/craft`) also creates the gitignored
symlink `craft-agent/.craft-home` -> `<dir>`, and copies `config.example.env` to
`<dir>/config.env` only when that file does not exist yet.

The scripts find `CRAFT_HOME` without an environment variable: each script resolves
its own real path (through the `~/.local/bin` symlink into the repository) and follows
`../.craft-home`. Claude Code starts the launcher and the hook as plain processes that
do not read shell rc files, so an environment variable would not reliably arrive
there, and the committed files stay free of personal paths. A `CRAFT_HOME`
environment variable, when set, still takes priority; the tests use it to point the
scripts at a temporary folder. `config.env` must not set `CRAFT_HOME`.

### The job folder rule

**The ArtCraft tools see only `$CRAFT_HOME/jobs/`.** This one rule replaces the
11 different folder flags.

- `craft-stage <job> <file>...` is the only way to bring input into a job. It runs in
  the main session, not in the agent. It copies with `cp -c` (APFS clone: no extra
  disk space until a copy changes). It refuses files outside `CRAFT_READ_ROOT`
  (checked on the resolved real path, so symlinks cannot escape) and file names that
  match `.env*`, `*.env`, `credentials`, `.databrickscfg`, `.netrc`.
- `craft-guard` runs as a `PreToolUse` hook in every agent, for `mcp__craft-.*` and
  `Read`. It walks `tool_input` recursively. Every string that looks like a path
  (starts with `/`, `~`, `./`, `../`, or contains `/`) is resolved against the
  server's working directory (`$CRAFT_HOME/jobs`) to a real path; for a file that
  does not exist yet, the parent folder is resolved. The call is blocked (exit 2,
  reason on stderr) if a path is outside `$CRAFT_HOME/jobs` or matches a secret file
  name. Strings that parse as JSON are walked too, because the generic command tools
  take their parameters as a JSON string.
- Where a tool has folder flags, the launcher also sets them to `$CRAFT_HOME/jobs`.
- Original files are never opened by an ArtCraft tool.

### Launcher: `craft-mcp`

`craft-mcp <tool> [--live]` reads `config.env` and `tools.tsv`, sets the working
directory to `$CRAFT_HOME/jobs`, appends stderr to `logs/<tool>.log`, and `exec`s the
real binary. Ports are `CRAFT_PORT_BASE` + offset (default base 7901: cad 7901,
design 7902, fig 7903, film 7904, grid 7905, light 7906, pdf 7907 reserved,
photo 7908, sound 7909, vector 7910, word 7911).

| Call | Command |
|---|---|
| `craft-mcp pdf` | `pdfcraft-cli mcp --root $J --compact` |
| `craft-mcp photo` | `photocraft-cli mcp --automation-read-root $J --automation-write-root $J` |
| `craft-mcp vector` | `vectorcraft-cli mcp --automation-read-root $J --automation-write-root $J` |
| `craft-mcp light` | `lightcraft-cli mcp --headless --compact --library $CRAFT_HOME/state/light` |
| `craft-mcp vector --live` | `vectorcraft-cli mcp --connect 127.0.0.1:7910` |
| `craft-mcp fig --live` | `figcraft-cli mcp --attach 127.0.0.1:7903` |
| `craft-mcp film --live` | `filmcraft-cli mcp --bridge 127.0.0.1:7904` |
| `craft-mcp photo --live` | `photocraft-cli mcp --bridge 127.0.0.1:7908 --control-token-file $CRAFT_HOME/photo.token` |

(`$J` = `$CRAFT_HOME/jobs`. The full table for all 21 cases is in `tests/expected_argv.txt`.)

- `--live`: the launcher first checks that the port is open. If it is closed, it exits
  with code 3 and `start the app with: craft-app <tool>`. All tools then fail the same
  way at startup.
- `--check <tool>`: exit 0 if the binary exists in `$CRAFT_HOME/bin` and is
  executable; otherwise exit 4 with `<tool>-cli not built: run make build TOOL=<tool>`.
  (The source review did not confirm a `--version` flag in every CLI.)

### `craft-app <tool>`

Starts the desktop app with `--control <port>`. For photocraft it first creates
`photo.token` (64 hex characters, mode 0600) and passes `--control-token-file`.
wordcraft writes its own key file; nothing to do.

### Agent files

Generated from `templates/agent.md.tmpl` and `tools.toml`. Example (shortened):

```markdown
---
name: craft-pdf
description: Edits PDF files with PdfCraft (merge, split, compress, forms, comments, redact). Use via /craft.
model: sonnet
tools: mcp__craft-pdf__*, Read
mcpServers:
  - craft-pdf:
      type: stdio
      command: craft-mcp
      args: ["pdf"]
hooks:
  PreToolUse:
    - matcher: "mcp__craft-.*|Read"
      hooks: [{ type: command, command: craft-guard }]
---
You work ONLY inside the job folder you are given: <job>/in (inputs), <job>/out (results).
1. Never open files whose name contains .env, or is credentials, .databrickscfg, .netrc.
2. Find a command with the server's list or search tool before you call it. Do not guess command ids.
3. Write results only to <job>/out. Never change <job>/in.
4. Check your result: render or inspect it and compare it with the task.
   One fix attempt; if it is still wrong, move it to <job>/out/_failed/ and say why.
5. If no command exists for the task, say so. Do not approximate it silently.
6. If a call is blocked by the hook, report it. Do not work around it.
7. Report: output paths, what you checked, what you could not do.
<tool notes from tools.toml>
```

The 10 agents with a live mode also get a second list entry `- <tool>-live:` with
`command: craft-mcp` and `args: ["<tool>", "--live"]` (`mcpServers` uses the list
form; the map form gave the subagent zero tools, verified 2026-10-14)
and the rule: "Use the live server only when the task says live. If it is not
reachable, tell the user `craft-app <tool>` and continue headless."

### The `/craft` skill

1. **Route.** A table maps file type and task to an agent (`.pdf` -> `craft-pdf`,
   `.xlsx/.csv` -> `craft-sheet`, `.svg/.ai/.eps` -> `craft-vector`, ...). If two
   agents fit, ask one question (single-image pixel edit -> `craft-photo`, many photos
   or raw development -> `craft-light`).
2. **Check.** `craft-mcp --check <tool>`. Stop with its message if it fails.
3. **Stage.** `craft-stage <job> <inputs>`.
4. **Hand over** to the agent: task, job folder, mode (headless unless the user says
   "live" or "show me").
5. **Report** the output paths and what the agent checked; offer `open <file>`.

A task that clearly needs two tools runs the agents one after another in the same job
folder. There is no general multi-tool planner.

### Build

`make build [TOOL=<tool>]` runs `cargo build --release -p <tool>-cli` in
`$ARTCRAFT_DIR/<repo>` and copies the binary to `$CRAFT_HOME/bin` only on success.
It refuses to build when the repository's current commit differs from
`$CRAFT_HOME/reviewed/<repo>`. That file is written after a `repo-install-safety-check`
review of that commit. Build scripts and proc macros run code during `cargo build`,
and the upstream repositories merge many community changes per day.

## Error handling

| Case | Behavior |
|---|---|
| Binary missing | `/craft` stops at step 2 with the `make build` hint; no agent starts. |
| Build fails | The previous binary stays in `$CRAFT_HOME/bin`. |
| New upstream commit | `make build` stops: run the safety check again. |
| Live app not running | Launcher exit 3 with the `craft-app` hint; agent continues headless. |
| Port used by another program | The connect error plus the hint to change `CRAFT_PORT_BASE`. |
| Server crash during a task | Agent reports the last command and `logs/<tool>.log`, retries once, then stops. `in/` is unchanged. |
| No command for the task | Agent reports it; no silent substitute. |
| Result fails its check | One fix; then `out/_failed/` and a report. Never reported as done. |
| Hook blocks a call | Agent reports the block; no workaround. |
| Job folders grow | `make clean-jobs DAYS=30`, only when the user runs it. |

## Verification

**`make test`** (no ArtCraft binaries needed):

- Generator drift: committed `agents/*.md` and `bin/tools.tsv` equal a fresh
  `make generate`.
- Launcher argv: fake `*-cli` scripts on `PATH` print their arguments. All 21 cases
  are compared with **hand-written** expected lines in `tests/expected_argv.txt`, not
  with lines derived from `tools.toml`.
- Live port check: closed port -> exit 3 and hint.
- `craft-stage`: refuses `.env`, `prod.env`, `credentials`, `.netrc`, `.databrickscfg`;
  refuses paths outside the read root, including a symlink that points outside;
  copies with `cp -c`.
- `craft-guard`: path in the job folder -> allowed; outside -> blocked;
  `jobs/x/../../..` -> blocked; symlink in `in/` pointing outside -> blocked; secret
  name -> blocked; a path inside a JSON-string parameter -> checked; non-path strings
  -> ignored; `Read` outside `$CRAFT_HOME` -> blocked.

**`make check`**: confidentiality search (see above) and `shellcheck` on `bin/`.

**`make smoke [TOOL=<tool>]`** (needs built binaries): a small Python MCP client starts
`craft-mcp <tool>`, sends `initialize` and `tools/list`, checks the core tools exist,
then runs one real command on a synthetic input created by the test (gridcraft:
`=SUM(1,2)` -> 3; pdfcraft: split a generated 2-page PDF; cadcraft: draw a circle,
export PNG). Tools that are not built are reported as skipped, not passed.

**Manual end-to-end** (checklist in the README, because it runs a model):

1. `/craft split sample.pdf into single pages` -> files in `out/`, agent states its check.
2. `/craft open <some folder>/.env` -> refused by `craft-stage` or `craft-guard`.
3. `/craft ... live` with the app closed -> `craft-app` hint, then headless.

## Open points

1. **Frontmatter hooks.** The Claude Code docs say a subagent file may declare
   `hooks`. Task 1 of the plan proves it with a test agent whose hook blocks a call.
   If it does not work, the hook moves to `~/.claude/settings.json` with matcher
   `mcp__craft-.*`, and `make install` merges it without changing other settings.
   Verified 2026-10-14: frontmatter hooks run in subagents (outcome A). A subagent
   file declares its own MCP server with the list form of `mcpServers`
   (`- craft-probe:` entries); the map form was run first and the subagent got zero
   tools, so use the list form.
2. **Per-tool notes** in `tools.toml` (supported formats, known gaps) are filled in
   while writing the smoke tests, from each tool's `docs/` folder.
3. **filmcraft `--data-dir`** and **designcraft/gridcraft `--sample`** are not used in
   the first version.
