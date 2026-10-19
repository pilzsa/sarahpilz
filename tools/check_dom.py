#!/usr/bin/env python3
"""Main regression suite: source files, local links, served DOM, hold frame.

Covers every page that ships: the home page, the three area pages, the gallery
feed (which must hold visualisations and nothing else) and one page per
visualisation.

Reads the post-JavaScript DOM dumps that tools/smoke.sh and tools/hold.sh write
into tools/.out/, so run those first -- tools/run_all.sh does everything in
order. Run from anywhere; exit code 0 means every check passed.
"""
import glob
import html.parser
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", ".out")

passes = []
fails = []


def check(name, ok, detail=""):
    (passes if ok else fails).append(name)
    print(("PASS  " if ok else "FAIL  ") + name + ((" :: " + str(detail)) if detail else ""))


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def dump(name):
    path = os.path.join(OUT, name)
    return read(path) if os.path.exists(path) else None


def brand_markup(dom):
    """The <a class="site-title"> element exactly as the served DOM has it."""
    match = re.search(r'<a class="site-title".*?</a>', dom, re.S)
    return match.group(0) if match else None


def brand_visible_text(brand):
    """What the wordmark intro leaves on screen: the caret plus the live copy.

    title.js layers a live copy over an invisible copy that holds the width, so
    the settled text is the caret plus .site-title-body, not the anchor's
    textContent (which also contains the width-holder and the screen-reader
    copy).
    """
    if brand is None:
        return None
    text = ""
    caret = re.search(r'<span class="site-title-caret([^"]*)"[^>]*>(.*?)</span>', brand, re.S)
    if caret and "is-off" not in caret.group(1):
        text += caret.group(2)
    body = re.search(r'<span class="site-title-body([^"]*)"[^>]*>(.*?)</span>', brand, re.S)
    if body:
        text += body.group(2)
    return html.unescape(text)


def nav_hrefs(text):
    """The hrefs of the shared nav, in order. Used to detect nav drift."""
    block = re.search(r'<div class="nav-links">(.*?)</div>', text, re.S)
    return re.findall(r'href="([^"]+)"', block.group(1)) if block else []


def nav_block(text):
    """The whole menu, so the theme toggle can be checked to live inside it."""
    match = re.search(r'<div class="nav-links">.*?</div>', text, re.S)
    return match.group(0) if match else ""


def theme_toggle(text):
    """The theme button exactly as the markup has it, so the copies can be
    compared and the DOM version recognised."""
    match = re.search(r'<button\s+class="theme-toggle".*?</button>', text, re.S)
    return match.group(0) if match else None


def served_toggle(dom):
    """The theme button's opening tag as the served DOM has it: theme.js drops
    the `hidden` attribute and sets aria-pressed, so this is where that shows."""
    match = re.search(r"<button[^>]*class=\"theme-toggle\"[^>]*>", dom)
    return match.group(0) if match else None


# HTML void elements plus the SVG shapes the pages emit self-closed.
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr",
    "circle", "line", "rect", "stop", "path", "polygon", "polyline", "ellipse", "use",
}


class Balance(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append("stray </%s>" % tag)
            return
        if self.stack[-1] != tag:
            self.errors.append("</%s> closes <%s>" % (tag, self.stack[-1]))
            return
        self.stack.pop()


# Every page that ships: the home page, the three area pages, the gallery feed,
# and one page per visualisation in that feed -- discovered with a glob so a new
# piece is covered by the suite as soon as its page exists.
PAGES = ("index.html", "about.html", "publications.html", "contact.html", "gallery.html")
PAGES += tuple(sorted(
    os.path.basename(path) for path in glob.glob(os.path.join(ROOT, "viz-*.html"))
))

# Shared assets plus the gallery art, which every tile and piece page loads.
ASSETS = (
    "styles.css", "hero.js", "logo.js", "title.js", "theme.js", "images/sarah-pilz.jpg",
    "images/gallery/big-tech-lobby-writes-eu-ai-act.png",
    "images/gallery/big-tech-lobby-writes-eu-ai-act-wide.png",
    "images/gallery/uk-ventilator-challenge.png",
    "images/gallery/uk-ventilator-challenge-wide.png",
)

print("== files ==")
for rel in PAGES + ASSETS:
    check("file exists: " + rel, os.path.exists(os.path.join(ROOT, rel)))

print()
print("== source files ==")
for name in PAGES:
    raw = read(os.path.join(ROOT, name))
    parser = Balance()
    parser.feed(raw)
    check(
        "%s: tag balance (unclosed %s)" % (name, parser.stack),
        not parser.stack and not parser.errors,
        parser.errors or parser.stack,
    )
    check("%s: no absolute filesystem paths" % name, "/home/" not in raw and "/Users/" not in raw)
    check("%s: links the shared stylesheet" % name, 'href="styles.css"' in raw)
    check("%s: loads the shared header mark" % name, 'src="logo.js"' in raw)
    check("%s: loads the shared title intro" % name, 'src="title.js"' in raw)
    check("%s: loads the shared theme script" % name, 'src="theme.js"' in raw)
    check("%s: offers both colour schemes" % name,
          '<meta name="color-scheme" content="light dark">' in raw)
    check("%s: carries the theme toggle" % name, theme_toggle(raw) is not None)
    check("%s: no inline <style> left" % name, "<style" not in raw, "styles belong in styles.css")
    check(
        "%s: carries the shared header markup" % name,
        'id="brand-logo-mark"' in raw and 'class="site-title"' in raw,
    )
    if name != "index.html":
        check("%s: has a page <h1>" % name, "<h1" in raw)

    # Local links must resolve to a real file, and any #anchor must exist there.
    for href in sorted({h for h in re.findall(r'href="([^"]+)"', raw)}):
        if href.startswith(("http://", "https://", "#", "mailto:")):
            continue
        path, _, anchor = href.partition("#")
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            check("%s: link target %s" % (name, href), False, "missing file")
            continue
        if anchor:
            check("%s: link %s anchor exists" % (name, href), ('id="%s"' % anchor) in read(full))
        else:
            check("%s: link %s" % (name, href), True)

    for src in sorted({s for s in re.findall(r'src="([^"]+)"', raw)}):
        if src.startswith(("http://", "https://")):
            continue
        check("%s: src %s exists" % (name, src), os.path.exists(os.path.join(ROOT, src)))

check("index.html: loads the hero script", 'src="hero.js"' in read(os.path.join(ROOT, "index.html")))

# Only the home page pulls React and D3; every other page must stay script-light.
for name in PAGES[1:]:
    raw = read(os.path.join(ROOT, name))
    check(
        "%s: no CDN or hero scripts" % name,
        "unpkg.com" not in raw and 'src="hero.js"' not in raw,
    )

# The nav is duplicated in every page (a static site has no template), so this
# is the check that keeps the copies honest.
print()
print("== shared navigation ==")
navs = {name: nav_hrefs(read(os.path.join(ROOT, name))) for name in PAGES}
check("index.html: nav is not empty", bool(navs["index.html"]), navs["index.html"])
for name in PAGES[1:]:
    check(
        "%s: nav matches index.html" % name,
        navs[name] == navs["index.html"],
        "%s vs %s" % (navs[name], navs["index.html"]),
    )
# The nav reaches the three area pages and the gallery; a piece page is reached
# from the feed, not from the nav.
for name in ("about.html", "publications.html", "contact.html", "gallery.html"):
    check("index.html: nav reaches %s" % name, name in navs["index.html"])

# The toggle is duplicated in every page like the nav, so the copies are held
# against each other: the header must read the same everywhere, and the button
# must be the one theme.js knows how to drive.
print()
print("== shared theme toggle ==")
toggles = {name: theme_toggle(read(os.path.join(ROOT, name))) for name in PAGES}
check("index.html: has the theme toggle", toggles["index.html"] is not None)
for name in PAGES:
    check("%s: the toggle sits in the menu" % name,
          bool(toggles[name]) and toggles[name] in nav_block(read(os.path.join(ROOT, name))))
for name in PAGES[1:]:
    check("%s: theme toggle matches index.html" % name, toggles[name] == toggles["index.html"])

# Contact icons: one per channel, each an inline SVG painted with currentColor so
# the stylesheet alone decides the colour a chip turns on hover.
print()
print("== contact icons (contact.html) ==")
contact = read(os.path.join(ROOT, "contact.html"))
row = re.search(r'<ul class="contact-links".*?</ul>', contact, re.S)
check("contact.html: has the contact-links row", row is not None)
if row:
    row_html = row.group(0)
    links = re.findall(
        r'<a\s+class="contact-link"\s+href="([^"]+)"\s+aria-label="([^"]+)"',
        row_html,
        re.S,
    )
    labels = [label for _, label in links]
    check("contact.html: six contact links", len(links) == 6, len(links))
    check(
        "contact.html: six distinct, non-empty labels",
        len(set(labels)) == len(labels) and all(labels),
        labels,
    )
    for host in ("linkedin.com", "wa.me", "signal.me", "instagram.com", "threema.id"):
        check(
            "contact.html: exactly one link to %s" % host,
            sum(host in href for href, _ in links) == 1,
        )
    mails = [href for href, _ in links if href.startswith("mailto:")]
    check(
        "contact.html: one usable mailto link",
        len(mails) == 1 and "@" in mails[0] and mails[0].endswith((".com", ".de", ".org", ".net", ".io")),
        mails,
    )
    check(
        "contact.html: every link is a real destination",
        all(href.startswith(("mailto:", "https://")) for href, _ in links),
    )
    check(
        "contact.html: icons are drawn with currentColor",
        row_html.count('stroke="currentColor"') == 6,
        row_html.count('stroke="currentColor"'),
    )
    check(
        "contact.html: icons are decorative for screen readers",
        len(re.findall(r'<svg[^>]*aria-hidden="true"', row_html)) == 6,
    )
    check(
        "contact.html: icons are not left empty",
        len(re.findall(r"<(?:rect|path)\b", row_html)) >= 8,
        len(re.findall(r"<(?:rect|path)\b", row_html)),
    )

# The gallery holds visualisations and nothing else. One tile per piece from the
# yellow (Visualization) section of the home page, newest first; no tile carries
# a colour of its own, because the whole page is one area; and the sections that
# are not visualisations do not lead into it.
print()
print("== gallery feed ==")
index_source = read(os.path.join(ROOT, "index.html"))
gallery_source = read(os.path.join(ROOT, "gallery.html"))
grid = re.search(r'<div class="gallery-grid">(.*?)</div>', gallery_source, re.S)
check("gallery.html: has the tile grid", grid is not None)
tiles = re.findall(r'<article class="tile".*?</article>', grid.group(1), re.S) if grid else []
check(
    "gallery.html: every tile is an article.tile",
    bool(tiles) and grid is not None and len(tiles) == grid.group(1).count("<article"),
    len(tiles),
)

years, pieces = [], []
for tile in tiles:
    ident = re.search(r'id="([a-z0-9-]+)"', tile)
    image = re.search(r'src="(images/gallery/[a-z0-9-]+\.png)"', tile)
    alt = re.search(r'alt="([^"]*)"', tile)
    kicker = re.search(r'<p class="tile-kicker">([^<]+)</p>', tile)
    link = re.search(r'href="(viz-[a-z0-9-]+\.html)"', tile)
    label = ident.group(1) if ident else "tile-%d" % (len(pieces) + 1)

    check("gallery.html: %s has an id" % label, ident is not None)
    check(
        "gallery.html: %s has a tile image with alt text" % label,
        image is not None and alt is not None and bool(alt.group(1).strip()),
    )
    check("gallery.html: %s names an area and a year" % label, kicker is not None)
    check(
        "gallery.html: %s links to its piece page" % label,
        (link is not None and os.path.exists(os.path.join(ROOT, link.group(1)))) if link else False,
    )
    if not (ident and link and kicker):
        continue

    check("gallery.html: %s is a visualization" % label,
          kicker.group(1).startswith("Visualization"), kicker.group(1))
    check("gallery.html: %s links back from its own page" % label,
          ("gallery.html#%s" % label) in read(os.path.join(ROOT, link.group(1))))
    year = re.search(r"(\d{4})", kicker.group(1))
    years.append(int(year.group(1)) if year else 0)
    pieces.append(label)

check("gallery.html: pieces are listed newest first", years == sorted(years, reverse=True), years)
check("gallery.html: no tile carries a colour of its own",
      grid is not None and "data-area" not in grid.group(1))
check("gallery.html: no area legend left", 'class="legend"' not in gallery_source)

viz_section = re.search(r'<section[^>]*id="visualization".*?</section>', index_source, re.S)
viz_links = set(re.findall(r'href="(viz-[a-z0-9-]+\.html)"', viz_section.group(0))) if viz_section else set()
tile_links = set(re.findall(r'href="(viz-[a-z0-9-]+\.html)"', grid.group(1))) if grid else set()
check("index.html: the Visualization section links its pieces", bool(viz_links), sorted(viz_links))
check(
    "gallery.html: every tile is a piece from the Visualization section",
    bool(tile_links) and tile_links <= viz_links,
    sorted(tile_links - viz_links),
)

print()
print("== no gallery links from the other areas ==")
for area in ("research", "data", "coordination"):
    section = re.search(r'<section[^>]*id="%s".*?</section>' % area, index_source, re.S)
    block = section.group(0) if section else ""
    check(
        "index.html: %s section does not link to the gallery" % area,
        section is not None and "viz-" not in block and "gallery.html" not in block,
    )
publications_source = read(os.path.join(ROOT, "publications.html"))
publications_body = publications_source.split("</header>", 1)[-1]
check(
    "publications.html: does not link to the gallery",
    "viz-" not in publications_body and "gallery.html" not in publications_body,
)

# The publications feed is written by tools/make_publications.py from
# tools/publications.json, so the data file is the source of truth and the page
# is checked against it: one link in the JSON, one tile in the HTML, in the same
# order, with the same picture, date, headline and teaser, newest first.
print()
print("== publications feed ==")
data_path = os.path.join(ROOT, "tools", "publications.json")
check("tools/publications.json exists", os.path.exists(data_path))
articles = json.loads(read(data_path)).get("articles", []) if os.path.exists(data_path) else []

feed = re.search(r'<div class="publication-grid">(.*?)</div>', publications_source, re.S)
check("publications.html: has the feed grid", feed is not None)
region = feed.group(1) if feed else ""
check(
    "publications.html: the feed sits between its two markers",
    region.count("<!-- publications:start -->") == 1
    and region.count("<!-- publications:end -->") == 1
    and region.index("publications:start") < region.index("publications:end"),
)
tiles = re.findall(r'<article class="publication".*?</article>', region, re.S)
check(
    "publications.html: every tile is an article.publication",
    bool(tiles) and len(tiles) == region.count("<article"),
    len(tiles),
)
check(
    "publications.html: one tile per link in tools/publications.json",
    len(tiles) == len(articles),
    "%d tiles / %d links" % (len(tiles), len(articles)),
)
check(
    "publications.html: the tiles are the links, in the file's order",
    bool(articles) and [a.get("id") for a in articles]
    == re.findall(r'<article class="publication" id="([a-z0-9-]+)"', region),
)
check("publications.html: no tile carries a colour of its own", "data-area" not in region)

dates = []
for index, tile in enumerate(tiles):
    article = articles[index] if index < len(articles) else {}
    label = article.get("id") or "tile-%d" % (index + 1)
    picture = article.get("image") or ""
    headline = re.search(
        r'<h3 class="publication-title">\s*<a href="([^"]+)">(.*?)</a>', tile, re.S
    )
    kicker = re.search(r'<p class="publication-kicker">(.*?)</p>', tile, re.S)
    teaser = re.search(r'<p class="publication-teaser">(.*?)</p>', tile, re.S)
    date = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})">', tile)
    image = re.search(r'<img\s+src="(images/publications/[a-z0-9-]+\.jpg)"', tile)
    alt = re.search(r'alt="([^"]*)"', tile)

    check(
        "publications.html: %s links to the published piece" % label,
        headline is not None and headline.group(1) == article.get("url"),
    )
    check(
        "publications.html: %s shows the headline from the article" % label,
        headline is not None
        and html.unescape(headline.group(2)) == (article.get("title") or ""),
        headline.group(2) if headline else None,
    )
    check(
        "publications.html: %s names its outlet" % label,
        bool(article.get("outlet"))
        and article["outlet"] in html.unescape(" ".join(kicker.group(1).split()) if kicker else ""),
    )
    check(
        "publications.html: %s dates the piece" % label,
        bool(date) == bool(article.get("date"))
        and (date is None or date.group(1) == article.get("date")),
        article.get("date"),
    )
    check(
        "publications.html: %s carries the teaser" % label,
        bool(teaser) == bool(article.get("teaser"))
        and (
            teaser is None
            or html.unescape(" ".join(teaser.group(1).split())) == article.get("teaser")
        ),
    )
    check(
        "publications.html: %s shows its preview picture" % label,
        (image is not None and image.group(1) == picture) if picture else image is None,
        picture,
    )
    check(
        "publications.html: %s picture is in the repo and described" % label,
        not picture
        or (
            os.path.exists(os.path.join(ROOT, picture))
            and alt is not None
            and bool(alt.group(1).strip())
        ),
    )
    if article.get("date"):
        dates.append(article["date"])

check("publications.html: articles are listed newest first", dates == sorted(dates, reverse=True), dates)

print()
print("== served DOM: index.html ==")
dom = dump("v_index.html")
check("index: DOM dump present (run tools/smoke.sh)", dom is not None,
      "" if dom else "missing tools/.out/v_index.html -- run tools/smoke.sh")
if dom is not None:
    check("index: logo mark has 4 circles", len(re.findall(r"<circle", dom)) == 4, len(re.findall(r"<circle", dom)))
    check("index: logo mark has 4 sides", len(re.findall(r'stroke-dasharray="24"', dom)) == 4)
    check("index: cropped viewBox present", 'viewBox="5 5 34 34"' in dom)
    check("index: hero beams svg rendered", 'class="hero-beams"' in dom)
    check("index: 4 beam rects", len(re.findall(r"<rect", dom)) == 4, len(re.findall(r"<rect", dom)))
    check("index: typed hero line", "Research. Data. Science. Collaboration." in dom)
    brand = brand_markup(dom)
    check("index: brand title links home",
          brand is not None and 'class="site-title" href="#home"' in brand)
    check("index: title keeps a screen-reader copy",
          brand is not None and '<span class="visually-hidden">_square one</span>' in brand)
    check("index: title width-holder keeps the caret still",
          brand is not None and 'class="site-title-fitter"' in brand)
    check("index: title caret is a lone underscore",
          brand is not None and len(re.findall(r'<span class="site-title-caret"[^>]*>_</span>', brand)) == 1)
    check("index: title intro finished with the whole wordmark on screen",
          brand_visible_text(brand) == "_square one", brand_visible_text(brand))
    check("index: title intro left nothing hidden", "is-off" not in dom)
    # Every id the source declares must survive into the rendered page, so no
    # in-page link can break once the markup is served.
    index_source = read(os.path.join(ROOT, "index.html"))
    for anchor in sorted(set(re.findall(r'id="([^"]+)"', index_source))):
        check("index: id=%s survives into the DOM" % anchor, ('id="%s"' % anchor) in dom)
    check("index: hero <h1> rendered by hero.js", re.search(r"<h1[ >]", dom) is not None)

print()
print("== served DOM: about.html ==")
adom = dump("v_about.html")
check("about: DOM dump present (run tools/smoke.sh)", adom is not None,
      "" if adom else "missing tools/.out/v_about.html -- run tools/smoke.sh")
if adom is not None:
    check("about: logo mark has 4 circles", len(re.findall(r"<circle", adom)) == 4, len(re.findall(r"<circle", adom)))
    check("about: logo mark has 4 sides", len(re.findall(r'stroke-dasharray="24"', adom)) == 4)
    check("about: cropped viewBox present", 'viewBox="5 5 34 34"' in adom)
    abrand = brand_markup(adom)
    check(
        "about: brand title links home",
        abrand is not None and 'class="site-title" href="index.html#home"' in abrand,
    )
    check("about: title keeps a screen-reader copy",
          abrand is not None and '<span class="visually-hidden">_square one</span>' in abrand)
    check("about: title width-holder keeps the caret still",
          abrand is not None and 'class="site-title-fitter"' in abrand)
    check("about: title intro finished with the whole wordmark on screen",
          brand_visible_text(abrand) == "_square one", brand_visible_text(abrand))
    check("about: title intro left nothing hidden", "is-off" not in adom)
    check(
        "about: served nav matches index",
        bool(nav_hrefs(adom)) and nav_hrefs(adom) == nav_hrefs(dom),
        nav_hrefs(adom),
    )
    about_source = read(os.path.join(ROOT, "about.html"))
    for anchor in sorted(set(re.findall(r'id="([^"]+)"', about_source))):
        check("about: id=%s survives into the DOM" % anchor, ('id="%s"' % anchor) in adom)
    check("about: portrait rendered", 'src="images/sarah-pilz.jpg"' in adom)
    check("about: h1", "<h1>About</h1>" in adom)
    check("about: no old header", "<h1> Sarah Pilz </h1>" not in adom)
    check(
        "about: no /about or /contact routes",
        'href="/about"' not in adom and 'href="/contact"' not in adom,
    )
    check("about: no stacked '|' nav", "<nav>" not in adom)
    check("about: the portrait is a circle beside the heading",
          'class="page-intro container page-intro-split"' in adom
          and 'class="portrait"' in adom)

print()
print("== served DOM: publications.html ==")
pdom = dump("v_publications.html")
check("publications: DOM dump present (run tools/smoke.sh)", pdom is not None,
      "" if pdom else "missing tools/.out/v_publications.html -- run tools/smoke.sh")
if pdom is not None:
    check("publications: logo mark has 4 circles", len(re.findall(r"<circle", pdom)) == 4,
          len(re.findall(r"<circle", pdom)))
    check("publications: cropped viewBox present", 'viewBox="5 5 34 34"' in pdom)
    check("publications: title intro finished with the whole wordmark on screen",
          brand_visible_text(brand_markup(pdom)) == "_square one", brand_visible_text(brand_markup(pdom)))
    check("publications: title intro left nothing hidden", "is-off" not in pdom)
    check(
        "publications: served nav matches index",
        bool(nav_hrefs(pdom)) and nav_hrefs(pdom) == nav_hrefs(index_source),
        nav_hrefs(pdom),
    )
    check("publications: h1", "<h1>Publications</h1>" in pdom)
    check(
        "publications: the feed rendered one tile per article",
        pdom.count('<article class="publication"') == len(articles),
        pdom.count('<article class="publication"'),
    )
    for article in articles:
        check("publications: tile #%s survives into the DOM" % article.get("id"),
              ('id="%s"' % article.get("id")) in pdom)
    for source in sorted(set(re.findall(r'src="(images/publications/[^"]+)"', pdom))):
        check("publications: %s is served" % source, os.path.exists(os.path.join(ROOT, source)))

print()
print("== served DOM: gallery.html ==")
gdom = dump("v_gallery.html")
check("gallery: DOM dump present (run tools/smoke.sh)", gdom is not None,
      "" if gdom else "missing tools/.out/v_gallery.html -- run tools/smoke.sh")
if gdom is not None:
    check("gallery: logo mark has 4 circles", len(re.findall(r"<circle", gdom)) == 4,
          len(re.findall(r"<circle", gdom)))
    check("gallery: cropped viewBox present", 'viewBox="5 5 34 34"' in gdom)
    check("gallery: title intro finished with the whole wordmark on screen",
          brand_visible_text(brand_markup(gdom)) == "_square one", brand_visible_text(brand_markup(gdom)))
    check("gallery: title intro left nothing hidden", "is-off" not in gdom)
    check(
        "gallery: served nav matches index",
        bool(nav_hrefs(gdom)) and nav_hrefs(gdom) == nav_hrefs(index_source),
        nav_hrefs(gdom),
    )
    check("gallery: h1", "<h1>Gallery</h1>" in gdom)
    check("gallery: the feed rendered one tile per piece",
          gdom.count('class="tile"') == len(pieces), gdom.count('class="tile"'))
    check("gallery: every tile is a click target",
          len(re.findall(r'class="tile-title"', gdom)) == len(pieces))
    for piece in pieces:
        check("gallery: tile #%s survives into the DOM" % piece, ('id="%s"' % piece) in gdom)

print()
print("== served DOM: the theme ==")
# The theme is the one thing on these pages that theme.js, not the markup,
# decides: the script settles <html data-theme> before the body is parsed and
# reveals the button it drives. The dark capture is the ?theme=dark preview, the
# only dark route a headless browser can be put on (see tools/smoke.sh).
for label, name in (("index", "v_index.html"), ("about", "v_about.html"),
                    ("publications", "v_publications.html"), ("gallery", "v_gallery.html")):
    served = dump(name)
    if served is None:
        continue
    toggle = served_toggle(served)
    check("%s: the served header carries the theme toggle" % label, toggle is not None)
    check("%s: theme.js revealed the toggle" % label,
          toggle is not None and "hidden" not in toggle, toggle)
    check("%s: the page starts in the light theme" % label,
          re.search(r'<html[^>]*data-theme="light"', served) is not None)
    check("%s: the toggle reports the light theme" % label,
          toggle is not None and 'aria-pressed="false"' in toggle)

dark = dump("v_index_dark.html")
check("dark: DOM dump present (run tools/smoke.sh)", dark is not None,
      "" if dark else "missing tools/.out/v_index_dark.html -- run tools/smoke.sh")
if dark is not None:
    check("dark: ?theme=dark raises the dark theme on <html>",
          re.search(r'<html[^>]*data-theme="dark"', dark) is not None)
    check("dark: the toggle reports the dark theme",
          'aria-pressed="true"' in (served_toggle(dark) or ""), served_toggle(dark))
    check("dark: the logo mark still has 4 circles", len(re.findall(r"<circle", dark)) == 4,
          len(re.findall(r"<circle", dark)))
    check("dark: the hero still types its line",
          "Research. Data. Science. Collaboration." in dark)
    check("dark: the nav is the same one dark or light",
          nav_hrefs(dark) == nav_hrefs(index_source))

# ... and the same page as a dark-mode visitor with no stored choice sees it: the
# preference is the browser's, not the URL's, so this is the one capture where
# theme.js has to have read the system.
system_dark = dump("v_index_dark_system.html")
check("dark system: DOM dump present (run tools/smoke.sh)", system_dark is not None,
      "" if system_dark else "missing tools/.out/v_index_dark_system.html -- run tools/smoke.sh")
if system_dark is not None:
    check("dark system: a dark system preference is honoured with nothing stored",
          re.search(r'<html[^>]*data-theme="dark"', system_dark) is not None)
    check("dark system: the toggle reports the dark theme",
          'aria-pressed="true"' in (served_toggle(system_dark) or ""))
    check("dark system: the logo mark still has 4 circles",
          len(re.findall(r"<circle", system_dark)) == 4)

print()
print("== phase-locked logo (hold frame, p=0.87) ==")
hdom = dump("hold_dom.html")
check("hold: DOM dump present (run tools/hold.sh)", hdom is not None,
      "" if hdom else "missing tools/.out/hold_dom.html -- run tools/hold.sh")
if hdom is not None:
    offsets = re.findall(r'stroke-dashoffset="([^"]*)"', hdom)
    check("hold: 4 sides fully drawn", offsets == ["0.00"] * 4, offsets)
    centres = re.findall(r'cx="([^"]*)" cy="([^"]*)"', hdom)
    check(
        "hold: dots sit on the square's corners",
        centres == [("10.00", "10.00"), ("34.00", "10.00"), ("34.00", "34.00"), ("10.00", "34.00")],
        centres,
    )

print()
print("== node --check ==")
for rel in ("theme.js", "logo.js", "title.js", "hero.js"):
    result = subprocess.run(["node", "--check", os.path.join(ROOT, rel)], capture_output=True, text=True)
    check("%s parses" % rel, result.returncode == 0, result.stderr.strip())

print()
print("PASSED %d / %d" % (len(passes), len(passes) + len(fails)))
if fails:
    print("FAILURES:")
    for name in fails:
        print(" -", name)
    sys.exit(1)
