---
name: statustable
description: Use when the user asks for a status table, a status overview, "where do we stand", "what is open", or a summary of all work in a long session that spans several repos, tickets, experiments, pipelines or conversations, and wants to see at a glance what is done, what runs, and what waits for them.
---

# Status table

One table holds the whole state of the session, grouped by workstream, with the
next actor in every row. Live facts are checked again before they go in.

## The reply is exactly three parts

1. **One header line:** `Status as of <date> <time> <timezone>. Checked just now: <systems>.`
   If nothing could be checked: `Checked just now: nothing; live rows show the time of the last check.`
2. **One Markdown table** with the columns `Workstream | Topic | State | Next step / who`.
3. **One line:** `Waiting for you: 1. <item> 2. <item> ...`, each item in at most six
   words and also a row in the table.

No second table, no separate list of decisions, no "not urgent" section.

## Filling the table

1. **Collect every item of the session**, done items included: code, pull requests,
   pipelines, jobs, experiments, documents, messages, ideas, decisions the user owes.
2. **Group by workstream**, a line of work the reader recognises: a repo or package,
   a ticket, an experiment series, a shared page, a chat. Sort by workstream, then
   topic. Bold the workstream name in its first row; leave the cell empty below it.
3. **Check live facts now.** Query each running system (CI, pull request, job,
   deploy, chat) before writing. If you cannot, the State cell says
   `running at 10:35, not checked since`.
4. **State starts with one marker**, then the fact with its number or name:
   ✅ done or green · 🔄 running · 🟡 open or in review · ⏸ paused at a manual step ·
   ⏳ not started · ❌ failed · 💡 idea, no ticket.
5. **Next step / who:** `me` (the agent can do it now without approval), `**you**`
   (the user decides or approves), a role (`reviewer`), or `—`.
6. **Open decisions are rows in their workstream**, with `**you**`.
7. **Every pull request and pipeline is a link** to its original page, in every
   cell where it appears: `[PR 12](<url>)`, `[build 88](<url>)`. Take the URL from
   the tool output or ask the host for it (`gh pr view 12 --json url`,
   `gh run view 88 --json url`, the `url` field of a Bitbucket or Jira API answer).
   Never build a URL from a guessed host, workspace or repo name. If no URL can be
   found, write `PR 12 (no link: URL not found)`.

Write in the user's language; keep the markers and column names.

## Example (synthetic)

Status as of 2026-03-04 14:05 UTC. Checked just now: CI, pull requests.

| Workstream | Topic | State | Next step / who |
|---|---|---|---|
| **Library `order-checks`** ([PR 12](https://git.example.com/acme/order-checks/pull/12)) | Code, tests | ✅ 12 checks, 40 tests pass | — |
| | CI | ✅ branch [build 88](https://ci.example.com/acme/order-checks/runs/88) green · ⏸ PR [build 89](https://ci.example.com/acme/order-checks/runs/89) at manual step (a few cents) | start it: **you** |
| | Branch vs main | 🟡 2 commits behind (docs only) | rebase: me, after your OK |
| | Decision: WARN counts as amber? | ⏳ open | **you** |
| **Experiments** | E7 choose early, check late | ✅ held on 3 of 3 datasets | — |
| | E8 | ⏳ planned, about 4 USD | go: **you** |
| **Shared results page** | "baseline always loses" | 🟡 wrong since E7; correction drafted | approve: **you** |

Waiting for you: 1. start PR build step 2. WARN as amber 3. go for E8 4. approve page correction

## Common mistakes

| Mistake | Fix |
|---|---|
| A second table for decisions | Decisions are rows in their workstream |
| Rows sorted by urgency | Sort by workstream; urgency shows in the waiting line |
| A pipeline state from an hour ago | Query it again, or write the time of the last check |
| "I can check it if you want" | Check it before writing |
| Done items left out | Keep them with ✅ |
| "PR 12" or "build 88" as plain text | Link it to the original page |
| A link built from a guessed URL pattern | Take the URL from the tool output, or write `no link: URL not found` |
