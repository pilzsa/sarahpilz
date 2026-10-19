#!/usr/bin/env python3
"""Pixel-level check of the captured screenshots.

Each pixel is classified by nearest accent colour, with a guard so anti-aliased
white background cannot be mistaken for a pale accent (a weak match to an
accent that is still closer to white is ignored). The bounding box of each
accent is printed in CSS pixels, which is what makes the numbers meaningful:

  hold_logo.png         the mark should show all four accents, each occupying one
                        side of the square
  v_*_desktop.png       the header crop of every page should contain all four
                        accents in the logo slot
  v_gallery_desktop     below the header, the gallery may show its own blue and
                        nothing from the other three areas: it holds
                        visualisations only and differentiates nothing inside
                        itself, so no lime, orange or yellow may appear
  v_about_desktop       the portrait beside the "About" heading must be round:
                        the box of everything that is not page white has white
                        corners, which is only true of a circle
  v_publications_desktop  the feed must show real preview pictures, so the
                        region below the header must hold the thousands of
                        distinct colours a photograph brings and the page's own
                        type and hairlines cannot

The dark theme is captured with ?theme=dark (see tools/smoke.sh) and is held to
the same rules -- the four accents, the gallery's own blue and nothing else, the
preview pictures -- plus two of its own: the page must really be painted dark,
and the paint behind the section headings must be a wash rather than the solid
accent band it is on white, which would swallow the near-white heading on top of
it. That painted heading is measured in both themes, side by side.

Usage:  python3 tools/analyze.py
Needs:  Pillow, and screenshots from tools/smoke.sh + tools/hold.sh
"""
import os
import sys

try:
    from PIL import Image
except ImportError:
    print("analyze: Pillow is required (python3 -m pip install Pillow)")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", ".out")

COLORS = {
    "yellow": (242, 255, 0),
    "lime": (194, 243, 69),
    "orange": (255, 163, 16),
    "blue": (185, 255, 231),
}
BACKGROUND = (255, 255, 255)      # the light page, and the ink guard's white
BACKGROUND_DARK = (15, 17, 19)    # styles.css, [data-theme="dark"] --background

# A pixel counts as ink when it is this far from white. The hairline --line
# (#e7e9ed) sits at 1384, so it reads as background -- which is what the
# circle test below needs, since the portrait's own border is that hairline.
INK_DISTANCE = 1600

# The header crop of every page: the mark's four dots sit here, so this is where
# the accents are counted -- in either theme.
HEADER = (100, 0, 320, 110)

# file, device scale factor, crop (left, top, right, bottom) or None
TARGETS = [
    ("hold_logo.png", 8, None),
    ("v_index_desktop.png", 1, HEADER),
    ("v_about_desktop.png", 1, HEADER),
    ("v_publications_desktop.png", 1, HEADER),
    ("v_gallery_desktop.png", 1, HEADER),
]

# Every screenshot whose header crop must show all four accents.
FOUR_ACCENTS = ("hold_logo.png", "v_index_desktop.png", "v_about_desktop.png",
                "v_publications_desktop.png", "v_gallery_desktop.png")

# The gallery below its header: the gallery's own blue is allowed, the other
# three areas' colours are not. See the module docstring.
GALLERY = ("v_gallery_desktop.png", (0, 200, 1440, 1500))
GALLERY_FORBIDDEN = ("lime", "orange", "yellow")

# The same two pages in the dark theme, re-run below their headers so a dark
# background cannot stand in for a missing picture or an extra colour.
DARK_GALLERY = ("v_gallery_dark_desktop.png", (0, 200, 1440, 1500))
DARK_PUBLICATIONS = ("v_publications_dark_desktop.png", (0, 380, 1440, 1600))

# Every dark screenshot whose header crop must still show all four accents: the
# mark's dots and the nav's link lines carry the accent map into the dark page,
# where the paint behind the headings is only a wash.
DARK_FOUR_ACCENTS = ("v_index_dark_desktop.png", "v_about_dark_desktop.png",
                     "v_publications_dark_desktop.png", "v_gallery_dark_desktop.png")

# The corner of the header -- page background above its hairline, nothing else --
# of the same page in both themes: enough to say which palette was painted.
CORNER = (0, 0, 60, 60)
CORNER_OFF = 60            # how close a pixel must sit to the page's own colour
THEMES = ("v_index_desktop.png", "v_index_dark_desktop.png")

# The brush behind the first section heading on the home page, and the ink that
# heading is drawn in per theme (--text). On white the paint is a solid band of
# the area's accent; on the dark page it must be a wash, or the near-white
# heading on top of it would be unreadable -- see --paint-blend and
# --paint-strength in styles.css.
PAINT = ("v_index_desktop.png", "v_index_dark_desktop.png", (150, 760, 285, 806))
PAINT_ACCENT = "lime"      # the Research section's own colour
HEADING_INK = {"v_index_desktop.png": (32, 33, 36), "v_index_dark_desktop.png": (242, 243, 245)}
SOLID_DISTANCE = 2000      # a pixel this close to a colour counts as that colour
PAINT_VISIBLE = 2000       # distance the crop's average must sit from the page

# about.html, the top right of the intro, where the round portrait sits.
PORTRAIT = ("v_about_desktop.png", (1000, 110, 1340, 400))
PORTRAIT_MIN_SIZE = 100          # px the picture must be across, in CSS pixels

# publications.html below the header: the feed with its four preview pictures.
PUBLICATIONS = ("v_publications_desktop.png", (0, 380, 1440, 1600))
PUBLICATIONS_MIN_COLOURS = 4000  # a photograph brings far more than type does


def distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def is_ink(pixel):
    """True when a pixel is clearly not the white page."""
    return distance(pixel, BACKGROUND) > INK_DISTANCE


def analyse(path, scale, region=None, max_distance=3000):
    image = Image.open(path).convert("RGB")
    if region:
        image = image.crop(region)
    width, height = image.size
    pixels = image.load()

    boxes = {}
    counts = {name: 0 for name in COLORS}
    for y in range(height):
        for x in range(width):
            colour = pixels[x, y]
            to_background = distance(colour, BACKGROUND)
            best, best_distance = None, None
            for name, accent in COLORS.items():
                d = distance(colour, accent)
                if best_distance is None or d < best_distance:
                    best, best_distance = name, d
            if best_distance < max_distance and best_distance < to_background / 4:
                counts[best] += 1
                box = boxes.setdefault(best, [x, y, x, y])
                box[0] = min(box[0], x)
                box[1] = min(box[1], y)
                box[2] = max(box[2], x)
                box[3] = max(box[3], y)

    print("== %s size=%s scale=%s region=%s" % (path, image.size, scale, region))
    for name in COLORS:
        if name in boxes:
            x0, y0, x1, y1 = boxes[name]
            print("   %-6s px=%6d  css bbox x:%.1f-%.1f y:%.1f-%.1f"
                  % (name, counts[name], x0 / scale, x1 / scale, y0 / scale, y1 / scale))
        else:
            print("   %-6s not drawn" % name)
    print()
    return {name: counts[name] for name in COLORS}


def portrait_is_round(path, region):
    """Measure the picture in a crop and say whether its box corners are page white.

    A rectangular picture fills its box, corners included; a circular one does
    not, so white corners are the proof that the clip is doing its job.
    """
    image = Image.open(path).convert("RGB").crop(region)
    width, height = image.size
    pixels = image.load()

    box = None
    for y in range(height):
        for x in range(width):
            if not is_ink(pixels[x, y]):
                continue
            box = (x, y, x, y) if box is None else (
                min(box[0], x), min(box[1], y), max(box[2], x), max(box[3], y))

    print("== %s portrait region=%s" % (path, region))
    if box is None:
        print("   no portrait: the whole crop is page white")
        print()
        return None

    x0, y0, x1, y1 = box
    corners = (pixels[x0, y0], pixels[x1, y0], pixels[x0, y1], pixels[x1, y1])
    inked = [corner for corner in corners if is_ink(corner)]
    print("   box %dx%d at x:%d y:%d, corners on the page: %d/4"
          % (x1 - x0 + 1, y1 - y0 + 1, x0 + region[0], y0 + region[1], 4 - len(inked)))
    print()
    return {"size": (x1 - x0 + 1, y1 - y0 + 1), "inked_corners": len(inked)}


def colour_count(path, region):
    """How many different colours a region holds: photographs bring thousands, type does not."""
    image = Image.open(path).convert("RGB").crop(region)
    colours = image.getcolors(1 << 20)  # None once the picture is more varied than that
    count = len(colours) if colours else 1 << 20
    print("== %s feed region=%s" % (path, region))
    print("   distinct colours: %d" % count)
    print()
    return count


def page_colour(path, region, colour):
    """How much of a crop is the page's own colour: the theme, read off a corner."""
    image = Image.open(path).convert("RGB").crop(region)
    pixels = image.load()
    area = image.size[0] * image.size[1]
    hits = sum(1 for y in range(image.size[1]) for x in range(image.size[0])
               if distance(pixels[x, y], colour) < CORNER_OFF)
    print("== %s corner region=%s" % (path, region))
    print("   %s: %d/%d px (%.1f%%)" % (colour, hits, area, 100.0 * hits / area))
    print()
    return hits / float(area)


def paint(path, region, accent, ink):
    """Measure a painted heading: how solid its paint is and whether the ink it
    is written in is still on top of it. A solid band of accent behind --text
    that is nearly white is what the dark theme has to avoid."""
    image = Image.open(path).convert("RGB").crop(region)
    pixels = image.load()
    area = image.size[0] * image.size[1]
    total = [0, 0, 0]
    solid = inked = 0
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            colour = pixels[x, y]
            total = [t + v for t, v in zip(total, colour)]
            if distance(colour, accent) < SOLID_DISTANCE:
                solid += 1
            if distance(colour, ink) < SOLID_DISTANCE:
                inked += 1
    mean = tuple(int(round(t / float(area))) for t in total)
    print("== %s painted heading region=%s" % (path, region))
    print("   solid accent px=%d  heading ink px=%d  mean=%s" % (solid, inked, mean))
    print()
    return {"solid": solid, "ink": inked, "mean": mean}


def main():
    missing = [name for name, _, _ in TARGETS if not os.path.exists(os.path.join(OUT, name))]
    if missing:
        print("analyze: missing %s -- run tools/smoke.sh and tools/hold.sh first" % ", ".join(missing))
        return 1

    results = {}
    for name, scale, region in TARGETS:
        results[name] = analyse(os.path.join(OUT, name), scale, region)

    failures = []
    for name in FOUR_ACCENTS:
        absent = [c for c, n in results[name].items() if not n]
        if absent:
            failures.append("%s: no %s pixels found" % (name, ", ".join(absent)))

    # The gallery is one area: below the header it may only show its own blue.
    gallery_path = os.path.join(OUT, GALLERY[0])
    if os.path.exists(gallery_path):
        counts = analyse(gallery_path, 1, GALLERY[1])
        stray = [name for name in GALLERY_FORBIDDEN if counts[name]]
        if stray:
            failures.append("%s: the gallery shows %s pixels" % (GALLERY[0], ", ".join(stray)))
        if not counts["blue"]:
            failures.append("%s: the gallery shows none of its own blue" % GALLERY[0])

    # The publications feed must show its preview pictures, not empty frames.
    publications_path = os.path.join(OUT, PUBLICATIONS[0])
    if os.path.exists(publications_path):
        colours = colour_count(publications_path, PUBLICATIONS[1])
        if colours < PUBLICATIONS_MIN_COLOURS:
            failures.append(
                "%s: only %d distinct colours below the header -- the preview pictures"
                " did not load" % (PUBLICATIONS[0], colours)
            )

    # The dark theme: the same rules, and the accents have to survive it.
    for dark_name in DARK_FOUR_ACCENTS:
        dark_path = os.path.join(OUT, dark_name)
        if not os.path.exists(dark_path):
            failures.append("%s: missing -- run tools/smoke.sh" % dark_name)
            continue
        counts = analyse(dark_path, 1, HEADER)
        absent = [name for name, count in counts.items() if not count]
        if absent:
            failures.append("%s: no %s pixels found" % (dark_name, ", ".join(absent)))

    # The gallery is one area in either theme: below the dark header it may only
    # show its own blue, and the dark publications feed must still show pictures.
    dark_gallery_path = os.path.join(OUT, DARK_GALLERY[0])
    if os.path.exists(dark_gallery_path):
        counts = analyse(dark_gallery_path, 1, DARK_GALLERY[1])
        stray = [name for name in GALLERY_FORBIDDEN if counts[name]]
        if stray:
            failures.append("%s: the gallery shows %s pixels"
                            % (DARK_GALLERY[0], ", ".join(stray)))
        if not counts["blue"]:
            failures.append("%s: the gallery shows none of its own blue" % DARK_GALLERY[0])

    dark_publications_path = os.path.join(OUT, DARK_PUBLICATIONS[0])
    if os.path.exists(dark_publications_path):
        colours = colour_count(dark_publications_path, DARK_PUBLICATIONS[1])
        if colours < PUBLICATIONS_MIN_COLOURS:
            failures.append(
                "%s: only %d distinct colours below the header -- the preview"
                " pictures did not load" % (DARK_PUBLICATIONS[0], colours)
            )

    # The theme that was actually painted: the same page, same corner, two
    # palettes. This is what says the dark screenshot is dark.
    if all(os.path.exists(os.path.join(OUT, name)) for name in THEMES):
        light_page = page_colour(os.path.join(OUT, THEMES[0]), CORNER, BACKGROUND)
        dark_page = page_colour(os.path.join(OUT, THEMES[1]), CORNER, BACKGROUND_DARK)
        if light_page < 0.99:
            failures.append("%s: the corner of the header is not page white" % THEMES[0])
        if dark_page < 0.99:
            failures.append("%s: the corner of the header is not the dark page" % THEMES[1])

    # The paint behind the headings, in both themes: a solid band of the area's
    # accent on white, a wash on the dark page, with the heading's own ink on top
    # of it either way.
    if all(os.path.exists(os.path.join(OUT, name)) for name in PAINT[:2]):
        light_paint = paint(os.path.join(OUT, PAINT[0]), PAINT[2],
                            COLORS[PAINT_ACCENT], HEADING_INK[PAINT[0]])
        dark_paint = paint(os.path.join(OUT, PAINT[1]), PAINT[2],
                           COLORS[PAINT_ACCENT], HEADING_INK[PAINT[1]])
        if not light_paint["solid"]:
            failures.append("%s: the brush behind the first heading is not painted" % PAINT[0])
        if not light_paint["ink"]:
            failures.append("%s: the heading is not on the painted band" % PAINT[0])
        if not dark_paint["ink"]:
            failures.append("%s: the heading is not on the dark page's paint" % PAINT[1])
        if dark_paint["solid"]:
            failures.append(
                "%s: %d px of the raw accent in the heading crop -- the dark paint"
                " is a solid band, not the wash that keeps the heading readable"
                % (PAINT[1], dark_paint["solid"])
            )
        for name, measured, page in ((PAINT[0], light_paint, BACKGROUND),
                                     (PAINT[1], dark_paint, BACKGROUND_DARK)):
            if distance(measured["mean"], page) < PAINT_VISIBLE:
                failures.append("%s: no paint visible behind the heading" % name)

    # The About portrait must be round, and big enough to read as a portrait.
    about_path = os.path.join(OUT, PORTRAIT[0])
    if os.path.exists(about_path):
        portrait = portrait_is_round(about_path, PORTRAIT[1])
        if portrait is None:
            failures.append("%s: no portrait beside the heading" % PORTRAIT[0])
        else:
            if min(portrait["size"]) < PORTRAIT_MIN_SIZE:
                failures.append("%s: the portrait is only %dx%d px"
                                % (PORTRAIT[0], portrait["size"][0], portrait["size"][1]))
            if portrait["inked_corners"]:
                failures.append(
                    "%s: the portrait is not a circle -- %d of the corners of its box"
                    " carry ink" % (PORTRAIT[0], portrait["inked_corners"])
                )

    if failures:
        print("analyze: %d problem(s)" % len(failures))
        for failure in failures:
            print("  " + failure)
        return 1

    print("analyze: both themes paint the page and keep the accent map, and the")
    print("         painted heading is a band on white and a wash in the dark")
    print("         with the heading readable on it; every accent is visible in")
    print("         the mark and in every header; the gallery shows no colour but")
    print("         its own; the About portrait is a circle; and the publications")
    print("         feed shows its pictures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
