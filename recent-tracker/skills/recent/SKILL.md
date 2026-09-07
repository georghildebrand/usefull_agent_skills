---
description: Show recently edited objects (design docs, code, memory notes) tracked by the recent-tracker hook. Use when the user asks "what did I edit recently", "recent design docs", or invokes /recent.
---

# Recent edits

Read `~/.claude/recent-tracker/log.jsonl` (one JSON object per line:
`ts`, `category`, `ref`, optional `repo`, `remote`, `project`, `tool`).

Arguments: `$ARGUMENTS` may contain a number N (max entries per category,
default 10) and/or a category filter (`design-doc`, `code`, `memory-note`).

Steps:

1. If the log file does not exist or is empty, say so and stop.
2. Read the file (tail is fine for large files, e.g. last 2000 lines).
3. Deduplicate by `ref`: keep only the newest entry per ref.
4. Filter by category if one was given.
5. Sort newest first, take N per category.
6. Print grouped by category, design-doc first. Per line: date, `ref`
   (shorten home dir to `~`), and the repo name in brackets. If `remote`
   exists, derive the repo name from it and make the bracket a markdown
   link to the remote URL (convert `git@host:owner/repo.git` to
   `https://host/owner/repo`).
7. Memory-note entries have no repo; show `project` instead when present.

Keep the output compact — no commentary beyond the list.
