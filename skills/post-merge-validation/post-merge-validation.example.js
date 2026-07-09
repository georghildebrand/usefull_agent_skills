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
