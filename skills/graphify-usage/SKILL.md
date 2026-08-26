---
name: graphify-usage
description: >
  Use graphify to build and refresh a local AST-based knowledge graph for a
  repository (code structure, community clusters, navigable graph.html).
  Use when onboarding to an unfamiliar/large repo, or when deciding how to
  keep a repo's graph current without touching git hooks.
---

# graphify-usage — Local Repo Knowledge Graph

`graphify` (PyPI package `graphifyy` — note the double `y`, plain `graphify`
is a different project) builds a queryable knowledge graph of a codebase via
tree-sitter AST parsing. Deterministic, no LLM needed for code. Optional
semantic pass (LLM) covers docs/PDF/image files only.

## What it's good for

- Fast orientation in one large/unfamiliar repo: `graph.html`, community
  clusters, `graphify explain "<node>"`, `graphify god-nodes`.
- Local dev-loop navigation aid, not a replacement for architecture docs.

## What it is NOT good for

- Cross-repo data contracts (e.g. repo A writes a table, repo B reads it via
  Spark/S3). This is a **structural code graph** — it has no notion of
  runtime data flow through external storage. `graphify merge-graphs` only
  concatenates two graphs; it does not discover new cross-repo edges.
  Measured on a real dbt-producer / Spark-consumer pair: the graphs gave
  **zero** cross-repo signal. The only bridge was prose — literal repo names
  mentioned in the consumer's own docstrings and test names. That is luck,
  not capability.
- **dbt lineage.** Even with the SQL grammar installed, `ref()` / `source()`
  are Jinja, not SQL, so tree-sitter never resolves them. Measured on a
  97-file dbt project: 52 nodes came from `.sql` files and **0 edges touched
  any of them** — the whole model-to-model DAG (staging -> intermediate ->
  mart layers) stayed invisible. Use `dbt ls` / `dbt docs` / the dbt manifest
  for lineage instead.
- **Which third-party library a module uses.** Only in-repo functions and
  classes are extracted; there are no import nodes for external packages.
  A plain `grep -rlE 'import (pkg_a|pkg_b)'` answers that faster than any
  graph query.
- For that class of problem, look at data-lineage tooling (OpenLineage,
  dbt-native lineage) or a multi-repo semantic-search tool (e.g. Sourcegraph),
  not graphify.

## Two extraction modes

| Mode | Command | LLM used | Cost |
|---|---|---|---|
| Code-only | `graphify . --code-only` | No | Free, fast |
| Full (docs+code) | `graphify . --backend <name>` | Yes, on doc/PDF/image files only | Depends on backend |

Community naming (`cluster-only` / `label`) always needs a small LLM call
regardless of mode — it just names already-computed clusters, cheap either way.

## Using your local Claude Code / Codex CLI subscription as the backend

No API key needed — `--backend claude-cli` shells out to your already
authenticated local CLI session instead of hitting a metered API.

```bash
GRAPHIFY_CLAUDE_CLI_MODEL=haiku graphify . --backend claude-cli
GRAPHIFY_CLAUDE_CLI_MODEL=haiku graphify cluster-only . --backend claude-cli
```

Set `GRAPHIFY_CLAUDE_CLI_MODEL` — default is Opus, which is overkill for the
structured extraction task and burns budget fast. Use `haiku` or `sonnet`.

## Language extras

Core install misses some tree-sitter grammars. Install as needed per repo
content, then delete `graphify-out/` and re-run — the incremental cache
does not detect "grammar became available", only file changes:

```bash
pip install "graphifyy[sql]"        # dbt / .sql-heavy repos — see caveat below
pip install "graphifyy[terraform]"  # .tf / .hcl repos
```

Measured effect of the SQL extra on a 97-file dbt project: node
coverage went from 90 nodes / 29 edges to **1051 nodes / 1001 edges**, so the
`.sql` files finally appear at all. But every one of those new edges is still
in shell scripts or JSON — the SQL nodes remain edgeless (see "NOT good for").
Worth installing for file-level coverage; do not expect model lineage.
Lock/seed JSON also dominates the edge count afterwards — consider excluding
lock files.

## Keeping the graph current

Prefer **not** using `graphify install` (writes git hooks — post-commit/
checkout rebuilds slow down every git operation). Instead use a plain script
run manually or on a schedule (cron/launchd), outside the repo so it never
touches git state:

```bash
#!/bin/bash
set -euo pipefail
GRAPHIFY_BIN="/path/to/graphify/.venv/bin/graphify"
REPO_PATH="${1:?usage: $0 <repo-path> [--semantic]}"
MODE="${2:---code-only}"
cd "$REPO_PATH"
if [ "$MODE" = "--semantic" ]; then
  GRAPHIFY_CLAUDE_CLI_MODEL=haiku "$GRAPHIFY_BIN" . --backend claude-cli
  GRAPHIFY_CLAUDE_CLI_MODEL=haiku "$GRAPHIFY_BIN" cluster-only . --backend claude-cli
else
  "$GRAPHIFY_BIN" . --code-only
  GRAPHIFY_CLAUDE_CLI_MODEL=haiku "$GRAPHIFY_BIN" cluster-only . --backend claude-cli
fi
```

Wrap that per-repo call in a loop script and trigger weekly via launchd
(macOS) or cron — code-only runs are free/fast enough for frequent use;
gate the `--semantic` doc pass to a slower cadence since it costs LLM calls.

## Install / security note

Ran a full security review (bandit/pip-audit clean, no telemetry, no eval/
exec/pickle on untrusted input, no hardcoded secrets) before adopting. One
real finding worth keeping in mind: the semantic pass auto-detects a backend
from whatever API key env var is set (priority order includes a China-hosted
provider before Anthropic/OpenAI) if you don't pass `--backend` explicitly —
always pass `--backend` explicitly on docs-heavy repos to avoid an
unintended provider getting your file content.
