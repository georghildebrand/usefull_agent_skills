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
