#!/usr/bin/env python3
"""Peek inside the built files without opening a browser.

  python3 tools/extract.py styles.css        selectors and at-rules, in order
  python3 tools/extract.py index.html        the inline <style>/<script> blocks
  python3 tools/extract.py index.html --tags every element tag with its line number

The selector listing is what was used to confirm that no CSS rule was lost when
the two pages' inline <style> blocks were merged into styles.css: run it on the
old inline CSS and on the new stylesheet and compare.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve(target):
    if os.path.isabs(target) and os.path.exists(target):
        return target
    return os.path.join(ROOT, target)


def selectors(path):
    with open(path, encoding="utf-8") as f:
        css = re.sub(r"/\*.*?\*/", "", f.read(), flags=re.S)
    print("== selectors in %s ==" % os.path.basename(path))
    count = 0
    for match in re.finditer(r"([^{}]+)\{", css):
        selector = " ".join(match.group(1).split())
        if not selector:
            continue
        count += 1
        print("%3d  %s" % (count, selector))
    print("-- %d rule(s)" % count)


def inline_blocks(path):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    print("== inline blocks in %s ==" % os.path.basename(path))
    for kind in ("style", "script"):
        for match in re.finditer(r"<%(k)s\b([^>]*)>(.*?)</%(k)s>" % {"k": kind}, html, re.S):
            attrs = match.group(1).strip()
            body = match.group(2)
            line = html[: match.start()].count("\n") + 1
            print("  <%s%s> at line %d, %d chars, %d lines"
                  % (kind, (" " + attrs) if attrs else "", line, len(body), body.count("\n")))
    print()


def tags(path):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    print("== tags in %s ==" % os.path.basename(path))
    counts = {}
    for match in re.finditer(r"<([a-zA-Z][\w-]*)", html):
        tag = match.group(1).lower()
        counts[tag] = counts.get(tag, 0) + 1
        print("%5d  <%s>" % (html[: match.start()].count("\n") + 1, tag))
    print("-- %s" % ", ".join("%s=%d" % item for item in sorted(counts.items())))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    target = sys.argv[1]
    path = resolve(target)
    if not os.path.exists(path):
        print("extract: no such file: %s" % path)
        return 1
    if target.endswith(".css"):
        selectors(path)
    elif "--tags" in sys.argv:
        tags(path)
    else:
        inline_blocks(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
