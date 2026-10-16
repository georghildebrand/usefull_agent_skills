/* Checks on the content in src/scene-data.js: scene count, poses, step panel lines, subtitle length, the red example. */
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { LAYOUT, STEPS, SCENES, STEP_OF_SCENE } = require("../src/scene-data.js");
const KEYS = ["x", "y", "z", "r", "theta", "phi"];
const okPose = p => KEYS.every(k => Number.isFinite(p[k])) && p.r > 0 && p.phi >= 0.2 && p.phi <= 1.45;

test("five scenes with unique keys, a title and a subtitle", () => {
  assert.equal(SCENES.length, 5); assert.equal(new Set(SCENES.map(s => s.key)).size, SCENES.length);
  assert.ok(SCENES.every(s => s.title && s.text));
});

test("every subtitle has at most 34 words", () => {
  for (const s of SCENES) assert.ok(s.text.split(/\s+/).length <= 34, s.key);
});

test("every scene has a complete pose, scene 0 also a start pose; playback stays wide (r >= 25)", () => {
  for (const s of SCENES) { assert.ok(okPose(s.pose), s.key); assert.ok(s.pose.r >= 25, s.key); }
  assert.ok(okPose(SCENES[0].start));
});

test("every scene lights an existing line of the step panel, never going back", () => {
  const last = STEPS.items.length + 1;
  assert.equal(STEP_OF_SCENE.length, SCENES.length);
  STEP_OF_SCENE.forEach((k, i) => { assert.ok(k >= 0 && k <= last); if (i) assert.ok(k >= STEP_OF_SCENE[i - 1]); });
  assert.equal(STEP_OF_SCENE[SCENES.length - 1], last);   /* the last scene shows the "Then" line */
});

test("the red run is marked as an example in its title and subtitle", () => {
  const red = SCENES.find(s => s.part === "red");
  assert.match(red.title, /example/i); assert.match(red.text, /example/i);
});

test("every station has a click card", () => {
  for (const s of LAYOUT.stations) assert.ok(LAYOUT.info[s.key], s.key);
});

test("story.js uses no setTimeout or setInterval: every timed effect goes through engine.tween or engine.later", () => {
  const src = fs.readFileSync(path.join(__dirname, "../src/story.js"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");   /* code only, no comments */
  assert.doesNotMatch(src, /setTimeout|setInterval/);
});
