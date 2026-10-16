---
name: explaining-systems-in-motion
description: Use when planning or building an animated explainer, 3D fly-through, model-railway or factory metaphor, or narrated video of a pipeline, release process, CI/CD chain or data flow for people who do not know the system, especially when it should look "cinematic", open a talk, or show what happens where and who triggers what.
---

# Explaining systems in motion

## Overview

After the animation, a newcomer must be able to say what starts the process, where each
step runs, who or what connects the parts, and what reaches the end user. Close-up
camera work, a missing map and invented hand-overs each break that.

Builds on `building-interactive-presentations` (render model, stills) and
`narrated-explainer-video` (voice, MP4).

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

## Common mistakes

| Mistake | Fix |
|---|---|
| Camera follows the train or pushes in on a station | Wide shot, light the active part |
| Process explained only in subtitles that vanish | Fixed step panel with the current step |
| Result record travels over the bridge to the customers | Check who reads it; usually a person and a pull request |
| "v2.4.0", "32/45" placeholders on screen | Real values from a run, or no number |
| Final totals visible before the test scene | Show each result only from its own scene |
| Same thing under several names on screen | One name per zone, the technical name small below it |
