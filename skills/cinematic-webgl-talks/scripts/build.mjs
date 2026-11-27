// Build one offline HTML file from a talk source made from template.html.
// Usage: node scripts/build.mjs <talk.html> <out.html>
// - Puts three.js inline (import map with a data: URL), so the file runs without network.
// - Fails if the output still loads anything from the network.
// three.js is taken from $THREE_JS, or from ~/.cache/cinematic-talks/three-0.170.0.module.min.js,
// which is downloaded once with `npm pack three@0.170.0` when it is missing.
import { readFileSync, writeFileSync, existsSync, mkdirSync, renameSync, rmSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { homedir } from "node:os";
import { join, dirname } from "node:path";

const [src, out] = process.argv.slice(2);
if (!src || !out) { console.error("usage: node scripts/build.mjs <talk.html> <out.html>"); process.exit(2); }

const VERSION = "0.170.0";
const cache = join(homedir(), ".cache", "cinematic-talks");
let three = process.env.THREE_JS || join(cache, `three-${VERSION}.module.min.js`);
if (!existsSync(three)) {
  mkdirSync(cache, { recursive: true });
  console.error(`three.js not found, running: npm pack three@${VERSION} in ${cache}`);
  execFileSync("npm", ["pack", `three@${VERSION}`, "--silent"], { cwd: cache, stdio: "inherit" });
  execFileSync("tar", ["-xzf", `three-${VERSION}.tgz`, "package/build/three.module.min.js"], { cwd: cache });
  renameSync(join(cache, "package/build/three.module.min.js"), three);
  rmSync(join(cache, "package"), { recursive: true }); rmSync(join(cache, `three-${VERSION}.tgz`));
}

let html = readFileSync(src, "utf8");
const marker = /<!-- THREE_IMPORTMAP[^>]*-->/;
if (!marker.test(html)) { console.error("marker <!-- THREE_IMPORTMAP --> not found in <head>"); process.exit(1); }
const code = readFileSync(three);
const map = { imports: { three: "data:text/javascript;base64," + code.toString("base64") } };
html = html.replace(marker, `<script type="importmap">${JSON.stringify(map)}</script>`);

// Offline check: no script, stylesheet, font, image or fetch from the network.
const bad = [...html.matchAll(/(?:src|href)\s*=\s*["'](https?:)?\/\/[^"']+|url\(\s*["']?https?:[^)]+\)|fetch\(\s*["']https?:[^"']+|@import\s+["']?https?:[^;]+/gi)].map(m => m[0]);
if (bad.length) { console.error("Network references found, the talk would not run offline:\n  " + bad.join("\n  ")); process.exit(1); }

mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, html);
console.log(`${out}  ${(Buffer.byteLength(html) / 1e6).toFixed(2)} MB, three.js ${VERSION} inline, no network references`);
