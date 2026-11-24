#!/usr/bin/env bash
# Renders assets/icon.svg to assets/icon.png (1024x1024, transparent background) with headless
# Chrome. Run it after editing the SVG; electron-builder turns the PNG into the app icon.
set -euo pipefail

cd "$(dirname "$0")/.."
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

cat > "$work/icon.html" <<HTML
<!doctype html>
<style>html, body { margin: 0; background: transparent; } svg { display: block; }</style>
$(cat assets/icon.svg)
HTML

"$chrome" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --default-background-color=00000000 --user-data-dir="$work/profile" \
  --window-size=1024,1024 --screenshot="$PWD/assets/icon.png" "file://$work/icon.html" 2> /dev/null
echo "Wrote assets/icon.png"
