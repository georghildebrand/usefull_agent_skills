#!/usr/bin/env bash
# Sign audit: per scene, lists the signs the layout rules hid (cut by the edge, under a DOM box, over a cart, overlapping)
# and any visible sign that is still cut off, overlapping another sign, covering a cart or lying under a DOM box.
# Usage: [SHOTS=dir] [RECTS=1] bash tools/audit.sh <WxH> <scene> [...]
#   SHOTS=dir also saves a still of each scene; RECTS=1 also lists the screen box of every sign. Scenes run in parallel.
set -euo pipefail
size="$1"; shift
w="${size%x*}"; h="${size#*x}"; hd=$((h + 87))   # headless --dump-dom loses 87 px of height to browser chrome
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
root="$(cd "$(dirname "$0")/.." && pwd)"; out="$(mktemp -d)"
one() {
  local sc="$1" tmp="$root/.audit-$1.html" q
  sed 's#<script src="src/main.js"></script>#<script src="tools/audit-pre.js"></script><script src="src/main.js"></script><script src="tools/audit-post.js"></script>#' "$root/index.html" > "$tmp"
  q="scene=${sc}&still${RECTS:+&rects}"
  if [ -n "${SHOTS:-}" ]; then
    mkdir -p "$SHOTS"; "$chrome" --headless=new --hide-scrollbars --window-size="$w,$h" --use-angle=swiftshader --enable-unsafe-swiftshader \
      --ignore-gpu-blocklist --virtual-time-budget=9000 --screenshot="$SHOTS/${sc}_${size}.png" "file://${tmp}?${q}" >/dev/null 2>&1 || echo "still failed: scene $sc" >&2
  fi
  "$chrome" --headless=new --hide-scrollbars --window-size="$w,$hd" --use-angle=swiftshader --enable-unsafe-swiftshader \
    --ignore-gpu-blocklist --virtual-time-budget=16000 --dump-dom "file://${tmp}?${q}" 2>/dev/null > "$out/$sc.dom" || true
  rm -f "$tmp"
}
for sc in "$@"; do one "$sc" & done; wait
for sc in "$@"; do
  echo "== scene $sc ($size)"
  python3 - "$out/$sc.dom" <<'PY'
import sys, re, json, html, os
dom = open(sys.argv[1]).read() if os.path.exists(sys.argv[1]) else ""
m = re.search(r'<pre id="audit"[^>]*>(.*?)</pre>', dom, re.S)
if not m:
    print("NO AUDIT OUTPUT"); sys.exit()
d = json.loads(html.unescape(m.group(1)))
print("signs:", d["n"])
for i in d["issues"]:
    print(" ", i)
PY
done
rm -rf "$out"
