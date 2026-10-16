/* The spoken lines for tools/narrate.sh, one per scene, from src/scene-data.js (a scene's say field, else its subtitle).
   node tools/lines.js        prints one line per scene
   node tools/lines.js --min  prints the shortest length of each scene in s, comma separated (MIN_S for narrate.sh):
                              anim + 600 ms, so a short line never cuts the scene's animation */
const { SCENES } = require("../src/scene-data.js");
const { lineOf } = require("../src/timing.js");
const minSeconds = scenes => scenes.map(s => (((s.anim || 0) + 600) / 1000).toFixed(2));
module.exports = { minSeconds };
if (require.main === module) {
  if (process.argv.includes("--min")) process.stdout.write(minSeconds(SCENES).join(",") + "\n");
  else process.stdout.write(SCENES.map(lineOf).join("\n") + "\n");
}
