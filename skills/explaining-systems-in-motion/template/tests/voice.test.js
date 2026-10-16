const test = require("node:test");
const assert = require("node:assert/strict");

/* voice.js is a browser script: give it self.EX and a fake Audio that counts play() calls */
let plays = 0;
globalThis.self = { EX: {} };
globalThis.Audio = class { constructor(src) { this.src = src; this.paused = true; this.currentTime = 0; }
  play() { plays++; this.paused = false; return Promise.resolve(); } pause() { this.paused = true; } };
require("../src/voice.js");
const { createVoice } = self.EX;

function ready() { const v = createVoice(["a", "b"]); v.unlock(); v.scene(1); plays = 0; return v; }

test("M unmutes while the story plays: the scene's line starts again", () => {
  const v = ready(); v.toggle(true); assert.equal(v.muted, true);
  v.toggle(true); assert.equal(v.muted, false); assert.equal(plays, 1);
});

test("M unmutes while the story is paused or in free mode: no line starts", () => {
  const v = ready(); v.toggle(false); v.toggle(false);
  assert.equal(v.muted, false); assert.equal(plays, 0);
});

test("without clips the voice does nothing", () => {
  const v = createVoice(); v.unlock(); v.scene(0); v.toggle(true); v.toggle(true);
  assert.equal(v.available, false); assert.equal(plays, 0);
});
