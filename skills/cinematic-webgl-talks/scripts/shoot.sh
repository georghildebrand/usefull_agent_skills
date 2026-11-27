#!/usr/bin/env bash
# Screenshot the END state of given beats of a built talk.
# Usage: bash scripts/shoot.sh <built.html> <out_dir> <scene-beat> [<scene-beat> ...]
#   scene-beat = deep link without "#", beat 1-based, e.g. dominoes-3 aim-2.
#   The page opens with ?still, so each beat is drawn finished and not animated.
# WebGL runs on the CPU (SwiftShader) in headless Chrome: slow, but the picture is the same.
# Needs Google Chrome (or set CHROME=/path/to/chrome).
set -euo pipefail
page="$1"; out="$2"; shift 2
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
abs="$(cd "$(dirname "$page")" && pwd)/$(basename "$page")"
mkdir -p "$out"
for sb in "$@"; do
  "$chrome" --headless=new --use-angle=swiftshader --enable-unsafe-swiftshader --hide-scrollbars \
    --window-size=1920,1080 --virtual-time-budget=8000 --screenshot="$out/$sb.png" \
    "file://$abs?still#$sb" >/dev/null 2>&1
  echo "$out/$sb.png"
done
