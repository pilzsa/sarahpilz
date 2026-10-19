#!/usr/bin/env bash
#
# Serve the site locally and capture what a real browser produces:
#   * post-JavaScript DOM of every page  -> tools/check_dom.py
#   * desktop + mobile screenshots       -> tools/analyze.py, in the light
#     theme and -- for the pages the pixel checks cover -- in the dark one.
#
# The DOM dumps matter because the logo mark and the hero are drawn by JS, so
# the served DOM is the only place their output exists.
#
# Usage:  tools/smoke.sh            (override with PORT=... CHROME=...)
# Needs:  python3, google-chrome-stable (or chromium; set $CHROME)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/tools/.out"
PORT="${PORT:-8127}"
CHROME="${CHROME:-google-chrome-stable}"
BASE="http://localhost:$PORT"

mkdir -p "$OUT"

if ! command -v "$CHROME" >/dev/null 2>&1; then
  echo "smoke: '$CHROME' not found -- install Chrome or set CHROME=/path/to/chrome" >&2
  exit 1
fi

python3 -m http.server "$PORT" --directory "$ROOT" >"$OUT/httpd.log" 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT
sleep 1.5

FLAGS=(--headless=new --disable-gpu --no-sandbox --hide-scrollbars
       --user-data-dir="$OUT/chrome-profile" --virtual-time-budget=6000)

# The 6 s budget is deliberately longer than every animation on the page: the
# hero types its line in ~3 s and title.js finishes the wordmark intro in 4.8 s,
# so the dumps and the screenshots show the settled page that check_dom.py and
# analyze.py assert against.

dump() { # page  window-size  output-file
  "$CHROME" "${FLAGS[@]}" --window-size="$2" --dump-dom "$BASE/$1" \
    >"$OUT/$3" 2>"$OUT/$3.err"
}

shot() { # page  window-size  output-file
  "$CHROME" "${FLAGS[@]}" --window-size="$2" --screenshot="$OUT/$3" \
    "$BASE/$1" >/dev/null 2>&1
}

# The same page as a dark-mode visitor with no stored choice sees it:
# --blink-settings=preferredColorScheme=0 makes Chrome report a dark system
# preference, so the theme comes from the system rather than from the URL. It is
# the capture that proves theme.js reads the system, which tools/check_theme.js
# can otherwise only stub.
dump_system_dark() { # page  window-size  output-file
  "$CHROME" "${FLAGS[@]}" --blink-settings=preferredColorScheme=0 \
    --window-size="$2" --dump-dom "$BASE/$1" >"$OUT/$3" 2>"$OUT/$3.err"
}

dump index.html 1440,1000 v_index.html
dump about.html 1440,1000 v_about.html
dump publications.html 1440,1600 v_publications.html
dump gallery.html 1440,1200 v_gallery.html
dump viz-uk-ventilator-challenge.html 1440,1000 v_viz.html

# The dark theme, through both doors it has:
#
#   * ?theme=dark, theme.js's one-page preview -- deterministic, stores nothing
#     and needs no browser preference, so this is what the dark screenshots (and
#     analyze.py's pixel checks) are taken from;
#   * a dark system preference, for the visitor who has never chosen (below).
#
# What neither can capture is the stylesheet's own prefers-color-scheme block:
# every served page runs theme.js in <head>, which settles data-theme before the
# first paint, so the media query never decides a served page by itself. That
# block is held to [data-theme="dark"] value for value by check_css.py.
dump index.html?theme=dark 1440,1000 v_index_dark.html
dump_system_dark index.html 1440,1000 v_index_dark_system.html

shot index.html 1440,1100 v_index_desktop.png
shot index.html  390,844  v_index_mobile.png
shot about.html 1440,1300 v_about_desktop.png
shot about.html  390,900  v_about_mobile.png
shot publications.html 1440,1600 v_publications_desktop.png
shot publications.html  390,1200 v_publications_mobile.png
shot gallery.html 1440,1500 v_gallery_desktop.png
shot gallery.html  390,1200 v_gallery_mobile.png
shot viz-uk-ventilator-challenge.html 1440,1400 v_viz_desktop.png
shot index.html?theme=dark 1440,1100 v_index_dark_desktop.png
shot index.html?theme=dark  390,844  v_index_dark_mobile.png
shot about.html?theme=dark 1440,1300 v_about_dark_desktop.png
shot publications.html?theme=dark 1440,1600 v_publications_dark_desktop.png
shot gallery.html?theme=dark 1440,1500 v_gallery_dark_desktop.png
shot gallery.html?theme=dark  390,1200 v_gallery_dark_mobile.png

ls -la "$OUT"/v_*.html "$OUT"/v_*.png
echo "smoke: DOM dumps and screenshots written to $OUT"
