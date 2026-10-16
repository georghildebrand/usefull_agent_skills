const test = require("node:test");
const assert = require("node:assert/strict");
const { makePath, joinPoints, carPositions } = require("../src/track.js");
const near = (a, b, eps = 1e-6) => Math.abs(a - b) <= eps;

test("a straight path has its real length and points", () => {
  const p = makePath([[0, 0], [10, 0]]);
  assert.ok(near(p.length, 10)); const q = p.at(5);
  assert.ok(near(q.x, 5) && near(q.z, 0) && near(q.angle, 0));
});

test("positions beyond the ends are clamped", () => {
  const p = makePath([[0, 0], [10, 0]]);
  assert.deepEqual([p.at(-3).x, p.at(99).x], [0, 10]);
});

test("the curve passes through its control points", () => {
  const p = makePath([[0, 0], [5, 3], [10, 0]]); const q = p.at(p.sOf(5, 3));
  assert.ok(Math.hypot(q.x - 5, q.z - 3) < 1e-6);
});

test("sOf finds the arc position of a nearby point", () => {
  const p = makePath([[0, 0], [10, 0]]);
  assert.ok(Math.abs(p.sOf(7, 0.3) - 7) < 0.4);
});

test("the angle follows the direction of travel", () => {
  const p = makePath([[0, 0], [0, 10]]);
  assert.ok(near(p.at(5).angle, Math.PI / 2, 1e-9));
});

test("joinPoints drops the shared joint", () => {
  assert.deepEqual(joinPoints([[0, 0], [1, 0]], [[1, 0], [2, 0]]), [[0, 0], [1, 0], [2, 0]]);
});

test("cars trail the head by the spacing and hide before the start", () => {
  const p = makePath([[0, 0], [10, 0]]);
  const a = carPositions(p, 5, 3, 1);
  assert.deepEqual(a.map(c => Math.round(c.x * 1e6) / 1e6), [5, 4, 3]); assert.ok(a.every(c => c.visible));
  const b = carPositions(p, 1, 3, 1);
  assert.deepEqual(b.map(c => c.visible), [true, true, false]);
});

test("every route is one full path from the start of the track", () => {
  const { buildPaths } = require("../src/track.js"), { LAYOUT } = require("../src/scene-data.js");
  const P = buildPaths(LAYOUT), start = LAYOUT.tracks.main[0];
  for (const p of Object.values(P)) { const q = p.at(0); assert.ok(Math.hypot(q.x - start[0], q.z - start[1]) < 1e-6); }
});
