---
name: close-pr
description: Use when the user wants to close out a finished PR (`/close-pr`, "close this PR", "merge and clean up"). Takes an author-side PR from "implementation done" to "merged + archived" — runs format and pre-commit on changed files, pushes, polls CI and approvals in parallel, stops before irreversible merge on manual-merge repos, handles auto-merge repos via comment+approve, cleans up branches with per-branch remote-delete confirmation, transitions the linked ticket, and commits a memory episode.
---

# /close-pr — Author-side PR Close

## When to invoke

- User types `/close-pr` (with no argument, derive PR from cwd) or `/close-pr <pr-url-or-id>`
- User says "close this PR", "merge and clean up", "finish the PR", or similar
- Skip if the PR is not yet code-complete — the user should finish their work first

Optional flag: `--dry-run` skips all writes and prints intended commands instead.

## What it does

Eight phases. Each is one agent dispatch (Phase 3 is a parallel barrier of four agents).

1. **Detect** — repo + branch + PR id from cwd, ticket id from branch name or PR title, repo policy classification (auto-merge vs manual)
2. **Local-ready** — formatter, scoped pre-commit, push if local ahead, stop on dirty tree
3. **Remote-poll** (parallel) — CI status, approvals + missing reviewers, mergeability, ticket status
4. **Decision gate** — STOP if CI red, conflicts, missing approvals, or unresolved review threads
5. **Merge** — auto-merge repo: comment + approve + verify state. Manual repo: STOP, print the merge command.
6. **Cleanup** — local branch delete; remote branch delete prompts per-branch
7. **Ticket transition** — extract ticket id, transition via tracker CLI, fall back to suggested command if ambiguous
8. **Memory commit + handoff** — write a per-PR memory episode, print `Merge landed. To follow the deploy pipeline, run /post-merge-validation`

Full design: see `DESIGN.md` in this directory.

## Configuration (private instance)

This file is the generic public reference. For your own use:

1. Copy this skill to `~/.claude/skills/close-pr/SKILL.md`
2. Copy `close-pr.example.js` to `~/.claude/workflows/close-pr.js`
3. In your private workflow, replace every `<PLACEHOLDER>` with your concrete value:
   - `<PLATFORM_CLI>` — your git platform CLI (e.g. the binary you use to talk to Bitbucket / GitHub / GitLab)
   - `<WORKSPACE>` and `<PROFILE>` — any flags your CLI needs to scope to your workspace/org
   - `<TICKET_PREFIX>` — the regex prefix for tickets in your tracker (e.g. `(?:ABC|DEF)`)
   - `<TRACKER_BASE_URL>` — full tracker URL prefix for cross-tenant explicit links
   - `REPO_POLICY` — your auto-merge repo list

## How Claude invokes this skill

When the user triggers this skill, dispatch the workflow:

```javascript
Workflow({
  name: 'close-pr',                          // private workflow registered name
  args: {
    pr: <arg-or-null>,                       // from slash command argument
    dryRun: <--dry-run-flag>                 // false unless flag present
  }
})
```

Then summarize the workflow's return value for the user: which phase it reached, what stopped it (if anything), what to do next.

## Safety rails (non-configurable)

- Never bulk-delete remote branches
- Never `--no-verify`
- Never `pre-commit --all-files`
- Always `git -C <path>` (no `cd && git`)
- Split compound bash; no `$(cmd)` inside larger strings
- Issue-tracker links use full URL form: `[ABC-123](https://tracker.example/browse/ABC-123)`
- Doc-only repos: stop at Phase 2 and surface the diff (never auto-commit)
- Auto-merge repo writes always followed by a verifying `pr get`
- Dry-run skips merge, ticket transition, and memory commit

## Failure UX

Every hard stop prints three things: **why** stopped, **next command** to run, **resume hint**.
