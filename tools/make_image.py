#!/usr/bin/env python3
"""Regenerate images/sarah-pilz.jpg from the original photo.

The committed image is the source of truth for the site -- run this only when
the original changes. Output is 900 px wide, JPEG quality 82, progressive.

Usage:  python3 tools/make_image.py [source.jpg] [output.jpg]
        defaults to ~/Pictures/profile_pics_2025/Sarah cv -18.jpg
        and images/sarah-pilz.jpg

If the aspect ratio changes, update the width/height attributes on the portrait
<img> in about.html to match (the printed size tells you the new values).
"""
import os
import sys

try:
    from PIL import Image
except ImportError:
    print("make_image: Pillow is required (python3 -m pip install Pillow)")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOURCE = os.path.expanduser("~/Pictures/profile_pics_2025/Sarah cv -18.jpg")
DEFAULT_OUTPUT = os.path.join(ROOT, "images", "sarah-pilz.jpg")
WIDTH = 900


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE
    output = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT

    if not os.path.exists(source):
        print("make_image: source not found: %s" % source)
        return 1

    os.makedirs(os.path.dirname(output), exist_ok=True)
    image = Image.open(source).convert("RGB")
    height = round(image.height * WIDTH / image.width)
    image = image.resize((WIDTH, height), Image.LANCZOS)
    image.save(output, "JPEG", quality=82, optimize=True, progressive=True)

    print("wrote %s (%d bytes, %dx%d)" % (output, os.path.getsize(output), *image.size))
    print("about.html <img> should say width=\"%d\" height=\"%d\"" % (WIDTH, height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
