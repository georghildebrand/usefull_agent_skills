---
name: narrated-explainer-video
description: Use when a technical result has to be delivered as a narrated MP4 video instead of slides - builds a Remotion composition with locally generated speech, where the scene lengths are derived from the audio
---

# Narrated explainer video

Turn a finished piece of work into a short video with a voice track: an MP4 you can
play in a meeting, attach to a report, or hand to someone who will not read the
document.

The video is a React component. Each scene asks `useCurrentFrame()` which frame it is
on and draws itself for that frame. A headless browser steps through every frame,
captures it, and `ffmpeg` joins the frames with the audio.

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

A locally generated voice is understandable but clearly synthetic. For anything
customer-facing, record a human voice over the same picture instead.

## Prerequisites

| Tool | Why | Check |
|---|---|---|
| Node.js 18+ | Remotion | `node -v` |
| `ffmpeg` | joins frames and audio, measures durations | `ffmpeg -version` |
| A Chrome-family browser | frame capture (Remotion downloads one if none is found) | — |
| A local text-to-speech engine | the voice track | see below |

**Licence.** Remotion is free for individuals, for non-profits, and for for-profit
organisations with up to three employees. Larger for-profit organisations need a paid
company licence. Evaluation is free. Check this before making it a standing workflow.

### Text to speech, locally

Speech recognition and speech synthesis are opposite directions. **Whisper transcribes
audio into text; it cannot produce a voice.** For a voice you need a synthesiser.

Two local options, in order of quality:

```bash
# Piper: small neural voices, clearly better than the operating system voices
uv tool install piper-tts          # or: pipx install piper-tts
mkdir -p ~/voices && cd ~/voices
python -m piper.download_voices <VOICE_NAME> --data-dir .

# Piper will not download a voice on its own. Passing `-m <VOICE_NAME>` without
# downloading first fails with "Unable to find voice". Pass the .onnx path:
echo "Hello." | piper -m ./<VOICE_NAME>.onnx -f out.wav
```

```bash
# macOS built-in: no install, lower quality
say -v <VOICE> -o out.aiff "Hello."
# Better voices exist but must be downloaded in the system settings first;
# only the basic set is installed by default.
```

Both run on the machine. Nothing is sent to a service. That matters when the
narration describes unpublished work.

## The pipeline

Write the words first, then let the picture follow them. The reverse order forces you
to tune every scene length by hand.

```
narration/*.txt  ──►  build-audio.sh  ──►  public/audio/*.wav
                           │                      │
                           └──►  src/scenes.json ◄┘   (scene lengths in frames)
                                       │
                                src/Video.tsx  ──►  stills  ──►  render  ──►  out/*.mp4
```

### 1. Scaffold

```bash
mkdir -p <PROJECT_DIR> && cd <PROJECT_DIR>
npx create-video@latest --yes --blank --no-tailwind .
npm i
npm i @remotion/google-fonts@<SAME_VERSION_AS_REMOTION> --save-exact
```

Keep every `remotion` and `@remotion/*` package on the same exact version.

### 2. Narration

One plain-text file per scene, named so they sort in order:
`narration/01-<topic>.txt`, `narration/02-<topic>.txt`, …

Write for the ear, not the eye:

- Short sentences. The listener cannot go back a line.
- Spell out what the synthesiser will mispronounce: write `S Q L` for an acronym the
  voice would otherwise try to say as a word, and `thirteen thousand eight hundred`
  for a figure you want spoken in full.
- Say the number once in the narration and show it on screen at the same time. Do not
  read out a table.
- Keep each scene between 15 and 30 seconds. Longer scenes make the picture static.

### 3. Audio and timings

`build-audio.sh` (in this skill directory) renders one WAV per scene, measures it with
`ffprobe`, adds a lead-in and a tail, and writes `src/scenes.json`:

```json
{ "fps": 30, "lead": 0.5,
  "scenes": [ { "id": 1, "label": "...", "audio": "audio/scene1.wav",
                "speech": 12.31, "durationInFrames": 424 } ] }
```

The composition reads that file, so changing a sentence and re-running the script
adjusts the scene length by itself. Never write `durationInFrames` by hand.

`tsconfig.json` needs `"resolveJsonModule": true` for the import.

### 4. Compose

See [reference/composition.md](reference/composition.md) for the skeleton: one sizing
unit, a theme block, a safe-area wrapper, and the two animation helpers that cover
almost every reveal.

### 5. Check stills before rendering

Rendering a four-minute video takes minutes. Rendering one frame takes seconds.

```bash
npx remotion still <COMPOSITION_ID> out/stills/f<N>.png --frame=<N>
```

Render one frame per scene, picked **near the end of the scene** so every element has
appeared. Look at the two or three densest scenes. Fix what you see, then render.

### 6. Render and verify

```bash
npx remotion render <COMPOSITION_ID> out/<NAME>.mp4

# the audio track is the part most likely to be silently missing
ffprobe -v error -show_entries format=duration -show_entries stream=codec_name,codec_type \
        -of default=nw=1 out/<NAME>.mp4
ffmpeg -ss 10 -t 20 -i out/<NAME>.mp4 -vn -af volumedetect -f null /dev/null 2>&1 \
  | grep -E "mean_volume|max_volume"
```

A mean volume near −18 dB with a peak near −3 dB is a healthy speech track. A mean
below −60 dB means the audio did not make it into the file.

## Mistakes that cost a render

| Symptom | Cause | Fix |
|---|---|---|
| Scene content overlaps the header or footer | each scene sets its own padding | one `Stage` wrapper with a fixed safe area, applied once in the composition |
| A long identifier breaks mid-word (`inventory_sync_s` / `ervice`) | it is one word to the line breaker | insert a zero-width space after each `_` and `/` |
| Cards in a row have different heights | content sets the height | fixed height plus `overflow: hidden`, and `alignItems: "stretch"` |
| Text spills out of a fixed-height card | the card was sized for the shortest item | size it for the longest item and check that scene's still |
| The render makes ~100 font requests per font | `loadFont()` with no arguments loads every weight and subset | `loadFont("normal", { weights: [...], subsets: ["latin"] })` |
| Audio track missing or silent | the `<Audio>` element sits outside the sequence that is on screen | keep the audio inside the same `Series.Sequence` as its scene |
| Picture and voice drift apart | scene lengths were written by hand | derive them from the measured audio |

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

Write in the project `README.md` who the video is for and whether it may leave the
organisation. Keep that note next to the file, not only in a chat message.
