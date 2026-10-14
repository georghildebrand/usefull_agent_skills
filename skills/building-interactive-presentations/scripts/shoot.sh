#!/usr/bin/env bash
# Screenshot the final state of stations of an interactive presentation built from template.html.
# Usage: bash scripts/shoot.sh <index.html> <out_dir> <station_step> [<station_step> ...]
#   station_step = "<station>_<step>", e.g. 3_2. The page is opened with ?s=3&p=2&still,
#   so earlier steps and the current step are applied without animation (final state).
# Needs Google Chrome (or set CHROME=/path/to/chrome).
set -euo pipefail
page="$1"; out="$2"; shift 2
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
mkdir -p "$out"
for sp in "$@"; do
  s="${sp%_*}"; p="${sp#*_}"
  "$chrome" --headless=new --disable-gpu --hide-scrollbars --window-size=1600,900 \
    --virtual-time-budget=4000 --screenshot="$out/s${s}p${p}.png" \
    "file://$(cd "$(dirname "$page")" && pwd)/$(basename "$page")?s=${s}&p=${p}&still" >/dev/null 2>&1
  echo "$out/s${s}p${p}.png"
done
