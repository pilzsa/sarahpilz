#!/usr/bin/env python3
"""Sanity-check the shared stylesheet against the pages that use it.

1. braces balance -- one missing } silently drops every rule after it
2. every var(--token) used has a declaration (:root or scoped to a component)
3. every class used by any page has a rule in styles.css

Usage (from anywhere):  python3 tools/check_css.py
Exit code 0 = the stylesheet is complete, 1 = something is missing.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLESHEET = os.path.join(ROOT, "styles.css")

# Every page that ships: the home page, the three area pages, the gallery feed,
# and one page per visualisation (viz-*.html), discovered so the coverage check
# follows the feed automatically.
PAGES = ("index.html", "about.html", "publications.html", "contact.html", "gallery.html")
PAGES += tuple(sorted(
    os.path.basename(path) for path in glob.glob(os.path.join(ROOT, "viz-*.html"))
))

fails = []


def check(name, ok, detail=""):
    if not ok:
        fails.append(name)
    print(("PASS  " if ok else "FAIL  ") + name + ((" :: " + str(detail)) if detail else ""))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


css = read(STYLESHEET)
code = re.sub(r"/\*.*?\*/", "", css, flags=re.S)  # comments can contain braces/colons

print("== structure ==")
check("braces balance", code.count("{") == code.count("}"),
      "%d open / %d close" % (code.count("{"), code.count("}")))
check("stylesheet is not empty", len(code.strip()) > 500, "%d bytes" % len(css))

root_block = re.search(r":root\s*\{(.*?)\}", code, re.S)
check(":root token block present", root_block is not None)

print()
print("== custom properties ==")
# A property may be declared in :root or scoped to a component -- the contact
# chips set --accent per position -- so declarations anywhere count.
declared = set(re.findall(r"--([a-z0-9-]+)\s*:", code))
root_block = re.search(r":root\s*\{(.*?)\}", code, re.S)
root_declared = set(re.findall(r"--([a-z0-9-]+)\s*:", root_block.group(1))) if root_block else set()
used = set(re.findall(r"var\(\s*--([a-z0-9-]+)", code))
undefined = sorted(used - declared)
unused = sorted(declared - used)
check("every var() has a declaration", not undefined, undefined)
print(
    "      declared: %d (%d in :root), used: %d, unused: %s"
    % (len(declared), len(root_declared), len(used), unused or "none")
)

print()
print("== class coverage ==")
selectors = set(re.findall(r"\.([A-Za-z][\w-]*)", code))
page_classes = set()
for page in PAGES:
    for attr in re.findall(r'class="([^"]+)"', read(os.path.join(ROOT, page))):
        page_classes.update(attr.split())
missing = sorted(c for c in page_classes if c not in selectors)
check("every class used in the HTML has a rule", not missing, missing)
print("      pages: %d, in HTML: %d styled classes, in CSS: %d selectors"
      % (len(PAGES), len(page_classes), len(selectors)))

print()
print("== reference styles (kept, not applied) ==")
# The marker highlight was replaced by the paint brush and is kept in section 19
# for reference. Both halves matter: the block must survive, and no page may use
# the class -- a heading wearing a tint and a stroke at once would be a mistake
# nobody would notice in a screenshot.
marker = re.search(r"\.highlight\s*\{.*?\}\s*\.highlight::before\s*\{.*?\}", code, re.S)
check("the marker highlight is kept in styles.css", marker is not None)
check("the marker highlight is not applied to any page", "highlight" not in page_classes)

print()
print("== light and dark themes ==")
# The dark palette is written twice -- once for the stored choice
# ([data-theme="dark"] on <html>) and once for the media query that a visitor
# with no choice inherits -- so the two must hold the same values or the page
# would change look depending on how it got there. No screenshot of a served
# page can tell them apart (theme.js settles the attribute before the paint, so
# this media query never decides one on its own), which is exactly why comparing
# them is the only way to keep the copy honest.
def declarations(block):
    return dict((name, " ".join(value.split()))
                for name, value in re.findall(r"--([a-z0-9-]+)\s*:\s*([^;}]+)", block))

dark_blocks = re.findall(
    r'\[data-theme="dark"\]\s*\{(.*?)\}|:root:not\(\[data-theme="light"\]\)\s*\{(.*?)\}',
    code, re.S,
)
dark_blocks = [a or b for a, b in dark_blocks]
stored_dark = declarations(dark_blocks[0]) if len(dark_blocks) == 2 else {}
media_dark = declarations(dark_blocks[1]) if len(dark_blocks) == 2 else {}
light = declarations(re.search(r":root\s*\{(.*?)\}", code, re.S).group(1))

check("both routes to the dark theme are declared", len(dark_blocks) == 2, len(dark_blocks))
check("the two dark themes carry the same values",
      bool(stored_dark) and stored_dark == media_dark,
      sorted(set(stored_dark.items()) ^ set(media_dark.items())))
check("every dark token has a light default",
      not [name for name in stored_dark if name not in light],
      [name for name in stored_dark if name not in light])
check("every dark token changes something",
      not [name for name in stored_dark if light.get(name) == stored_dark[name]],
      [name for name in stored_dark if light.get(name) == stored_dark[name]])
print("      the dark theme swaps: %s" % ", ".join("--" + name for name in sorted(stored_dark)))

print()
if fails:
    print("check_css: %d problem(s)" % len(fails))
    sys.exit(1)
print("check_css: styles.css is complete")
