---
name: building-interactive-presentations
description: Use when someone wants a talk, slide deck or explanation turned into an interactive, animated, non-linear presentation that runs in a browser (a local web app, an "explorer", "PowerPoint is too linear"), especially for processes, pipelines or system flows that should be shown moving, and when it must run offline on a projector.
---

# Building interactive presentations

An interactive presentation is not a slide deck in a browser. It is a set of **stations**:
each one SVG diagram that changes over a few **steps**. Start from `template.html` in this
folder (engine, navigation, one example station). It runs offline from disk.

## A station is

1. **One diagram** (SVG 1380x690): boxes for things, arrows for hand-overs. Show a process
   as a **token moving along the arrows** (`moveToken`), not as cards with bullets.
2. **2 to 5 steps**, each changing one thing. Alternatives are separate steps (green
   outcome, then red outcome), never shown together.
3. **One caption per step**: the sentence the speaker would say (max ~25 words). Text on
   the canvas is labels only.

## Render model (keep as is)

`render()` rebuilds the station, replays earlier steps with `INSTANT = true`, then animates
the current step. So every timed effect must go through `later()` or `tween()`, and each
step's `run()` sets its full end state. Raw `setTimeout`, CSS-only delays or own
`requestAnimationFrame` break going back, deep links and replay.

## Helpers

`hidden`/`show`/`dim`/`staggerIn` (appear, focus) · `moveToken` (moving process) ·
`drawPath` (line draws itself) · `slideX` (group moves) · `badge` (✓ ✗ …) ·
`para` (SVG text does not wrap). Keys: arrows, space, click, number per section, `R`, `F`.

## Content

- Every step shows a fact the source deck or notes state. No extra steps or claims, even
  plausible ones: list them as questions in your report. The deck stays the fallback.
- Group stations by the deck's sections; backup last. No external scripts, fonts or images.

## Verify before handing over

1. `node --check` on the extracted `<script>`.
2. `bash scripts/shoot.sh index.html shots 0_1 1_2 ...` with the last step of every
   station; look at every image and fix overlaps, clipped text, empty areas.
3. Say what was not checked: animations in motion and keyboard use.

## Common mistakes

| Mistake | Fix |
|---|---|
| Cards with bullets, nothing moves | Draw the flow, move a token along it |
| Deep link to the last step shows empty results | Timing outside `later`/`tween` |
| `setAttribute("fill"/"stroke")` has no effect | CSS class wins: set `.style.fill` / `.style.stroke` |
| Layout breaks on the projector | Keep the fixed 1600x900 stage; `fit()` scales it |
