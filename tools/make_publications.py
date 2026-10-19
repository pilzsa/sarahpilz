#!/usr/bin/env python3
"""Build the Publications feed on publications.html from a list of links.

publications.html shows one tile per article -- preview picture, date, outlet,
headline and teaser -- and every tile is a link to the piece where it was
published. The list itself lives in tools/publications.json, so adding an
article is adding a link:

    {
      "articles": [
        {"url": "https://example.org/story"},
        {"url": "https://example.org/other", "date": "2024-05-06",
         "outlet": "Example", "teaser": "Written by hand, and it wins."}
      ]
    }

Run this script and it reads each page once and fills in what the page says
about itself -- Open Graph and article:* metadata, <title>, <time> -- so the
headline, the teaser, the date, the outlet and the preview picture come from the
article and not from memory. Pictures are downloaded into
images/publications/ and re-saved as small progressive JPEGs. A value already
written in the file is never overwritten, so a hand-written date or teaser wins;
--refresh reads every link again from scratch.

Why a script and not JavaScript: a browser may not read another site's metadata
(cross-origin), and the site should stay a static page that also works with
JavaScript off and straight from the filesystem. The feed in publications.html
is plain markup between two markers; this script is the only thing that writes
between them, and the committed page is the source of truth for the site.

Usage (from anywhere):
  python3 tools/make_publications.py            fetch what is missing, rebuild
  python3 tools/make_publications.py --refresh  read every link again
  python3 tools/make_publications.py --offline  fetch nothing, rebuild from the file
  python3 tools/make_publications.py --check    write nothing; exit 1 when the page
                                                is not what this script would write

Needs:  Python 3 (stdlib) to read the pages, Pillow to re-save the pictures.
Exit code 0 = the feed is up to date, 1 = something could not be built.
"""
import html
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

try:
    from PIL import Image
except ImportError:
    print("make_publications: Pillow is required (python3 -m pip install Pillow)")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tools", "publications.json")
PAGE = os.path.join(ROOT, "publications.html")
PICTURES = os.path.join(ROOT, "images", "publications")
PICTURE_DIR = "images/publications"

START = "<!-- publications:start -->"
END = "<!-- publications:end -->"

# A real browser user agent: most news sites serve their metadata to one and
# an empty page (or a 403) to anything else.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)
TIMEOUT = 25
MAX_PICTURE_WIDTH = 1200          # the site never shows a preview wider than this
TEASER_LIMIT = 300                # characters kept from a meta description
FIELDS = ("title", "date", "teaser", "outlet")

# Where the publication date hides, best first. Everything is compared in
# lowercase, so itemprop="datePublished" lands on "datepublished".
DATE_META = (
    "article:published_time",
    "datepublished",
    "og:published_time",
    "date",
    "sailthru.date",
)

MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

META_RE = re.compile(r"<meta\b[^>]*>", re.I)
ATTR_RE = re.compile(r"""([a-zA-Z:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""")
TIME_RE = re.compile(r"<time[^>]*\bdatetime=\"([^\"]+)\"", re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def rel(path):
    """A path as it reads from the repo root, for messages."""
    return os.path.relpath(path, ROOT)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def meta_map(page):
    """property/name/itemprop -> content, first mention winning."""
    found = {}
    for tag in META_RE.findall(page):
        attrs = {}
        for match in ATTR_RE.finditer(tag):
            value = match.group(2) or match.group(3) or match.group(4) or ""
            attrs[match.group(1).lower()] = html.unescape(value)
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").lower()
        content = (attrs.get("content") or "").strip()
        if key and content and key not in found:
            found[key] = content
    return found


def page_title(page):
    match = TITLE_RE.search(page)
    return " ".join(html.unescape(match.group(1)).split()) if match else ""


def iso_date(value):
    match = re.match(r"\s*(\d{4})-(\d{2})-(\d{2})", value or "")
    return "-".join(match.groups()) if match else ""


def published(page, meta):
    """The publication date as YYYY-MM-DD, or "" when the page does not say."""
    for key in DATE_META:
        if meta.get(key):
            iso = iso_date(meta[key])
            if iso:
                return iso
    match = TIME_RE.search(page)
    return iso_date(match.group(1)) if match else ""


def friendly_date(value):
    """2025-01-14 -> 14 January 2025. Locale-independent, so the page is stable."""
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", value or "")
    if not match:
        return value
    year, month, day = match.groups()
    name = MONTHS[int(month) - 1] if 1 <= int(month) <= 12 else month
    return "%d %s %s" % (int(day), name, year)


def shorten(text, limit=TEASER_LIMIT):
    """A meta description cut to a teaser at a word boundary."""
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"


def slug(text, limit=60):
    """A stable id for a tile: lowercase words joined by hyphens."""
    text = re.sub(r"[^a-z0-9]+", "-", html.unescape(text or "").lower()).strip("-")
    return text[:limit].rstrip("-") or "article"


def unique(base, taken):
    candidate, number = base, 2
    while candidate in taken:
        candidate = "%s-%d" % (base, number)
        number += 1
    return candidate


def by_date(articles):
    """Newest first, like the gallery; entries without a date sink to the end."""
    dated = sorted([a for a in articles if a.get("date")],
                   key=lambda a: a["date"], reverse=True)
    return dated + [a for a in articles if not a.get("date")]


def fetch_meta(url):
    """Read one article page and pull the feed's fields out of its head.

    Returns None when the page cannot be read at all; a page that is read but
    says nothing useful still returns a dict, with the empty strings left in.
    """
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"}
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            final = response.geturl()
    except Exception as error:
        print("      ! could not read the page (%s)" % error)
        return None

    page = raw.decode(charset, "replace")
    meta = meta_map(page)
    title = meta.get("og:title") or meta.get("twitter:title") or page_title(page)
    teaser = meta.get("og:description") or meta.get("twitter:description") or meta.get("description")
    image = (meta.get("og:image") or meta.get("twitter:image") or "").strip()
    return {
        "title": " ".join((title or "").split()),
        "teaser": shorten(teaser),
        "date": published(page, meta),
        # A site name beats a hostname when the page offers one.
        "outlet": (meta.get("og:site_name") or "").strip()
        or urllib.parse.urlsplit(final).netloc.removeprefix("www."),
        "image_url": urllib.parse.urljoin(final, image) if image else "",
    }


def download_picture(url, dest):
    """Fetch a preview picture and re-save it as a small progressive JPEG.

    Returns the written size, or None when the URL is not a picture we can read
    (an SVG logo, say) -- the tile then simply ships without its picture.
    """
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()
    except Exception as error:
        print("      ! could not read the picture (%s)" % error)
        return None

    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except Exception as error:
        print("      ! picture: %s" % error)
        return None

    if image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        flattened = Image.new("RGB", image.size, (255, 255, 255))
        flattened.paste(rgba, mask=rgba.split()[-1])
        image = flattened
    else:
        image = image.convert("RGB")

    if image.width > MAX_PICTURE_WIDTH:
        height = round(image.height * MAX_PICTURE_WIDTH / image.width)
        image = image.resize((MAX_PICTURE_WIDTH, height), Image.LANCZOS)

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    image.save(dest, "JPEG", quality=82, progressive=True, optimize=True)
    return image.size


def image_size(path):
    """(width, height) of a picture already in the repo, or None."""
    full = os.path.join(ROOT, path) if path else ""
    if not path or not os.path.exists(full):
        return None
    try:
        with Image.open(full) as image:
            return image.size
    except OSError:
        return None


def picture_markup(article, indent):
    """The preview picture, or nothing at all when there is none to show.

    width and height are the file's real pixel size, so the feed reserves the
    space before the picture arrives and the page never jumps while it loads.
    """
    size = image_size(article.get("image"))
    if not size:
        return []
    alt = html.escape(article.get("title") or article["url"], quote=True)
    return [
        "%s<figure class=\"publication-figure\">" % indent,
        "%s  <img" % indent,
        "%s    src=\"%s\"" % (indent, article["image"]),
        "%s    alt=\"%s\"" % (indent, alt),
        "%s    width=\"%d\"" % (indent, size[0]),
        "%s    height=\"%d\"" % (indent, size[1]),
        "%s  >" % indent,
        "%s</figure>" % indent,
    ]


def kicker_text(article):
    """Date and outlet, joined the way the rest of the site joins small print."""
    parts = []
    if article.get("date"):
        parts.append(
            "<time datetime=\"%s\">%s</time>" % (article["date"], friendly_date(article["date"]))
        )
    if article.get("outlet"):
        parts.append(html.escape(article["outlet"]))
    return " · ".join(parts)


def render_article(article, indent):
    inner = indent + "  "
    lines = ["%s<article class=\"publication\" id=\"%s\">" % (indent, article["id"])]
    lines.extend(picture_markup(article, inner))

    kicker = kicker_text(article)
    if kicker:
        lines.append("%s<p class=\"publication-kicker\">" % inner)
        lines.append("%s  %s" % (inner, kicker))
        lines.append("%s</p>" % inner)

    title = html.escape(article.get("title") or article["url"], quote=False)
    lines.append("%s<h3 class=\"publication-title\">" % inner)
    lines.append("%s  <a href=\"%s\">%s</a>" % (inner, html.escape(article["url"], quote=True), title))
    lines.append("%s</h3>" % inner)

    teaser = (article.get("teaser") or "").strip()
    if teaser:
        lines.append("%s<p class=\"publication-teaser\">" % inner)
        lines.append("%s  %s" % (inner, html.escape(teaser, quote=False)))
        lines.append("%s</p>" % inner)

    lines.append("%s</article>" % indent)
    return lines


def render(articles, indent):
    """The feed markup, indented to sit inside the marker it replaces."""
    if not articles:
        return [
            "%s<p class=\"publication-empty\">" % indent,
            "%s  No publications yet — add a link to tools/publications.json and" % indent,
            "%s  run tools/make_publications.py." % indent,
            "%s</p>" % indent,
        ]
    lines = []
    for article in articles:
        lines.extend(render_article(article, indent))
    return lines


def splice(page, body, indent):
    """Replace everything between the two markers, keeping their indentation."""
    pattern = re.compile(
        r"%s%s.*?%s" % (re.escape(indent), re.escape(START), re.escape(END)), re.S
    )
    if not pattern.search(page):
        return None
    region = "%s%s\n%s\n%s%s" % (indent, START, body, indent, END)
    return pattern.sub(lambda _: region, page, count=1)


def resolve(articles, refresh, offline):
    """Read every link that needs it and fill in what the pages say about themselves.

    Only a missing field is fetched, so the second run of this script is a
    no-op: titles, dates, teasers and pictures already in the file are left
    alone (--refresh is the way to read them again).
    """
    harvested = {}
    for index, article in enumerate(articles):
        url = (article.get("url") or "").strip()
        if not url:
            print("  %2d ! this entry has no url" % (index + 1))
            continue

        picture = os.path.join(ROOT, article["image"]) if article.get("image") else ""
        if offline or not (refresh or not article.get("title") or not os.path.exists(picture)):
            continue

        print("  %2d %s" % (index + 1, url))
        meta = fetch_meta(url)
        if meta is None:
            continue
        harvested[index] = meta
        for field in FIELDS:
            if meta.get(field) and (refresh or not article.get(field)):
                article[field] = meta[field]
        print("      %s | %s | %s"
              % (meta.get("date") or "no date",
                 meta.get("outlet") or "no outlet",
                 meta.get("image_url") or "no picture"))
        if not article.get("date"):
            print("      ! the page does not say when it was published"
                  " — set a date in %s" % rel(DATA))

    # Ids are settled after the titles are known, and an id already in the file
    # is never changed: a tile's anchor stays put when its headline is re-read.
    taken = set()
    for article in articles:
        if not article.get("id"):
            article["id"] = unique(slug(article.get("title") or article.get("url")), taken)
        taken.add(article["id"])

    for index, article in enumerate(articles):
        target = os.path.join(PICTURES, "%s.jpg" % article["id"])
        relative = "%s/%s.jpg" % (PICTURE_DIR, article["id"])
        if os.path.exists(target) and not refresh:
            article["image"] = relative
            continue
        source = (harvested.get(index) or {}).get("image_url") or ""
        if source and not offline:
            if download_picture(source, target):
                article["image"] = relative
                print("      picture: %s" % relative)
                continue
        if os.path.exists(target):
            article["image"] = relative
        else:
            article.pop("image", None)


def main():
    flags = set(sys.argv[1:])
    unknown = flags - {"--refresh", "--offline", "--check"}
    if unknown:
        print("make_publications: unknown option %s" % ", ".join(sorted(unknown)))
        return 1
    refresh = "--refresh" in flags
    check = "--check" in flags
    offline = "--offline" in flags or check  # --check never touches the network

    if not os.path.exists(DATA):
        print("make_publications: %s is missing — it holds the list of links" % rel(DATA))
        return 1
    if not os.path.exists(PAGE):
        print("make_publications: %s is missing" % rel(PAGE))
        return 1

    before = read(DATA)
    data = json.loads(before)
    articles = data.get("articles")
    if articles is None:
        articles = data["articles"] = []

    print("== links ==")
    print("  %d article(s) in %s%s"
          % (len(articles), rel(DATA), " (nothing will be fetched)" if offline else ""))
    resolve(articles, refresh, offline)

    data["articles"] = by_date(articles)
    after = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    page = read(PAGE)
    marker = re.search(r"(?P<indent>[ \t]*)%s" % re.escape(START), page)
    if not marker:
        print("make_publications: %s has no %s marker" % (rel(PAGE), START))
        return 1
    indent = marker.group("indent")
    updated = splice(page, "\n".join(render(data["articles"], indent + "  ")), indent)
    if updated is None:
        print("make_publications: the feed markers in %s are out of order" % rel(PAGE))
        return 1

    stale = [rel(path) for path, text in ((DATA, after), (PAGE, updated)) if read(path) != text]

    print()
    if check:
        if stale:
            print("make_publications: out of date: %s" % ", ".join(stale))
            print("  run:  python3 tools/make_publications.py")
            return 1
        print("make_publications: the feed matches %s (%d article%s)"
              % (rel(DATA), len(data["articles"]),
                 "" if len(data["articles"]) == 1 else "s"))
        return 0

    for path, text in ((DATA, after), (PAGE, updated)):
        if read(path) != text:
            write(path, text)
            print("make_publications: wrote %s" % rel(path))
    print("make_publications: %d article(s) in the feed" % len(data["articles"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
