#!/usr/bin/env bash
# Make out/explainer.mp4: spoken lines (Piper) -> timing check -> frames (headless Chrome) -> MP4 -> ffprobe check.
# The scene lengths follow the spoken lines (out/audio/durations.json). Frames go to out/frames, and the last frame
# of each scene is copied to out/check/scene-NN.png: look at these before you watch the video.
# Usage: bash tools/render.sh
# Env: W=1920 H=1080 FPS=30   video size and frame rate
#      GL=swiftshader|metal   software WebGL (default, same result on every machine) or the GPU (about 5x faster)
#      VOICE=new              make the voice again (default: reuse out/audio when it was made for the same FPS and
#                             the same lines; new lines, from changed subtitles or LINES=, make it again)
#      LINES=<file>           narrate your own lines (one per scene) instead of the subtitles in src/scene-data.js
#      SILENT=1               no voice: each scene lasts its anim + hold
#      PIPER, PIPER_VOICE     see tools/narrate.sh
# Needs vendor/three.min.js (bash tools/fetch-three.sh), Google Chrome or Chromium, ffmpeg with libx264, node, python3.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
W="${W:-1920}"; H="${H:-1080}"; FPS="${FPS:-30}"
[ -f vendor/three.min.js ] || { echo "vendor/three.min.js is missing: run bash tools/fetch-three.sh" >&2; exit 1; }
mkdir -p out/audio
args=()
if [ -z "${SILENT:-}" ]; then
  # the lines to speak now; the voice in out/audio was made from out/audio/lines.txt
  if [ -n "${LINES:-}" ]; then cp "$LINES" out/audio/lines.new; else node tools/lines.js > out/audio/lines.new; fi
  same_fps=$(python3 -c "import json,sys;print(int(json.load(open(sys.argv[1]))['fps'])==int(sys.argv[2]))" out/audio/durations.json "$FPS" 2>/dev/null || echo False)
  same_lines=False; cmp -s out/audio/lines.new out/audio/lines.txt && same_lines=True
  if [ "${VOICE:-}" = new ] || [ "$same_fps" != True ] || [ "$same_lines" != True ]; then
    [ "$same_lines" = True ] || [ ! -f out/audio/lines.txt ] || echo "the lines changed since the last voice: making the voice again"
    FPS="$FPS" MIN_S="$(node tools/lines.js --min)" bash tools/narrate.sh out/audio/lines.new out/audio
    mv out/audio/lines.new out/audio/lines.txt   # only after a full voice, so a failed run never looks up to date
  else
    rm -f out/audio/lines.new; echo "reusing the voice in out/audio (same lines, $FPS fps); VOICE=new makes it again"
  fi
  node tools/timing.js out/audio/durations.json
  args=(--timing out/audio/durations.json --audio out/audio/narration.wav)
fi
start=$(date +%s)
python3 tools/record.py --out out/frames --w "$W" --h "$H" --fps "$FPS" --gl "${GL:-swiftshader}" \
  ${args[@]+"${args[@]}"} --mp4 out/explainer.mp4
echo "frames and MP4 took $(( $(date +%s) - start )) s"
python3 - "$W" "$H" "$FPS" "${SILENT:-}" <<'PY'
import json, pathlib, shutil, subprocess, sys
w, h, fps, silent = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), bool(sys.argv[4])
p = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
    "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,duration", "-of", "json", "out/explainer.mp4"]))
v = next(s for s in p["streams"] if s["codec_type"] == "video")
assert (v["codec_name"], v["width"], v["height"], v["r_frame_rate"], v["pix_fmt"]) == ("h264", w, h, f"{fps}/1", "yuv420p"), v
frames = sorted(pathlib.Path("out/frames").glob("*.png"))
want = len(frames) / fps
assert abs(float(v["duration"]) - want) <= 0.1, ("video", v["duration"], want)
if not silent:
    a = next(s for s in p["streams"] if s["codec_type"] == "audio")
    assert a["codec_name"] == "aac", a
    assert abs(float(a["duration"]) - want) <= 0.15, ("audio", a["duration"], want)
    check = pathlib.Path("out/check"); shutil.rmtree(check, ignore_errors=True); check.mkdir()
    for k, s in enumerate(json.load(open("out/audio/durations.json"))["scenes"], 1):
        shutil.copy(frames[s["start_frame"] + s["frames"] - 1], check / f"scene-{k:02d}.png")
    print(f"video ok: {w}x{h} {fps} fps, {float(v['duration']):.2f} s, H.264 + AAC; last frame of each scene in out/check/")
else:
    print(f"video ok: {w}x{h} {fps} fps, {float(v['duration']):.2f} s, H.264, no sound")
PY
