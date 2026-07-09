export const meta = {
  name: 'close-pr',
  description: 'Author-side PR close: format/push/poll/merge/cleanup/ticket/memory',
  phases: [
    { title: 'Detect',           detail: 'repo + branch + PR + ticket' },
    { title: 'LocalReady',       detail: 'format + pre-commit + push' },
    { title: 'RemotePoll',       detail: 'CI + approvals + mergeability + ticket (parallel)' },
    { title: 'Decision',         detail: 'gate on signals' },
    { title: 'Merge',            detail: 'auto-merge handling or stop' },
    { title: 'Cleanup',          detail: 'local + remote branch (per-branch confirm)' },
    { title: 'TicketTransition', detail: 'tracker CLI' },
    { title: 'MemoryCommit',     detail: 'episode + handoff hint' },
  ],
}

// === CONFIG (replace placeholders in your private instance) ===

const PLATFORM_CLI = '<PLATFORM_CLI>'                    // e.g. 'atlassian-cli', 'gh', 'glab'
const PLATFORM_FLAGS = '<PLATFORM_FLAGS>'                // e.g. '--profile myprofile --workspace myws'
const TRACKER_BASE_URL = '<TRACKER_BASE_URL>'            // e.g. 'https://tracker.example/browse'
const TICKET_PREFIX_REGEX_SOURCE = '<TICKET_PREFIX>'     // e.g. 'ABC|DEF'

const REPO_POLICY = [
  // { repo: 'owner/name', mergeMode: 'auto', requiredApprovals: 3, note: 'why' },
  // populate per environment
]

// === PURE HELPERS ===
// Mirror these definitions into helpers/pure.test.js when you change them.

function parsePrArg(arg) {
  if (arg == null || arg === '') return null
  // URL form: https://<host>/<workspace>/<repo>/pull-requests/<id>
  const urlMatch = arg.match(/\/([^/]+)\/pull(?:-requests)?\/(\d+)\/?$/)
  if (urlMatch) return { repo: urlMatch[1], prId: parseInt(urlMatch[2], 10) }
  // Short form: <repo>#<id>
  const shortMatch = arg.match(/^([\w.-]+)#(\d+)$/)
  if (shortMatch) return { repo: shortMatch[1], prId: parseInt(shortMatch[2], 10) }
  return null
}

function extractTicketId(branchName, prTitle, prefixRegex) {
  const combined = `${branchName || ''} ${prTitle || ''}`
  const re = new RegExp(`(${prefixRegex.source})-\\d+`)
  const m = combined.match(re)
  return m ? m[0] : null
}

function classifyRepo(repo, policy) {
  const found = policy.find((p) => p.repo === repo)
  if (found) return { mergeMode: found.mergeMode, requiredApprovals: found.requiredApprovals }
  return { mergeMode: 'manual', requiredApprovals: 1 }
}

// === SCHEMAS ===

const DETECT_SCHEMA = {
  type: 'object',
  required: ['repo', 'branch', 'prId', 'prTitle', 'isDocOnlyRepo'],
  properties: {
    repo:            { type: 'string',  description: 'Repo slug (last path segment of git remote)' },
    repoFullPath:    { type: 'string',  description: 'Owner/repo, e.g. workspace/name' },
    branch:          { type: 'string',  description: 'Current branch name' },
    prId:            { type: ['integer', 'null'], description: 'PR id, null if no open PR found' },
    prTitle:         { type: 'string',  description: 'PR title (empty string if no PR)' },
    prUrl:           { type: 'string',  description: 'Full PR URL (empty string if no PR)' },
    ticketId:        { type: ['string', 'null'], description: 'Extracted ticket id like ABC-123' },
    isDocOnlyRepo:   { type: 'boolean', description: 'true if no Makefile/build config and only .md/.txt changes' },
    cwd:             { type: 'string',  description: 'Absolute path to the repo root' },
  },
}

const LOCAL_READY_SCHEMA = {
  type: 'object',
  required: ['dirty', 'pushed', 'formatterRan', 'hooksRan'],
  properties: {
    dirty:         { type: 'boolean', description: 'true if uncommitted changes remain after hooks ran' },
    pushed:        { type: 'boolean', description: 'true if a push occurred or was unnecessary' },
    formatterRan:  { type: 'boolean', description: 'true if a project formatter was detected and run' },
    formatterCmd:  { type: 'string',  description: 'The exact command used to run the formatter, empty if none' },
    hooksRan:      { type: 'boolean', description: 'true if pre-commit hooks ran on changed files' },
    stopReason:    { type: 'string',  description: 'Reason for stopping, empty if no stop' },
    diffSummary:   { type: 'string',  description: 'Brief summary of remaining dirty changes if any' },
  },
}

const CI_SCHEMA = {
  type: 'object',
  required: ['state', 'failingSteps'],
  properties: {
    state:         { type: 'string', enum: ['green', 'red', 'running', 'unknown'] },
    pipelineId:    { type: ['string', 'null'] },
    pipelineUrl:   { type: 'string', description: 'Empty if unknown' },
    failingSteps:  { type: 'array',  items: { type: 'string' } },
  },
}

const APPROVAL_SCHEMA = {
  type: 'object',
  required: ['count', 'missing'],
  properties: {
    count:    { type: 'integer', description: 'Approvals already given' },
    missing:  { type: 'array', items: { type: 'string' }, description: 'Reviewers requested but not yet approving' },
  },
}

const MERGE_SCHEMA = {
  type: 'object',
  required: ['mergeable', 'hasConflicts', 'unresolvedThreads'],
  properties: {
    mergeable:         { type: 'boolean' },
    hasConflicts:      { type: 'boolean' },
    unresolvedThreads: { type: 'integer', description: 'Open review threads count' },
  },
}

const TICKET_SCHEMA = {
  type: 'object',
  required: ['ticketId', 'status'],
  properties: {
    ticketId:        { type: ['string', 'null'] },
    status:          { type: 'string', description: 'Current ticket status, empty if no ticket' },
    availableTransitions: { type: 'array', items: { type: 'string' } },
  },
}

// === PHASES ===

const args_ = typeof args !== 'undefined' ? args : {}
const dryRun = args_.dryRun === true
const argPr = parsePrArg(args_.pr ?? null)

phase('Detect')

const detectPrompt = `
You are the Detect phase of the close-pr workflow.

Run these checks using Bash with git -C <path> (never cd && git):

1. Determine the repo root: \`git -C "$PWD" rev-parse --show-toplevel\`
2. Read the origin URL: \`git -C <repo-root> remote get-url origin\`. Extract owner/repo.
3. Get the current branch: \`git -C <repo-root> rev-parse --abbrev-ref HEAD\`
4. ${
  argPr
    ? `The user passed --pr=${JSON.stringify(argPr)}; use it instead of looking up by branch.`
    : `Find the open PR for this branch using ${PLATFORM_CLI} ${PLATFORM_FLAGS} pr list filtering by branch. If multiple, pick the most recent open one.`
}
5. Fetch the PR title and full URL.
6. Extract a ticket id matching /(${TICKET_PREFIX_REGEX_SOURCE})-\\d+/ from the branch name or PR title.
7. Detect doc-only repo: no Makefile AND no package.json AND no pyproject.toml AND no setup.py at the root, AND the PR diff touches only .md or .txt files. Set isDocOnlyRepo accordingly.

Return a JSON object matching the DETECT_SCHEMA. If no PR is found, set prId to null and prTitle/prUrl to empty strings.
`

const ctx = await agent(detectPrompt, { schema: DETECT_SCHEMA, label: 'detect' })

if (!ctx || ctx.prId == null) {
  log('No open PR found for the current branch.')
  log('Next: open a PR first, then re-run /close-pr.')
  return { stop: 'no-pr', ctx }
}

const repoPolicy = classifyRepo(ctx.repoFullPath, REPO_POLICY)
log(`Repo policy: ${repoPolicy.mergeMode} mode, ${repoPolicy.requiredApprovals} required approval(s)`)

phase('LocalReady')

if (ctx.isDocOnlyRepo) {
  log('Doc-only repo detected — stopping at Phase 2 by policy. Author reviews diff manually.')
  return { stop: 'doc-repo-no-autocommit', ctx, repoPolicy }
}

const localReadyPrompt = `
You are the LocalReady phase of the close-pr workflow.
Repo root: ${ctx.cwd}
Branch: ${ctx.branch}
dryRun: ${dryRun}

Steps:
1. Detect a formatter target:
   - If \`${ctx.cwd}/Makefile\` has a target named "format", set formatterCmd to "make -C ${ctx.cwd} format".
   - Else if \`${ctx.cwd}/package.json\` contains a "format" script, set formatterCmd to "npm --prefix ${ctx.cwd} run format".
   - Else if \`${ctx.cwd}/Cargo.toml\` exists, set formatterCmd to "cargo fmt --manifest-path ${ctx.cwd}/Cargo.toml".
   - Else leave formatterCmd empty.
2. If formatterCmd is set${dryRun ? ' AND dryRun is false (it is true — skip running)' : ''}: run it. Capture stdout/stderr.
3. Compute changed files relative to the merge base with the default branch:
   \`git -C ${ctx.cwd} fetch origin --quiet && git -C ${ctx.cwd} diff --name-only origin/HEAD...HEAD\`
   (If origin/HEAD is not set, fall back to origin/main, then origin/master.)
4. Run scoped pre-commit on changed files only (never --all-files):
   \`pre-commit run --files <space-separated-changed-files>\` from ${ctx.cwd}.
   If pre-commit is not installed in this repo, skip and set hooksRan to false.
5. Check for remaining dirty state: \`git -C ${ctx.cwd} status --porcelain\`. If output non-empty, set dirty=true and put a brief summary in diffSummary; do NOT push, set stopReason to "dirty-tree-after-hooks".
6. If clean, check whether the local branch is ahead of origin: \`git -C ${ctx.cwd} rev-list --count origin/${ctx.branch}..${ctx.branch}\` (handle the case where the remote branch does not yet exist by treating it as ahead).
7. If ahead${dryRun ? ' AND dryRun is false (it is true — skip pushing, set pushed=true and note dry-run)' : ''}: push with \`git -C ${ctx.cwd} push origin ${ctx.branch}\`. Never pass --no-verify.

Return a JSON object matching LOCAL_READY_SCHEMA.
`

const localState = await agent(localReadyPrompt, { schema: LOCAL_READY_SCHEMA, label: 'local-ready' })

if (localState.dirty) {
  log(`Stopping: ${localState.stopReason || 'dirty tree after hooks'}`)
  log(`Diff: ${localState.diffSummary}`)
  log('Next: review changes, commit or revert, then re-run /close-pr.')
  return { stop: 'dirty', ctx, repoPolicy, localState }
}

phase('RemotePoll')

const ciPrompt = `Fetch CI pipeline state for PR ${ctx.prId} in repo ${ctx.repoFullPath} using ${PLATFORM_CLI} ${PLATFORM_FLAGS}. Return state ("green"|"red"|"running"|"unknown"), pipelineId, pipelineUrl, and failingSteps array.`
const approvalPrompt = `Fetch reviewer approvals for PR ${ctx.prId} in ${ctx.repoFullPath} using ${PLATFORM_CLI} ${PLATFORM_FLAGS}. Return count and array of missing reviewer names.`
const mergePrompt = `Fetch mergeability and review-thread state for PR ${ctx.prId} in ${ctx.repoFullPath} using ${PLATFORM_CLI} ${PLATFORM_FLAGS}. Return mergeable, hasConflicts, unresolvedThreads count.`
const ticketPrompt = `Fetch the status of ticket ${ctx.ticketId ?? 'NONE'} using your tracker CLI. If no ticket, return ticketId=null, status="", availableTransitions=[].`

const [ci, approval, merge, ticket] = await parallel([
  () => agent(ciPrompt,       { schema: CI_SCHEMA,       label: 'ci' }),
  () => agent(approvalPrompt, { schema: APPROVAL_SCHEMA, label: 'approvals' }),
  () => agent(mergePrompt,    { schema: MERGE_SCHEMA,    label: 'mergeability' }),
  () => agent(ticketPrompt,   { schema: TICKET_SCHEMA,   label: 'ticket' }),
])

const signals = { ci, approval, merge, ticket }

phase('Decision')

const reasons = []
if (!ci || ci.state !== 'green') reasons.push(`CI not green (state=${ci?.state}, failing=${(ci?.failingSteps || []).join(',')})`)
if (!merge || merge.hasConflicts) reasons.push('Merge conflicts present')
if (!merge || !merge.mergeable) reasons.push('PR not mergeable')
if (merge && merge.unresolvedThreads > 0) reasons.push(`${merge.unresolvedThreads} unresolved review thread(s)`)
if (!approval || approval.count < repoPolicy.requiredApprovals) reasons.push(`Need ${repoPolicy.requiredApprovals} approvals, have ${approval?.count ?? 0}; missing: ${(approval?.missing || []).join(',')}`)

const verdict = { stop: reasons.length > 0, reasons }

if (verdict.stop) {
  log('Decision gate STOP:')
  for (const r of reasons) log(`  - ${r}`)
  log(`Next: address the items above. Pipeline URL: ${ci?.pipelineUrl || 'unknown'}`)
  log('Resume: re-run /close-pr once the above are resolved.')
  return { stop: 'decision-gate', ctx, repoPolicy, signals, verdict }
}

phase('Merge')

let mergeResult
if (dryRun) {
  log(`Dry-run: would attempt ${repoPolicy.mergeMode} merge here.`)
  mergeResult = { dryRun: true, mode: repoPolicy.mergeMode }
} else if (repoPolicy.mergeMode === 'auto') {
  const explicitTicketLink = ctx.ticketId
    ? `[${ctx.ticketId}](${TRACKER_BASE_URL}/${ctx.ticketId})`
    : '(no ticket linked)'

  const autoMergePrompt = `
You are the Merge phase for an auto-merge repo (${ctx.repoFullPath}).
Required approvals reached. Action sequence:
1. Post a review comment via ${PLATFORM_CLI} ${PLATFORM_FLAGS} that includes the explicit cross-tenant ticket link: ${explicitTicketLink}.
2. Approve the PR via ${PLATFORM_CLI} ${PLATFORM_FLAGS}.
3. Verify final state with a fresh \`${PLATFORM_CLI} ${PLATFORM_FLAGS} pr get ${ctx.prId}\`.
Return a JSON object: {posted: boolean, approved: boolean, finalState: string, merged: boolean}
`
  mergeResult = await agent(autoMergePrompt, {
    schema: {
      type: 'object',
      required: ['posted', 'approved', 'finalState', 'merged'],
      properties: {
        posted:     { type: 'boolean' },
        approved:   { type: 'boolean' },
        finalState: { type: 'string' },
        merged:     { type: 'boolean' },
      },
    },
    label: 'auto-merge',
  })
} else {
  const mergeCmd = `${PLATFORM_CLI} ${PLATFORM_FLAGS} pr merge ${ctx.prId}`
  log(`Manual-merge repo. STOP before irreversible action.`)
  log(`Next: ${mergeCmd}`)
  log(`Resume: re-run /close-pr after merge lands on main.`)
  return { stop: 'manual-merge-pending', ctx, repoPolicy, signals, verdict, mergeCmd }
}

phase('Cleanup')

let cleanup = { localDeleted: false, remoteDeleted: false, skipped: dryRun }

if (!dryRun) {
  const cleanupAgentPrompt = `
You are the Cleanup phase. The PR has merged.
1. Switch to the default branch: \`git -C ${ctx.cwd} checkout main || git -C ${ctx.cwd} checkout master\`.
2. Pull latest: \`git -C ${ctx.cwd} pull --ff-only\`.
3. Delete the local feature branch: \`git -C ${ctx.cwd} branch -d ${ctx.branch}\` (use -d, not -D, so unmerged branches fail loud).
4. DO NOT delete the remote branch yet. Just return localDeleted state.
Return JSON: {localDeleted: boolean, error: string}
`
  const localCleanup = await agent(cleanupAgentPrompt, {
    schema: {
      type: 'object',
      required: ['localDeleted'],
      properties: { localDeleted: { type: 'boolean' }, error: { type: 'string' } },
    },
    label: 'cleanup-local',
  })

  cleanup.localDeleted = localCleanup.localDeleted

  log(`Local branch ${ctx.branch} delete: ${cleanup.localDeleted ? 'OK' : `FAILED (${localCleanup.error || 'unknown'})`}`)
  log(`Remote branch ${ctx.branch} on ${ctx.repoFullPath}: NOT deleted automatically.`)
  log(`To delete the remote branch run: ${PLATFORM_CLI} ${PLATFORM_FLAGS} branch delete ${ctx.branch}`)
  log(`Per-branch confirmation is required by policy (never bulk-delete remote branches).`)
}

phase('TicketTransition')

let ticketResult = { skipped: dryRun || !ctx.ticketId, transitioned: false }

if (!dryRun && ctx.ticketId) {
  const desiredTransitions = ['Done', 'Closed', 'Resolved']
  const available = signals.ticket?.availableTransitions || []
  const match = desiredTransitions.find((d) => available.includes(d))

  if (match) {
    const ticketPrompt = `Transition ticket ${ctx.ticketId} to status "${match}" via your tracker CLI. Return JSON: {transitioned: boolean, newStatus: string, error: string}`
    ticketResult = await agent(ticketPrompt, {
      schema: {
        type: 'object',
        required: ['transitioned'],
        properties: {
          transitioned: { type: 'boolean' },
          newStatus:    { type: 'string' },
          error:        { type: 'string' },
        },
      },
      label: 'ticket-transition',
    })
    log(`Ticket ${ctx.ticketId} → ${ticketResult.newStatus || match}: ${ticketResult.transitioned ? 'OK' : `FAILED (${ticketResult.error || 'unknown'})`}`)
  } else {
    log(`Ticket ${ctx.ticketId} has no Done/Closed/Resolved transition available (have: ${available.join(',')}).`)
    log(`Suggested: transition manually in the tracker UI or via CLI.`)
    ticketResult = { skipped: true, reason: 'no-matching-transition', available }
  }
}

phase('MemoryCommit')

let memory = { skipped: dryRun, committed: false }

if (!dryRun) {
  const summary = `Closed PR ${ctx.repoFullPath}#${ctx.prId} (${ctx.prTitle}); ticket ${ctx.ticketId || 'none'}.`
  const memPrompt = `
Commit a memory episode for this PR close.
Project: <PROJECT_SLUG>
Type: task
Summary: ${summary}
Include in the body:
- PR URL: ${ctx.prUrl}
- Ticket: ${ctx.ticketId ? `[${ctx.ticketId}](${TRACKER_BASE_URL}/${ctx.ticketId})` : 'none'}
- Repo: ${ctx.repoFullPath}
- Merge mode: ${repoPolicy.mergeMode}
- CI: ${signals.ci?.state}
- Approvals: ${signals.approval?.count}
Populate repos=[${JSON.stringify(ctx.repo)}], tags=["close-pr", "<TAG_PROJECT>"], related_keys=[].
Return JSON: {committed: boolean, memId: string, error: string}
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

log(`Merge landed on main. To follow the deploy pipeline, run /post-merge-validation`)

return {
  closed: true,
  ctx,
  repoPolicy,
  signals,
  verdict,
  mergeResult,
  cleanup,
  ticketResult,
  memory,
}
