#!/usr/bin/env bash
#
# Run every check in order and print one summary.
#
#   tools/run_all.sh
#
# Exit code 0 only when every step passes. Full output is in tools/.out/run_all.log;
# on failure the last few lines of that step are echoed here.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/tools/.out"
LOG="$OUT/run_all.log"
CHROME="${CHROME:-google-chrome-stable}"
export CHROME

mkdir -p "$OUT"
: >"$LOG"
failures=0
ran=0

run() { # label  command...
  local label="$1"
  shift
  ran=$((ran + 1))
  printf '\n===== %s =====\n' "$label" >>"$LOG"
  if "$@" >>"$LOG" 2>&1; then
    printf 'PASS  %-18s %s\n' "$label" "$*"
  else
    printf 'FAIL  %-18s %s\n' "$label" "$*"
    tail -n 12 "$LOG" | sed 's/^/        /'
    failures=$((failures + 1))
  fi
}

preflight() {
  local status=0
  for tool in python3 node; do
    if command -v "$tool" >/dev/null 2>&1; then
      printf 'ok    %s\n' "$tool"
    else
      printf 'MISSING %s (required)\n' "$tool"
      status=1
    fi
  done
  if command -v "$CHROME" >/dev/null 2>&1; then
    printf 'ok    %s\n' "$CHROME"
  else
    printf 'MISSING %s (needed for smoke.sh / hold.sh; set CHROME=...)\n' "$CHROME"
    status=1
  fi
  if python3 -c "import PIL" >/dev/null 2>&1; then
    printf 'ok    Pillow\n'
  else
    printf 'MISSING Pillow (needed for analyze.py; python3 -m pip install Pillow)\n'
    status=1
  fi
  return $status
}

echo "== preflight =="
if ! preflight; then
  echo
  echo "run_all: fix the missing tools above first"
  exit 1
fi

# Browser captures first: the DOM checks read what these produce.
run smoke    "$ROOT/tools/smoke.sh"
run hold     "$ROOT/tools/hold.sh"

# Then the static and DOM checks.
run html     python3 "$ROOT/tools/check_html.py"
run js       node "$ROOT/tools/check_js.js"
run theme    node "$ROOT/tools/check_theme.js"
run css      python3 "$ROOT/tools/check_css.py"
run colors   python3 "$ROOT/tools/check_colors.py"
run publications python3 "$ROOT/tools/make_publications.py" --check
run dom      python3 "$ROOT/tools/check_dom.py"
run pixels   python3 "$ROOT/tools/analyze.py"

echo
if [ "$failures" -eq 0 ]; then
  echo "run_all: all $ran steps passed  (log: $LOG)"
  exit 0
fi
echo "run_all: $failures of $ran steps failed  (log: $LOG)"
exit 1
