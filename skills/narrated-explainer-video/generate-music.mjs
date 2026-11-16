// Generates a quiet pad track that is exactly as long as the narration.
// Plain Node, no packages, no samples: there is nothing to license.
//
// Usage (from the project directory, after build-audio.py):
//   node scripts/generate-music.mjs            -> public/audio/music.wav
// Env: MUSIC_MOOD=calm|bright   (default calm)
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";

const SR = 44100;
const { fps, scenes } = JSON.parse(readFileSync("src/scenes.json", "utf8"));
const seconds = scenes.reduce((a, s) => a + s.durationInFrames, 0) / fps;

// Each chord is a list of frequencies in Hz. Four chords repeat, 8 s each.
const CHORDS = {
  calm:   [[220, 261.63, 329.63], [174.61, 220, 261.63], [130.81, 164.81, 196], [196, 246.94, 293.66]],
  bright: [[261.63, 329.63, 392], [196, 246.94, 293.66], [220, 277.18, 329.63], [174.61, 220, 261.63]],
}[process.env.MUSIC_MOOD ?? "calm"];
const SEG = 8; // seconds per chord

const n = Math.ceil(seconds * SR);
const out = new Int16Array(n);
const chordAt = (k) => CHORDS[((k % CHORDS.length) + CHORDS.length) % CHORDS.length];

for (let i = 0; i < n; i++) {
  const t = i / SR;
  const k = Math.floor(t / SEG);
  let s = 0;
  // Two chords overlap at any time. sin^2 windows sum to 1, so the change is smooth.
  for (const j of [k, k + 1]) {
    const w = Math.sin((Math.PI * (t - (j - 1) * SEG)) / (2 * SEG)) ** 2;
    for (const f of chordAt(j)) {
      s += w * (Math.sin(2 * Math.PI * f * t) + 0.5 * Math.sin(2 * Math.PI * (f * 1.004) * t));
    }
  }
  const fade = Math.min(1, t / 2, (seconds - t) / 2); // 2 s in and out
  out[i] = Math.round(Math.max(-1, Math.min(1, (s / 9) * 0.5 * fade)) * 32767);
}

const header = Buffer.alloc(44);
header.write("RIFF", 0); header.writeUInt32LE(36 + out.length * 2, 4); header.write("WAVE", 8);
header.write("fmt ", 12); header.writeUInt32LE(16, 16); header.writeUInt16LE(1, 20);
header.writeUInt16LE(1, 22); header.writeUInt32LE(SR, 24); header.writeUInt32LE(SR * 2, 28);
header.writeUInt16LE(2, 32); header.writeUInt16LE(16, 34); header.write("data", 36);
header.writeUInt32LE(out.length * 2, 40);
mkdirSync("public/audio", { recursive: true });
writeFileSync("public/audio/music.wav", Buffer.concat([header, Buffer.from(out.buffer)]));
console.log(`music.wav  ${seconds.toFixed(1)} s`);
