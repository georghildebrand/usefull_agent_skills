/* Checks a durations.json from tools/narrate.sh against the scenes in src/scene-data.js (the same check the page runs).
   Exit 1 when the scene count differs, the start frames have a gap, or a scene is shorter than its animation + 300 ms.
   A line whose text differs from the scene line is a warning only (you may have narrated your own lines file).
   Usage: node tools/timing.js <durations.json> */
const fs = require("node:fs");
const { SCENES } = require("../src/scene-data.js");
const { checkTiming } = require("../src/timing.js");
const file = process.argv[2];
if (!file) { console.error("usage: node tools/timing.js <durations.json>"); process.exit(2); }
const d = JSON.parse(fs.readFileSync(file, "utf8"));
const { errors, warnings } = checkTiming(d, SCENES);
warnings.forEach(w => console.error("timing warning: " + w));
if (errors.length) { errors.forEach(e => console.error("timing: " + e)); process.exit(1); }
console.log(`timing ok: ${d.scenes.length} scenes, ${d.total_frames} frames, ${d.total_s} s at ${d.fps} fps`);
