#!/usr/bin/env python3
"""Regenerate the gallery placeholder art in images/gallery/.

Two pieces, two sizes each -- a square tile (900x900) for the feed and a wide
image (1600x1000) for the piece page -- so the gallery can ship without real
screenshots and still with no build step in the site itself.

The art is deliberately neutral: ink, greys and the gallery's own blue. The
gallery holds visualisations only, so nothing in it points at one of the other
three areas, and tools/analyze.py asserts that no lime, orange or yellow pixel
appears on the page.

Deterministic: every coordinate is a fixed formula, never a random number, so
re-running the script rewrites byte-identical files.

Usage (from anywhere):  python3 tools/make_gallery.py
Needs:  Pillow (python3 -m pip install Pillow)
Exit code 0 = images written, 1 = Pillow missing.
"""
import math
import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("make_gallery: Pillow is required (python3 -m pip install Pillow)")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "images", "gallery")

BACKGROUND = (255, 255, 255)
INK = (32, 33, 36)              # --text
MUTED = (102, 107, 115)         # --muted
LINE = (231, 233, 237)          # --line
ACCENT = (185, 255, 231)        # --blue, the gallery's own accent
ACCENT_INK = (96, 150, 133)     # the accent readable as a line on white

TILE = (900, 900)
WIDE = (1600, 1000)


def frame(size):
    """A white sheet with a hairline border, like the framed hero."""
    image = Image.new("RGB", size, BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, size[0] - 1, size[1] - 1], outline=LINE)
    return image, draw


def plot(draw, size, series, fill=False):
    """Draw a grid plus one series, in a margin that scales with the sheet."""
    width, height = size
    margin = min(width, height) * 0.12
    left, right = margin, width - margin
    top, bottom = margin, height - margin

    for step in range(1, 5):                     # horizontal rules
        y = top + (bottom - top) * step / 5
        draw.line([(left, y), (right, y)], fill=LINE, width=2)
    draw.line([(left, bottom), (right, bottom)], fill=MUTED, width=3)
    draw.line([(left, top), (left, bottom)], fill=MUTED, width=3)

    points = [
        (left + (right - left) * i / (len(series) - 1), bottom - (bottom - top) * value)
        for i, value in enumerate(series)
    ]
    if fill:
        draw.polygon([(points[0][0], bottom)] + points + [(points[-1][0], bottom)], fill=ACCENT)
    draw.line(points, fill=ACCENT_INK, width=max(3, int(min(width, height) * 0.006)), joint="curve")
    radius = max(4, int(min(width, height) * 0.012))
    for x, y in points:
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=INK)


def network(draw, size):
    """A lobby network: a few hubs, spokes and cross-links."""
    width, height = size
    centre = (width / 2, height / 2)
    radius = min(width, height) * 0.33
    radius_inner = radius * 0.55

    nodes = []
    for i in range(14):
        angle = i * 2.39996322972865332     # golden angle: even, never random
        r = radius_inner if i % 3 else radius
        nodes.append((centre[0] + r * math.cos(angle), centre[1] + r * math.sin(angle)))
    nodes.append(centre)

    hub = len(nodes) - 1
    for i, node in enumerate(nodes[:-1]):
        draw.line([node, nodes[(i + 3) % (len(nodes) - 1)]], fill=LINE, width=3)
        draw.line([node, nodes[hub]], fill=LINE, width=2)

    outer = max(8, int(min(width, height) * 0.018))
    inner = max(4, int(min(width, height) * 0.010))
    for i, (x, y) in enumerate(nodes):
        r = outer if i in (hub, 1, 4, 9) else inner
        draw.ellipse([x - r, y - r, x + r, y + r], fill=ACCENT, outline=INK, width=3)


def write(name, size, paint):
    image, draw = frame(size)
    paint(draw, size)
    path = os.path.join(DEST, name)
    image.save(path, "PNG", optimize=True)
    print("make_gallery: %s %dx%d" % (os.path.relpath(path, ROOT), size[0], size[1]))


def main():
    os.makedirs(DEST, exist_ok=True)

    # A gently declining curve: measured need against capacity over 12 periods,
    # enough shape to read as a chart in a tile and on a piece page.
    series = [0.86, 0.72, 0.79, 0.58, 0.63, 0.47, 0.52, 0.38, 0.42, 0.31, 0.36, 0.24]

    write("uk-ventilator-challenge.png", TILE, lambda d, s: plot(d, s, series, fill=True))
    write("uk-ventilator-challenge-wide.png", WIDE, lambda d, s: plot(d, s, series, fill=True))
    write("big-tech-lobby-writes-eu-ai-act.png", TILE, network)
    write("big-tech-lobby-writes-eu-ai-act-wide.png", WIDE, network)
    return 0


if __name__ == "__main__":
    sys.exit(main())
