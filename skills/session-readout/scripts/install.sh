#!/usr/bin/env bash
# Build the reader app and install the launcher and the /stand command. macOS only.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
APP="${STAND_APP:-$HOME/Applications/Sitzungsstand.app}"
BINDIR="${BINDIR:-$HOME/.local/bin}"
CMDDIR="${CMDDIR:-$HOME/.claude/commands}"

echo "== build $APP"
mkdir -p "$APP/Contents/MacOS"
swiftc -O -swift-version 5 -o "$APP/Contents/MacOS/Sitzungsstand" "$HERE/app/Sitzungsstand.swift"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Sitzungsstand</string>
  <key>CFBundleIdentifier</key><string>local.session-readout.sitzungsstand</string>
  <key>CFBundleExecutable</key><string>Sitzungsstand</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSUIElement</key><true/>
  <key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
</dict></plist>
PLIST
codesign --force --sign - "$APP" >/dev/null 2>&1 || true

echo "== launcher $BINDIR/stand-speak"
mkdir -p "$BINDIR"
install -m 755 "$HERE/scripts/stand-speak" "$BINDIR/stand-speak"

echo "== command $CMDDIR/stand.md (symlink)"
mkdir -p "$CMDDIR"
ln -sfn "$HERE/commands/stand.md" "$CMDDIR/stand.md"

"$BINDIR/stand-speak" --check
echo "Done. Type /stand in a Claude Code session."
