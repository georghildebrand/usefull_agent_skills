# post-merge-validation smoke test

## Prerequisites

- A recent merge to main with a triggered pipeline (low-stakes change preferred).
- The private workflow at `~/.claude/workflows/post-merge-validation.js` configured with concrete platform CLI, Databricks CLI/profile, and stage names.
- Platform CLI authenticated; Databricks CLI authenticated.

## 1. Pure helper unit tests

```bash
node --test skills/post-merge-validation/helpers/pure.test.js
```

Expected: 8 tests pass.

## 2. Dry-run on the example workflow

In a Claude Code session positioned in the repo whose pipeline you want to follow:

```
Workflow({
  scriptPath: '<absolute-path>/skills/post-merge-validation/post-merge-validation.example.js',
  args: { dryRun: true }
})
```

Expected progress UI: Detect → StageFollow → DbxScope → DbxValidation → Report → MemoryCommit.

Expected return shape:
- `done: true` if the pipeline completed without a gate, OR
- `stop: 'staging-gate' | 'prod-gate' | 'pipeline-failure' | 'timeout' | 'no-pipeline'` with reason populated
- `dbxFindings.findings` array present if `ctx.hasDbxStep` was true

Placeholder errors are expected on the public example — the point is orchestration shape.

## 3. Dry-run on the private workflow

```
Workflow({ name: 'post-merge-validation', args: { dryRun: true } })
```

Expected: same shape; real platform CLI and Databricks CLI calls succeed.

## 4. Real-run on the private workflow

Once dry-runs are clean:

```
Workflow({ name: 'post-merge-validation', args: { dryRun: false } })
```

Behavior to verify:

- Dev gate auto-approved (visible in pipeline UI as "approved by user X").
- At staging gate: workflow stops, prints approval URL. Approve in UI. Re-run. Workflow picks up from staging and continues to prod gate.
- At prod gate: same behavior. Approve, re-run, workflow runs to completion.
- DBX validation: if there were DABs changes, each affected job has a finding line. FLAGGED entries print the suggested `bundle summary | jq` inspect command.

## 5. Failure paths to verify at least once each

- **No pipeline run for commit**: workflow stops at Phase 1 with `stop: 'no-pipeline'`.
- **Pipeline step failure**: workflow stops at Phase 2 with `stop: 'pipeline-failure'`, prints failed step + log URL.
- **Long-running stage**: artificially set `pollTimeout: 60` and run during a slow deploy; workflow stops with `stop: 'timeout'`.
- **DBX task-count delta FLAG**: deploy a change that silently drops tasks (e.g. broken per-target include); validation finding should be FLAG.

After each failure path, the `Next:` and `Resume:` lines should be copy-pasteable.
