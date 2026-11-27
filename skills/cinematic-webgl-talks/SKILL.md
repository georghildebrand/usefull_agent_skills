---
name: cinematic-webgl-talks
description: Use when someone wants a persuasive talk or keynote built as a cinematic 3D presentation in the browser (three.js, WebGL), where each scene makes one number or claim felt through a physical picture (exponential growth, scale, small errors that grow), and it must run offline from a laptop on a projector. Not for process or pipeline explainers built from diagrams; use building-interactive-presentations for those.
---

# Cinematic WebGL talks

A talk of 5 to 15 **scenes**. Each scene is one claim, shown as one 3D picture whose
geometry IS the number. Each scene has 2 to 4 **beats** (steps the speaker triggers with
the arrow key). Start from `template.html` in this folder. It holds the engine and two
finished example scenes (dominoes for 1.5^29, an aim that is one degree off).

## Choosing scenes

For every claim, find a physical picture in which the number becomes a size, a distance
or a count. You do not show the number next to the picture, the picture shows it.

| Claim | Picture | Why it works |
| --- | --- | --- |
| 1.5x per step, 30 steps | dominoes, each 1.5x taller; camera pulls back | the size of the last domino is the result |
| 1 degree error | two lines from one point; target at 10 m, Moon, star | the gap is `distance × tan(1°)` |
| progress speeds up | a calendar where each day's width = progress that day | late days stop fitting on the wall |
| many agents in parallel | 30,000 instanced figures, counter running | the count is the crowd |

Write the result of the arithmetic into the scene `source` and check it once by hand.

## The scene contract (engine rules)

```js
{ id: "aim", title: "One degree",
  source: "Geometry: miss = distance × tan(1°)",       // on screen, bottom left
  beats: [{ dur: 1, hold: 4 }, { dur: 3, hold: 4 }],   // dur = animation s, hold = pause in auto mode
  notes: ["What the speaker says. (Stage direction in brackets.)", "…"],  // one per beat
  create(ctx) { /* build once */ return { scene, camera, update(s) { … } }; } }
```

- **`update(s)` sets every value from `s = {beat, t}`. It never adds to a value that
  lives between frames** (a position, a counter on the object). A local sum that starts
  at 0 inside one `update` call is fine. Use
  `k(s, beat, from, to)` (0..1 progress of a time window inside a beat; earlier beats
  are 1, later beats 0). Then deep links, going back and screenshots show the right state.
  `t = Infinity` means "beat finished".
- **Deep link `#<scene id>-<beat>`, 1-based** (e.g. `#aim-2`). Never number all steps of
  the talk in one sequence: adding one scene would break every link.
- **Zoom across orders of magnitude with `lerpLog`**, and set `camera.near`/`far`
  relative to the current size each frame. With a linear zoom, the camera skips the
  middle and the depth buffer breaks at kilometre scale.
- **Text is HTML in the 1920x1080 layer** (`ctx.text`), not text in WebGL. It stays sharp
  and uses system fonts. If a brand font is required, embed it as a base64 `woff2`.
- Keep the engine parts as they are: 16:9 fit, lower pixel ratio when frames are slow
  (needed for 4K projectors), WebGL 2 fallback message, presenter window (`P`, updated
  through the `window.open` reference, works on `file://`), notes (`N`), black screen (`B`),
  auto mode (`A`).

## Honesty on screen

Every number on screen gets one of these labels in `source`: a source with a date,
"Arithmetic:" or "Geometry:" with the formula, "Trend continued, not measured",
"Illustration" or "Speaker's own estimate". Build only scenes and beats that the
user's material contains. Write suggestions for more scenes into your report as questions.

## Build and verify

1. `node scripts/build.mjs talk.html out/index.html` puts three.js 0.170.0 inline and
   fails if anything still loads from the network.
2. `bash scripts/shoot.sh out/index.html shots <id>-<beat> …` for the last beat of every
   scene (opens `?still#id-beat`). Look at every image. Fix text that covers the 3D
   object, objects outside the frame, and empty frames.
3. Report what you did not check: the animation in motion, key presses, the presenter
   window, frame rate on the real laptop and projector.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Screenshot shows text but an empty 3D canvas | the render loop stopped after one frame; keep `requestAnimationFrame` running in still mode |
| Deep link shows the start of an animation | a value was animated with `+=` or `setTimeout`; derive it from `k(s, …)` |
| End of a big zoom is a tiny object or a black frame | interpolate with `lerpLog` and scale `near`/`far` with the camera distance |
| Notes window does not follow on `file://` | use the `window.open` reference, not `localStorage` events |
| Text floats over the important object | move the camera target, not the text; headline zone is the top 300 px |
