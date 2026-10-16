/* The timing table from tools/narrate.sh (durations.json): the reader and its checks, the silent fallback, the spoken
   lines, and the slow camera move after a scene's animation. */
const test = require("node:test");
const assert = require("node:assert/strict");
const { checkTiming, sceneMs, sceneStarts, sceneAt, timingFromScenes, lineOf, frameTime } = require("../src/timing.js");
const { driftPose } = require("../src/engine.js");
const { SCENES } = require("../src/scene-data.js");

/* a durations.json as narrate.sh writes it: every scene anim + 2 s long, at 30 fps */
function fixture() {
  let start = 0;
  const scenes = SCENES.map((s, i) => {
    const frames = Math.round((s.anim + 2000) * 30 / 1000), r = { id: i + 1, text: lineOf(s), speech_s: 1, scene_s: frames / 30, frames, start_frame: start };
    start += frames; return r;
  });
  return { fps: 30, total_frames: start, total_s: start / 30, scenes };
}
const copy = x => JSON.parse(JSON.stringify(x));

test("a timing file that fits passes, and gives each scene's length and start", () => {
  const d = fixture(), c = checkTiming(d, SCENES);
  assert.deepEqual(c, { errors: [], warnings: [] });
  assert.deepEqual(sceneMs(d), d.scenes.map(s => s.frames * 1000 / 30));
  assert.deepEqual(sceneStarts(d), d.scenes.map(s => s.start_frame));
});

test("a wrong scene count is an error", () => {
  const d = copy(fixture()); d.scenes.pop(); d.total_frames = undefined;
  assert.ok(checkTiming(d, SCENES).errors.some(e => /scenes/.test(e)));
});

test("a scene shorter than its animation is an error that names the scene", () => {
  const d = copy(fixture()), k = d.scenes[2].frames - 15;
  d.scenes[2].frames = 15; d.scenes.slice(3).forEach(s => (s.start_frame -= k)); d.total_frames -= k;
  const e = checkTiming(d, SCENES).errors;
  assert.equal(e.length, 1); assert.match(e[0], /scene 3/);
});

test("a gap in the start frames and a wrong total are errors", () => {
  const d = copy(fixture()); d.scenes[1].start_frame += 1;
  assert.ok(checkTiming(d, SCENES).errors.some(e => /scene 2 .*start_frame/.test(e)));
  const t = copy(fixture()); t.total_frames += 5;
  assert.ok(checkTiming(t, SCENES).errors.some(e => /total_frames/.test(e)));
});

test("a voice made from other words is only a warning", () => {
  const d = copy(fixture()); d.scenes[0].text = "something else";
  const c = checkTiming(d, SCENES);
  assert.deepEqual(c.errors, []); assert.match(c.warnings[0], /scene 1/);
});

test("junk input is an error, not a crash", () => {
  assert.ok(checkTiming(null, SCENES).errors.length);
  assert.ok(checkTiming({ fps: 30 }, SCENES).errors.length);
});

test("sceneAt finds the scene of a frame; frames after the end belong to the last scene", () => {
  const d = fixture();
  assert.equal(sceneAt(d, 0), 0);
  assert.equal(sceneAt(d, d.scenes[1].start_frame), 1);
  assert.equal(sceneAt(d, d.scenes[1].start_frame - 1), 0);
  assert.equal(sceneAt(d, d.total_frames + 10), SCENES.length - 1);
  assert.equal(frameTime(45, 30), 1500);
});

test("without narration each scene lasts anim + hold, and the table passes the check", () => {
  const d = timingFromScenes(SCENES, 30);
  assert.equal(d.scenes[0].frames, Math.round((SCENES[0].anim + SCENES[0].hold) * 30 / 1000));
  assert.equal(d.scenes[1].frames, Math.round((SCENES[1].anim + 2200) * 30 / 1000));
  assert.deepEqual(checkTiming(d, SCENES).errors, []);
});

test("the spoken line is the say field when there is one, else the subtitle", () => {
  assert.equal(lineOf({ text: "Runs  the\nCI." }), "Runs the CI.");
  assert.equal(lineOf({ text: "Runs the CI.", say: "Runs the C I." }), "Runs the C I.");
});

test("the drift starts still, stays a wide shot and turns towards the front", () => {
  const base = { x: 1, y: 0, z: 2, r: 27, theta: 0.12, phi: 0.72 };
  assert.deepEqual(driftPose(base, 0), base);
  const near = driftPose(base, 100), mid = driftPose(base, 8000);
  assert.ok(Math.abs(near.theta - base.theta) < 0.001);            /* zero speed at the start: no jerk after the flight */
  assert.ok(mid.theta < base.theta && base.theta - mid.theta <= 0.14 + 1e-9);
  assert.ok(mid.r >= base.r * 0.96 - 1e-9 && mid.r < base.r);
  assert.equal(mid.phi, base.phi); assert.equal(mid.x, base.x);
  for (let ms = 0; ms <= 40000; ms += 500) assert.ok(driftPose(base, ms).r >= 25, "playback stays wide (r >= 25)");
  /* it moves: between 1 s and 3 s the angle changes visibly */
  assert.ok(Math.abs(driftPose(base, 3000).theta - driftPose(base, 1000).theta) > 0.01);
});
