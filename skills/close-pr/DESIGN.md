# `/close-pr` — Author-side PR Close Workflow (Design)

**Date:** 2026-06-23
**Status:** Draft — pending implementation
**Audience:** Skill author + future maintainers

## Goal

A slash command `/close-pr` that takes an author's PR from "implementation done" to "merged + archived" deterministically, with hard stops at every irreversible action and explicit handling for repos with auto-merge policies.

## Non-goals

- Reviewing someone else's PR (separate skill / pattern).
- Sweeping stale PRs across repos (separate skill / pattern).
- Implementing changes inside the PR. The PR is assumed code-complete.
- Replacing CI or human reviewers. The workflow waits for both.

## Why a workflow, not a single agent prompt

PR closure is a pipeline with mixed dependencies:

- **Sequential**: detection → local readiness → merge → cleanup → memory.
- **Parallelizable**: CI status, approval roster, mergeability, ticket fetch are independent signals; collecting them in parallel cuts wall-clock.
- **Hard gates**: every step has an early-exit condition (CI red, missing approvals, conflicts, dirty tree).

A deterministic workflow keeps phases isolated, makes failures legible, and avoids the silent-step-skipping that happens when a single agent juggles many constraints in one prompt.

## Surface

- Slash command: `/close-pr [pr-url-or-id]`
- Backed by a skill: `skills/close-pr/SKILL.md`
- Skill body dispatches a workflow script (`close-pr.example.js` in this repo as reference; user customizes to their environment).
- Argument is optional. With no argument the workflow auto-detects from the current working directory (git remote + current branch + PR API lookup).
- Optional `--dry-run` flag on the slash command sets `args.dryRun = true` on the workflow; the workflow skips all writes and prints intended commands instead.

## Phases

| # | Phase | Action | Hard-stop on fail |
|---|-------|--------|-------------------|
| 1 | Detect | cwd → git remote → repo platform → branch → PR id. Extract ticket id from branch name or PR title. Classify repo: auto-merge policy vs manual merge. | Yes (no PR found → abort) |
| 2 | Local ready | Run the repo's formatter (e.g. `make format`, `npm run format`, `cargo fmt` — discover by inspecting Makefile / package.json / equivalent). Run pre-commit hooks scoped to *changed files only* (never `--all-files`). Push if local is ahead of remote. Dirty working tree → stop and surface diff. | Yes |
| 3 | Remote poll *(parallel)* | Concurrent fetch: CI status, approval count + missing reviewers, mergeable flag, ticket status. | No — collect all signals before deciding |
| 4 | Decision | Apply rules: CI must be green, no conflicts, required approvals met, no unresolved review threads. Any failure → STOP with actionable next step. | Yes |
| 5 | Merge | Auto-merge repo: post review comment with explicit issue-tracker link → approve → verify state with a final `pr get`. Manual repo: STOP, print the exact merge command for the user to run. | Hard stop on manual repos |
| 6 | Cleanup | Delete local branch automatically after merge. Remote branch deletion is **per-branch confirmed**, never bulk. | No |
| 7 | Ticket transition | Resolve ticket transition (e.g. `In Review` → `Done`). Execute. If transition is ambiguous, print the suggested CLI command instead of guessing. | No |
| 8 | Memory commit + handoff | Write an episode to the project memory system, marked as an explicit per-PR commit. Populate `repos`, `tags`, `related_keys` so the item is retrievable. Print a one-line suggestion: `Merge landed on main. To follow the deploy pipeline, run /post-merge-validation`. | No |

Phase 3 is the only place a barrier (`parallel` with `await all`) is justified: the decision in Phase 4 needs every signal at once. All other phases use pipeline-style sequencing.

## Safety rails

Rails are non-configurable. Each one traces to a principle worth keeping even on a fast day.

| Rail | Behavior |
|------|----------|
| Never bulk-delete remote branches | Phase 6 prompts per branch. No `--force`, no batch. |
| Never skip hooks | Phase 2 fails closed. No `--no-verify`. |
| Pre-commit scope = changed files | Never `--all-files`; CI handles whole-repo runs. |
| Issue-tracker links explicit | All review comments and tracker writes use the full URL (e.g. `[ABC-123](https://tracker.example/browse/ABC-123)`) — cross-tenant link auto-resolution is unreliable. |
| No auto-commit in doc / architecture repos | Phase 2 detects doc-only repos and stops, surfacing diff. |
| Path-safe shell | Use `git -C <path>` instead of `cd && git`. Split compound commands into discrete tool calls instead of `$(cmd)` capture inside larger bash strings. Reason: unattended Claude Code sessions block on shell-approval prompts triggered by `cd` and `$(cmd)` in compound commands, hanging the workflow indefinitely. |
| Verify auto-merge state after writes | Phase 5 always re-fetches PR state after comment + approve so the workflow can report the final outcome. |
| Hard-fail decision gate | CI red, mergeable false, approvals short, or unresolved threads → STOP with actionable next step. No silent retries. |
| Dry-run flag honored | `args.dryRun` skips merge, ticket transition, memory commit, and prints intended commands instead. |

## Repo policy registry

Some repositories auto-merge on the Nth approval; the workflow must comment + approve rather than calling a merge endpoint. Other repositories require an explicit merge call from the author.

Keep a small inline table at the top of the workflow script:

```javascript
const REPO_POLICY = [
  // { repo: 'owner/name', mergeMode: 'auto'|'manual', requiredApprovals: <int> }
  // populate per environment
]
```

Default policy when a repo is not in the table: `mergeMode: 'manual'`, `requiredApprovals: 1`. The user is expected to extend the table as they discover auto-merge repos.

## Argument contract

| Arg | Type | Default | Meaning |
|-----|------|---------|---------|
| `pr` | string or null | null | PR URL, or `repo#id`, or omitted (detect from cwd) |
| `dryRun` | boolean | false | Skip writes; print intended commands |

## Failure UX

Every stop point prints three things:

1. **Why** the workflow stopped (one line).
2. **Next command** to run (copy-pasteable).
3. **Resume hint** (re-run `/close-pr` after the next command succeeds).

Example:

> CI is red on pipeline #4421 (`build/integration-test` failed).
> Next: `<platform-cli> pipeline view 4421 --log integration-test`
> Resume: re-run `/close-pr` once the failing test is fixed and pushed.

## Artifact split: private instance vs public pattern

This repo holds the **public, generic pattern**. A private instance in the user's `~/.claude/` adds environment-specific values.

| Artifact | Repo | Contents |
|----------|------|----------|
| `skills/close-pr/SKILL.md` | this repo | Trigger phrases, behavior description, configuration guidance, placeholders |
| `skills/close-pr/close-pr.example.js` | this repo | Reference workflow script with placeholders for platform, tracker, repo policy |
| `skills/close-pr/DESIGN.md` | this repo | This document |
| `~/.claude/skills/close-pr/SKILL.md` | private | Same skill body, points at private workflow |
| `~/.claude/workflows/close-pr.js` | private | Instance with concrete platform CLI, profile flags, repo policy registry, tracker URL, ticket-prefix regex |

Public artifacts must contain **no internal repo names, profile names, workspace identifiers, ticket prefixes, tracker hostnames, or anything else that would identify a private environment**. Placeholders use angle brackets: `<PLATFORM_CLI>`, `<WORKSPACE>`, `<TICKET_PREFIX>`, `<TRACKER_BASE_URL>`.

## Out of scope (explicitly)

- **Two-review audit before merge.** The author opted out; CI and human reviewers handle final correctness. If reinstated later, add as Phase 4.5 (subagent panel + flat-source review).
- **Auto-merge trigger on manual repos.** Manual repos always stop before merge. The user clicks. Reason: irreversibility.
- **Cross-PR batching.** One PR per invocation. Repeated calls for repeated PRs.
- **Following the post-merge deployment pipeline.** Handled by the companion skill `/post-merge-validation` (see `skills/post-merge-validation/DESIGN.md`). Phase 8 of this workflow prints a suggestion to invoke it once the merge lands.

## Open questions

- Whether `dryRun` should also skip Phase 2 push. Current answer: yes — dry-run is read-only.
- How to surface the "no PR found" case when the branch exists but no PR has been opened. Current answer: print the `pr create` command and stop.
- Whether to record `dryRun` invocations in memory at all. Current answer: no — dry-runs are inspection, not work.

## Implementation order (for the writing-plans skill that follows)

1. Public `SKILL.md` (manifest + body) — establishes the surface.
2. Public `close-pr.example.js` reference workflow with placeholders.
3. Private `~/.claude/skills/close-pr/SKILL.md` — thin wrapper.
4. Private `~/.claude/workflows/close-pr.js` — concrete instance.
5. Smoke test on a known PR in `--dry-run` mode.
6. Real-run on a low-stakes PR with `dryRun=false` to validate the full chain.
