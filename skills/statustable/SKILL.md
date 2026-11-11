---
name: statustable
description: Use when the user asks for a status table, a status overview, "where do we stand", "what is open", or a summary of all work in a long session that spans several repos, tickets, experiments, pipelines or conversations, and wants to see at a glance what is done, what runs, and what waits for them.
---

# Status table

One table holds the whole state of the session, grouped by workstream, with the
next actor in every row. Live facts are checked again before they go in.

## The reply has three parts, plus optional notes

1. **One header line:** `Status as of <date> <time> <timezone>. Checked just now: <systems>.`
   If nothing could be checked: `Checked just now: nothing; live rows show the time of the last check.`
2. **One Markdown table** with the columns `Workstream | Topic | Context | State | Next step / who`.
3. **Optional notes** between table and waiting line, only when a `**you**` row needs
   more than about 20 words (see rule 7). A short numbered list, at most 3 notes.
4. **One line:** `Waiting for you: 1. <item> 2. <item> ...`, each item in at most six
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
4. **Context says what and why**, in one or two short sentences (at most 30 words).
   A reader who missed the session must understand what is going on in this row.
   No internal jargon, hook names, tool names, masked strings or codes without a
   plain explanation. If something is blocked or failed, say in plain words what
   the blocker is, what it stops, and whether the cause is verified or a guess.
   First what the item is,
   then why it matters: the problem it solves, the risk it removes, or what depends
   on it. "Rounding fix for invoice totals. Totals were off by 1 cent, so the
   customer export failed." not "fix". Background facts that explain the state go
   here, not in State. Leave it empty only when the Topic already says everything.
5. **State starts with one marker**, then the fact with its number or name:
   ✅ done or green · 🔄 running · 🟡 open or in review · ⏸ paused at a manual step ·
   ⏳ not started · ❌ failed · 💡 idea, no ticket.
6. **Next step / who:** `me` (the agent can do it now without approval), `**you**`
   (the user decides or approves), a role (`reviewer`), or `—`.
7. **Every `**you**` row must be doable without asking back.** The Next step cell
   (or Context) names the concrete action and how to do it, in at most about 20
   words: the command, the link, or the exact reply to give. Say what each outcome
   means, and name a cheaper alternative if one exists. If this needs more, put a
   short numbered note below the table and write "see note 1" in the row. At most
   3 notes.
8. **Open decisions are rows in their workstream**, with `**you**`.
9. **Every pull request, pipeline and ticket is a link** to its original page, in
   every cell where it appears: `[PR 12](<url>)`, `[build 88](<url>)`,
   `[ABC-123](<url>)`. Take the URL from the tool output or ask the host for it
   (`gh pr view 12 --json url`, `gh run view 88 --json url`, `gh issue view 7 --json url`,
   the `url` field of a Bitbucket API answer). A Jira API answer gives only the REST
   URL in `self`; for the browser link use `<site>/browse/<KEY>`, with the site taken
   from the same answer or from the CLI profile that fetched the ticket. Never build
   a URL from a guessed host, site, workspace or repo name. Never leave a ticket key
   as plain text: some hosts turn a bare key into a link to the wrong Jira site. If
   no URL can be found, write `PR 12 (no link: URL not found)`.
10. **Every git worktree is a link** to its directory, in every cell where it
   appears, so the user can click it and open the directory. Link text and target
   are both the full absolute path: `[/home/dev/worktrees/app/fix-x](/home/dev/worktrees/app/fix-x)`.
   If the path contains spaces, put the target in angle brackets:
   `[/a b/c](</a b/c>)`. Take the path from `git worktree list` or from the
   command that created the worktree. Never shorten it to the branch name, `~`
   or a relative path.

Write in the user's language; keep the markers and column names.

## Example (synthetic)

Status as of 2026-03-04 14:05 UTC. Checked just now: CI, pull requests.

| Workstream | Topic | Context | State | Next step / who |
|---|---|---|---|---|
| **Library `order-checks`** ([PR 12](https://git.example.com/acme/order-checks/pull/12)) | Code, tests | New checks that reject orders with negative totals | ✅ 12 checks, 40 tests pass | — |
| | CI | PR pipeline has a paid manual integration step | ✅ branch [build 88](https://ci.example.com/acme/order-checks/runs/88) green · ⏸ PR [build 89](https://ci.example.com/acme/order-checks/runs/89) at manual step (a few cents) | start it: **you**, see note 1 |
| | Branch vs main | Main moved while the PR was open | 🟡 2 commits behind (docs only), worktree [/home/dev/worktrees/order-checks/fix-rounding](/home/dev/worktrees/order-checks/fix-rounding) | rebase: me, after your OK |
| | Decision: WARN counts as amber? | Decides whether warnings block the release dashboard | ⏳ open, asked in [ABC-123](https://jira.example.com/browse/ABC-123) | **you**: reply "amber" or "red" in the ticket |
| **Experiments** | E7 choose early, check late | Tests if picking the model before the holdout check holds up | ✅ held on 3 of 3 datasets | — |
| | E8 | Same test on the large dataset | ⏳ planned, about 4 USD | go: **you** |
| **Shared results page** | "baseline always loses" | Team page claim that E7 disproved | 🟡 wrong since E7; correction drafted | approve: **you** |

Notes:
1. Open [build 89](https://ci.example.com/acme/order-checks/runs/89) and press "Run" on the integration step. It costs a few cents. Green means the PR can merge. Red means the agent reads the log and reports. Or skip it: the same checks already passed on the branch in build 88.

Waiting for you: 1. start PR build step 2. WARN as amber 3. go for E8 4. approve page correction

## Common mistakes

| Mistake | Fix |
|---|---|
| A second table for decisions | Decisions are rows in their workstream |
| Rows sorted by urgency | Sort by workstream; urgency shows in the waiting line |
| A pipeline state from an hour ago | Query it again, or write the time of the last check |
| "I can check it if you want" | Check it before writing |
| Done items left out | Keep them with ✅ |
| Context repeats the Topic ("CI: the CI") or explains the state | Context says what the item is and why it exists; the state goes in State |
| "PR 12", "build 88" or "ABC-123" as plain text | Link it to the original page |
| A link built from a guessed URL pattern | Take the URL from the tool output, or write `no link: URL not found` |
| A `**you**` step such as "check lines" that does not say what to check, how, or what the result means | Name the action, the command or link, and what each outcome means; add a numbered note if it needs more than about 20 words |
| Context with a hook name, masked string or code the reader never saw ("blocked by X hook, match pro****ET!") | Say in plain words what blocked what, why it matters, and whether the cause is verified |
| Worktree named only by branch, or as plain text | Link the full absolute path from `git worktree list` |
