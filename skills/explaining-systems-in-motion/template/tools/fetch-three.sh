#!/usr/bin/env bash
# Download three.js r147 (MIT licence) into vendor/three.min.js and check its SHA-256.
# The template keeps no copy of three.js in the repository; run this once after you copy the template.
# Usage: bash tools/fetch-three.sh
set -euo pipefail
# cdnjs names r147 "0.147.0" (the path .../three.js/r147/ answers 404); jsDelivr serves the same file
urls="https://cdnjs.cloudflare.com/ajax/libs/three.js/0.147.0/three.min.js https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js"
want="f34446bf875b5fb0dcd93819ffe1d9e182d46634ee855f5d904c6c4ac7cdbc95"
root="$(cd "$(dirname "$0")/.." && pwd)"; dest="$root/vendor/three.min.js"
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
if [ -f "$dest" ] && [ "$(sha "$dest")" = "$want" ]; then echo "$dest is already there (SHA-256 ok)"; exit 0; fi
mkdir -p "$root/vendor"; tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
for url in $urls; do curl -fsSL "$url" -o "$tmp" && break; echo "failed: $url" >&2; done
got="$(sha "$tmp")"
if [ "$got" != "$want" ]; then echo "SHA-256 mismatch: got $got, want $want" >&2; exit 1; fi
mv "$tmp" "$dest"; trap - EXIT
echo "$dest (SHA-256 ok)"
