# three.js explainer template

A runnable 3D explainer: a parcel on a cart runs over a board on a table through three stations (receive, check, ship), with a fixed step panel, captions, a green run, a red example run and free mode. Copy the folder and replace the example with your own system.

**Start:** `bash tools/fetch-three.sh` (downloads three.js r147, MIT licence, and checks its SHA-256), then open `index.html` from disk. Keys: space, arrows, R, F. URL options: `?scene=N`, `&still` (end state of scene N at once), `?free`, `?autoplay`, `?debug`.
**Stills:** `bash tools/shoot.sh index.html shots 1920x1080 0 1 2 3 4` (headless Chrome with SwiftShader). Look at every image.
**Sign audit:** `SHOTS=shots bash tools/audit.sh 1920x1080 0 1 2 3 4` lists signs that are hidden, cut off or overlapping.
**Tests:** `node --test tests/`. **Single offline file:** `python3 build.py` writes `explainer.html` (under 1 MB).

| File | Purpose |
|---|---|
| `src/scene-data.js` | all content: layout, stations, tracks, click cards, step panel, scenes and camera poses. Change this first |
| `src/world.js` | table, board, rails, stations, lamps, signal, result panels, carts; returns the handles the story uses |
| `src/story.js` | what each scene does, only through `engine.tween` / `engine.later` |
| `src/engine.js` | timing engine and story runner (instant replay, `play(until)`, hold between scenes) |
| `src/track.js`, `src/declutter.js`, `src/util3d.js` | path math, sign placement, three.js helpers |
| `src/camera.js`, `src/ui.js`, `src/main.js` | orbit camera, overlay and keys, wiring and WebGL check |

**Rule:** every timed effect goes through `engine.tween` or `engine.later`, never `setTimeout`. Then `story.go(n)` can replay scenes 0 to n-1 instantly and animate only scene n, and `?scene=N&still` shows a correct end state.

Traps seen in a real project built from this pattern:
- ES modules do not load from `file://`. Keep classic `<script>` tags in dependency order.
- A train that splits or takes another branch is a separate consist with its own full path from the start. Do not re-parent cars to another group at run time.
- `story.go` rebuilds moving objects on every scene change. Dispose their geometries, materials and textures (see `clear()` in `world.js`), or GPU memory grows with each jump.
- Free mode must stop the story's camera flights (`rig.setFree` changes a generation counter), or the camera keeps moving while the viewer drags.
- Signs the story switched off for a scene must show again in free mode (`EX.allSigns`). Result signs are the exception: they stay with their scene.
- After a red example scene, the next scene must restore the green state (lamps, signal, glows, result board) before it does anything else.
- Show each result (totals, result board) only from the scene where it happens, not earlier.
