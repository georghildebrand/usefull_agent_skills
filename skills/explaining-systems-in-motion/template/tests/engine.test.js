const test = require("node:test");
const assert = require("node:assert/strict");
const { createEngine, createStory, ease } = require("../src/engine.js");

test("ease runs from 0 to 1", () => {
  assert.equal(ease(0), 0); assert.equal(ease(1), 1); assert.ok(Math.abs(ease(0.5) - 0.5) < 1e-9);
});

test("a tween reports progress and ends at 1", () => {
  const e = createEngine(); e.step(0); const seen = [];
  e.tween(100, t => seen.push(t));
  e.step(50); e.step(100); e.step(150);
  assert.deepEqual(seen, [0.5, 1]); assert.equal(e.pending(), 0);
});

test("a delayed tween waits for its start", () => {
  const e = createEngine(); e.step(0); const seen = [];
  e.tween(100, t => seen.push(t), 200);
  e.step(100); e.step(250);
  assert.deepEqual(seen, [0.5]);
});

test("instant mode applies the end state at once", () => {
  const e = createEngine(); e.setInstant(true); const seen = [];
  e.tween(500, t => seen.push(t), 900);
  assert.deepEqual(seen, [1]); assert.equal(e.pending(), 0);
});

test("cancelAll drops pending tweens", () => {
  const e = createEngine(); e.step(0); const seen = [];
  e.tween(100, t => seen.push(t)); e.cancelAll(); e.step(200);
  assert.deepEqual(seen, []); assert.equal(e.pending(), 0);
});

test("later fires exactly once after its delay", () => {
  const e = createEngine(); e.step(0); let n = 0;
  e.later(100, () => n++);
  e.step(99); assert.equal(n, 0); e.step(101); e.step(300); assert.equal(n, 1);
});

test("a tween started inside another tween runs afterwards", () => {
  const e = createEngine(); e.step(0); const seen = [];
  e.tween(10, t => { if (t >= 1) e.tween(10, u => seen.push(u)); });
  e.step(10); e.step(15); e.step(20);
  assert.deepEqual(seen, [0.5, 1]);
});

function fakeScenes(e, n, log) {
  return Array.from({ length: n }, (_, i) => ({ hold: 100, run() { log.push([i, e.instant]); e.tween(100, () => {}); } }));
}

test("go(n) replays earlier scenes instantly and animates scene n", () => {
  const e = createEngine(); e.step(0); const log = []; let resets = 0, shown = null;
  const s = createStory(fakeScenes(e, 4, log), e, { reset: () => resets++, onScene: n => (shown = n) });
  s.go(2);
  assert.deepEqual(log, [[0, true], [1, true], [2, false]]);
  assert.equal(resets, 1); assert.equal(shown, 2); assert.equal(e.pending(), 1);
});

test("go clamps the scene number and treats junk as 0", () => {
  const e = createEngine(); e.step(0); const s = createStory(fakeScenes(e, 3, []), e);
  assert.equal(s.go(99), 2); assert.equal(s.go(-4), 0); assert.equal(s.go(NaN), 0);
});

test("jumping to the next scene cancels the old scene's tweens", () => {
  const e = createEngine(); e.step(0); const moved = [];
  const scenes = [{ run() { e.tween(1000, t => moved.push(t)); } }, { run() {} }];
  const s = createStory(scenes, e);
  s.go(0); e.step(100); s.next();
  const n = moved.length; e.step(2000);
  assert.equal(moved.length, n);
});

test("still mode shows the end state of the current scene too", () => {
  const e = createEngine(); e.step(0); const log = [];
  const s = createStory(fakeScenes(e, 3, log), e, { still: true });
  s.go(1);
  assert.deepEqual(log, [[0, true], [1, true]]); assert.equal(e.instant, false);
});

test("autoplay waits for the scene, holds, moves on and stops at the end", () => {
  const e = createEngine(); e.step(0); let ended = null;
  const s = createStory(fakeScenes(e, 3, []), e, { onEnd: n => (ended = n) });
  s.go(0); s.play();
  const run = t => { e.step(t); s.tick(t); };
  run(50); assert.equal(s.cur, 0);
  run(100); assert.equal(s.cur, 0);
  run(150); assert.equal(s.cur, 0);
  run(200); assert.equal(s.cur, 1);
  run(300); run(400); assert.equal(s.cur, 2);
  run(500); assert.equal(s.playing, false); assert.equal(ended, 2);
});

test("play(until) stops at that scene", () => {
  const e = createEngine(); e.step(0); let ended = null;
  const s = createStory(fakeScenes(e, 4, []), e, { onEnd: n => (ended = n) });
  s.go(1); s.play(2);
  for (let t = 50; t <= 1000; t += 50) { e.step(t); s.tick(t); }
  assert.equal(s.cur, 2); assert.equal(ended, 2); assert.equal(s.playing, false);
});
