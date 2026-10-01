---
description: Show a weekly report of where Claude Code time goes — topics, correction and steering rates, and sessions that produced no change. Use when the user asks "where does my Claude time go", "weekly stats", "what do I spend time on", or invokes /usage-stats.
---

# Usage statistics

Reports on the user's own Claude Code transcripts. It reads
`~/.claude/projects/*/*.jsonl`, which Claude Code writes for every session, and
stores derived rows in a private database outside this repository.

## Commands

Scripts live in `${CLAUDE_PLUGIN_ROOT}/scripts`. Run them with `python3`; they
need only the standard library.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/extract.py"              # index new transcripts
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/classify.py" --dry-run   # cost estimate, calls nothing
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/classify.py"             # assign topics and prompt kinds
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py"               # previous completed week
```

`$ARGUMENTS` may contain:

| Argument | Effect |
|---|---|
| a week such as `2026-W36` | report that week |
| a number such as `4` | compare the last 4 completed weeks |
| `refresh` | run `extract.py` and `classify.py` before reporting |
| `cost` | run `classify.py --dry-run` only |

With no argument, run `extract.py` first (it takes about a second), then
`report.py` for the previous completed week. Print the table as it comes out;
do not reformat the columns.

## Reading the report

| Column | Meaning |
|---|---|
| `You` | active time in interactive sessions. A lower bound: pauses over 5 minutes are dropped, so time spent reading an answer is not counted. |
| `Backgrd` | active time of background jobs. Machine time, never added to `You`. |
| `Corr` | share of prompts that reject or fix the previous answer. High means the assistant misread a clear request. |
| `Steer` | share of prompts that change direction during the task. High means the goal was unclear when the session started. |
| `->Edit` | median number of prompts before the first file change. |

`Corr` and `Steer` need different fixes, so never add them together. A high
`Corr` points at how the assistant is being instructed. A high `Steer` points at
the first prompt of the session.

Every table prints its own data basis: how many sessions were found, how many
carry a topic, and how many prompts are labelled. A week that is only partly
classified must not be read as complete.

## First run

`classify.py` calls a model, so check the estimate first:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/classify.py" --dry-run
```

Sessions are classified in batches because one `claude -p` call carries a fixed
floor of roughly 19,000 input tokens whatever the prompt size. Batching ten
sessions per call cut a measured list price of about USD 0.04 per session to
about USD 0.004. Results are cached per session and never recomputed.

## When classification fails for every session

`classify.py` prints how many sessions could not be classified and stores the
last 800 characters of the failing command's stderr in the `runs` table:

```bash
sqlite3 ~/.claude/usage-stats/stats.db \
  "SELECT note FROM runs WHERE kind='classify' ORDER BY id DESC LIMIT 1"
```

The common cause is that `claude` on `PATH` is a wrapper rather than the
program itself. A wrapper that starts a sandbox has to write its own state, and
a nested call started from inside an already sandboxed session may be refused.
The stderr tail names the path it could not write.

Run the backfill with the real binary ahead of the wrapper on `PATH`:

```bash
PATH="$HOME/.local/bin:$PATH" python3 "${CLAUDE_PLUGIN_ROOT}/scripts/classify.py"
```

Check `command -v claude` first to confirm which one is being picked up. The
plugin resolves `claude` from `PATH` on purpose, so nothing needs changing on a
machine without such a wrapper.

## Configuration

`~/.claude/usage-stats/config.json`, created on demand:

```json
{
  "model": "claude-haiku-4-5-20251001",
  "batch_size": 10,
  "zero_output_token_threshold": 50000,
  "ticket_prefixes": ["PROJ", "OPS"],
  "topic_hints": ["billing", "infra", "data-pipeline"]
}
```

`topic_hints` steers topic naming so sessions on the same subject group
together instead of getting three similar names.

## Where files live

Every path the plugin writes resolves against `$CLAUDE_USAGE_STATS_HOME`,
default `~/.claude/usage-stats`:

| File | Content |
|---|---|
| `stats.db` | one row per session and per prompt |
| `config.json` | settings above |
| `weekly/<week>.md` | snapshot written by `report.py --write-snapshot` |

Nothing is written inside the plugin directory. The database holds the first 200
characters of each prompt and the snapshots name real repositories and topics,
so they stay out of version control. Assistant replies, tool results and file
contents are never stored.

`classify.py` runs from an empty scratch directory. Claude Code finds
`CLAUDE.md` by walking up from the working directory, and `--setting-sources ""`
does not stop that, so running from a project directory would send that
project's instructions on every call.
