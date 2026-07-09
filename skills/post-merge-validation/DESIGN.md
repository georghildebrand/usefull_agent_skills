# `/post-merge-validation` — Staged-pipeline + Databricks Validation Workflow (Design)

**Date:** 2026-06-23
**Status:** Draft — pending implementation
**Companion skill:** `/close-pr` (see `skills/close-pr/DESIGN.md`)

## Goal

After a PR has merged to the main branch, drive the multi-stage deployment pipeline (typically `dev → staging → prod`) through its manual approval gates and, when a Databricks deployment is involved, verify that affected Databricks jobs deployed correctly via a task-count delta canary check.

## Relationship to `/close-pr`

Loose coupling. `/close-pr` ends at merge + cleanup + memory commit and prints a suggestion to run `/post-merge-validation` at the end. The user invokes the second workflow explicitly. Reasons:

- Post-merge pipelines can take minutes to hours; the user typically does not want to block their terminal in a single workflow that long.
- Gate approvals are a separate decision the user makes when they're ready to promote.
- The two skills are independently useful: `/post-merge-validation` runs equally well against any merged commit, not just one closed via `/close-pr`.

## Non-goals

- Triggering the post-merge pipeline. Assumed to start automatically on merge to main.
- Approving staging or production gates automatically. Those gates exist for a reason; the workflow stops at them.
- Rolling back failed deployments. Out of scope; print a suggested rollback command and stop.
- Full Databricks bundle validation (DABs `bundle summary` parse, runtime liveness via start-then-cancel). Deferred — see *Open questions*.

## Phases

| # | Phase | Action | Hard-stop on fail |
|---|-------|--------|-------------------|
| 1 | Detect | Resolve repo + main-branch commit. Find post-merge pipeline run for that commit via platform CLI. Identify pipeline stages and approval gates. Detect whether a Databricks deployment step exists by matching step name patterns (configurable; default: `databricks-deploy`, `dabs-deploy`, `bundle-deploy`). | Yes (no pipeline run → abort) |
| 2 | Stage follow | Poll the pipeline. For each completed stage: print result. For dev stage manual gate: auto-approve. For staging or prod manual gates: STOP, print `Stage <name> awaiting approval at <url>`, exit. | Yes on any failed stage |
| 3 | DBX scope *(if Databricks step present)* | Parse PR diff against `main~1..main`. Cross-reference changed files with DABs config (`databricks.yml`, `resources/*.yml`) to derive the set of affected jobs per target. | No — empty set means skip Phase 4 |
| 4 | DBX validation | For each affected job in the just-deployed target: fetch task count from the deployed job spec. Compare against a baseline (previous deployment of the same job). Flag jobs whose task count changed unexpectedly. | No — surface findings |
| 5 | Report | Print stage outcomes, gate position (where the workflow stopped), Databricks delta findings, next-action hint. | No |
| 6 | Memory commit | Write an episode marking the validation event: which commit, which target promoted, what was found. | No |

Phase 2 is a polling loop, not a fan-out. Rule: poll until the stage completes or hits a gate; do not retry.

## Gate policy

| Stage | Gate behavior |
|-------|---------------|
| `dev` | Auto-approve via platform CLI. Low blast radius. |
| `staging` | Stop. Print approval URL + commit being promoted. User approves in platform UI. Re-run workflow to continue. |
| `prod` | Same as staging. Stop. Print approval URL + the diff between staging and prod targets if available. |

Stage names are configurable per environment. The workflow exposes them as a small policy table:

```javascript
const STAGE_POLICY = {
  dev:     { autoApprove: true,  reason: 'low blast radius' },
  staging: { autoApprove: false, reason: 'manual gate by design' },
  prod:    { autoApprove: false, reason: 'manual gate by design' },
}
```

Stages not in the policy default to `autoApprove: false` (safer default).

## Databricks affected-job derivation

```text
PR diff (main~1..main)
  └─ filter to paths under DABs config
       (databricks.yml, resources/, src/jobs/, conf/)
  └─ for each changed path
       └─ resolve to job name(s) via DABs target include/exclude rules
  └─ deduplicate
  └─ {affected_jobs: [...], per_target_map: {staging: [...], prod: [...]}}
```

Edge cases:

- Path matches no job → log as "diff path with no job binding" and continue.
- Job in multiple targets → validated separately per target.
- Diff is empty (e.g. re-deploy without code change) → skip Phase 4 entirely.

## Task-count delta canary

For each affected job in the target just deployed:

1. Fetch current deployed job spec from Databricks Workflows API.
2. Look up the previous deployed version of the same job (from job history or a stored baseline).
3. Compute `delta = current_task_count - previous_task_count`.
4. Classify (where "tasks" means entries in the job's `tasks[]` list in the DABs resource YAML — adding/removing/renaming any `tasks[].task_key` counts as touching task definitions):
   - `delta == 0` → OK.
   - `delta > 0` and PR diff added `tasks[]` entries → OK.
   - `delta < 0` and PR diff removed `tasks[]` entries → OK.
   - `delta != 0` and PR diff did not touch `tasks[]` definitions → FLAG (silent drop or silent add — symptom of per-target include misconfig dropping tasks at deploy time, the class of failure where DABs validation passes but the deployed job is missing tasks).
5. Print findings table.

No hard stop. The user reads the findings and decides whether to roll back or promote forward.

## Safety rails

| Rail | Behavior |
|------|----------|
| Never auto-approve staging or prod gates | Hard rule; default to stop even for unknown stage names. |
| Pipeline polling = run once, then poll | Run once, then poll. No chained re-runs. Poll interval grows with stage age. |
| Failed stage → STOP immediately | Print the failed step + log URL. No retry. |
| DBX validation findings never block promotion | Phase 4 reports, does not stop. The user is the decision-maker. |
| Issue-tracker links explicit cross-tenant | Same rule as `/close-pr`. |
| Path-safe shell | Same rule as `/close-pr`. |
| Dry-run honored | `args.dryRun = true` skips dev gate auto-approve; everything else is read-only and runs normally. |

## Argument contract

| Arg | Type | Default | Meaning |
|-----|------|---------|---------|
| `commit` | string or null | null | Commit SHA on main. Default: latest main HEAD. |
| `target` | string or null | null | Which target's deployment to validate. Default: latest promoted target. |
| `dryRun` | boolean | false | Skip dev gate auto-approve; still print findings. |
| `pollInterval` | number (seconds) | 30 | Polling cadence for stage status. |
| `pollTimeout` | number (seconds) | 1800 | Give up after this long if pipeline neither passes nor hits a gate. |

## Failure UX

Same shape as `/close-pr`: every stop point prints **why**, **next action**, and **resume hint**.

Examples:

> Pipeline #5210 stage `staging` is awaiting approval.
> Approve at: `<pipeline-url>/steps/<step-id>`
> Resume: re-run `/post-merge-validation` after approval.

> Pipeline #5210 stage `dev` FAILED on step `databricks-deploy`.
> Logs: `<platform-cli> pipeline log 5210 --step databricks-deploy`
> Resume: fix and re-merge; do not auto-rerun.

> Databricks job `<job-name>` task count dropped from N to M.
> No matching change in PR diff. Possible silent per-target include drop.
> Inspect: `databricks bundle summary --target <target> | jq '.resources.jobs.<job_key>.tasks'`
> Decision: roll back or investigate before promoting further.

## Artifact split

| Artifact | Repo | Contents |
|----------|------|----------|
| `skills/post-merge-validation/SKILL.md` | this repo | Triggers, behavior description, configuration guidance, placeholders |
| `skills/post-merge-validation/post-merge-validation.example.js` | this repo | Reference workflow with placeholders |
| `skills/post-merge-validation/DESIGN.md` | this repo | This document |
| `~/.claude/skills/post-merge-validation/SKILL.md` | private | Thin wrapper |
| `~/.claude/workflows/post-merge-validation.js` | private | Concrete instance: platform CLI, stage policy with real environment names, DBX workspace host |

Same confidentiality rule as `/close-pr`: no internal repo names, environment names, host URLs, or tracker prefixes in public artifacts.

## Open questions

- **Start-then-cancel liveness test.** Originally scoped in, then deferred. Add as Phase 4.5 if task-count delta proves insufficient. Cost: ~1 minute per job + cluster spin-up time.
- **DABs `bundle summary` audit.** Deeper validation than task-count delta. Catches the per-target-include-silently-ignored failure class (where DABs CLI validation passes but the deployed job spec is missing tasks the source declared). Deferred — start small, add when needed.
- **Baseline storage.** Where to store the "previous deployed job spec" for delta comparison? Options: query Databricks job history API; cache in `~/.claude/cache/post-merge-validation/`; rely on `.deployed/<stage>/` artifacts produced by the deploy pipeline. Decision deferred to implementation.
- **Multi-commit pipeline runs.** If two PRs merge in quick succession and the pipeline coalesces, which commit's diff drives the affected-job set? Probably the merge-commit range from the last successful prod deploy to the current one. Decision deferred.

## Implementation order

1. Public `SKILL.md` (manifest + body).
2. Public `post-merge-validation.example.js` reference workflow with placeholders.
3. Private `~/.claude/skills/post-merge-validation/SKILL.md`.
4. Private `~/.claude/workflows/post-merge-validation.js`.
5. Smoke test in `--dry-run` on a known-good pipeline run.
6. Real-run on a low-stakes post-merge pipeline.
