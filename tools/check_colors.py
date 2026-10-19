#!/usr/bin/env python3
"""Keep the four accent colours identical across the three files that use them.

The palette is declared in three places, because CSS, the D3 beams and the
animated header mark each need the raw value:

    styles.css  :root           --yellow --lime --orange --blue
    hero.js     BEAMS[].color   the D3 beam gradients
    logo.js     COLORS[]        the four dots and the square's sides

Editing one and forgetting the others is the easiest way to make the site look
inconsistent, so this script fails loudly instead.

Note: the CSS --orange is #ffa310ed (it carries alpha for the arrow rule) while
the JavaScript uses the opaque #ffa310, so only the first six hex digits are
compared.

Usage (from anywhere):  python3 tools/check_colors.py
Exit code 0 = in sync, 1 = drift found.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Order matters: it is the same order used by logo.js COLORS[] and by the
# row order documented in styles.css.
TOKENS = ["yellow", "lime", "orange", "blue"]

# CSS token -> hero.js beam key (they currently match, kept explicit for clarity).
BEAM_KEY = {"yellow": "yellow", "lime": "lime", "orange": "orange", "blue": "blue"}

# The four accents are also the site's map of itself: every area owns one, and a
# page or a section declares which area it is with data-area="...". These eight
# values are what the site currently uses -- the four areas of the home page,
# each with the page that fronts it -- so a new area cannot appear without a
# colour and the map cannot drift from the pages.
AREAS = {
    "research": "lime",
    "publications": "lime",
    "data": "blue",
    "gallery": "blue",
    "coordination": "orange",
    "about": "orange",
    "visualization": "yellow",
    "contact": "yellow",
}


def css_areas():
    """data-area -> accent token, as declared in styles.css."""
    text = re.sub(r"/\*.*?\*/", "", read("styles.css"), flags=re.S)
    found = {}
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
        accent = re.search(r"--area-accent:\s*var\(--([a-z]+)\)", body)
        if not accent:
            continue
        for area in re.findall(r'\[data-area="([a-z-]+)"\]', selector):
            found[area] = accent.group(1)
    return found


def html_areas():
    """The data-area values the pages actually declare."""
    found = set()
    for path in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        with open(path, encoding="utf-8") as f:
            found |= set(re.findall(r'data-area="([a-z-]+)"', f.read()))
    return found


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


def normalise(value):
    """#RRGGBB or #RRGGBBAA (or short form) -> lowercase #rrggbb."""

    return value.lower()[:7]


def css_palette():
    text = read("styles.css")
    root = re.search(r":root\s*\{(.*?)\}", text, re.S)
    if not root:
        return {}
    found = {}
    for name, value in re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{3,8})", root.group(1)):
        found[name] = normalise(value)
    return found


def hero_palette():
    text = read("hero.js")
    found = {}
    for key, value in re.findall(r'\{\s*key:\s*"(\w+)",\s*color:\s*"(#[0-9a-fA-F]{3,8})"', text):
        found[key] = normalise(value)
    return found


def logo_palette():
    text = read("logo.js")
    block = re.search(r"COLORS\s*=\s*\[(.*?)\]", text, re.S)
    if not block:
        return {}
    values = re.findall(r"#[0-9a-fA-F]{3,8}", block.group(1))
    return dict(zip(TOKENS, (normalise(v) for v in values)))


def main():
    css = css_palette()
    hero = hero_palette()
    logo = logo_palette()

    print("%-8s %-9s %-9s %-9s %s" % ("token", "styles.css", "hero.js", "logo.js", "status"))
    print("-" * 52)

    failures = []
    for token in TOKENS:
        values = {
            "styles.css": css.get(token),
            "hero.js": hero.get(BEAM_KEY[token]),
            "logo.js": logo.get(token),
        }
        missing = [src for src, value in values.items() if not value]
        agree = len(set(v for v in values.values() if v)) <= 1
        ok = not missing and agree
        if not ok:
            failures.append((token, values, missing))
        print(
            "%-8s %-9s %-9s %-9s %s"
            % (
                "--" + token,
                values["styles.css"] or "MISSING",
                values["hero.js"] or "MISSING",
                values["logo.js"] or "MISSING",
                "ok" if ok else "DRIFT",
            )
        )

    print()
    if failures:
        print("check_colors: %d token(s) out of sync" % len(failures))
        for token, values, missing in failures:
            print("  --%s: %s" % (token, values))
            if missing:
                print("    not declared in: %s" % ", ".join(missing))
        return 1

    # The area map: every area a page or section declares must resolve to one of
    # the four accents, and none of the eight may go unused.
    declared = css_areas()
    used = html_areas()
    print()
    print("== area colours (styles.css: data-area -> accent) ==")
    for area in sorted(AREAS):
        token = AREAS[area]
        print("  %s  %-13s --%s" % ("ok   " if declared.get(area) == token else "DRIFT",
                                    area, declared.get(area, "MISSING")))
    unknown = sorted(used - set(AREAS))
    missing = sorted(set(AREAS) - used)
    print("  %s  every data-area in the HTML has a colour%s"
          % ("ok   " if not unknown else "DRIFT",
             "" if not unknown else ": " + ", ".join(unknown)))
    print("  %s  every mapped area is used by a page%s"
          % ("ok   " if not missing else "DRIFT",
             "" if not missing else ": " + ", ".join(missing)))
    if declared != AREAS or unknown or missing:
        print()
        print("check_colors: the area colour map is incomplete")
        return 1

    # The four accents also ride the contact chips, one per position. Keeping the
    # cycle in logo order is what makes the row read as "the logo colours".
    cycle = re.findall(
        r"li:nth-child\(4n \+ (\d)\)\s*\{\s*--accent:\s*var\(--([a-z]+)\)",
        read("styles.css"),
    )
    expected = list(zip("1234", TOKENS))
    have = dict(cycle)
    print()
    print("== contact chip accents (styles.css) ==")
    for position, token in expected:
        ok = have.get(position) == token
        print(
            "  %s  4n+%s -> --%-7s%s"
            % ("ok   " if ok else "DRIFT", position, token,
               "" if ok else " is " + str(have.get(position)))
        )
    hover = re.search(r"\.contact-link:hover[^{]*\{([^}]*)\}", read("styles.css"), re.S)
    uses_accent = bool(hover) and "var(--accent)" in hover.group(1)
    print("  %s  hover fill uses the cycle (var(--accent))" % ("ok   " if uses_accent else "DRIFT"))
    if cycle != expected or not uses_accent:
        print()
        print("check_colors: the contact chip accent cycle is incomplete")
        return 1

    # The four accents are the site's map of itself, so they are the one thing
    # the dark theme may not restyle: [data-theme="dark"] swaps the neutrals and
    # the theme mechanics, never one of the four. (check_css.py compares the two
    # dark token blocks with each other; this keeps them off the palette.)
    dark = re.findall(
        r'(?:\[data-theme="dark"\]|:root:not\(\[data-theme="light"\]\))\s*\{(.*?)\}',
        read("styles.css"),
        re.S,
    )
    restyled = sorted(
        {name for block in dark for name in re.findall(r"--([a-z-]+)\s*:", block)} & set(TOKENS)
    )
    print()
    print("== the dark theme keeps the accent map ==")
    for token in TOKENS:
        print(
            "  %s  --%-7s %s"
            % ("ok   " if token not in restyled else "DRIFT", token,
               "read on the dark page as it is" if token not in restyled
               else "must not be redeclared in the dark theme")
        )
    if restyled:
        print()
        print("check_colors: the dark theme must not restyle the accents")
        return 1

    print("check_colors: all four accents agree across styles.css, hero.js and logo.js")
    return 0


if __name__ == "__main__":
    sys.exit(main())
