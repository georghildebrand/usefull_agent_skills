---
name: post-merge-validation
description: Use when the user wants to validate a post-merge deployment (`/post-merge-validation`, "watch the deploy", "follow the pipeline"). Polls the staged deployment pipeline triggered by the latest merge to main, auto-approves the dev gate only (stops at staging and prod with an approval URL), and — if a Databricks deployment is involved — derives affected jobs from the PR diff and runs a task-count delta canary check against the previous deployed version of each affected job.
---

# /post-merge-validation — Staged Pipeline + DBX Validation

## When to invoke

- User types `/post-merge-validation` after a merge to main
- User says "follow the deploy", "watch the pipeline", "validate the merge"
- `/close-pr` Phase 8 prints a handoff hint suggesting this skill

Optional args: `--commit=<sha>` (default: latest main HEAD), `--target=<env>` (default: latest promoted target), `--dry-run` (skip dev gate auto-approve), `--poll-interval=<seconds>` (default 30), `--poll-timeout=<seconds>` (default 1800).

## What it does

Six phases:

1. **Detect** — repo + main HEAD commit (or `--commit`) + pipeline run + stages + gates + whether a DBX deploy step exists
2. **Stage follow** — poll until the next stage completes or hits a gate; auto-approve dev gate; stop at staging/prod gates with approval URL; stop on failure
3. **DBX scope** (if DBX deploy present) — parse PR diff vs `main~1..main` and cross-reference with DABs config to derive the affected job set per target
4. **DBX validation** — for each affected job in the just-deployed target, fetch current deployed task count, compare to previous, classify delta against PR diff
5. **Report** — print stage outcomes, gate position, DBX findings, next-action hint
6. **Memory commit** — write an episode marking the validation event

Full design: see `DESIGN.md` in this directory.

## Configuration (private instance)

Copy to `~/.claude/skills/post-merge-validation/SKILL.md` and `~/.claude/workflows/post-merge-validation.js`. Replace placeholders:

- `<PLATFORM_CLI>` and `<PLATFORM_FLAGS>` — git platform CLI for pipeline status + gate approval
- `<DBX_CLI>` — Databricks CLI binary path (default: `databricks`)
- `<DBX_HOST>` and `<DBX_PROFILE>` — Databricks workspace and CLI profile
- `<STAGE_POLICY>` — your dev/staging/prod stage names if they differ from the defaults
- `<DEPLOY_STEP_PATTERNS>` — step name patterns that indicate a DBX deploy (default: `databricks-deploy`, `dabs-deploy`, `bundle-deploy`)
- `<TICKET_PREFIX>` and `<TRACKER_BASE_URL>` — same as /close-pr

## How Claude invokes this skill

```javascript
Workflow({
  name: 'post-merge-validation',
  args: {
    commit:       <--commit-arg-or-null>,
    target:       <--target-arg-or-null>,
    dryRun:       <--dry-run-flag>,
    pollInterval: <--poll-interval-or-30>,
    pollTimeout:  <--poll-timeout-or-1800>,
  }
})
```

Summarize the return value: which stage was reached, where it stopped (gate, failure, completion), DBX findings if any.

## Safety rails

- Never auto-approve staging or prod
- Polling loop: run once, then poll; no chained re-runs
- Failed stage → STOP immediately, no retry
- DBX findings report-only; never block promotion
- Tracker links always full URL form
- Dry-run skips dev gate auto-approve (everything else is read-only and runs normally)

## Failure UX

Every stop point prints **why**, **next action**, **resume hint**.
