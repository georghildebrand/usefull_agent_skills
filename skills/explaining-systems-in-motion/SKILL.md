---
name: explaining-systems-in-motion
description: Use when planning or building an animated explainer, 3D fly-through, model-railway or factory metaphor, or narrated video of a pipeline, release process, CI/CD chain or data flow for people who do not know the system, especially when it should look "cinematic", open a talk, or show what happens where and who triggers what.
---

# Explaining systems in motion

## Overview

After the animation, a newcomer must be able to say what starts the process, where each
step runs, who or what connects the parts, and what reaches the end user. Close-up
camera work, a missing map and invented hand-overs each break that.

For a 3D page, start from `template/` in this folder (section 4); it can also make an MP4
and a page with voice, but only when asked. For 2D SVG stations use
`building-interactive-presentations`. Use `narrated-explainer-video` only for a narrated
MP4 that is not built from this 3D template (for example a Remotion video of a result).

## 1. Connection table first

Before any scene, build this table from the source files (pipeline YAML, job and bundle
definitions, deploy repos). One row per hand-over:

| from (zone) | to (zone) | what moves | mechanism | automatic / manual | source file:line |
|---|---|---|---|---|---|
| repo X CI (Bitbucket Pipelines) | package registry | wheel `<VERSION>` | publish | automatic | `bitbucket-pipelines.yml:88` |
| result table | production pins | nothing | a person reads it, opens a pull request | manual | deploy repo has no reader |

- A zone is a place people know: "repo X CI", "repo X Databricks jobs", "central deploy
  pipeline", "customer tenant".
- Draw only hand-overs that are in the table. Check the last hand-over to the end user
  hardest: a result record (bundle, report, test verdict) is often drawn as if it ships
  itself to production, when in fact a person reads it.
- Anything you could not prove gets UNVERIFIED and stays off the screen.

## 2. What the screen shows

**Camera in playback:** every shot shows the whole system, or a whole group of zones,
from above at an angle. Slow pans and small moves are fine while that stays in frame.
Mark the active part with light, and dim the rest. Chase, cab and close-up shots exist
only in free mode, also when someone asks for "cinematic".

**Fixed step panel**, on the screen edge in every playback scene:
1. one question line: what the system answers;
2. the 4 to 6 process steps in plain words, numbered;
3. the current step highlighted, earlier steps marked done;
4. a last line saying what happens after the system, as it really happens (often manual).

**Zones and lines:** each zone is a labelled area ("CI (Bitbucket Pipelines)",
"Databricks jobs"). Each table row is a visible line labelled with its mechanism
("publish wheel", "jobs run-now", "writes table"). Manual rows show a person and the word
"manual". One early scene shows all zones and lines before the story starts.

**Facts:** every name, version and count comes from a run or a repo file. No invented
versions or partial counters. An invented run (the red case) carries a visible "example"
sign and no ids. A result appears only from the scene where it happens.

**Subtitles:** one or two sentences: why this step exists, then what happens.

## 3. Verify with a newcomer lens

Take a still of every scene's end state and look at each one. Give a reviewer only the
stills and the subtitles. It must answer: what starts it, what it tests, what makes it
fail, what reaches the end user, and who connects to whom. Every question it cannot
answer is a finding.

## 4. Building a 3D page: start from `template/`

Copy `template/` (three.js, offline, runs from `file://`) and replace the example in
`src/scene-data.js`, `src/world.js` and `src/story.js`. Its `README.md` has the commands.
The template already has the parts that hand-built pages miss:

- **Signs that cannot overlap.** Every label is a sign made with `util3d.js`; the sign pass
  hides the lower-priority sign of any overlapping pair each frame. Mark the scene's
  focused signs with `H.focus([...])` so they win. Do not place labels by hand.
- **A sign audit.** Run `bash tools/audit.sh` on every scene; it lists signs that are
  hidden, cut at the edge or overlapping. Fix every sign the scene needs that it reports.
- **One state per scene.** `story.go(n)` resets, replays scenes before n at once and
  animates only n. A scene shows only results that exist at its moment: a red example
  hides or greys the green results, and the next scene restores the green state first.
  The step panel follows the same run: it ticks only the steps that run went through.
  Free mode shows one consistent state, never two results on the same spot.

Check every scene with `bash tools/shoot.sh` at 1920x1080 and at 1280x720, and look at
each image.

**Video and voice, only when the user asks.** Do not make them by default. An MP4 comes
from `bash tools/render.sh`; a single page with spoken lines comes from
`python3 build.py --voice`. The voice is made by Piper on the local machine, so no text
leaves it. Look at each `out/check/scene-NN.png` (last frame of each scene) before you
hand the video over. The commands are in the template's `README.md`.

## Common mistakes

| Mistake | Fix |
|---|---|
| Labels placed by hand at fixed 3D points | Signs from `util3d.js` with focus priority; run the audit |
| Red example scene still shows the green parcel, total or badge | Hide or grey the other run's results in that scene |
| Camera follows the train or pushes in on a station | Wide shot, light the active part |
| Process explained only in subtitles that vanish | Fixed step panel with the current step |
| Result record travels over the bridge to the customers | Check who reads it; usually a person and a pull request |
| "v2.4.0", "32/45" placeholders on screen | Real values from a run, or no number |
| Final totals visible before the test scene | Show each result only from its own scene |
| Same thing under several names on screen | One name per zone, the technical name small below it |
