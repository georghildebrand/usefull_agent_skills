---
name: narrated-explainer-video
description: Use when a technical result has to be delivered as a narrated MP4 video instead of slides - builds a Remotion composition with a local Kokoro voice and generated music, where the voice is made first and every animation is pinned to one narration line
---

# Narrated explainer video

Turn a finished piece of work into a short video with a voice track: an MP4 you can
play in a meeting, attach to a report, or hand to someone who will not read the
document.

## What a video is made of

A video is code plus audio files. Four free pieces, and Claude writes and runs all of them:

| Piece | Role | What it does |
|---|---|---|
| Claude Code | director | interviews you, writes the script, builds the scenes, renders and reviews stills |
| Remotion | picture | videos as React components; every frame is a function of time; renders to MP4 |
| Kokoro TTS | voice | natural voice that runs offline on the CPU; Apache-2.0, so no attribution is needed |
| a small Node script | music and sound effects | generates the music, so there is nothing to license; quiet under the voice |

Each scene asks `useCurrentFrame()` which frame it is on and draws itself for that
frame. A headless browser steps through every frame, captures it, and `ffmpeg` joins
the frames with the audio.

## Read this first: is a video worth it?

A video costs roughly one to two hours of authoring plus a few minutes of render
time, and it is harder to correct than a document. One wrong number means a new
render.

| Use a video when | Use slides or a page instead when |
|---|---|
| The audience will not read the document | The audience will read it |
| The result has a sequence that benefits from motion (a process, a mechanism, a before/after) | The content is a list of facts |
| It will be shown more than once, or sent to people who were not in the room | It is for one meeting |
| You want a fixed, self-contained artifact with no presenter | You will present it live and want to answer questions |

A local voice is understandable but clearly synthetic. For anything customer-facing,
record a human voice over the same picture instead.

## The workflow: voice first, then the picture follows the voice

```
1 Brief ─► 2 Script ─► 3 Voice ─► 4 Music ─► 5 Scenes ─► 6 Stills ─► Render
           narration   Kokoro     generated  animations  check      out/video.mp4
           .json       → WAV      to fit     per line    frames
```

**Why voice first.** The real audio length sets the timing. Every animation is pinned
to a narration line, so changing a sentence never breaks the sync. The reverse order
(picture first) forces you to tune every scene length by hand.

### 1. Brief

Before any file exists, Claude asks you questions until the decisions are settled.
Do not skip this; a wrong answer found after the render costs a full render.

Settle these:

- **Audience and use**: who watches it, and may it leave the organisation?
- **The one message**: what should the viewer remember in one sentence?
- **Length**: target total minutes. Scenes are 15 to 30 seconds each.
- **Proof**: which numbers appear, and which command produces each one?
- **Tone and look**: calm or bright; one accent colour for the thing the video is about.

Write the answers into the project `README.md`. Include whether the video may leave
the organisation, and keep that note next to the file.

### 2. Script: `narration.json`

One idea per line. A line is the unit that the voice, the timing and the animation
all share.

```json
{ "scenes": [
  { "id": "problem", "label": "The problem",
    "lines": ["Releases drift between environments.",
              "Here is what that looked like last month."] }
] }
```

Write for the ear, not the eye:

- Short sentences. The listener cannot go back a line.
- Spell out what the synthesiser will mispronounce: write `S Q L` for an acronym the
  voice would otherwise say as a word, and `thirteen thousand eight hundred` for a
  figure you want spoken in full.
- Say the number once in the narration and show it on screen at the same time. Do not
  read out a table.
- Keep each scene between 15 and 30 seconds. Longer scenes make the picture static.

### 3. Voice: Kokoro to WAV, durations measured

Kokoro runs offline on the CPU. Nothing is sent to a service, which matters when the
narration describes unpublished work.

```bash
uv pip install kokoro-onnx soundfile      # or: pip install kokoro-onnx soundfile
mkdir -p ~/voices && cd ~/voices
# Download kokoro-v1.0.onnx and voices-v1.0.bin from the kokoro-onnx project
# release page (check the project README for the current URLs).
```

`build-audio.py` (in this skill directory; copy it to `<PROJECT_DIR>/scripts/`)
renders every line, joins the lines of one scene with a short gap, adds a lead-in and
a tail, measures the result, and writes `src/scenes.json`:

```bash
KOKORO_MODEL=~/voices/kokoro-v1.0.onnx KOKORO_VOICES=~/voices/voices-v1.0.bin \
  python3 scripts/build-audio.py
```

```json
{ "fps": 30,
  "scenes": [ { "id": "problem", "label": "The problem", "audio": "audio/problem.wav",
                "durationInFrames": 424,
                "lines": [ { "text": "Releases drift ...", "startFrame": 15, "endFrame": 98 },
                           { "text": "Here is what ...",  "startFrame": 109, "endFrame": 201 } ] } ] }
```

The composition reads that file. Never write `durationInFrames` or a reveal delay by
hand: use the `startFrame` of the line the element belongs to.

`tsconfig.json` needs `"resolveJsonModule": true` for the import. Pick another voice
with `KOKORO_VOICE=<name>`; the voice names are listed in the voices file
(`kokoro.get_voices()`).

If Kokoro does not install on the machine, the macOS `say` command is a lower-quality
fallback (`say -v <VOICE> -o out.aiff "Hello."`). Whisper does not help here: it
transcribes audio into text and cannot produce a voice.

### 4. Music, generated to fit the narration

```bash
node scripts/generate-music.mjs        # reads src/scenes.json, writes public/audio/music.wav
```

The script makes a slow pad track as long as the narration. `MUSIC_MOOD=bright` picks
the other chord set. Play it under the whole video at volume 0.10 to 0.15; the voice
must stay clearly in front. Run it after step 3, so the length matches the final
voice.

### 5. Scenes: animations timed to each line

One component per scene in `src/scenes/*.tsx`. Each reveal gets its `delay` from the
`startFrame` of its line. See [reference/composition.md](reference/composition.md)
for the skeleton: one sizing unit, a theme block, a safe-area wrapper, the two
animation helpers, and how to read line timings.

```bash
npm i
npm i @remotion/google-fonts@<SAME_VERSION_AS_REMOTION> --save-exact
```

Keep every `remotion` and `@remotion/*` package on the same exact version. Scaffold a
new project with `npx create-video@latest --yes --blank --no-tailwind .`.

Preview live while you work: `npx remotion studio`. The studio reloads when you save,
and it plays the real audio.

### 6. Stills, then render

Rendering a four-minute video takes minutes. Rendering one frame takes seconds.

```bash
npx remotion still <COMPOSITION_ID> out/stills/f<N>.png --frame=<N>
```

Render one frame per scene, picked **near the end of the scene** so every element has
appeared. Look at the two or three densest scenes. Fix what you see, then render:

```bash
npx remotion render <COMPOSITION_ID> out/video.mp4

# the audio track is the part most likely to be silently missing
ffprobe -v error -show_entries format=duration -show_entries stream=codec_name,codec_type \
        -of default=nw=1 out/video.mp4
ffmpeg -ss 10 -t 20 -i out/video.mp4 -vn -af volumedetect -f null /dev/null 2>&1 \
  | grep -E "mean_volume|max_volume"
```

A mean volume near −18 dB with a peak near −3 dB is a healthy speech track. A mean
below −60 dB means the audio did not make it into the file.

## Iterate in plain words

After the first render, change the video by saying what is wrong, in everyday words:
"slower in scene 3", "the table is too small", "make the music quieter". Claude maps
each request to one place:

| You say | What changes | Then |
|---|---|---|
| "slower in scene 3" / a sentence is wrong | the line in `narration.json` | re-run `build-audio.py` and `generate-music.mjs`; lines move the picture by themselves |
| "the table is too small" | sizes in that scene file | check that scene's still |
| "make the music quieter" | the music `volume` in the composition | listen in `remotion studio` |

## Prerequisites

| Tool | Why | Check |
|---|---|---|
| Node.js 18+ | Remotion and the music script | `node -v` |
| Python 3.10+ | Kokoro | `python3 --version` |
| `ffmpeg` | joins frames and audio, measures durations | `ffmpeg -version` |
| A Chrome-family browser | frame capture (Remotion downloads one if none is found) | — |

**Licence.** Remotion is free for individuals, for non-profits, and for for-profit
organisations with up to three employees. Larger for-profit organisations need a paid
company licence. Evaluation is free. Check this before making it a standing workflow.
Kokoro is Apache-2.0. The generated music has no licence question.

## Mistakes that cost a render

| Symptom | Cause | Fix |
|---|---|---|
| Scene content overlaps the header or footer | each scene sets its own padding | one `Stage` wrapper with a fixed safe area, applied once in the composition |
| A long identifier breaks mid-word (`inventory_sync_s` / `ervice`) | it is one word to the line breaker | insert a zero-width space after each `_` and `/` |
| Cards in a row have different heights | content sets the height | fixed height plus `overflow: hidden`, and `alignItems: "stretch"` |
| Text spills out of a fixed-height card | the card was sized for the shortest item | size it for the longest item and check that scene's still |
| The render makes ~100 font requests per font | `loadFont()` with no arguments loads every weight and subset | `loadFont("normal", { weights: [...], subsets: ["latin"] })` |
| Audio track missing or silent | the `<Audio>` element sits outside the sequence that is on screen | keep the audio inside the same `Series.Sequence` as its scene |
| Picture and voice drift apart | reveal delays or scene lengths were written by hand | take them from `scenes.json` (`startFrame`, `durationInFrames`) |
| Music is as loud as the voice | music volume left at 1 | set `volume={0.12}` on the music `<Audio>` |
| Music ends before the video | music was made before the voice changed | re-run `generate-music.mjs` after every `build-audio.py` run |

## Honest-numbers rules

A video is harder to correct than a document, so put less in it and make each claim
survivable.

- **Compute the numbers, do not type them.** If a figure comes from code, run the code
  and paste the output. A number invented for a slide will be quoted back at you.
- **Count steps, not time**, unless you measured the time.
- **Label drawn charts.** A bar chart drawn to explain an idea gets the word
  `schematic` on screen. Never let an illustration pass as measured data.
- **Show the failure too.** A result that is amber in the video is more credible than
  an all-green one, and it stops the one question you cannot answer later.

## Confidentiality

Apply [`skill-confidentiality-boundary`](../skill-confidentiality-boundary/SKILL.md)
to the narration, not only to the code. A voice track carries customer names, internal
system names and error figures just as a document does, and a video is easier to
forward than a document.
