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
