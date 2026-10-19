#!/usr/bin/env python3
"""Regenerate the --brush-stroke token in styles.css.

The paint-brush highlight behind the four section headings on index.html is a
masked SVG, so its whole shape lives in one CSS custom property. Hand-editing a
data URI that long is hopeless, so the geometry is generated here instead:

  * a solid sweep -- thick where the brush lands, thinning to a pointed tip
  * bristle streaks, knocked out of the same path with fill-rule='evenodd', so
    the paint looks dragged rather than printed (the same path works as a CSS
    mask, where only alpha counts -- separate light-coloured holes would not)
  * a faint second pass under the tail: paint that did not fully take

Writes styles.css in place and prints the size change. Run it only when the
stroke itself should change; the committed token is the source of truth for the
page, exactly like images/sarah-pilz.jpg is for the portrait.

Usage (from anywhere):  python3 tools/make_brush.py
Exit code 0 = styles.css updated, 1 = the token could not be found.
"""
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLESHEET = os.path.join(ROOT, "styles.css")

WIDTH, HEIGHT = 300.0, 72.0        # the canvas the mask is stretched over

# Shape. The brush lands at x~4 fat, peaks around a third of the way along and
# thins to a point at the far right, where the bristles are nearly empty.
THIN_END = 2.0                     # half-thickness at the lifting tip
FAT = 16.0                         # extra half-thickness at the belly
BODY_SAMPLES = 7
HOLE_SAMPLES = 5
HOLES = [                          # x0, x1, offset across the belly, thickness
    (46.0, 252.0, -0.40, 1.9),
    (58.0, 238.0, 0.16, 1.7),
    (126.0, 216.0, 0.52, 1.6),
]
TAIL = (150.0, 292.0, 0.52, 5.5)   # the faint second pass, under the tail
TAIL_OPACITY = 0.34


def profile(x):
    """Centre line and half-thickness of the sweep at x."""
    t = x / WIDTH
    half = THIN_END + FAT * math.sin(math.pi * (0.2 + 0.8 * t)) ** 1.6
    centre = 38.0 - 5.0 * t + 1.8 * math.sin(t * 4.7)
    return centre, half


def catmull(points, move=True):
    """A smooth curve through points, as cubic segments.

    The second edge of a closed shape must open with an explicit L: a dangling
    coordinate pair after a C command is read as another (incomplete) cubic and
    silently swallows the rest of the path.
    """
    padded = [points[0]] + list(points) + [points[-1]]
    out = ["%s %.1f %.1f" % ("M" if move else "L", points[0][0], points[0][1])]
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6.0, p1[1] + (p2[1] - p0[1]) / 6.0)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6.0, p2[1] - (p3[1] - p1[1]) / 6.0)
        out.append("C %.1f %.1f %.1f %.1f %.1f %.1f" % (c1 + c2 + p2))
    return " ".join(out)


def body():
    """One solid sweep: a ragged landing, a fat belly, a thinning ragged tip."""
    top, bottom = [], []
    for i in range(BODY_SAMPLES):
        x = 4.0 + (294.0 - 4.0) * i / (BODY_SAMPLES - 1)
        centre, half = profile(x)
        top.append((x, centre - half + 1.6 * math.sin(x / 47.0)))
        bottom.append((x, centre + half + 1.4 * math.cos(x / 39.0)))
    top[0] = (7.0, top[0][1] + 3.0)          # lands at an angle
    bottom[0] = (1.5, bottom[0][1] - 1.0)
    top[-1] = (297.0, top[-1][1] - 1.0)      # lifts off higher than it landed
    bottom[-1] = (286.0, bottom[-1][1] + 2.5)
    return catmull(top) + " " + catmull(list(reversed(bottom)), move=False) + " Z"


def ribbon(x0, x1, offset, thickness, wobble=0.4):
    """A closed band of paint, offset across the belly of the sweep.

    wobble must stay under thickness/2, or the long edges cross and the band
    becomes a self-intersecting knot instead of a hole.
    """
    top, bottom = [], []
    for i in range(HOLE_SAMPLES):
        x = x0 + (x1 - x0) * i / (HOLE_SAMPLES - 1)
        centre, half = profile(x)
        y = centre + offset * half
        top.append((x, y - thickness / 2 + wobble * math.sin(x / 44.0 + offset * 7)))
        bottom.append((x, y + thickness / 2 + wobble * math.cos(x / 37.0 + offset * 3)))
    return catmull(top) + " " + catmull(list(reversed(bottom)), move=False) + " Z"


def svg():
    paint = " ".join([body()] + [ribbon(*hole) for hole in HOLES])
    parts = [
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 72'"
        " preserveAspectRatio='none'><g fill='white'>",
        "<path fill-opacity='%.2f' d='%s'/>" % (TAIL_OPACITY, ribbon(*TAIL)),
        "<path fill-rule='evenodd' d='%s'/>" % paint,
        "</g></svg>",
    ]
    return " ".join("".join(parts).split())


def token():
    """The declaration as it appears in styles.css, ready to paste in."""
    uri = "data:image/svg+xml," + svg().replace("<", "%3C").replace(">", "%3E")
    return '--brush-stroke: url("%s");' % uri


def main():
    with open(STYLESHEET, encoding="utf-8") as f:
        css = f.read()

    pattern = re.compile(r"--brush-stroke:\s*url\(.*?\);", re.S)
    matches = pattern.findall(css)
    if len(matches) != 1:
        print("make_brush: found %d --brush-stroke declarations, expected 1" % len(matches))
        return 1

    new = token()
    updated = pattern.sub(lambda _: new, css, count=1)
    with open(STYLESHEET, "w", encoding="utf-8") as f:
        f.write(updated)

    print("make_brush: --brush-stroke %d -> %d bytes" % (len(matches[0]), len(new)))
    print("make_brush: styles.css updated (%d bytes)" % len(updated))
    return 0


if __name__ == "__main__":
    sys.exit(main())
