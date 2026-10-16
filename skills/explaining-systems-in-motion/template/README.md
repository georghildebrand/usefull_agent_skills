# three.js explainer template

A runnable 3D explainer: a parcel on a cart runs over a board on a table through three stations (receive, check, ship), with a fixed step panel, captions, a green run, a red example run and free mode. Copy the folder and replace the example with your own system.

**Start:** `bash tools/fetch-three.sh` (downloads three.js r147, MIT licence, and checks its SHA-256), then open `index.html` from disk. Keys: space, arrows, R, F (M in the voice build). URL options: `?scene=N`, `&still` (end state of scene N at once), `?free`, `?autoplay`, `?debug`; `?record` is for `tools/record.py` only.
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
| `src/timing.js`, `src/record.js`, `src/paint2d.js`, `src/voice.js` | video and voice only: scene lengths from the narration, record mode, overlay drawn into the frame, spoken lines in the page |

**Rule:** every timed effect goes through `engine.tween` or `engine.later`, never `setTimeout`. Then `story.go(n)` can replay scenes 0 to n-1 instantly and animate only scene n, and `?scene=N&still` shows a correct end state.

Traps seen in a real project built from this pattern:
- ES modules do not load from `file://`. Keep classic `<script>` tags in dependency order.
- A train that splits or takes another branch is a separate consist with its own full path from the start. Do not re-parent cars to another group at run time.
- `story.go` rebuilds moving objects on every scene change. Dispose their geometries, materials and textures (see `clear()` in `world.js`), or GPU memory grows with each jump.
- Free mode must stop the story's camera flights (`rig.setFree` changes a generation counter), or the camera keeps moving while the viewer drags.
- Signs the story switched off for a scene must show again in free mode (`EX.allSigns`). Result signs are the exception: they stay with their scene.
- After a red example scene, the next scene must restore the green state (lamps, signal, glows, result board) before it does anything else.
- Show each result (totals, result board) only from the scene where it happens, not earlier.

## Video and voice (only on request)

Make these only when someone asks for a video or for a page that speaks. The page itself needs neither.
Both use one spoken line per scene: the scene's `say` field, else its subtitle in `src/scene-data.js`.
The voice is made with [Piper](https://github.com/OHF-Voice/piper1-gpl) on your machine; no text leaves it.

```bash
uv tool install piper-tts                                   # once; or: pipx install piper-tts
uvx --from piper-tts python -m piper.download_voices en_US-ryan-high --download-dir ~/piper-voices
#   or download en_US-ryan-high.onnx and en_US-ryan-high.onnx.json into one folder from
#   https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/<file name>
export PIPER_VOICE=~/piper-voices/en_US-ryan-high.onnx      # PIPER=<command> when piper is not on PATH

bash tools/render.sh            # voice -> out/audio, frames -> out/frames, video -> out/explainer.mp4
W=1280 H=720 GL=metal bash tools/render.sh   # smaller, and with the GPU on macOS: faster
SILENT=1 bash tools/render.sh   # no Piper: a video without sound, each scene anim + hold long
python3 build.py --voice        # explainer-voice.html: the single file with the spoken lines (Opus in base64, about 40 KB per 10 s)
```

- **Video.** `tools/record.py` opens `index.html?record` in headless Chrome. The frame number is the clock (frame n is at n × 1000 / fps ms), so a slow frame never skips a tween. The page draws the title, step panel and caption into each frame, because ffmpeg often has no text filter. Each scene lasts as long as its spoken line (`out/audio/durations.json`), at least `anim` + 600 ms. When the line is longer than the animation, the camera turns slowly, so the picture is never still for more than about 2 s. Look at `out/check/scene-NN.png` (last frame of each scene) before you watch the video. Check for still stretches: `ffmpeg -i out/explainer.mp4 -vf "scale=480:-1,freezedetect=n=0.0005:d=2" -map 0:v -f null - 2>&1 | grep freeze` (no output is good).
- **Time.** 1280x720 with software WebGL: about 0.1 s per frame, so a 45 s video takes about 2.5 minutes. 1920x1080 needs about twice the time per frame. `GL=metal` (the GPU on macOS) is about 5 times faster.
- **`anim`** in each scene is the length of its animation in ms. Record mode prints the measured value per scene; raise `anim` when you make a scene longer. A recording stops with an error when a scene still animates at its end.
- **Voice in the page.** The line of a scene plays when the scene starts and stops at the next scene and in free mode. Browsers play sound only after a key press or click, so space starts the current scene again, together with its line. **M** turns the voice off and on. Without `--voice` the build does not change.
- Make the voice once. `tools/render.sh` reuses `out/audio` while the lines and the fps stay the same; changed subtitles, `say` fields or `LINES=` make the voice again, and so does `VOICE=new`. Piper does not give exactly the same length twice, so a new voice needs new frames.
