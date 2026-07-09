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
