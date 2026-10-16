/* build.py: the plain single file has no audio; --voice embeds one audio data URI per scene and the timing table.
   Needs python3, ffmpeg and vendor/three.min.js (bash tools/fetch-three.sh); skipped when one is missing. */
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync, spawnSync } = require("node:child_process");
const { SCENES } = require("../src/scene-data.js");
const { lineOf } = require("../src/timing.js");
const ROOT = path.join(__dirname, "..");
const has = cmd => spawnSync(cmd, ["-version"], { stdio: "ignore" }).status === 0 || spawnSync(cmd, ["--version"], { stdio: "ignore" }).status === 0;
const missing = !fs.existsSync(path.join(ROOT, "vendor/three.min.js")) ? "vendor/three.min.js is missing"
  : !has("python3") ? "no python3" : !has("ffmpeg") ? "no ffmpeg" : false;

/* a fake voice: one short tone per scene and a durations.json that fits the scenes */
function fakeVoice(dir) {
  let start = 0;
  const scenes = SCENES.map((s, i) => {
    const wav = path.join(dir, `scene${String(i + 1).padStart(2, "0")}.wav`);
    execFileSync("ffmpeg", ["-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", `sine=frequency=${300 + 50 * i}:duration=0.4`, wav]);
    const frames = Math.round((s.anim + 1000) * 30 / 1000), r = { id: i + 1, text: lineOf(s), frames, start_frame: start };
    start += frames; return r;
  });
  fs.writeFileSync(path.join(dir, "durations.json"), JSON.stringify({ fps: 30, total_frames: start, total_s: start / 30, scenes }));
}

test("build.py without --voice has no audio; with --voice one audio data URI per scene and the timing", { skip: missing }, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "explainer-voice-"));
  try {
    fakeVoice(dir);
    const plain = path.join(dir, "plain.html"), voiced = path.join(dir, "voice.html");
    execFileSync("python3", [path.join(ROOT, "build.py"), "--out", plain], { stdio: "pipe" });
    execFileSync("python3", [path.join(ROOT, "build.py"), "--voice", "--audio", dir, "--out", voiced], { stdio: "pipe" });
    const a = fs.readFileSync(plain, "utf8"), b = fs.readFileSync(voiced, "utf8");
    assert.doesNotMatch(a, /data:audio\//); assert.doesNotMatch(a, /EX\.VOICE =/);
    assert.ok(a.length < 1_000_000, "the plain build stays under 1 MB");
    const uris = b.match(/data:audio\/(ogg;codecs=opus|mp4);base64,[A-Za-z0-9+/=]+/g) || [];
    assert.equal(uris.length, SCENES.length);
    assert.match(b, /EX\.TIMING = \{"fps": 30/);
    assert.ok(b.indexOf("EX.VOICE =") < b.indexOf("/* src/main.js */"), "the voice is set before main.js runs");
    assert.doesNotMatch(b, /<script src=/);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test("build.py --voice stops with a message when the voice is missing", { skip: missing }, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "explainer-novoice-"));
  try {
    const r = spawnSync("python3", [path.join(ROOT, "build.py"), "--voice", "--audio", dir, "--out", path.join(dir, "x.html")], { encoding: "utf8" });
    assert.notEqual(r.status, 0); assert.match(r.stderr, /durations\.json/);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
