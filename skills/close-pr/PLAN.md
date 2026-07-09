# `/close-pr` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `/close-pr` slash command that takes an author's PR from "implementation done" to "merged + archived" deterministically, in two artifact pairs: a generic public reference (this repo) and a concrete private instance (`~/.claude/`).

**Architecture:** A skill manifest (`SKILL.md`) is the surface — Claude Code reads it when the user types `/close-pr` and dispatches a workflow script. The workflow script orchestrates phased agent dispatches: detect → local-ready → remote-poll → decision → merge → cleanup → ticket → memory. Each phase agent uses Bash + Read tools to do the actual git/CLI work and returns structured JSON via the workflow tool's `schema` option. The workflow itself is pure orchestration; it cannot run shell commands directly (Workflow tool sandbox restriction).

**Tech Stack:**
- Markdown (skill manifests, design, this plan)
- JavaScript (workflow orchestration scripts running inside the Workflow tool sandbox)
- Bash + platform CLI inside agent prompts (atlassian-cli, gh, git, make — whichever the user's environment provides)

## Global Constraints

- Workflow scripts run in a sandboxed JS context: **no `require`, no filesystem, no Node API, no `Date.now()`, no `Math.random()`, no argless `new Date()`**. Stamp timestamps via `args` if needed. Standard JS built-ins (JSON, Math, Array) are available.
- Each phase **must** dispatch an `agent()` call to do real work; the workflow script alone cannot run shell commands.
- Public artifacts (this repo) must contain **no internal identifiers**: no real repo names, no platform profile names, no workspace IDs, no tracker prefixes, no host URLs. Use placeholders: `<PLATFORM_CLI>`, `<WORKSPACE>`, `<TICKET_PREFIX>`, `<TRACKER_BASE_URL>`.
- Hard rails non-configurable: never bulk-delete remote branches, never `--no-verify`, never `pre-commit --all-files`, always `git -C <path>` instead of `cd && git`, split compound bash to avoid security-prompt traps.
- Source spec: `skills/close-pr/DESIGN.md` (this directory). Every task implements something the spec calls for.
- Use TDD where pure JS helpers exist (URL parsing, ticket extraction, repo policy lookup). For phase orchestration, use manual smoke tests in `--dry-run` mode against a known PR.
- Do not auto-commit in this repo (per the author's no-autocommit-in-doc-repos rule). Leave changes as unstaged diffs and prompt the user before each commit.

---

## File Structure

```
skills/close-pr/
├── DESIGN.md                          (already exists)
├── PLAN.md                            (this file)
├── SKILL.md                           (Task 1 — creates)
├── close-pr.example.js                (Tasks 2-4 — creates + extends)
├── helpers/
│   └── pure.test.js                   (Task 2 — unit tests for pure helpers)
└── tests/
    └── smoke.md                       (Task 5 — manual smoke test procedure)
```

```
README.md                              (Task 7 — modifies: add close-pr row)
```

```
~/.claude/skills/close-pr/
└── SKILL.md                           (Task 6 — creates; thin wrapper)

~/.claude/workflows/
└── close-pr.js                        (Task 6 — creates; concrete instance)
```

Responsibilities:

- `SKILL.md` (public): trigger phrases, behavior summary, configuration guidance, link to DESIGN.md. Adapter-shaped: anyone can copy it and fill in their environment.
- `close-pr.example.js`: complete reference workflow with placeholders. Self-contained. Demonstrates every phase, every safety rail, every schema.
- `helpers/pure.test.js`: node:test unit tests for the pure functions inside the workflow (URL parsing, repo policy lookup). The functions themselves live inline in `close-pr.example.js`; the test file duplicates them in a `// === PURE HELPERS (mirrored from close-pr.example.js) ===` block. We accept the duplication because the Workflow sandbox cannot import.
- `tests/smoke.md`: end-to-end procedure: dry-run, observe each phase, expected outputs.
- Private `SKILL.md`: identical body to public, but its description names the private workflow path.
- Private `close-pr.js`: the example with placeholders replaced by concrete values.

---

## Task 1: Public SKILL.md

**Files:**
- Create: `skills/close-pr/SKILL.md`

**Interfaces:**
- Consumes: nothing
- Produces: skill trigger surface (Claude Code picks up `/close-pr` based on this file's frontmatter)

- [ ] **Step 1: Write the SKILL.md file**

````markdown
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

````

- [ ] **Step 2: Verify Claude Code can see the skill**

Reload Claude Code skill index (open a new session or restart the CLI). Type `/close-pr` at a prompt and confirm the skill description appears in the suggestion list. Expected: skill name `close-pr` and the description from frontmatter.

- [ ] **Step 3: Show diff, ask user before committing**

Run:
```bash
git -C /path/to/usefull_agent_skills diff --stat skills/close-pr/SKILL.md
git -C /path/to/usefull_agent_skills status -s skills/close-pr/
```

Print the diff summary to the user. Ask: "Commit `skills/close-pr/SKILL.md` now, or wait until Task 2 lands?" Default: wait — see Task 7 for the combined commit point.

---

## Task 2: Public workflow — meta, pure helpers, Phase 1 (Detect)

**Files:**
- Create: `skills/close-pr/close-pr.example.js`
- Create: `skills/close-pr/helpers/pure.test.js`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `meta` export (workflow tool reads it for the permission dialog)
  - `parsePrArg(arg: string|null): {repo: string|null, prId: number|null} | null`
  - `extractTicketId(branchName: string, prTitle: string, prefixRegex: RegExp): string|null`
  - `classifyRepo(repo: string, policy: Array<{repo, mergeMode, requiredApprovals}>): {mergeMode: 'auto'|'manual', requiredApprovals: number}`
  - A `DETECT_SCHEMA` JSON Schema describing the Phase 1 agent output
  - Phase 1 (`Detect`) calling `agent(prompt, {schema: DETECT_SCHEMA})` and returning the structured context

- [ ] **Step 1: Write failing tests for the pure helpers**

Create `skills/close-pr/helpers/pure.test.js`:

```javascript
import { test } from 'node:test'
import assert from 'node:assert/strict'

// === PURE HELPERS (mirrored from close-pr.example.js) ===
// Keep these definitions identical to the inline copy in close-pr.example.js.
// The Workflow tool sandbox cannot import, which forces the duplication.

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

// === TESTS ===

test('parsePrArg handles URL form', () => {
  assert.deepEqual(
    parsePrArg('https://bitbucket.org/example/my-repo/pull-requests/42'),
    { repo: 'my-repo', prId: 42 }
  )
})

test('parsePrArg handles short form repo#id', () => {
  assert.deepEqual(parsePrArg('my-repo#42'), { repo: 'my-repo', prId: 42 })
})

test('parsePrArg returns null for empty', () => {
  assert.equal(parsePrArg(null), null)
  assert.equal(parsePrArg(''), null)
})

test('parsePrArg returns null for unparseable input', () => {
  assert.equal(parsePrArg('not-a-pr'), null)
})

test('extractTicketId finds ticket from branch name', () => {
  assert.equal(
    extractTicketId('feature/ABC-123-add-thing', 'add thing', /ABC|DEF/),
    'ABC-123'
  )
})

test('extractTicketId finds ticket from PR title when branch lacks it', () => {
  assert.equal(
    extractTicketId('feature/add-thing', 'DEF-456 add thing', /ABC|DEF/),
    'DEF-456'
  )
})

test('extractTicketId returns null when no ticket present', () => {
  assert.equal(extractTicketId('feature/add-thing', 'add thing', /ABC|DEF/), null)
})

test('classifyRepo returns policy entry for known repo', () => {
  const policy = [{ repo: 'auto-repo', mergeMode: 'auto', requiredApprovals: 3 }]
  assert.deepEqual(
    classifyRepo('auto-repo', policy),
    { mergeMode: 'auto', requiredApprovals: 3 }
  )
})

test('classifyRepo defaults to manual mode for unknown repo', () => {
  assert.deepEqual(
    classifyRepo('unknown', []),
    { mergeMode: 'manual', requiredApprovals: 1 }
  )
})
```

- [ ] **Step 2: Run tests, verify all fail**

Run:
```bash
cd /path/to/usefull_agent_skills && node --test skills/close-pr/helpers/pure.test.js
```

Expected: all 9 tests pass immediately because the helpers are defined inline in the test file. This is intentional — the test file is the canonical home of the helper definitions for verification. The next step writes the example workflow that mirrors them.

- [ ] **Step 3: Write `close-pr.example.js` with meta, helpers, schemas, Phase 1**

Create `skills/close-pr/close-pr.example.js`:

```javascript
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
  const urlMatch = arg.match(/\/([^/]+)\/pull(?:-requests)?\/(\d+)\/?$/)
  if (urlMatch) return { repo: urlMatch[1], prId: parseInt(urlMatch[2], 10) }
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

// === NEXT PHASES IMPLEMENTED IN TASK 3 ===
// LocalReady, RemotePoll (parallel barrier), Decision gate

return { stop: 'task-2-stub', ctx, repoPolicy }
```

- [ ] **Step 4: Re-run helper tests; verify they still pass**

Run:
```bash
node --test /path/to/usefull_agent_skills/skills/close-pr/helpers/pure.test.js
```

Expected: 9 tests pass. If anything fails, the inline helpers in `close-pr.example.js` have drifted from the test file — fix the drift before proceeding.

- [ ] **Step 5: Show diff, do not commit yet**

Run:
```bash
git -C /path/to/usefull_agent_skills status -s skills/close-pr/
```

Expected output: two new files, `close-pr.example.js` and `helpers/pure.test.js`, both untracked. Do not commit — Task 7 batches the public-repo commit.

---

## Task 3: Public workflow — Phases 2-4 (LocalReady, RemotePoll, Decision)

**Files:**
- Modify: `skills/close-pr/close-pr.example.js` (replace the `// === NEXT PHASES IMPLEMENTED IN TASK 3 ===` stub block and the trailing `return { stop: 'task-2-stub' ... }`)

**Interfaces:**
- Consumes: `ctx`, `repoPolicy`, `dryRun` from Task 2
- Produces:
  - `LOCAL_READY_SCHEMA`, `CI_SCHEMA`, `APPROVAL_SCHEMA`, `MERGE_SCHEMA`, `TICKET_SCHEMA` JSON Schemas
  - `signals` object: `{ci, approval, merge, ticket}` available to later phases
  - `verdict` object: `{stop: boolean, reasons: string[]}` available to later phases

- [ ] **Step 1: Append schemas to `close-pr.example.js`**

Insert above the `// === PHASES ===` line (or after the existing `DETECT_SCHEMA`):

```javascript
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
```

- [ ] **Step 2: Replace the Task 2 stub with Phase 2 (LocalReady)**

Replace this exact block at the end of the file:

```javascript
// === NEXT PHASES IMPLEMENTED IN TASK 3 ===
// LocalReady, RemotePoll (parallel barrier), Decision gate

return { stop: 'task-2-stub', ctx, repoPolicy }
```

with:

```javascript
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

// === NEXT PHASES IMPLEMENTED IN TASK 4 ===
// Merge, Cleanup, TicketTransition, MemoryCommit

return { stop: 'task-3-stub', ctx, repoPolicy, signals, verdict }
```

- [ ] **Step 3: Sanity-load the workflow via the Workflow tool in dry-run**

In a Claude Code session positioned in a repo with an open low-stakes PR, invoke:

```
Workflow({
  scriptPath: '/path/to/usefull_agent_skills/skills/close-pr/close-pr.example.js',
  args: { pr: null, dryRun: true }
})
```

Expected: workflow runs Phase 1 → Phase 2 → Phase 3 → Phase 4 and returns `{ stop: 'task-3-stub', ... }` populated with `ctx`, `repoPolicy`, `signals`, `verdict`. If the workflow errors on `<PLATFORM_CLI>` (since it is still a placeholder), that is expected — Task 6 is where placeholders get replaced. For now, validate that the workflow loads, that placeholder substitution sites are obvious in the error output, and that phases progress in order via the progress UI.

If the smoke load fails for a non-placeholder reason (syntax error, missing schema field), fix inline before continuing.

- [ ] **Step 4: Re-run unit tests to confirm no helper drift**

```bash
node --test /path/to/usefull_agent_skills/skills/close-pr/helpers/pure.test.js
```

Expected: 9 tests pass.

- [ ] **Step 5: Status check, no commit**

```bash
git -C /path/to/usefull_agent_skills status -s skills/close-pr/close-pr.example.js
```

Expected: file modified, still untracked or with the prior Task 2 add staged depending on user's choice. No commit yet.

---

## Task 4: Public workflow — Phases 5-8 (Merge, Cleanup, TicketTransition, MemoryCommit)

**Files:**
- Modify: `skills/close-pr/close-pr.example.js` (replace the `// === NEXT PHASES IMPLEMENTED IN TASK 4 ===` stub and trailing `return`)

**Interfaces:**
- Consumes: `ctx`, `repoPolicy`, `signals`, `verdict`, `dryRun` from Task 3
- Produces: terminal workflow return value `{ closed: boolean, ctx, signals, verdict, merge, cleanup, ticketResult, memory }`

- [ ] **Step 1: Replace the Task 3 stub with Phases 5-8**

Replace this block:

```javascript
// === NEXT PHASES IMPLEMENTED IN TASK 4 ===
// Merge, Cleanup, TicketTransition, MemoryCommit

return { stop: 'task-3-stub', ctx, repoPolicy, signals, verdict }
```

with:

```javascript
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
```

- [ ] **Step 2: Smoke-test the full pipeline in dry-run**

In a Claude Code session in a repo with an open low-stakes PR:

```
Workflow({
  scriptPath: '/path/to/usefull_agent_skills/skills/close-pr/close-pr.example.js',
  args: { pr: null, dryRun: true }
})
```

Expected: all 8 phases run; phases 5-8 print dry-run notices instead of acting. Final return value includes `closed: true` and a populated `mergeResult`, `cleanup`, `ticketResult`, `memory` (each marked `dryRun: true` / `skipped: true`). If any phase errors on the `<PLACEHOLDER>` strings, that confirms substitution is still required — expected. The point of this smoke test is the orchestration shape, not the platform CLI being correct.

- [ ] **Step 3: Re-run unit tests for helpers**

```bash
node --test /path/to/usefull_agent_skills/skills/close-pr/helpers/pure.test.js
```

Expected: 9 tests pass.

- [ ] **Step 4: Status check, no commit yet**

```bash
git -C /path/to/usefull_agent_skills status -s skills/close-pr/
```

Expected: SKILL.md, close-pr.example.js, helpers/pure.test.js all untracked. PLAN.md and DESIGN.md present (DESIGN.md already exists). No commit yet — Task 7 batches.

---

## Task 5: Smoke test procedure document

**Files:**
- Create: `skills/close-pr/tests/smoke.md`

**Interfaces:**
- Consumes: nothing
- Produces: a written procedure another maintainer can follow to verify the workflow end-to-end

- [ ] **Step 1: Create the smoke test doc**

```markdown
# close-pr smoke test

Run these checks after any non-trivial change to `close-pr.example.js` or a private instance.

## Prerequisites

- A repo with an open, low-stakes PR (a typo fix, a comment change — something safe to merge).
- The private workflow at `~/.claude/workflows/close-pr.js` configured with your concrete platform CLI, profile, ticket prefix, tracker base URL, and (if applicable) auto-merge repo registry.
- All platform CLIs authenticated (`<PLATFORM_CLI> auth test` returns OK).

## 1. Pure helper unit tests

From this repo root:

```bash
node --test skills/close-pr/helpers/pure.test.js
```

Expected: all 9 tests pass. No external dependencies needed.

## 2. Dry-run on the example workflow

In a Claude Code session positioned in the PR's repo:

```
Workflow({
  scriptPath: '<absolute-path>/skills/close-pr/close-pr.example.js',
  args: { pr: null, dryRun: true }
})
```

Expected progress UI: phases Detect → LocalReady → RemotePoll → Decision → Merge → Cleanup → TicketTransition → MemoryCommit all execute or print dry-run notices.

Expected final return shape:
- `closed: true`
- `ctx`: populated `repo`, `branch`, `prId`, `prTitle`, `ticketId`
- `signals`: CI, approval, merge, ticket entries each present
- `mergeResult.dryRun: true`
- `cleanup.skipped: true`
- `ticketResult.skipped: true`
- `memory.skipped: true`

If any phase errors on a `<PLACEHOLDER>` string, that confirms the public example needs substitution before real use. That is expected — the public version is a reference, not a runnable instance.

## 3. Dry-run on the private workflow

```
Workflow({
  name: 'close-pr',
  args: { pr: null, dryRun: true }
})
```

Expected: same shape as above, but every CLI call succeeds because placeholders are now concrete. Verify the printed CI status, approval count, ticket id match what you see in the platform UI.

## 4. Real-run on the private workflow

Once dry-runs are clean, run for real:

```
Workflow({
  name: 'close-pr',
  args: { pr: null, dryRun: false }
})
```

Expected for an auto-merge repo: comment posted, approval given, `pr get` confirms merged state, local branch deleted, ticket transitioned, memory episode written.

Expected for a manual repo: workflow stops with `stop: 'manual-merge-pending'` and prints the exact `pr merge` command to run.

## 5. Failure paths to verify at least once each

- **No PR open on current branch**: workflow stops at Phase 1 with `stop: 'no-pr'`.
- **Dirty working tree**: stage a dummy change, re-run; workflow stops at Phase 2 with `stop: 'dirty'` and prints diff summary.
- **CI red**: when a build fails on a feature branch, workflow stops at Phase 4 listing the failing steps.
- **Missing approvals**: open a PR, do not approve, re-run; workflow stops at Phase 4 listing missing reviewers.
- **Doc-only repo**: in a repo with no Makefile/package.json/pyproject and only .md changes, workflow stops at Phase 2 with `stop: 'doc-repo-no-autocommit'`.

After each failure path, the printed `Next:` and `Resume:` lines should be copy-pasteable. If they are not, fix the phase that produced them.
```

- [ ] **Step 2: Status check**

```bash
git -C /path/to/usefull_agent_skills status -s skills/close-pr/tests/
```

Expected: `tests/smoke.md` listed as untracked.

---

## Task 6: Private skill and workflow instance

**Files:**
- Create: `~/.claude/skills/close-pr/SKILL.md`
- Create: `~/.claude/workflows/close-pr.js`

**Interfaces:**
- Consumes: public `close-pr.example.js` as the source template; private config values from the user's environment
- Produces: a runnable `/close-pr` slash command bound to a registered workflow named `close-pr`

- [ ] **Step 1: Create the private skill directory and SKILL.md**

```bash
mkdir -p ~/.claude/skills/close-pr
```

Then create `~/.claude/skills/close-pr/SKILL.md`. Use the public `SKILL.md` as the base; change two things:

1. The frontmatter `description` line keeps the same trigger phrases.
2. The "How Claude invokes this skill" section already references `Workflow({name: 'close-pr', ...})` — this is correct because the workflow file at `~/.claude/workflows/close-pr.js` registers under that name.

If you want the private skill to be a thin wrapper rather than a full duplicate, replace the body with:

```markdown
See the generic reference at `~/workspace/github.com/usefull_agent_skills/skills/close-pr/SKILL.md`.

Invoke via:

```javascript
Workflow({
  name: 'close-pr',
  args: { pr: <arg-or-null>, dryRun: <--dry-run-flag> }
})
```
```

The thin-wrapper form is preferred — less duplication, the canonical doc stays in the public repo.

- [ ] **Step 2: Create `~/.claude/workflows/close-pr.js` from the example**

```bash
mkdir -p ~/.claude/workflows
cp /path/to/usefull_agent_skills/skills/close-pr/close-pr.example.js ~/.claude/workflows/close-pr.js
```

Then open the copied file and replace each placeholder with the user's concrete value. Ask the user for each value rather than assuming — these are environment-specific:

- `<PLATFORM_CLI>` (e.g. `atlassian-cli`)
- `<PLATFORM_FLAGS>` (e.g. `--profile myprofile --workspace myworkspace`)
- `<TRACKER_BASE_URL>` (e.g. `https://<your-tracker>/browse`)
- `<TICKET_PREFIX>` (e.g. `ABC|DEF` — the alternation for ticket key prefixes in your tracker)
- `REPO_POLICY` (start empty; add entries `{ repo, mergeMode, requiredApprovals, note }` as you identify auto-merge repos)
- `<PROJECT_SLUG>` and `<TAG_PROJECT>` inside the memory commit prompt (e.g. your project slug used by your memory MCP server)

Ask the user to paste each value. Do NOT guess. After substitution, the file should contain zero `<` and zero `>` characters that look like a placeholder marker (literal `<` in regex source is fine if any exist).

Quick check:
```bash
grep -nE '<[A-Z_]+>' ~/.claude/workflows/close-pr.js || echo "No placeholders remain"
```

Expected: `No placeholders remain`.

- [ ] **Step 3: Register the private workflow with Claude Code**

If Claude Code requires explicit workflow registration (varies by version), use the documented registration path. If workflows under `~/.claude/workflows/` are auto-discovered by name, no registration step is needed — verify with:

```
Workflow({ name: 'close-pr', args: { dryRun: true } })
```

Expected: the workflow either runs (auto-discovered) or returns "unknown workflow name" (requires registration). If the latter, follow Claude Code's workflow registration docs and re-test.

- [ ] **Step 4: Dry-run on a known PR**

In a repo with an open low-stakes PR, run:

```
Workflow({
  name: 'close-pr',
  args: { pr: null, dryRun: true }
})
```

Expected: every phase prints sensible output, no `<PLACEHOLDER>` strings appear in errors, and the final return shape matches the smoke-test expectation in `tests/smoke.md`.

If anything looks wrong, fix in `~/.claude/workflows/close-pr.js` and re-run.

- [ ] **Step 5: Do not commit the private files**

They live under `~/.claude/`, which is not a tracked git location for this repo. No commit step. Confirm by checking the public repo's status:

```bash
git -C /path/to/usefull_agent_skills status -s
```

Expected: nothing under `.claude/` (the directory is outside the worktree).

---

## Task 7: README.md update + public-repo commit

**Files:**
- Modify: `/path/to/usefull_agent_skills/README.md`

**Interfaces:**
- Consumes: the public skill artifacts produced by Tasks 1-5
- Produces: an updated skills index in the README and a single commit batching the public-repo additions

- [ ] **Step 1: Read the existing skills table**

```bash
sed -n '7,21p' /path/to/usefull_agent_skills/README.md
```

Expected: the existing markdown table with columns `Skill | What it covers | Use when` and ten rows. Note the alphabetical / topical ordering it currently uses.

- [ ] **Step 2: Add a row for close-pr**

Open `README.md` and insert a new row in the skills table. Place it near logically-related skills (atlassian-cli-usage, cross-repo-epic-review). Suggested row:

```markdown
| [`close-pr`](skills/close-pr/SKILL.md) | Author-side PR close workflow: format, push, poll, merge, cleanup, ticket transition, memory commit | You finished a PR and want to take it from "implementation done" to "merged + archived" deterministically |
```

- [ ] **Step 3: Show diff to user**

```bash
git -C /path/to/usefull_agent_skills diff README.md
git -C /path/to/usefull_agent_skills status -s
```

Print both outputs. Ask the user: "Diff above adds `close-pr` to the README. Plus untracked files in `skills/close-pr/`. Commit now?" Wait for explicit `yes` before committing.

- [ ] **Step 4: On user `yes`, commit the public-repo changes**

Stage explicitly (never `git add -A` per global instructions):

```bash
git -C /path/to/usefull_agent_skills add \
  README.md \
  skills/close-pr/SKILL.md \
  skills/close-pr/DESIGN.md \
  skills/close-pr/PLAN.md \
  skills/close-pr/close-pr.example.js \
  skills/close-pr/helpers/pure.test.js \
  skills/close-pr/tests/smoke.md
```

Then commit:

```bash
git -C /path/to/usefull_agent_skills commit -m "$(cat <<'EOF'
Add close-pr skill: author-side PR close workflow

Reference workflow + skill manifest for closing finished PRs via
phased orchestration (detect, local-ready, parallel remote poll,
decision gate, merge, cleanup, ticket transition, memory commit).
Public artifacts use placeholders; private instance lives under
~/.claude/.
EOF
)"
```

Do NOT add `Co-Authored-By: Claude` per global rules.

- [ ] **Step 5: Verify commit landed**

```bash
git -C /path/to/usefull_agent_skills log -1 --oneline
git -C /path/to/usefull_agent_skills status
```

Expected: log shows the new commit; status shows clean working tree.

---

## Task 8: Real-run validation on a low-stakes PR

**Files:**
- None (validation only)

**Interfaces:**
- Consumes: the private workflow registered in Task 6
- Produces: confirmed end-to-end behavior on a real PR; any drift surfaces as follow-up tasks

- [ ] **Step 1: Pick a real low-stakes PR**

Identify a real PR ready to close. Criteria: small diff, CI green, approvals already in, low blast radius if merge goes wrong. Ask the user for the URL or repo+id.

- [ ] **Step 2: Run dry-run first**

```
Workflow({
  name: 'close-pr',
  args: { pr: '<pr-url-or-repo#id-from-user>', dryRun: true }
})
```

Expected: phases 1-4 execute against real data and return `verdict.stop: false`. Phases 5-8 print dry-run notices. Final return: `closed: true`, dry-run flags set on action phases.

If `verdict.stop: true`, do not proceed — read the reasons and fix the underlying issue (CI, approvals, threads, conflicts) before continuing.

- [ ] **Step 3: Run for real**

```
Workflow({
  name: 'close-pr',
  args: { pr: '<same-arg>', dryRun: false }
})
```

Expected for an auto-merge repo:
- Phase 5 posts a review comment containing the explicit cross-tenant ticket link
- Phase 5 approves the PR
- Phase 5 verifies merged state via `pr get`
- Phase 6 deletes the local branch with `git branch -d`
- Phase 6 prints (does not run) the remote branch delete command
- Phase 7 transitions the ticket to Done/Closed/Resolved
- Phase 8 writes a memory episode and prints the handoff hint for `/post-merge-validation`

Expected for a manual-merge repo:
- Phase 5 stops with `stop: 'manual-merge-pending'` and prints the `pr merge` command
- You run that command manually; the workflow does not continue automatically

- [ ] **Step 4: Cross-check against the real-world state**

Independently verify in the platform UI: PR is merged, ticket is transitioned, branch is deleted on remote (if you ran the delete command). If anything is wrong, capture it as a follow-up:

- File a real bug if the workflow misbehaved
- Update the spec if the design was wrong
- Update this PLAN.md if a step was unclear

---

## Self-Review

### Spec coverage

Walking the DESIGN.md spec section by section:

- **Goal + non-goals** — Stated in PLAN header. Covered.
- **Surface** — Task 1 (SKILL.md). Slash command + optional arg + `--dry-run` flag.
- **Phases 1-8** — Tasks 2-4 implement them in three batches. Each phase maps to an `agent()` call with a schema.
- **Safety rails** — Embedded in phase prompts and the `SKILL.md` body. Task 1 lists them in the skill body; Tasks 3-4 implement the enforcement points (doc-only stop, dirty stop, hard-stop decision gate, manual-merge stop, no remote bulk delete, no `--no-verify`, no `--all-files`, explicit ticket link in auto-merge comment, dry-run honored).
- **Repo policy registry** — Task 2 declares it; classifyRepo helper tested in pure tests.
- **Argument contract** — Task 2's `parsePrArg`, `dryRun` flag honored across Tasks 3-4. `pollInterval`/`pollTimeout` not applicable to close-pr (they belong to post-merge-validation).
- **Failure UX** — Each phase prints `Stopping:` + `Next:` + `Resume:`. Verified in Task 5 smoke procedure.
- **Artifact split** — Task 2 produces public example, Task 6 produces private instance.
- **Implementation order** — Tasks 1-8 follow the spec's stated order.

### Placeholder scan

- No "TBD" / "TODO" / "fill in later" — verified.
- Every code step shows the actual code, not a description.
- The phrase `<PLACEHOLDER>` appears intentionally in the public reference and is explicitly called out as needing substitution in Task 6. Task 6 has a grep check to confirm substitution.
- Test code is present, not described.

### Type consistency

- `parsePrArg` returns `{repo, prId}` in both the test file (Task 2 Step 1) and the inline copy (Task 2 Step 3).
- `extractTicketId(branchName, prTitle, prefixRegex)` signature matches in both copies.
- `classifyRepo(repo, policy)` returns `{mergeMode, requiredApprovals}` consistently.
- `ctx` shape from `DETECT_SCHEMA` (Task 2) is consumed by Tasks 3-4 using the same property names: `ctx.repo`, `ctx.repoFullPath`, `ctx.branch`, `ctx.prId`, `ctx.prTitle`, `ctx.prUrl`, `ctx.ticketId`, `ctx.isDocOnlyRepo`, `ctx.cwd`.
- `signals.ci.state` enum (`green|red|running|unknown`) used identically in Phase 4's decision logic.
- `repoPolicy.mergeMode` enum (`auto|manual`) used identically in Phase 5's branching.
- No naming drift between tasks.
