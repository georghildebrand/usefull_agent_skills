#!/usr/bin/env bash
# Stills of the 3D page with headless Chrome and software WebGL (SwiftShader), one per scene end state.
# Usage: bash tools/shoot.sh <page.html> <out_dir> <WxH> <scene|nowebgl> [...]
#   a scene number opens ?scene=N&still (end state of that scene); "nowebgl" opens ?nowebgl (the fallback message)
#   CHROME=/path/to/chrome overrides the browser (default: Google Chrome on macOS)
set -euo pipefail
page="$1"; out="$2"; size="$3"; shift 3
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
abs="$(cd "$(dirname "$page")" && pwd)/$(basename "$page")"
mkdir -p "$out"
for sc in "$@"; do
  case "$sc" in nowebgl) q="nowebgl" ;; *) q="scene=${sc}&still" ;; esac
  "$chrome" --headless=new --hide-scrollbars --window-size="${size/x/,}" \
    --use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist \
    --virtual-time-budget=8000 --screenshot="$out/${sc}_${size}.png" "file://${abs}?${q}" >/dev/null 2>&1
  echo "$out/${sc}_${size}.png"
done
