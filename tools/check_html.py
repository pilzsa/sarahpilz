#!/usr/bin/env python3
"""Strict tag-balance check for the site's HTML files.

Browsers silently forgive an unclosed <div>, which is how a small edit turns
into a broken layout that only shows up in a screenshot. This walks every
*.html page with html.parser and reports tags that never close or that close in
the wrong order.

Usage (from anywhere):  python3 tools/check_html.py
Exit code 0 = all pages balanced, 1 = at least one problem.
"""
import glob
import html.parser
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Elements that never take a closing tag: HTML void elements plus the SVG shape
# elements that our pages emit self-closed (logo.js, hero.js).
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr",
    "circle", "line", "rect", "stop", "path", "polygon", "polyline", "ellipse", "use",
}


class Balance(html.parser.HTMLParser):
    def __init__(self, name):
        super().__init__(convert_charrefs=True)
        self.name = name
        self.stack = []          # [(tag, line), ...]
        self.errors = []
        self.tags = 0

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        self.tags += 1
        self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append("%s:%d stray </%s>" % (self.name, self.getpos()[0], tag))
            return
        opened, line = self.stack.pop()
        if opened != tag:
            self.errors.append(
                "%s:%d </%s> closes <%s> opened on line %d"
                % (self.name, self.getpos()[0], tag, opened, line)
            )


def main():
    pages = sorted(glob.glob(os.path.join(ROOT, "*.html")))
    if not pages:
        print("no HTML files found in %s" % ROOT)
        return 1

    bad = 0
    for path in pages:
        rel = os.path.relpath(path, ROOT)
        parser = Balance(rel)
        with open(path, encoding="utf-8") as f:
            parser.feed(f.read())
        for tag, line in parser.stack:
            parser.errors.append("%s unclosed <%s> opened on line %d" % (rel, tag, line))
        if parser.errors:
            bad += 1
            print("FAIL  %s" % rel)
            for error in parser.errors:
                print("      %s" % error)
        else:
            print("PASS  %s (%d elements balanced)" % (rel, parser.tags))

    print()
    print("check_html: %d/%d pages balanced" % (len(pages) - bad, len(pages)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
