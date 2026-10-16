# craft-agent

`/craft` plus 12 Claude Code subagents that edit files with the
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
| `craft-effect` | EffectCraft | `effect` | After Effects |

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
5. Some ArtCraft repositories ship a `.mcp.json` (FilmCraft and EffectCraft at the
   time of writing). Claude Code started inside such a folder offers to run those
   servers, and one of them runs `cargo run`, which builds the code without the
   review gate. Do not start Claude Code inside the ArtCraft folders. To block
   these servers by name, add them to `~/.claude/settings.json`:
   `"disabledMcpjsonServers": ["filmcraft", "filmcraft-headless", "effectcraft", "effectcraft-app"]`
   and set `"enableAllProjectMcpServers": false`.
6. Start a new Claude Code session, so it loads the agents.

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

- The ArtCraft tools are given only copies in `jobs/`. Files that a document links
  to (see Limits) are opened by the tool itself and are not checked.
- `craft-stage` copies only from inside `CRAFT_READ_ROOT`, and refuses secret
  file names: any name that contains `.env`, and `credentials`, `.databrickscfg`,
  `.netrc`.
- `craft-guard` checks every string in a tool call that looks like a path: it
  starts with `/`, `~`, `./`, `../` or `file:`, or it contains `/`. It also checks
  every word inside a string that starts with `/`, `~` or `file:` (words are split
  at spaces and at ``' " ` [ ] ( ) , ; = ! < > |``), and plain names that exist in
  `jobs/`. Strings that hold JSON are parsed and checked too. `Read` may open only
  files in `jobs/` and `logs/`.
- Start a desktop app for live mode only with `craft-app <tool>`: it starts the
  app in `jobs/`, and the guard resolves relative paths against `jobs/`.

### Limits

- Six tools have no folder limit of their own: cadcraft, designcraft, figcraft,
  filmcraft, gridcraft, lightcraft. For them, `craft-guard` is the only check.
- In live mode, no tool has a folder limit of its own. The desktop app may also
  use folders from its own settings (recent files, default export folder). The
  hook cannot see those.
- The hook also blocks normal text that contains `.env` or `../`, a word that
  starts with `/` or `~` (for example "about ~5 pages"), and a call with more than
  5000 strings. Rephrase the task in that case.
- A new output path in `jobs/` is blocked when one of the split characters above
  stands directly before a `/` in it, for example `out/Photos (2024)/a.jpg`. Use
  simple output names.
- Correctly percent-encoded `file://` URLs are blocked. Pass plain paths.
- `craft-stage` does not detect hard links.
- Inside a longer text, `craft-guard` checks only the words that start with `/`,
  `~` or `file:`. A relative word such as `in/photo.jpg` in "open in/photo.jpg" is
  not checked on its own. It can only reach outside `jobs/` through a symlink in
  `jobs/`, and `craft-stage` copies no symlinks.
- Paths stored inside documents are not checked: linked images in IDML and DOCX
  files, external references (xrefs) in CAD drawings, media in film projects,
  `href` links in SVG files. The tool opens these files itself, and the hook never
  sees the paths. The agents are told not to follow such links and to report
  them.
- `craft-guard` does not check `http://` or `https://` URLs. A tool that fetches
  URLs could send data out of this machine.
- Claude Code lets a tool call through when a hook times out or cannot start.
  `craft-mcp` refuses to start when `craft-guard` is not on `PATH`, and the guard
  blocks a call when its checks take more than 20 seconds.
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
