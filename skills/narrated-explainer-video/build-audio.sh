#!/bin/bash
# Renders one narration WAV per scene, measures it, and writes src/scenes.json with
# the scene lengths in frames. Everything runs locally; no text leaves the machine.
#
# Usage:  PIPER_VOICE=/path/to/voice.onnx ./build-audio.sh
#
# Expects:  narration/*.txt   one file per scene, named so they sort in order
# Writes:   public/audio/sceneN.wav  and  src/scenes.json
set -euo pipefail

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
VOICE="${PIPER_VOICE:?set PIPER_VOICE to the .onnx voice file}"
PIPER="${PIPER_BIN:-piper}"
FPS="${FPS:-30}"
LEAD="${LEAD:-0.5}"   # silence before the voice starts, in seconds
TAIL="${TAIL:-1.3}"   # silence after the voice ends, in seconds

cd "$PROJECT"
mkdir -p public/audio src

# One label per narration file, in the same order. Shown in the video and in the log.
LABELS=("Scene one" "Scene two" "Scene three")

json='{"fps":'"$FPS"',"lead":'"$LEAD"',"scenes":['
i=0
for f in narration/*.txt; do
  i=$((i + 1))
  out="public/audio/scene$i.wav"
  "$PIPER" -m "$VOICE" --length-scale 1.06 --sentence-silence 0.4 \
           -i "$f" -f "$out" >/dev/null 2>&1
  speech=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out")
  total=$(python3 -c "print($LEAD + $speech + $TAIL)")
  frames=$(python3 -c "import math; print(int(math.ceil($total * $FPS)))")
  label="${LABELS[$((i-1))]:-Scene $i}"
  printf '  scene %d  %-20s speech %6.2fs  scene %6.2fs  %5d frames\n' \
         "$i" "$label" "$speech" "$total" "$frames"
  [ "$i" -gt 1 ] && json="$json,"
  json="$json"'{"id":'"$i"',"label":"'"$label"'","audio":"audio/scene'"$i"'.wav","speech":'"$speech"',"durationInFrames":'"$frames"'}'
done
json="$json]}"
python3 -c "import json,sys; print(json.dumps(json.loads(sys.argv[1]), indent=2))" "$json" > src/scenes.json

python3 -c "
import json
d = json.load(open('src/scenes.json'))
f = sum(s['durationInFrames'] for s in d['scenes'])
print(f'total: {f} frames = {f / d[\"fps\"]:.1f} s')
"
