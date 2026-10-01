# Design: `usage-stats` plugin

Date: 2026-09-08
Status: approved, implementation in progress

## Problem

A Claude Code user wants to know where their time goes: which topics they spend
the most effort on, and where effort produces nothing. They also want to see what
kinds of prompts they write, so they can judge whether unclear prompts are causing
long sessions.

## Key finding: the data already exists

Claude Code writes a full transcript of every session to
`~/.claude/projects/<project-slug>/<session-id>.jsonl`. One JSON object per line.
No logging hook is needed. The relevant record types and fields:

| Record `type` | Fields used |
|---|---|
| `user` | `timestamp`, `message.content`, `cwd`, `gitBranch`, `sessionKind`, `isMeta`, `isSidechain` |
| `assistant` | `timestamp`, `message.usage` (input/output/cache tokens), `message.model`, `message.content[].tool_use.name` |
| `ai-title` | `aiTitle` — a session title Claude Code generates itself |

`sessionKind` is `bg` for background jobs and absent for interactive sessions.
`isSidechain` marks subagent traffic.

Because the transcripts are the source of truth, the plugin only reads them. It
never writes into `~/.claude/projects/`.

## Non-goal: a `SessionEnd` hook

A hook that queues each finished transcript was considered and rejected. A weekly
run can list every transcript file and compare `mtime` against the last run in
under a second. The hook would add a component and per-session latency without
changing any result. If transcripts are ever rotated or deleted faster than the
weekly cadence, revisit this.

## Confidentiality boundary

This plugin lives in a public repository. The `skill-confidentiality-boundary`
rules apply. The design enforces them structurally, not by convention:

**Every runtime output path resolves against a single base directory**, taken from
`$CLAUDE_USAGE_STATS_HOME` and defaulting to `~/.claude/usage-stats`. No code path
writes anywhere inside the repository. This is a property, not a list of ignored
filenames — a `.gitignore` entry naming `stats.db` would miss the weekly snapshots,
the config file, and any later export.

| Artifact | Location | Reason |
|---|---|---|
| `stats.db` | `$CLAUDE_USAGE_STATS_HOME/stats.db` | holds up to 200 characters of each real prompt |
| `weekly/<ISO-week>.md` | `$CLAUDE_USAGE_STATS_HOME/weekly/` | topic and repository names from real work |
| `config.json` | `$CLAUDE_USAGE_STATS_HOME/config.json` | ticket prefixes and topic hints are organisation-specific |
| test fixtures | `usage-stats/tests/fixtures/` | **hand-written synthetic transcripts only**; copying a real transcript would publish real prompts |
| examples in docs | repository | invented topics such as `payment-api`, `infra-terraform` |

No `.gitignore` entry is added. An earlier draft planned one as a second
layer, but `connect()` refuses to open the database when the state directory
lies inside a git working tree, which covers every file the plugin writes
including ones added later. A `.gitignore` line would protect only the
filenames it happens to mention and would suggest a guarantee it does not
give.

The classifier changes to an empty working directory before calling the model.
Claude Code discovers `CLAUDE.md` by walking up from the current directory, and
`--setting-sources ""` does not suppress that. Without the directory change, a
user's project instructions would be sent on every classification call.

## Architecture

```
~/.claude/projects/*/*.jsonl        read-only source
        |  files with mtime newer than the last run
        v
   extract.py     JSONL -> rows. Pure Python, no network.
        |
        v
   stats.db       sessions / prompts / classifications / runs
        |  sessions with no classification row
        v
   classify.py    the only component that calls a model
        |
        v
   signals.py     pure functions over rows, no I/O
        |
        v
   report.py      terminal table   <-- /usage-stats
```

Five components, each testable alone. Only `classify.py` touches the network.
Only `extract.py` reads transcripts. Only `report.py` formats output.

Standard library only (`sqlite3`, `json`, `argparse`, `subprocess`). No install step.

## Schema

```sql
CREATE TABLE sessions (
  session_id TEXT PRIMARY KEY,
  transcript_path TEXT NOT NULL,
  transcript_mtime REAL NOT NULL,   -- re-extract when the file grows
  project_slug TEXT,
  cwd TEXT,
  repo TEXT,                        -- last path segment of cwd
  git_branch TEXT,
  session_kind TEXT,                -- 'bg' or 'interactive'
  is_sidechain INTEGER,
  ai_title TEXT,
  started_at TEXT, ended_at TEXT,
  wall_seconds REAL,                -- last timestamp minus first
  active_seconds REAL,              -- sum of gaps <= IDLE_GAP_SECONDS
  n_user_prompts INTEGER, n_assistant INTEGER,
  tokens_in INTEGER, tokens_out INTEGER,
  tokens_cache_read INTEGER, tokens_cache_write INTEGER,
  models TEXT,
  n_tool_calls INTEGER, n_edit INTEGER, n_write INTEGER,
  n_bash INTEGER, n_commits INTEGER, n_claude_questions INTEGER,
  first_edit_turn INTEGER,          -- NULL when no edit ever happened
  indexed_at TEXT
);

CREATE TABLE prompts (
  session_id TEXT NOT NULL,
  turn INTEGER NOT NULL,            -- 1-based index of this user prompt
  ts TEXT, chars INTEGER,
  text_head TEXT,                   -- first 200 characters, nothing more
  kind TEXT,                        -- NULL until classify.py fills it
  PRIMARY KEY (session_id, turn)
);

CREATE TABLE classifications (
  session_id TEXT PRIMARY KEY,
  topic TEXT, model TEXT, classified_at TEXT,
  batch_tokens_in INTEGER, batch_tokens_out INTEGER
);

CREATE TABLE runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT, finished_at TEXT, kind TEXT,
  files_scanned INTEGER, sessions_indexed INTEGER,
  sessions_classified INTEGER, calls INTEGER, cost_usd REAL, note TEXT
);
```

`active_seconds` uses `IDLE_GAP_SECONDS = 300`. Gaps longer than five minutes
between consecutive records are treated as the user being away and are not
counted. Wall time is kept as well, so the two can be compared.

Only real user prompts enter `prompts`. Records with `isMeta` set, records whose
content is a tool result, and hook-injected content are skipped.

## What is stored from a prompt

The first 200 characters, and nothing else. Assistant text, tool results, and file
contents never enter the database. This keeps the database small and limits what a
classification call can leak.

## Classification

One model call per **batch of sessions**, not per session. Measured on 2026-09-08:
a single `claude -p` call carries a fixed floor of about 19,000 input tokens
because Claude Code always ships its base system prompt. Disabling tools, MCP
servers and setting sources reduced 38,700 tokens to 18,900 — it does not remove
the floor. Per-session calls would therefore cost about USD 0.04 each regardless of
how short the actual input is.

Batching 10 sessions per call spreads that fixed cost across ten sessions. For 270
sessions this is 27 calls instead of 270.

Call shape:

```
claude -p <batch prompt> \
  --model claude-haiku-4-5-20251001 \
  --strict-mcp-config --setting-sources "" --allowed-tools "" \
  --no-session-persistence --output-format json
```
run with the working directory set to an empty scratch directory.

Input per session in the batch: repository name, `ai_title`, and each prompt's
`turn` with its `text_head`. Output: strict JSON, one object per session, with a
topic and one kind per turn.

Prompt kinds:

| Kind | Meaning |
|---|---|
| `task` | a new request for work |
| `correction` | rejects or fixes the previous answer |
| `steer` | changes direction or scope during the task |
| `clarify_answer` | answers a question the assistant asked |
| `info_request` | a question only, no change wanted |
| `meta` | about the assistant, tooling, or permissions |

Detecting `correction` with a keyword list is explicitly rejected. A list such as
`{"no", "wrong", "again"}` matches "that is wrong" and misses "hm, actually I meant
something else", and every phrasing in another language. The property to test is
*does this prompt reject or redirect the previous answer* — a model can judge that,
a pattern cannot. A regular expression is used only for a pre-classification
estimate, and any figure derived from it is labelled a lower bound.

Results are keyed by `session_id` and never recomputed. `--dry-run` prints the
planned call count and an estimated cost without calling the model. `--reset`
drops every topic and kind so a changed instruction or changed `topic_hints`
takes effect.

**Topics fragment unless earlier choices are fed back.** The first backfill
produced `systemgraph-development` and `system-graph-testing` as separate
topics for the same subject, and three names for work on one tool: 30 topics
across about 110 sessions, with no group large enough to report. Each batch is
its own call and cannot see what the other batches chose.

Two changes fix it. Each batch is shown the topics already assigned, capped at
the 40 most used, and told to reuse an existing name when the subject matches.
Sessions are classified oldest first, so the vocabulary grows as work proceeds;
newest first would classify the most recent week — the one most likely to be
reported — against an empty vocabulary.

Failure handling: a batch whose output does not parse is retried once at half the
batch size, then skipped and recorded in `runs.note`. Unclassified sessions still
appear in the report under `topic = NULL`.

## Signals

Derived by `signals.py` from rows only.

| Signal | Definition |
|---|---|
| `correction_ratio` | `correction` prompts divided by classified prompts, per topic |
| `steer_ratio` | `steer` prompts divided by classified prompts, per topic |
| `turns_to_first_edit` | median `first_edit_turn` per topic; sessions without an edit are excluded and counted separately |
| `zero_output_sessions` | `tokens_out > 50000` and `n_edit + n_write = 0` and `n_commits = 0` |
| distribution | sessions, active time, wall time, output tokens per topic, repository, model, and `session_kind` |

`correction_ratio` and `steer_ratio` answer different questions. A high correction
ratio means the assistant misread a clear request. A high steer ratio means the
request was not clear when the session started. The two call for different fixes,
so they are reported separately rather than summed.

## Report

`/usage-stats` renders a terminal table for a week. Default week is the previous
completed ISO week. `--weeks N` compares several weeks. `--week 2026-W36` selects
one. Every table prints its own data basis: how many sessions were found and how
many carry a topic, so a partly classified week cannot be misread as complete.

## Weekly run

A cron entry on Friday at 18:00 local time runs, in order: `extract.py`,
`classify.py`, `report.py --write-snapshot`. The snapshot is written to
`$CLAUDE_USAGE_STATS_HOME/weekly/<ISO-week>.md`.

## Verification

1. `extract.py` against a synthetic fixture -> counts match values asserted in the test
2. `extract.py` across all transcripts -> completes without error, row counts plausible
3. `signals.py` unit tests on synthetic rows -> each signal returns the expected value
4. `classify.py --dry-run` -> printed call count and cost estimate match the batch size
5. one real batch -> output parses, topics readable, measured cost within a factor of two of the estimate
6. `report.py` -> figures reconcile against a hand-written SQL query
7. cron entry triggered once by hand -> snapshot file appears

Results, 2026-09-08:

| Step | Outcome |
|---|---|
| 1, 3 | 14 tests pass against the synthetic fixture |
| 2 | 270 transcripts, 233 MB, indexed in 1.6 seconds |
| 4 | 20 calls for 196 sessions; the first estimate of USD 0.58 was three times too low, see below |
| 5 | full backfill: 195 of 195 sessions in 20 calls for USD 1.83 |
| 6 | all 7 reported figures for one week match plain SQL |
| 7 | snapshot written; the cron entry itself is not installed yet |

The estimate failed its own factor-of-two criterion and was corrected against
the measured run. Output, not input, drives the cost: about 1,400 output tokens
per session including thinking tokens, billed at five times the input price.
The first estimator counted only the JSON the model returns.

Two limits found during the backfill:

- **Label coverage.** One week labelled 208 of 499 prompts. 199 prompts sat
  beyond the per-session cap of 40, and the model returned no kind for another
  92 inside the cap. Both causes sit late in a session, and late prompts are
  the ones more likely to be corrections, so `correction_ratio` and
  `steer_ratio` are floors. The report states the coverage and says so when it
  falls below 80 percent. A fix would sample prompts across the whole session
  instead of taking the first 40.
- **A wrapper around `claude` can break every call.** If `claude` on `PATH`
  starts a sandbox, a nested call from inside an already sandboxed session may
  be refused and every session fails. The stored stderr tail names the path
  that could not be written.

Step 7 is incomplete: `crontab -` was refused with "Operation not permitted"
under the sandbox that ran the build, so the schedule must be installed by the
user. On macOS a cron-started process does not inherit Full Disk Access, so it
can fail to read `~/.claude` silently. `weekly.sh` therefore logs every run,
and the first scheduled run must be checked in that log rather than assumed to
have worked.

## Open points

- Backfill covers the last 8 weeks by decision. A `--since` flag allows extending it later.
- Cost figures reported by `claude -p` are list prices. On a subscription no
  per-token charge appears; the calls consume usage limits instead. Both are stated
  when the tool prints an estimate.
