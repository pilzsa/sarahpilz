#!/usr/bin/env python3
"""Build the phase-locked harness page used by tools/hold.sh.

The header mark runs for 5.2 s, so a screenshot catches it in a random phase.
This page stubs requestAnimationFrame to deliver exactly two frames -- t=0 and
t at the middle of the mark's "hold" window -- which is the moment where the
four dots sit on the square's corners and all four sides are fully drawn.
hold.sh copies the real logo.js next to it, so what gets captured is the
shipped code, not a copy.

The duration and hold window are read out of logo.js, so this harness cannot
drift if the animation timing is retuned.

Usage:  python3 tools/hold_frame.py [output-dir]
        (default: tools/.out/holdtest)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(ROOT, "tools", ".out", "holdtest")

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>hold frame harness</title>
<style>
  body { margin: 0; padding: 12px; background: #ffffff; }
  .brand-logo svg { display: block; width: 120px; height: 120px; overflow: visible; }
</style>
<script>
  /* Stub rAF so the shared mark lands on its "hold" frame and stays there.
     Frames are delivered synchronously because headless virtual time does not
     reliably deliver BeginFrame callbacks to a page with no other work. */
  (function () {
    var step = 0;
    var DURATION = %(duration)s;
    var HOLD_FRAME = %(hold_frame)s;
    window.requestAnimationFrame = function (callback) {
      if (step === 0) { step = 1; callback(0); return 1; }
      if (step === 1) { step = 2; callback(HOLD_FRAME); return 2; }
      return 0;
    };
  })();
</script>
</head>
<body>
  <span class="brand-logo">
    <svg id="brand-logo-mark" viewBox="5 5 34 34" aria-hidden="true"></svg>
  </span>
  <script src="logo.js"></script>
</body>
</html>
"""


def logo_constant(name, fallback):
    """Read a numeric constant out of logo.js so the harness follows the real timing."""
    with open(os.path.join(ROOT, "logo.js"), encoding="utf-8") as f:
        match = re.search(r"\b%s\s*=\s*([0-9.]+)" % name, f.read())
    return float(match.group(1)) if match else fallback


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    os.makedirs(out_dir, exist_ok=True)

    duration = logo_constant("DURATION", 5200)
    draw_end = logo_constant("DRAW_END", 0.82)
    hold_end = logo_constant("HOLD_END", 0.92)
    hold_frame = duration * (draw_end + hold_end) / 2

    path = os.path.join(out_dir, "hold.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(PAGE % {"duration": duration, "hold_frame": hold_frame})
    print("wrote %s (duration=%g, hold frame t=%.0fms = p %.3f)"
          % (path, duration, hold_frame, hold_frame / duration))
    return 0


if __name__ == "__main__":
    sys.exit(main())
