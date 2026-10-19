#!/usr/bin/env bash
#
# Capture the animated header mark frozen at its "hold" frame, using the real
# logo.js. Writes tools/.out/hold_dom.html (for tools/check_dom.py) and
# tools/.out/hold_logo.png (for tools/analyze.py).
#
# Usage:  tools/hold.sh            (override with HOLD_PORT=... CHROME=...)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/tools/.out"
HARNESS="$OUT/holdtest"
PORT="${HOLD_PORT:-8129}"
CHROME="${CHROME:-google-chrome-stable}"

mkdir -p "$HARNESS"

if ! command -v "$CHROME" >/dev/null 2>&1; then
  echo "hold: '$CHROME' not found -- install Chrome or set CHROME=/path/to/chrome" >&2
  exit 1
fi

python3 "$ROOT/tools/hold_frame.py" "$HARNESS"
cp "$ROOT/logo.js" "$HARNESS/logo.js"

python3 -m http.server "$PORT" --directory "$HARNESS" >"$OUT/hold_httpd.log" 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT
sleep 1.5

FLAGS=(--headless=new --disable-gpu --no-sandbox --hide-scrollbars
       --user-data-dir="$OUT/chrome-hold" --virtual-time-budget=1500)

"$CHROME" "${FLAGS[@]}" --window-size=400,200 --dump-dom \
  "http://localhost:$PORT/hold.html" >"$OUT/hold_dom.html" 2>"$OUT/hold_dom.err"

# Large scale factor so the mark covers enough pixels to analyse.
"$CHROME" "${FLAGS[@]}" --force-device-scale-factor=8 --window-size=400,200 \
  --screenshot="$OUT/hold_logo.png" \
  "http://localhost:$PORT/hold.html" >"$OUT/hold_shot.log" 2>&1

ls -la "$OUT/hold_dom.html" "$OUT/hold_logo.png"
echo "hold: frozen mark captured in $OUT"
