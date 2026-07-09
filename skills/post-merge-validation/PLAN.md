# `/post-merge-validation` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `/post-merge-validation` slash command that drives a staged deployment pipeline (dev → staging → prod) through manual approval gates and, when a Databricks deployment is involved, verifies affected jobs deployed correctly via a task-count delta canary check.

**Architecture:** Same shape as `/close-pr`: a `SKILL.md` describes the surface; a workflow script orchestrates phased agent dispatches. Phases: detect → stage-follow (polling) → DBX scope (diff-derived affected jobs) → DBX validation (task-count delta) → report → memory commit. Stage follow auto-approves the `dev` gate only; staging and prod always stop with an approval URL.

**Tech Stack:**
- Markdown (skill manifest, design, this plan)
- JavaScript (workflow orchestration scripts in the Workflow tool sandbox)
- Bash + platform CLI + Databricks CLI (`databricks bundle`, `databricks jobs`) inside agent prompts

## Global Constraints

- Same sandbox limits as `/close-pr`: no `require`, no filesystem, no Node API, no `Date.now()`, no `Math.random()`, no argless `new Date()`. Standard JS built-ins are available.
- Each phase **must** dispatch an `agent()` call.
- Public artifacts contain no internal identifiers — use placeholders `<PLATFORM_CLI>`, `<WORKSPACE>`, `<DBX_HOST>`, `<TICKET_PREFIX>`, `<TRACKER_BASE_URL>`.
- Never auto-approve staging or prod gates. Hard rule.
- Pipeline polling = run once, then poll; never chained re-runs (per author's loop-then-monitor rule).
- Failed stage → STOP immediately; no retry.
- DBX validation findings never block promotion — print and let the user decide.
- Source spec: `skills/post-merge-validation/DESIGN.md`. Every task implements something the spec calls for.
- Do not auto-commit; show diff and ask before committing in this repo.

---

## File Structure

```
skills/post-merge-validation/
├── DESIGN.md                          (already exists)
├── PLAN.md                            (this file)
├── SKILL.md                           (Task 1 — creates)
├── post-merge-validation.example.js   (Tasks 2-4 — creates + extends)
├── helpers/
│   └── pure.test.js                   (Task 2 — unit tests for pure helpers)
└── tests/
    └── smoke.md                       (Task 5 — manual smoke test procedure)
```

```
README.md                              (Task 7 — modifies: add row)
```

```
~/.claude/skills/post-merge-validation/
└── SKILL.md                           (Task 6 — creates)

~/.claude/workflows/
└── post-merge-validation.js           (Task 6 — creates; concrete instance)
```

Responsibilities mirror the `/close-pr` plan exactly: public reference vs private instance, pure helpers extracted into a unit-testable file, smoke procedure documented.

---

## Task 1: Public SKILL.md

**Files:**
- Create: `skills/post-merge-validation/SKILL.md`

**Interfaces:**
- Consumes: nothing
- Produces: skill trigger surface for `/post-merge-validation`

- [ ] **Step 1: Write SKILL.md**

````markdown
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

````

- [ ] **Step 2: Verify Claude Code sees the skill**

Reload, type `/post-merge-validation`. Expected: skill appears in the suggestion list with description text.

- [ ] **Step 3: Status, no commit yet**

```bash
git -C /path/to/usefull_agent_skills status -s skills/post-merge-validation/
```

Expected: SKILL.md listed as untracked.

---

## Task 2: Public workflow — meta, pure helpers, Phase 1 (Detect)

**Files:**
- Create: `skills/post-merge-validation/post-merge-validation.example.js`
- Create: `skills/post-merge-validation/helpers/pure.test.js`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `meta` export
  - `classifyStage(stageName: string, policy: object): {autoApprove: boolean, reason: string}`
  - `classifyTaskCountDelta({prevCount, currCount, diffTouchedTasks: boolean}): 'OK'|'FLAG'`
  - `DETECT_SCHEMA` JSON Schema
  - Phase 1 agent dispatch returning structured `ctx`

- [ ] **Step 1: Write failing tests for pure helpers**

Create `skills/post-merge-validation/helpers/pure.test.js`:

```javascript
import { test } from 'node:test'
import assert from 'node:assert/strict'

// === PURE HELPERS (mirrored from post-merge-validation.example.js) ===

function classifyStage(stageName, policy) {
  const entry = policy[stageName]
  if (entry) return entry
  return { autoApprove: false, reason: 'unknown stage — default safer (manual approval)' }
}

function classifyTaskCountDelta({ prevCount, currCount, diffTouchedTasks }) {
  const delta = currCount - prevCount
  if (delta === 0) return 'OK'
  if (delta !== 0 && diffTouchedTasks) return 'OK'
  return 'FLAG'
}

// === TESTS ===

const POLICY = {
  dev:     { autoApprove: true,  reason: 'low blast radius' },
  staging: { autoApprove: false, reason: 'manual gate by design' },
  prod:    { autoApprove: false, reason: 'manual gate by design' },
}

test('classifyStage returns autoApprove for dev', () => {
  assert.deepEqual(classifyStage('dev', POLICY), { autoApprove: true, reason: 'low blast radius' })
})

test('classifyStage stops at staging', () => {
  assert.equal(classifyStage('staging', POLICY).autoApprove, false)
})

test('classifyStage stops at prod', () => {
  assert.equal(classifyStage('prod', POLICY).autoApprove, false)
})

test('classifyStage defaults to manual for unknown stage', () => {
  assert.equal(classifyStage('canary', POLICY).autoApprove, false)
})

test('classifyTaskCountDelta returns OK when no delta', () => {
  assert.equal(classifyTaskCountDelta({ prevCount: 10, currCount: 10, diffTouchedTasks: false }), 'OK')
})

test('classifyTaskCountDelta returns OK when delta explained by PR diff', () => {
  assert.equal(classifyTaskCountDelta({ prevCount: 10, currCount: 12, diffTouchedTasks: true }), 'OK')
  assert.equal(classifyTaskCountDelta({ prevCount: 10, currCount: 8,  diffTouchedTasks: true }), 'OK')
})

test('classifyTaskCountDelta FLAGs unexplained delta (silent drop)', () => {
  assert.equal(classifyTaskCountDelta({ prevCount: 32, currCount: 8, diffTouchedTasks: false }), 'FLAG')
})

test('classifyTaskCountDelta FLAGs unexplained delta (silent add)', () => {
  assert.equal(classifyTaskCountDelta({ prevCount: 10, currCount: 14, diffTouchedTasks: false }), 'FLAG')
})
```

- [ ] **Step 2: Run tests, verify pass**

```bash
node --test /path/to/usefull_agent_skills/skills/post-merge-validation/helpers/pure.test.js
```

Expected: 8 tests pass.

- [ ] **Step 3: Write `post-merge-validation.example.js` with meta, helpers, schemas, Phase 1**

Create `skills/post-merge-validation/post-merge-validation.example.js`:

```javascript
export const meta = {
  name: 'post-merge-validation',
  description: 'Staged pipeline + Databricks task-count delta validation',
  phases: [
    { title: 'Detect',        detail: 'pipeline run + stages + DBX step' },
    { title: 'StageFollow',   detail: 'poll; auto-approve dev; stop at staging/prod gates' },
    { title: 'DbxScope',      detail: 'derive affected jobs from PR diff (if DBX present)' },
    { title: 'DbxValidation', detail: 'task-count delta canary' },
    { title: 'Report',        detail: 'summary + next action' },
    { title: 'MemoryCommit',  detail: 'episode' },
  ],
}

// === CONFIG (replace placeholders in your private instance) ===

const PLATFORM_CLI = '<PLATFORM_CLI>'
const PLATFORM_FLAGS = '<PLATFORM_FLAGS>'
const DBX_CLI = '<DBX_CLI>'                   // default: 'databricks'
const DBX_HOST = '<DBX_HOST>'
const DBX_PROFILE = '<DBX_PROFILE>'
const TRACKER_BASE_URL = '<TRACKER_BASE_URL>'

const STAGE_POLICY = {
  dev:     { autoApprove: true,  reason: 'low blast radius' },
  staging: { autoApprove: false, reason: 'manual gate by design' },
  prod:    { autoApprove: false, reason: 'manual gate by design' },
}

const DEPLOY_STEP_PATTERNS = ['databricks-deploy', 'dabs-deploy', 'bundle-deploy']

// === PURE HELPERS ===
// Mirror into helpers/pure.test.js when you change them.

function classifyStage(stageName, policy) {
  const entry = policy[stageName]
  if (entry) return entry
  return { autoApprove: false, reason: 'unknown stage — default safer (manual approval)' }
}

function classifyTaskCountDelta({ prevCount, currCount, diffTouchedTasks }) {
  const delta = currCount - prevCount
  if (delta === 0) return 'OK'
  if (delta !== 0 && diffTouchedTasks) return 'OK'
  return 'FLAG'
}

// === SCHEMAS ===

const DETECT_SCHEMA = {
  type: 'object',
  required: ['commit', 'pipelineId', 'stages', 'hasDbxStep'],
  properties: {
    commit:        { type: 'string', description: 'Main HEAD commit SHA used' },
    repoFullPath:  { type: 'string', description: 'owner/repo' },
    pipelineId:    { type: ['string', 'null'], description: 'Pipeline run id or null if none found' },
    pipelineUrl:   { type: 'string' },
    stages: {
      type: 'array',
      description: 'Ordered stages of the pipeline run',
      items: {
        type: 'object',
        required: ['name', 'state'],
        properties: {
          name:        { type: 'string' },
          state:       { type: 'string', enum: ['pending', 'running', 'success', 'failed', 'awaiting-approval', 'skipped'] },
          stepUrl:     { type: 'string' },
          isGate:      { type: 'boolean' },
          deployTarget:{ type: 'string', description: 'Deploy target this stage promotes to (empty if not a deploy stage)' },
        },
      },
    },
    hasDbxStep:    { type: 'boolean', description: 'true if any stage step name matches DEPLOY_STEP_PATTERNS' },
  },
}

// === PHASES ===

const args_ = typeof args !== 'undefined' ? args : {}
const dryRun = args_.dryRun === true
const commitArg = args_.commit ?? null
const targetArg = args_.target ?? null
const pollInterval = Math.max(5, Math.min(args_.pollInterval ?? 30, 600))
const pollTimeout  = Math.max(60, Math.min(args_.pollTimeout ?? 1800, 7200))

phase('Detect')

const detectPrompt = `
You are the Detect phase of the post-merge-validation workflow.

Steps:
1. Determine the repo root: \`git -C "$PWD" rev-parse --show-toplevel\`. Read origin URL.
2. Resolve the commit:
   - If args.commit is set (${commitArg ? JSON.stringify(commitArg) : 'null'}), use it.
   - Else use \`git -C <repo-root> rev-parse origin/main\` (or origin/master as fallback).
3. Find the pipeline run for that commit using ${PLATFORM_CLI} ${PLATFORM_FLAGS} pipeline list with a commit filter. Pick the most recent.
4. List the stages of that run; for each, capture name, state, step URL, whether it is a manual approval gate, and (for deploy stages) the deploy target.
5. Detect a DBX deploy step: hasDbxStep = true if any step name contains one of ${JSON.stringify(DEPLOY_STEP_PATTERNS)}.

Return JSON matching DETECT_SCHEMA. If no pipeline run found, set pipelineId=null, stages=[], hasDbxStep=false.
`

const ctx = await agent(detectPrompt, { schema: DETECT_SCHEMA, label: 'detect' })

if (!ctx || ctx.pipelineId == null) {
  log(`No pipeline run found for commit ${ctx?.commit || '<unknown>'}.`)
  log('Next: confirm the merge triggered a pipeline. Re-run once it appears.')
  return { stop: 'no-pipeline', ctx }
}

log(`Pipeline ${ctx.pipelineId} found. Stages: ${ctx.stages.map((s) => `${s.name}(${s.state})`).join(', ')}`)
log(`DBX deploy step present: ${ctx.hasDbxStep}`)

// === NEXT PHASES IMPLEMENTED IN TASK 3 ===
return { stop: 'task-2-stub', ctx }
```

- [ ] **Step 4: Re-run unit tests**

```bash
node --test /path/to/usefull_agent_skills/skills/post-merge-validation/helpers/pure.test.js
```

Expected: 8 tests pass.

- [ ] **Step 5: Status check, no commit**

```bash
git -C /path/to/usefull_agent_skills status -s skills/post-merge-validation/
```

Expected: SKILL.md, post-merge-validation.example.js, helpers/pure.test.js untracked.

---

## Task 3: Public workflow — Phases 2-3 (StageFollow + DbxScope)

**Files:**
- Modify: `skills/post-merge-validation/post-merge-validation.example.js`

**Interfaces:**
- Consumes: `ctx`, `dryRun`, `pollInterval`, `pollTimeout` from Task 2
- Produces:
  - `stageOutcome`: `{stoppedAt: string, reason: string, lastStage: string, lastState: string}`
  - `dbxScope`: `{affectedJobs: Array<{target, jobKey, sourcePaths}>, perTargetMap: object, diffTouchedTaskKeys: object}`
  - `STAGE_FOLLOW_SCHEMA`, `DBX_SCOPE_SCHEMA`

- [ ] **Step 1: Append schemas**

Add to `post-merge-validation.example.js` after `DETECT_SCHEMA`:

```javascript
const STAGE_FOLLOW_SCHEMA = {
  type: 'object',
  required: ['stoppedAt', 'reason', 'lastStage', 'lastState'],
  properties: {
    stoppedAt:    { type: 'string', enum: ['completed', 'failure', 'staging-gate', 'prod-gate', 'unknown-gate', 'timeout'] },
    reason:       { type: 'string' },
    lastStage:    { type: 'string' },
    lastState:    { type: 'string' },
    approvalUrl:  { type: 'string', description: 'URL to approve the pending gate, empty if none' },
    failedStep:   { type: 'string', description: 'Step name that failed, empty if no failure' },
    failedStepUrl:{ type: 'string' },
  },
}

const DBX_SCOPE_SCHEMA = {
  type: 'object',
  required: ['affectedJobs', 'perTargetMap', 'diffTouchedTaskKeys', 'diffEmpty'],
  properties: {
    diffEmpty: { type: 'boolean', description: 'true if PR diff vs main~1..main contains no DABs-relevant changes' },
    affectedJobs: {
      type: 'array',
      items: {
        type: 'object',
        required: ['target', 'jobKey'],
        properties: {
          target:       { type: 'string' },
          jobKey:       { type: 'string', description: 'The resources.jobs.<jobKey> key in the DABs config' },
          sourcePaths:  { type: 'array', items: { type: 'string' } },
        },
      },
    },
    perTargetMap: {
      type: 'object',
      description: 'Map of target name to array of jobKey strings',
      additionalProperties: { type: 'array', items: { type: 'string' } },
    },
    diffTouchedTaskKeys: {
      type: 'object',
      description: 'Map of jobKey to array of task_key strings that the diff added/removed/renamed',
      additionalProperties: { type: 'array', items: { type: 'string' } },
    },
  },
}
```

- [ ] **Step 2: Replace the Task 2 stub with Phases 2-3**

Replace:

```javascript
// === NEXT PHASES IMPLEMENTED IN TASK 3 ===
return { stop: 'task-2-stub', ctx }
```

with:

```javascript
phase('StageFollow')

const stageFollowPrompt = `
You are the StageFollow phase. Pipeline ${ctx.pipelineId} for commit ${ctx.commit} on ${ctx.repoFullPath}.
Stage policy: ${JSON.stringify(STAGE_POLICY)}.
dryRun: ${dryRun}.
pollInterval: ${pollInterval}s, pollTimeout: ${pollTimeout}s.

Per the run-once-then-poll rule: do NOT trigger any pipeline runs. Only observe.

Loop:
1. Fetch pipeline ${ctx.pipelineId} state via ${PLATFORM_CLI} ${PLATFORM_FLAGS}.
2. Walk stages in order. For the first stage in state pending or running, sleep ${pollInterval}s and re-fetch.
3. When you reach a stage with state="failed": stop with stoppedAt="failure", capture failedStep and failedStepUrl, return.
4. When you reach a stage with state="awaiting-approval" (a gate):
   - Look up its policy via classifyStage. (The agent should hardcode the JS policy above: dev autoApprove=true; others not.)
   - If stage name is "dev" AND policy.autoApprove is true AND dryRun is false: approve via ${PLATFORM_CLI} ${PLATFORM_FLAGS} pipeline approve --pipeline ${ctx.pipelineId} --step <step-id>. Then continue polling.
   - If dev AND dryRun is true: log "would auto-approve dev gate", do not approve, stop with stoppedAt="staging-gate" if that's next, or "completed" if dev is the last stage.
   - If stage name is "staging": stop with stoppedAt="staging-gate", capture approvalUrl, return.
   - If stage name is "prod": stop with stoppedAt="prod-gate", capture approvalUrl, return.
   - If unknown stage: stop with stoppedAt="unknown-gate" (safer default), capture approvalUrl, return.
5. When all stages reach state="success" or "skipped": stop with stoppedAt="completed".
6. If total elapsed time exceeds ${pollTimeout}s: stop with stoppedAt="timeout".

Return JSON matching STAGE_FOLLOW_SCHEMA.
`

const stageOutcome = await agent(stageFollowPrompt, { schema: STAGE_FOLLOW_SCHEMA, label: 'stage-follow' })

log(`StageFollow: ${stageOutcome.stoppedAt} (lastStage=${stageOutcome.lastStage}, state=${stageOutcome.lastState})`)

if (stageOutcome.stoppedAt === 'failure') {
  log(`Stage ${stageOutcome.lastStage} FAILED on step ${stageOutcome.failedStep}.`)
  log(`Logs: ${stageOutcome.failedStepUrl}`)
  log('Next: fix and re-merge; do not auto-rerun.')
  return { stop: 'pipeline-failure', ctx, stageOutcome }
}

if (stageOutcome.stoppedAt === 'timeout') {
  log(`Timed out waiting on stage ${stageOutcome.lastStage} after ${pollTimeout}s.`)
  log('Next: investigate why the stage is stuck. Resume: re-run /post-merge-validation.')
  return { stop: 'timeout', ctx, stageOutcome }
}

if (stageOutcome.stoppedAt === 'staging-gate' || stageOutcome.stoppedAt === 'prod-gate' || stageOutcome.stoppedAt === 'unknown-gate') {
  log(`Stage ${stageOutcome.lastStage} awaiting approval at ${stageOutcome.approvalUrl}`)
  log(`Reason: ${stageOutcome.reason}`)
  // Run DBX validation against the last successfully deployed target before yielding
}

phase('DbxScope')

let dbxScope = { affectedJobs: [], perTargetMap: {}, diffTouchedTaskKeys: {}, diffEmpty: true }

if (ctx.hasDbxStep) {
  const dbxScopePrompt = `
You are the DbxScope phase. Repo ${ctx.repoFullPath}, commit ${ctx.commit}.

Steps:
1. Compute the diff: \`git -C <repo-root> diff --name-only ${ctx.commit}~1..${ctx.commit}\`.
2. Filter to DABs-relevant paths:
   - databricks.yml
   - resources/**/*.yml
   - any path under src/jobs/ or conf/
3. If filtered list is empty: set diffEmpty=true and return.
4. Else parse databricks.yml + resources/*.yml. For each affected source path, determine which job key(s) reference it. Build affectedJobs entries.
5. Build perTargetMap: which jobs deploy to which targets (read the DABs target include/exclude rules).
6. For each affected job, detect which task_key entries the diff added, removed, or renamed (look for changes in the tasks[] block of the job's YAML).

Return JSON matching DBX_SCOPE_SCHEMA. Empty arrays are fine.
`
  dbxScope = await agent(dbxScopePrompt, { schema: DBX_SCOPE_SCHEMA, label: 'dbx-scope' })
}

if (dbxScope.diffEmpty || dbxScope.affectedJobs.length === 0) {
  log('No affected Databricks jobs in this commit. Skipping DBX validation.')
}

// === NEXT PHASES IMPLEMENTED IN TASK 4 ===
return { stop: 'task-3-stub', ctx, stageOutcome, dbxScope }
```

- [ ] **Step 3: Smoke-load via the Workflow tool**

In a Claude Code session, against a real commit on main that has a recent pipeline run:

```
Workflow({
  scriptPath: '/path/to/usefull_agent_skills/skills/post-merge-validation/post-merge-validation.example.js',
  args: { dryRun: true }
})
```

Expected: phases Detect → StageFollow → DbxScope progress in the UI. Workflow returns `{ stop: 'task-3-stub', ... }` populated. Placeholder errors are expected — the point is orchestration shape.

- [ ] **Step 4: Re-run unit tests**

```bash
node --test /path/to/usefull_agent_skills/skills/post-merge-validation/helpers/pure.test.js
```

Expected: 8 pass.

- [ ] **Step 5: Status, no commit**

```bash
git -C /path/to/usefull_agent_skills status -s skills/post-merge-validation/
```

---

## Task 4: Public workflow — Phases 4-6 (DbxValidation, Report, MemoryCommit)

**Files:**
- Modify: `skills/post-merge-validation/post-merge-validation.example.js`

**Interfaces:**
- Consumes: `ctx`, `stageOutcome`, `dbxScope`, `dryRun` from Task 3
- Produces: terminal return `{ done: boolean, ctx, stageOutcome, dbxScope, dbxFindings, memory }`

- [ ] **Step 1: Append `DBX_VALIDATION_SCHEMA`**

```javascript
const DBX_VALIDATION_SCHEMA = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['target', 'jobKey', 'prevCount', 'currCount', 'verdict'],
        properties: {
          target:      { type: 'string' },
          jobKey:      { type: 'string' },
          prevCount:   { type: 'integer' },
          currCount:   { type: 'integer' },
          diffTouchedTasks: { type: 'boolean' },
          verdict:     { type: 'string', enum: ['OK', 'FLAG'] },
          note:        { type: 'string' },
        },
      },
    },
    skipped: { type: 'boolean', description: 'true if no affected jobs or no last-deployed-target info' },
  },
}
```

- [ ] **Step 2: Replace the Task 3 stub with Phases 4-6**

Replace:

```javascript
// === NEXT PHASES IMPLEMENTED IN TASK 4 ===
return { stop: 'task-3-stub', ctx, stageOutcome, dbxScope }
```

with:

```javascript
phase('DbxValidation')

let dbxFindings = { findings: [], skipped: true }

const lastDeployedTarget = determineLastDeployedTarget(ctx, stageOutcome, targetArg)

if (ctx.hasDbxStep && !dbxScope.diffEmpty && dbxScope.affectedJobs.length > 0 && lastDeployedTarget) {
  const jobsForTarget = dbxScope.affectedJobs.filter((j) => j.target === lastDeployedTarget)
  if (jobsForTarget.length === 0) {
    log(`No affected jobs target ${lastDeployedTarget}; skipping DBX validation.`)
  } else {
    const validationPrompt = `
You are the DbxValidation phase. Target: ${lastDeployedTarget}. Jobs to validate: ${JSON.stringify(jobsForTarget.map((j) => j.jobKey))}.

For each job:
1. Fetch current deployed task count from Databricks Workflows API via ${DBX_CLI} -p ${DBX_PROFILE} jobs get --job-id <id> (resolve job id by name first if needed). Read tasks[] length.
2. Fetch the previous deployed task count. Two acceptable sources:
   a. Job run history: query the most recent run that completed BEFORE this commit's deploy and read its task count.
   b. \`${DBX_CLI} -p ${DBX_PROFILE} bundle summary --target ${lastDeployedTarget}\` parsed against the previous main commit's snapshot. (Less ideal; use if a). is unavailable.)
3. Look up diffTouchedTasks for the jobKey in this map: ${JSON.stringify(dbxScope.diffTouchedTaskKeys)}. Set diffTouchedTasks = true if the array for that jobKey is non-empty.
4. Compute verdict: OK if delta=0, OK if delta!=0 AND diffTouchedTasks=true, FLAG otherwise.
5. Add a one-line note explaining the verdict.

Return JSON: {findings: [...], skipped: false}.
`
    dbxFindings = await agent(validationPrompt, { schema: DBX_VALIDATION_SCHEMA, label: 'dbx-validation' })
  }
} else {
  log(`Skipping DBX validation. hasDbxStep=${ctx.hasDbxStep}, diffEmpty=${dbxScope.diffEmpty}, lastDeployedTarget=${lastDeployedTarget || 'none'}`)
}

phase('Report')

log('=== Post-merge validation report ===')
log(`Pipeline: ${ctx.pipelineId} (${ctx.pipelineUrl})`)
log(`Commit:   ${ctx.commit}`)
log(`Stage outcome: ${stageOutcome.stoppedAt} at ${stageOutcome.lastStage}`)
if (stageOutcome.approvalUrl) log(`Approval URL: ${stageOutcome.approvalUrl}`)
if (stageOutcome.failedStepUrl) log(`Failed step log: ${stageOutcome.failedStepUrl}`)

if (!dbxFindings.skipped) {
  log(`DBX findings (${dbxFindings.findings.length} jobs validated):`)
  for (const f of dbxFindings.findings) {
    log(`  ${f.verdict} ${f.target}/${f.jobKey}  prev=${f.prevCount} curr=${f.currCount}  ${f.note}`)
  }
  const flags = dbxFindings.findings.filter((f) => f.verdict === 'FLAG')
  if (flags.length > 0) {
    log(`FLAGGED jobs: ${flags.length}. Inspect each with:`)
    for (const f of flags) {
      log(`  ${DBX_CLI} -p ${DBX_PROFILE} bundle summary --target ${f.target} | jq '.resources.jobs.${f.jobKey}.tasks'`)
    }
    log('Decision is yours: roll back, investigate, or accept and continue promotion.')
  }
}

if (stageOutcome.stoppedAt === 'staging-gate' || stageOutcome.stoppedAt === 'prod-gate') {
  log(`Next: approve at ${stageOutcome.approvalUrl}, then re-run /post-merge-validation.`)
}
if (stageOutcome.stoppedAt === 'completed') {
  log('Next: nothing. Pipeline complete.')
}

phase('MemoryCommit')

let memory = { skipped: dryRun, committed: false }

if (!dryRun) {
  const memPrompt = `
Commit a memory episode for this validation event.
Project: <PROJECT_SLUG>
Type: ops
Summary: post-merge validation for ${ctx.repoFullPath} commit ${ctx.commit}; pipeline ${ctx.pipelineId}; stopped at ${stageOutcome.stoppedAt}; DBX findings ${dbxFindings.skipped ? 'skipped' : `${dbxFindings.findings.length} (${dbxFindings.findings.filter((f) => f.verdict === 'FLAG').length} flagged)`}.
Populate repos=[<repo>], tags=["post-merge-validation", "<TAG_PROJECT>"], related_keys=[].
Return JSON: {committed: boolean, memId: string, error: string}.
`
  memory = await agent(memPrompt, {
    schema: {
      type: 'object',
      required: ['committed'],
      properties: {
        committed: { type: 'boolean' },
        memId:     { type: 'string' },
        error:     { type: 'string' },
      },
    },
    label: 'memory-commit',
  })
}

return { done: true, ctx, stageOutcome, dbxScope, dbxFindings, memory }

// === HELPERS used above ===

function determineLastDeployedTarget(ctx, stageOutcome, targetArg) {
  if (targetArg) return targetArg
  // Walk stages in reverse; the last stage with state="success" and a deployTarget set is our answer.
  for (let i = ctx.stages.length - 1; i >= 0; i--) {
    const s = ctx.stages[i]
    if (s.state === 'success' && s.deployTarget) return s.deployTarget
  }
  return null
}
```

- [ ] **Step 3: Smoke-run end-to-end (dry-run)**

```
Workflow({
  scriptPath: '/path/to/usefull_agent_skills/skills/post-merge-validation/post-merge-validation.example.js',
  args: { dryRun: true }
})
```

Expected: all 6 phases execute. Stops at a gate or completes. Report block prints. Memory phase skips because dryRun.

- [ ] **Step 4: Re-run unit tests**

```bash
node --test /path/to/usefull_agent_skills/skills/post-merge-validation/helpers/pure.test.js
```

Expected: 8 pass.

- [ ] **Step 5: Status, no commit**

```bash
git -C /path/to/usefull_agent_skills status -s skills/post-merge-validation/
```

---

## Task 5: Smoke test procedure document

**Files:**
- Create: `skills/post-merge-validation/tests/smoke.md`

**Interfaces:**
- Consumes: nothing
- Produces: written verification procedure

- [ ] **Step 1: Create the smoke test doc**

```markdown
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
```

- [ ] **Step 2: Status**

```bash
git -C /path/to/usefull_agent_skills status -s skills/post-merge-validation/tests/
```

Expected: smoke.md untracked.

---

## Task 6: Private skill and workflow instance

**Files:**
- Create: `~/.claude/skills/post-merge-validation/SKILL.md`
- Create: `~/.claude/workflows/post-merge-validation.js`

**Interfaces:**
- Consumes: public example as template
- Produces: runnable `/post-merge-validation` slash command

- [ ] **Step 1: Create private skill dir + SKILL.md (thin wrapper)**

```bash
mkdir -p ~/.claude/skills/post-merge-validation
```

Write `~/.claude/skills/post-merge-validation/SKILL.md`:

````markdown
---
name: post-merge-validation
description: Use when the user wants to validate a post-merge deployment (`/post-merge-validation`, "watch the deploy", "follow the pipeline"). Polls the staged deployment pipeline triggered by the latest merge to main, auto-approves the dev gate only (stops at staging and prod with an approval URL), and — if a Databricks deployment is involved — derives affected jobs from the PR diff and runs a task-count delta canary check against the previous deployed version of each affected job.
---

See the generic reference at `~/workspace/github.com/usefull_agent_skills/skills/post-merge-validation/SKILL.md`.

Invoke via:

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
````

- [ ] **Step 2: Copy and concretize the workflow**

```bash
mkdir -p ~/.claude/workflows
cp /path/to/usefull_agent_skills/skills/post-merge-validation/post-merge-validation.example.js \
   ~/.claude/workflows/post-merge-validation.js
```

Open the copied file. Ask the user for each value:

- `<PLATFORM_CLI>`, `<PLATFORM_FLAGS>` — same as their `/close-pr` choices (reuse)
- `<DBX_CLI>` (default `databricks`)
- `<DBX_HOST>`, `<DBX_PROFILE>` — Databricks workspace + profile
- `<TRACKER_BASE_URL>` — same as /close-pr
- `<PROJECT_SLUG>`, `<TAG_PROJECT>` — same as /close-pr
- `STAGE_POLICY` — override `dev`/`staging`/`prod` names if your environment uses different names
- `DEPLOY_STEP_PATTERNS` — extend if your DBX deploy step uses a different name

Substitute every `<…>` placeholder. Verify:

```bash
grep -nE '<[A-Z_]+>' ~/.claude/workflows/post-merge-validation.js || echo "No placeholders remain"
```

Expected: `No placeholders remain`.

- [ ] **Step 3: Register and dry-run**

```
Workflow({ name: 'post-merge-validation', args: { dryRun: true } })
```

Expected: workflow runs, every phase prints sensible output. Fix any issues inline.

- [ ] **Step 4: No public-repo commit (private files only)**

```bash
git -C /path/to/usefull_agent_skills status -s
```

Expected: nothing new from this task — private files are outside the worktree.

---

## Task 7: README.md update + public-repo commit

**Files:**
- Modify: `/path/to/usefull_agent_skills/README.md`

**Interfaces:**
- Consumes: public artifacts from Tasks 1-5
- Produces: updated skills index + single commit

- [ ] **Step 1: Add row to skills table**

Insert near `close-pr` (these two are companion skills):

```markdown
| [`post-merge-validation`](skills/post-merge-validation/SKILL.md) | Staged pipeline + Databricks task-count delta validation: poll, auto-approve dev, stop at staging/prod, validate DBX deploys | A merge landed and you want to drive the deploy pipeline through its gates and verify Databricks jobs deployed correctly |
```

- [ ] **Step 2: Show diff to user**

```bash
git -C /path/to/usefull_agent_skills diff README.md
git -C /path/to/usefull_agent_skills status -s
```

Ask: "Diff adds post-merge-validation to README. Plus untracked skill files. Commit now?" Wait for `yes`.

- [ ] **Step 3: Commit explicitly**

```bash
git -C /path/to/usefull_agent_skills add \
  README.md \
  skills/post-merge-validation/SKILL.md \
  skills/post-merge-validation/DESIGN.md \
  skills/post-merge-validation/PLAN.md \
  skills/post-merge-validation/post-merge-validation.example.js \
  skills/post-merge-validation/helpers/pure.test.js \
  skills/post-merge-validation/tests/smoke.md
```

```bash
git -C /path/to/usefull_agent_skills commit -m "$(cat <<'EOF'
Add post-merge-validation skill: staged pipeline + DBX canary

Reference workflow + skill manifest for following a post-merge
deployment pipeline through staged gates (auto-approve dev only,
stop at staging/prod) and validating Databricks deploys via a
task-count delta canary check derived from the PR diff.
Public artifacts use placeholders; private instance under ~/.claude/.
EOF
)"
```

No `Co-Authored-By` lines.

- [ ] **Step 4: Verify**

```bash
git -C /path/to/usefull_agent_skills log -1 --oneline
git -C /path/to/usefull_agent_skills status
```

Expected: commit landed, working tree clean.

---

## Task 8: Real-run validation on a real post-merge pipeline

**Files:**
- None

**Interfaces:**
- Consumes: private workflow from Task 6
- Produces: confirmed end-to-end behavior; follow-ups for any drift

- [ ] **Step 1: Pick a recent merge with a triggered pipeline**

Ask the user to identify a commit on main with a pipeline run in progress (dev stage running or staging gate pending) and a small DABs delta.

- [ ] **Step 2: Dry-run first**

```
Workflow({
  name: 'post-merge-validation',
  args: { commit: '<sha>', dryRun: true }
})
```

Expected: workflow follows stages, prints dev gate as "would auto-approve" (dry-run), stops at staging gate with approval URL, dbxScope/Validation populated if applicable.

- [ ] **Step 3: Real run**

```
Workflow({
  name: 'post-merge-validation',
  args: { commit: '<sha>', dryRun: false }
})
```

Expected:
- Dev gate auto-approved (verify in pipeline UI)
- Workflow stops at staging gate
- DBX validation findings printed if applicable
- Memory episode committed

- [ ] **Step 4: Continue from staging gate**

After approving staging in the UI, re-run the same workflow. Expected: workflow picks up, stops at prod gate.

- [ ] **Step 5: Verify failure path on a real broken pipeline**

When you next hit a real pipeline failure, re-run the workflow against that commit. Expected: workflow stops at Phase 2 with `stop: 'pipeline-failure'`, prints failed step + log URL.

- [ ] **Step 6: Capture follow-ups**

Anything that misbehaves: file an issue on this repo (public artifact bugs) or fix the private workflow (environment-specific issues). Document recurring issues in PLAN.md or DESIGN.md updates.

---

## Self-Review

### Spec coverage

Walking the DESIGN.md spec:

- **Goal + non-goals + relationship to /close-pr** — Stated in PLAN header and Task 1 SKILL.md body.
- **Phases 1-6** — Tasks 2-4 implement in three batches. Each phase maps to an `agent()` call with a schema.
- **Gate policy table** — STAGE_POLICY constant in Task 2; classifyStage helper unit-tested.
- **Databricks affected-job derivation** — Phase 3 (DbxScope) in Task 3; schema captures perTargetMap + diffTouchedTaskKeys.
- **Task-count delta canary** — classifyTaskCountDelta helper in Task 2 unit tests; Phase 4 (DbxValidation) in Task 4 uses the same classification rules.
- **Safety rails** — Embedded in phase prompts and SKILL.md body: never auto-approve staging/prod, polling run-once-then-monitor, failed stage stops, DBX findings report-only, tracker links explicit, path-safe shell, dry-run honored.
- **Argument contract** — `commit`, `target`, `dryRun`, `pollInterval`, `pollTimeout` all honored across phases. Bounds applied (`Math.max(5, Math.min(...))`).
- **Failure UX** — Every stop point in Tasks 3-4 prints why + next + resume.
- **Artifact split** — Public reference (Task 2-5) vs private instance (Task 6).
- **Open questions in DESIGN.md (start-cancel liveness, bundle summary audit, baseline storage, multi-commit pipelines)** — Acknowledged as deferred; not implemented in this plan. Baseline storage decision: workflow asks the agent to try job-run-history first, fall back to bundle summary. Documented in Phase 4 prompt.

### Placeholder scan

- No "TBD" / "TODO" / "fill in later".
- Code blocks present in every code step.
- `<PLACEHOLDER>` strings appear intentionally; Task 6 has a grep check to confirm substitution.
- Test code is real, not described.

### Type consistency

- `classifyStage(stageName, policy)` returns `{autoApprove, reason}` in both the test file and the inline copy.
- `classifyTaskCountDelta({prevCount, currCount, diffTouchedTasks})` returns `'OK'|'FLAG'` consistently.
- `ctx` shape from DETECT_SCHEMA used identically in Tasks 3-4: `ctx.pipelineId`, `ctx.commit`, `ctx.stages`, `ctx.hasDbxStep`, `ctx.repoFullPath`, `ctx.pipelineUrl`.
- `stageOutcome.stoppedAt` enum (`completed|failure|staging-gate|prod-gate|unknown-gate|timeout`) used identically in the report + return branching.
- `dbxScope.affectedJobs[].target` and `.jobKey` and `dbxScope.diffTouchedTaskKeys[jobKey]` shape used consistently in DBX validation.
- `determineLastDeployedTarget(ctx, stageOutcome, targetArg)` signature matches its only call site.
