const test = require("node:test");
const assert = require("node:assert/strict");
const { declutter } = require("../src/declutter.js");
const view = { w: 1000, h: 600 }, r = (x0, y0, x1, y1, prio = 1, dist = 10, extra = {}) => Object.assign({ x0, y0, x1, y1, prio, dist }, extra);

test("a sign that is cut by the picture edge is hidden", () => {
  const out = declutter([r(-5, 100, 80, 130), r(950, 100, 1010, 130), r(0, 0, 50, 20), r(900, 560, 1000, 600)], view);
  assert.deepEqual(out.map(o => o.show), [false, false, true, true]); assert.equal(out[0].why, "edge");
});

test("a sign outside the picture is hidden with the reason out, not edge", () => {
  assert.equal(declutter([r(-200, 10, -50, 40), r(1010, 10, 1100, 40)], view).every(o => o.why === "out"), true);
});

test("of two overlapping signs the one with the higher prio stays, equal prio: the nearer one", () => {
  assert.deepEqual(declutter([r(0, 0, 100, 40, 1), r(50, 10, 150, 50, 3)], view).map(o => o.show), [false, true]);
  assert.deepEqual(declutter([r(0, 0, 100, 40, 2, 20), r(50, 10, 150, 50, 2, 8)], view).map(o => o.show), [false, true]);
});

test("signs that only touch at a gap larger than the padding both stay", () => {
  assert.deepEqual(declutter([r(0, 0, 100, 40), r(105, 0, 200, 40)], view).map(o => o.show), [true, true]);
  assert.deepEqual(declutter([r(0, 0, 100, 40), r(101, 0, 200, 40)], view).map(o => o.show), [true, false]);
});

test("a sign over a keep-out box is hidden, but not the sign that belongs to that box", () => {
  const car = { x0: 100, y0: 100, x1: 160, y1: 140, owner: "car1" };
  const out = declutter([r(120, 110, 200, 130, 5), r(110, 90, 190, 150, 5, 10, { owner: "car1" })], view, [car]);
  assert.equal(out[0].show, false); assert.equal(out[0].why, "box"); assert.equal(out[1].show, true);
});

test("the result is stable: a hidden sign never blocks another sign", () => {
  const out = declutter([r(0, 0, 100, 40, 3), r(50, 0, 150, 40, 2), r(120, 0, 220, 40, 1)], view);
  assert.deepEqual(out.map(o => o.show), [true, false, true]);
});

test("an overCars sign may cover any car box, but never a DOM box", () => {
  const car = { x0: 100, y0: 100, x1: 160, y1: 140, owner: "car2" }, dom = { x0: 300, y0: 100, x1: 400, y1: 140 };
  const out = declutter([r(110, 110, 150, 130, 5, 10, { overCars: true }), r(310, 110, 350, 130, 5, 10, { overCars: true })], view, [car, dom]);
  assert.deepEqual(out.map(o => o.show), [true, false]);
});

test("a box and a sign without an owner never belong together", () => {
  const out = declutter([r(0, 0, 100, 40)], view, [{ x0: 50, y0: 10, x1: 150, y1: 50 }]);
  assert.equal(out[0].show, false); assert.equal(out[0].why, "box");
});

test("a sign nearer to the picture edge than the margin counts as cut", () => {
  const out = declutter([r(5, 100, 80, 130), r(20, 100, 80, 130, 1, 10)], view, [], 3, 8);
  assert.deepEqual(out.map(o => o.show), [false, true]); assert.equal(out[0].why, "edge");
});
