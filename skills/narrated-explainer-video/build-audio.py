#!/usr/bin/env python3
"""Voice first: render every narration line to speech, measure it, write src/scenes.json.

Everything runs locally on the CPU. No text leaves the machine.

Usage (from the project directory):
    KOKORO_MODEL=~/voices/kokoro-v1.0.onnx KOKORO_VOICES=~/voices/voices-v1.0.bin \
        python3 scripts/build-audio.py

Reads:   narration.json   {"scenes": [{"id": "...", "label": "...", "lines": ["...", "..."]}]}
Writes:  public/audio/<scene id>.wav   one file per scene (lead-in + lines + tail)
         src/scenes.json               scene lengths and the start frame of every line

One idea per line. A scene animation is pinned to a line through its start frame,
so changing a sentence and re-running this script moves the picture with it.
"""
import json
import math
import os
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent
FPS = int(os.environ.get("FPS", "30"))
LEAD = float(os.environ.get("LEAD", "0.5"))   # silence before the first line, seconds
GAP = float(os.environ.get("GAP", "0.35"))    # silence between lines, seconds
TAIL = float(os.environ.get("TAIL", "1.3"))   # silence after the last line, seconds
VOICE = os.environ.get("KOKORO_VOICE", "af_sarah")
SPEED = float(os.environ.get("KOKORO_SPEED", "0.95"))

model = Path(os.environ["KOKORO_MODEL"]).expanduser()
voices = Path(os.environ["KOKORO_VOICES"]).expanduser()
kokoro = Kokoro(str(model), str(voices))

spec = json.loads((ROOT / "narration.json").read_text())
out_dir = ROOT / "public" / "audio"
out_dir.mkdir(parents=True, exist_ok=True)
(ROOT / "src").mkdir(exist_ok=True)


def silence(seconds: float, sr: int) -> np.ndarray:
    return np.zeros(int(round(seconds * sr)), dtype=np.float32)


scenes = []
for scene in spec["scenes"]:
    parts, lines, sr, cursor = [], [], 24000, 0  # Kokoro outputs 24 kHz; sr is reset per line
    for text in scene["lines"]:
        samples, sr = kokoro.create(text, voice=VOICE, speed=SPEED, lang="en-us")
        samples = samples.astype(np.float32)
        if not parts:
            parts.append(silence(LEAD, sr))
            cursor = len(parts[0])
        lines.append({
            "text": text,
            "startFrame": math.ceil(cursor / sr * FPS),
            "endFrame": math.ceil((cursor + len(samples)) / sr * FPS),
        })
        parts += [samples, silence(GAP, sr)]
        cursor += len(samples) + len(parts[-1])
    parts.append(silence(TAIL - GAP if TAIL > GAP else 0, sr))
    audio = np.concatenate(parts)
    sf.write(out_dir / f"{scene['id']}.wav", audio, sr)
    frames = math.ceil(len(audio) / sr * FPS)
    scenes.append({
        "id": scene["id"],
        "label": scene.get("label", scene["id"]),
        "audio": f"audio/{scene['id']}.wav",
        "durationInFrames": frames,
        "lines": lines,
    })
    print(f"  {scene['id']:<20} {frames / FPS:6.1f} s  {frames:5d} frames  {len(lines)} lines")

(ROOT / "src" / "scenes.json").write_text(json.dumps({"fps": FPS, "scenes": scenes}, indent=2))
total = sum(s["durationInFrames"] for s in scenes)
print(f"total: {total} frames = {total / FPS:.1f} s")
