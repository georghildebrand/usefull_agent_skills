#!/usr/bin/env bash
# Spoken lines with Piper text-to-speech, fully local: no text leaves the machine.
# Input: a text file with one line per scene (node tools/lines.js writes it from src/scene-data.js).
# Output in <out_dir>:
#   lineNN.wav       the voice only, one file per scene
#   sceneNN.wav      LEAD s of silence + voice + TAIL s of silence: this is the length of the scene
#   narration.wav    all scene WAVs joined, start to end (the sound track of the video)
#   durations.json   fps, total_frames, total_s and per scene: text, speech_s, scene_s, frames, start_frame
# Usage: bash tools/narrate.sh <lines.txt> <out_dir>
# Env:   PIPER         the Piper command (default: piper), e.g. PIPER="/path/to/venv/bin/python -m piper"
#        PIPER_VOICE   path to a voice model (.onnx, with its .onnx.json next to it); required
#        FPS=30 LEAD=0.4 TAIL=0.9 LENGTH_SCALE=1.06 (above 1 speaks slower)
#        MIN_S="5.2,5.3,..." the shortest length of each scene in s (node tools/lines.js --min); silence is added
#        at the end when LEAD + voice + TAIL is shorter, so a short line never cuts an animation
# Install Piper once (Python 3.9+):
#   uv tool install piper-tts              (or: pipx install piper-tts)
#   python3 -m piper.download_voices en_US-ryan-high --download-dir ~/piper-voices
#     (run it with the Python of the piper install, or download en_US-ryan-high.onnx and .onnx.json from
#      https://huggingface.co/rhasspy/piper-voices, folder en/en_US/ryan/high)
#   export PIPER_VOICE=~/piper-voices/en_US-ryan-high.onnx
# Piper is not exactly repeatable (the same line differs by up to 0.1 s), so make the voice once and record from
# that durations.json; never make the voice again after the frames are recorded.
set -euo pipefail
if [ $# -ne 2 ]; then sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 2; fi
src="$1"; out="$2"
FPS="${FPS:-30}"; LEAD="${LEAD:-0.4}"; TAIL="${TAIL:-0.9}"; LENGTH_SCALE="${LENGTH_SCALE:-1.06}"
read -r -a PIPER_CMD <<< "${PIPER:-piper}"
install_help() { echo "$1" >&2; sed -n '15,20p' "$0" | sed 's/^# \{0,1\}/  /' >&2; exit 2; }
command -v "${PIPER_CMD[0]}" >/dev/null || install_help "Piper not found (PIPER=${PIPER:-piper})."
[ -n "${PIPER_VOICE:-}" ] && [ -f "$PIPER_VOICE" ] || install_help "No voice model: set PIPER_VOICE to an .onnx file."
command -v ffmpeg >/dev/null || { echo "ffmpeg not found" >&2; exit 2; }
IFS=, read -r -a MINS <<< "${MIN_S:-}"
mkdir -p "$out"
rm -f "$out"/line[0-9]*.wav "$out"/line[0-9]*.txt "$out"/scene[0-9]*.wav "$out"/narration.wav "$out"/durations.json "$out"/concat.txt

i=0
while IFS= read -r line || [ -n "$line" ]; do
  [ -z "${line// }" ] && continue
  i=$((i + 1)); n=$(printf '%02d' "$i")
  printf '%s\n' "$line" > "$out/line$n.txt"
  "${PIPER_CMD[@]}" -m "$PIPER_VOICE" --length-scale "$LENGTH_SCALE" --sentence-silence 0.3 \
        -i "$out/line$n.txt" -f "$out/line$n.wav" >/dev/null 2>&1
  # pad: LEAD s before, TAIL s after, at least MIN_S in all (adelay and apad are core ffmpeg filters)
  ms=$(python3 -c "print(int(round($LEAD * 1000)))")
  af="adelay=${ms}:all=1,apad=pad_dur=${TAIL}"
  min="${MINS[$((i - 1))]:-}"; [ -n "$min" ] && af="$af,apad=whole_dur=${min}"
  ffmpeg -y -hide_banner -loglevel error -i "$out/line$n.wav" -af "$af" "$out/scene$n.wav"
  echo "file 'scene$n.wav'" >> "$out/concat.txt"
done < "$src"
[ "$i" -gt 0 ] || { echo "no lines in $src" >&2; exit 1; }

ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i "$out/concat.txt" -c copy "$out/narration.wav"

python3 - "$out" "$FPS" "$i" <<'PY'
import json, pathlib, subprocess, sys
out, fps, count = pathlib.Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]).decode())
scenes, start = [], 0
for k in range(1, count + 1):
    n = f"{k:02d}"
    speech, total = dur(out / f"line{n}.wav"), dur(out / f"scene{n}.wav")
    frames = int(round(total * fps))
    scenes.append({"id": k, "text": (out / f"line{n}.txt").read_text().strip(), "speech_s": round(speech, 3),
                   "scene_s": round(total, 3), "frames": frames, "start_frame": start})
    print(f"  scene {k:2d}  speech {speech:6.2f} s  scene {total:6.2f} s  {frames:5d} frames")
    start += frames
nar = dur(out / "narration.wav")
json.dump({"fps": fps, "total_frames": start, "total_s": round(start / fps, 3), "narration_s": round(nar, 3),
           "scenes": scenes}, open(out / "durations.json", "w"), indent=2)
print(f"  total {start} frames = {start / fps:.2f} s (narration.wav {nar:.2f} s)")
PY
