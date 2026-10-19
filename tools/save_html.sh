#!/usr/bin/env bash
#
# Save the post-JavaScript DOM of every page and every visualisation sub-page
# into saved/ at the repo root, so the markup can be opened and edited later.
#
#   tools/save_html.sh            save every page; keep a snapshot you edited
#   tools/save_html.sh --force    rebuild snapshots that have changed
#   tools/save_html.sh --raw      Chrome's DOM exactly, without <base href="../">
#
# Pages: the same set tools/check_dom.py counts as "the pages that ship" -- the
# five section pages plus one page per visualisation (viz-*.html, discovered
# with a glob, so a new piece page needs no change here).
#
# Why a browser: the header mark, the wordmark intro, the theme and the hero are
# all drawn by JavaScript, so the served DOM is the only place their output
# exists. The 6 s virtual-time budget matches tools/smoke.sh -- longer than every
# animation -- so what is saved is the settled page.
#
# Why the repo and not tools/.out/: the captures under tools/.out/ are
# git-ignored build output that the checks read; saved/ is a set of files meant
# to be read, edited and kept. Each snapshot therefore carries
# <base href="../"> right after <head>, so its relative links (styles.css,
# images/, the scripts and the other pages) resolve against the repo root and
# the snapshot looks like the page it came from. --raw leaves Chrome's output
# exactly as it is.
#
# A snapshot that already exists and would change is kept, not overwritten, so
# re-running this script can never silently throw away an edit. Pass --force to
# rebuild it from the served page. The two things a dump can never reproduce are
# blanked out on both sides of the comparison, so "same" means "the page has not
# changed" rather than "the animation happened to line up": the header mark, which
# headless virtual time catches mid-orbit on an arbitrary frame, and the hero beam
# background, whose d3.timer never stops. See signature() below.
#
# Needs: python3, google-chrome-stable (or chromium; set $CHROME).
# Usage:  tools/save_html.sh [--force] [--raw]  (override with PORT=... CHROME=...)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/saved"
PORT="${PORT:-8131}"
CHROME="${CHROME:-google-chrome-stable}"
BASE="http://localhost:$PORT"
WORK="$(mktemp -d)"
SERVER_PID=""

cleanup() {
  if [ -n "$SERVER_PID" ]; then
    kill "$SERVER_PID" 2>/dev/null || true
  fi
  rm -rf "$WORK"
}
trap cleanup EXIT

usage() {
  # Everything the header comment says, with the leading '# ' stripped.
  sed -n '2,/^set -euo/p' "$0" | sed -n 's/^# \{0,1\}//p'
}

force=0
raw=0
for arg in "$@"; do
  case "$arg" in
    --force) force=1 ;;
    --raw) raw=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "save_html: unknown option: $arg (try --help)" >&2; exit 2 ;;
  esac
done

if ! command -v "$CHROME" >/dev/null 2>&1; then
  echo "save_html: '$CHROME' not found -- install Chrome or set CHROME=/path/to/chrome" >&2
  exit 1
fi

mkdir -p "$DEST"

python3 -m http.server "$PORT" --directory "$ROOT" >"$WORK/httpd.log" 2>&1 &
SERVER_PID=$!
sleep 1.5

FLAGS=(--headless=new --disable-gpu --no-sandbox --hide-scrollbars
       --user-data-dir="$WORK/chrome-profile" --virtual-time-budget=6000)

pages=(index.html about.html publications.html contact.html gallery.html)
for path in "$ROOT"/viz-*.html; do
  if [ -e "$path" ]; then
    pages+=("$(basename "$path")")
  fi
done

# The two live animations a dump can never reproduce: the header mark (caught
# mid-orbit, so its four dots' cx/cy move by a fraction of a unit between runs)
# and the hero beam background on index.html (a d3.timer, so its rects' transforms
# follow elapsed virtual time). Blank them out on both sides of the comparison;
# their colours and structure are still verified independently, by tools/smoke.sh
# and tools/check_dom.py.
signature() {
  sed -E \
    -e 's|<svg id="brand-logo-mark".*</svg>|<svg id="brand-logo-mark"></svg>|' \
    -e 's|<svg class="hero-beams".*</svg>|<svg class="hero-beams"></svg>|' \
    "$1"
}

echo "save_html: $CHROME -> $DEST"
echo

saved=0
kept=0
same=0

for page in "${pages[@]}"; do
  fresh="$WORK/$page"
  "$CHROME" "${FLAGS[@]}" --window-size=1440,1000 --dump-dom "$BASE/$page" \
    >"$fresh" 2>"$WORK/$page.err"

  if [ "$raw" -eq 0 ]; then
    # Chrome's dump carries no <base>, and every page writes its relative links
    # for the repo root -- without this the snapshot would ask for saved/styles.css.
    sed -i '0,/<head>/s|<head>|<head><base href="../">|' "$fresh"
  fi

  if [ ! -f "$DEST/$page" ]; then
    mv "$fresh" "$DEST/$page"
    printf 'saved    %s\n' "$page"
    saved=$((saved + 1))
  elif cmp -s <(signature "$fresh") <(signature "$DEST/$page"); then
    printf 'same     %s\n' "$page"
    same=$((same + 1))
  elif [ "$force" -eq 1 ]; then
    mv "$fresh" "$DEST/$page"
    printf 'updated  %s\n' "$page"
    saved=$((saved + 1))
  else
    printf 'kept     %s (differs from the served page; --force to overwrite)\n' "$page"
    kept=$((kept + 1))
  fi
done

echo
printf 'save_html: %d saved, %d unchanged, %d kept  (%s)\n' \
  "$saved" "$same" "$kept" "$DEST"
