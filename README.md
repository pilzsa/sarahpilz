# _square one — sarahpilz

A small, no-build static site: plain HTML, one shared stylesheet, and four
progressive-enhancement scripts. Seven pages: the home page with its four areas
(Research, Data, Coordination, Visualization), Publications, Gallery, About and
Contact, plus one page per visualisation in the gallery. Every link is drawn in
the colour of the area it belongs to, so the palette doubles as a map of the
site. There is nothing to compile, bundle or install — serve the folder and it
runs.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | Home page — hero and the four areas: Research, Data, Coordination, Visualization |
| `publications.html` | Publications page — one preview tile per article (picture, date, outlet, headline, teaser), written from `tools/publications.json` by `tools/make_publications.py` |
| `gallery.html` | Gallery — every visualisation, newest first. Visualisations only: nothing from Publications, Data or Coordination appears here |
| `viz-<slug>.html` | One page per visualisation in the gallery — the full-size graphic, a caption, and a way back to the feed |
| `about.html` | About page — intro, portrait, favourites |
| `contact.html` | Contact page — icon row (email, LinkedIn, WhatsApp, Signal, Instagram, Threema) with placeholder links to swap for your own |
| `styles.css` | **Every** style for all seven pages: design tokens (light and dark), area colours, header, hero, sections, brush highlights, gallery grid, publications feed, piece pages, portrait, contact chips, footer, breakpoints |
| `logo.js` | Animated header mark (four dots orbit, then form a square) — loaded by every page |
| `title.js` | Header wordmark intro: the underscore blinks, "square one" is deleted from the left, then the whole title returns — loaded by every page |
| `theme.js` | Light/dark theme: settles `<html data-theme>` before the first paint, drives the header toggle and remembers the choice — loaded by every page |
| `hero.js` | D3 light beams + React typing line — loaded by `index.html` only |
| `images/sarah-pilz.jpg` | Portrait, 900 px wide |
| `images/gallery/*.png` | Gallery art: `<slug>.png` (900 px square) for the tile, `<slug>-wide.png` (1600 × 1000) for the piece page |
| `images/publications/*.jpg` | Publications preview pictures — downloaded from each article's own `og:image` and resized by `tools/make_publications.py`, never drawn by hand |
| `tools/` | Development checks and helpers — **not** part of the published site |
| `tools/publications.json` | The list of article links the Publications feed is built from — the one place an article is added or corrected |
| `saved/` | Snapshots of every page and every visualisation sub-page — the post-JavaScript DOM, written by `tools/save_html.sh` and meant to be edited later (not part of the published site) |

React 18 and D3 v7 are pulled from a CDN at the bottom of `index.html`; anything
else is local. Because everything is a classic script (no ES modules) and a
plain `<link>` stylesheet, opening `index.html` straight from the filesystem
works exactly like serving it.

## Preview locally

```sh
python3 -m http.server 8000     # then open http://localhost:8000
```

Double-clicking `index.html` also works; the local server is only nicer for
checking cross-page links.

## Verify it still works

```sh
tools/run_all.sh                # preflight + browser capture + all checks
```

See `tools/README.md` for what each script does and the requirements (Python 3,
Node, Chrome, Pillow). Full output lands in `tools/.out/`, which is git-ignored.
The one helper `tools/run_all.sh` does **not** run is `tools/save_html.sh`: it
writes the editable page snapshots under `saved/`, so the checks must not be able
to overwrite them.

## Where to change things

| I want to change… | Edit |
| --- | --- |
| An accent colour | `styles.css` `:root` **and** `hero.js` `BEAMS[].color` **and** `logo.js` `COLORS[]` (guarded by `tools/check_colors.py`) |
| Which accent an area gets | `styles.css` section 3 — the `[data-area="…"]` groups (guarded by `tools/check_colors.py`) |
| The dark theme's palette | `styles.css` section 1 — `[data-theme="dark"]` **and** the matching `prefers-color-scheme` block, which must carry the same values (`tools/check_css.py` compares them) |
| How a visitor gets a theme, and which one they start in | `theme.js` — the `?theme=` preview, then the stored choice, then the system, then light (behaviour guarded by `tools/check_theme.js`) |
| The brush stroke behind the section headings | run `tools/make_brush.py` — it regenerates the `--brush-stroke` token in `styles.css` |
| The highlight behind the section headings | `styles.css` section 10 (`class="brush"` on the `<h2>`s in `index.html`), or `class="highlight"` for the flat marker pen kept, unused, in section 19 |
| The green/blue/orange/yellow dots in front of the project names | `styles.css` section 9 — `.topics a::before`; the dot itself is written by the link, its colour comes from the section's area |
| Which articles are on Publications | `tools/publications.json` — add a link, then run `tools/make_publications.py`, which reads each page and fills in its picture, date, headline and teaser (nothing on the page is written by hand) |
| A wrong headline, date or teaser on Publications | write the field by hand in `tools/publications.json` — a hand-written value always wins — and re-run `tools/make_publications.py` |
| The gallery feed | `gallery.html` — add one `<article class="tile">` at the **top** of `.gallery-grid`, its `viz-<slug>.html` page and its two images; visualisations only (guarded by `tools/check_dom.py`) |
| Gallery artwork | replace `images/gallery/*.png`, or regenerate the placeholders with `tools/make_gallery.py` |
| Type scale, spacing, breakpoints | `styles.css` — sections 5 (header and navigation), 8 (page intro), 18 (breakpoints) |
| Hero copy | `HERO_TEXT` in `hero.js` (the accessible copy lives in the same string) |
| Mark timing | `DURATION` / `ORBIT_END` / `HOLD_END` in `logo.js`; the hold-frame harness reads them automatically |
| The site title text | the `<a class="site-title">` text in every page — `title.js` reads it, so the intro follows automatically |
| Header intro timing | `BLINK_HALF` / `BLINKS_BEFORE_DELETE` / `DELETE_STEP` / `BLINKS_BEFORE_REVEAL` in `title.js`; the intro takes 4.8 s, inside `tools/smoke.sh`'s 6 s capture budget |
| Portrait | replace `images/sarah-pilz.jpg`, or regenerate with `tools/make_image.py` |
| Contacts and profile links | the six `<a href>` values in `contact.html` (`#get-in-touch`); they ship as `you@example.com`, `your-handle`, `4500000000` and `XXXXXXX` placeholders |
| Which logo colour a contact chip takes | `styles.css` section 12 — the `li:nth-child(4n + n)` cycle, guarded by `tools/check_colors.py` |
| A page as the browser actually builds it, to edit by hand | run `tools/save_html.sh` — it writes the post-JS DOM of every page and every piece page into `saved/`, and keeps a snapshot you have edited unless `--force` is passed |

## Design tokens

| Token | Value | Used for |
| --- | --- | --- |
| `--background` | `#ffffff` | page, hero sheet, footer |
| `--text` | `#202124` | body copy, focus rings |
| `--muted` | `#666b73` | secondary copy, nav links |
| `--line` | `#e7e9ed` | hairline rules and borders |
| `--paint-blend` / `--paint-strength` | `multiply` / `1` (`screen` / `0.34` in the dark) | how the brush highlight meets the page, and how solid the paint is |
| `--sheet-shadow` | `rgba(32, 33, 36, 0.12)` | the hero sheet's lift off the page |
| `--dot-ring` | `rgba(32, 33, 36, 0.18)` | the inner hairline that keeps the pale accents visible as dots |
| `--hover-fill` | `#f6f7f8` | the wash under the hero button |
| `--chip-ink` | `--text` (`#101214` in the dark) | the icon inside a contact chip filled with an accent |
| `--yellow` | `#f2ff00` | visualization / Contact: link lines, brush, beam and dot |
| `--lime` | `#c2f345` | research / Publications: link lines, brush, beam and dot |
| `--orange` | `#ffa310` (CSS declares `#ffa310ed`) | coordination / About: link lines, brush, beam and dot |
| `--blue` | `#b9ffe7` | data / Gallery: link lines, brush, beam and dot |
| `--area-accent` | one of the four | set per area by `[data-area]`; everything coloured reads this |
| `--brush-stroke` | generated SVG | the paint-brush highlight behind the section headings (`tools/make_brush.py`) |
| `--content-width` | `1120px` | `.container` max width |
| `--font-display` | Konkhmer Sleokchher | headings, site title |
| `--font-body` | Inter | everything else |

The four accents are the only colour in the design, and they carry one meaning:
**a link's colour says which area of the site you are in.** Every link is drawn
with a 3 px line in its area's accent (section 3 of `styles.css`), and the same
accent paints the brush highlight behind that area's heading on the home page.
They also appear as four faint hero beams, four dots in the header mark, and the
contact chips, which fill with their accent on hover or keyboard focus (one chip
per colour, cycled along the row).

The theme is the one thing the palette does not change. The dark theme in
section 1 swaps the four neutrals (`--background`, `--text`, `--muted`, `--line`)
and the theme mechanics above, and leaves the four accents exactly as they are,
because a link's colour has to mean the same area in either theme;
`tools/check_colors.py` fails if a dark block redeclares one. The paint behind the
section headings is the one treatment that is not a straight swap: on white it
counts by `multiply`, but a solid accent band on the dark page would swallow the
near-white heading on top of it, so the dark theme screens it in as a wash
(`--paint-blend: screen` with `--paint-strength: 0.34`) in the same area colour,
and `tools/analyze.py` measures the heading in both themes to prove it stays
readable.

## Conventions

* **Styles live in `styles.css`, never inline.** A page should only carry markup.
* **Colour means area.** A page or a section declares `data-area="…"`, section 3
  of `styles.css` turns that into `--area-accent`, and every link line and brush
  highlight reads it — so no page repeats a colour and the map cannot drift.
  `tools/check_colors.py` guards the eight areas; the gallery's tiles carry no
  colour of their own, because the whole feed is the Visualization area.
* **The gallery holds visualisations only.** It lists the work from the
  Visualization area and nothing from Publications, Data or Coordination, which
  is also why those sections do not link into it. Each tile links to its own
  `viz-<slug>.html`, which links back to `gallery.html#<slug>`; the order
  (newest first), the ids and the "visualisations only" rule are guarded by
  `tools/check_dom.py`.
* **Scripts live in their own file.** `logo.js`, `title.js` and `theme.js` are
  shared, so neither the header mark, the wordmark intro nor the theme can drift
  between the pages.
* **The theme is a choice, and the choice wins.** `theme.js` reads
  `?theme=dark|light` (a one-page preview, never stored), then the visitor's
  stored choice, then the operating system, then light, and writes the answer to
  `<html data-theme>` from `<head>` — before the body exists — so a dark page can
  never flash white first. The stylesheet carries the same order:
  `[data-theme="dark"]` for a choice, and a `prefers-color-scheme` block that
  steps aside as soon as one is stored, which is the only route a browser takes
  without JavaScript. `tools/check_theme.js` runs `theme.js` against a stub of
  the DOM it touches and holds every one of those decisions, `tools/check_css.py`
  fails if the two dark token blocks drift apart, and `tools/analyze.py` keeps
  the dark palette honest at the pixel level.
* **The header markup is duplicated across the pages** (a static site has no
  template), so keep the `<nav class="navigation">` blocks in sync —
  `tools/check_dom.py` compares the navs of every page and fails if one
  drifts.
* **The contact icons are inline SVG.** Each `<a class="contact-link">` carries
  one 24 × 24 icon drawn with `stroke="currentColor"`, so `styles.css` alone
  decides the colour a chip takes; the markup only supplies the link and an
  `aria-label`. `tools/check_dom.py` guards the six links and
  `tools/check_colors.py` the accent cycle.
* **Motion is optional.** `logo.js`, `title.js` and `hero.js` all check
  `prefers-reduced-motion: reduce` and show the finished state immediately.
  `title.js` also derives its text from the markup it finds, so a visitor
  without JavaScript sees the settled header too.
* **Every tile in the publications feed comes from one link.**
  `publications.html` is generated between two markers by
  `tools/make_publications.py` from the links in `tools/publications.json`: the
  script reads each article's own metadata (`og:title`, `og:description`,
  `og:image`, `article:published_time`) and downloads the preview picture, so a
  headline is never re-typed and cannot drift from the piece it links to. A
  hand-written field in the JSON wins over the page, and `--check` — which
  `tools/run_all.sh` runs — fails when the page no longer matches the list. The
  feed still ships as plain markup: no JavaScript, no request at load time,
  nothing to build.
* **The highlight behind the section headings is kept in two versions.**
  `styles.css` section 10 paints the brush (`class="brush"` on the `<h2>`s);
  section 19 keeps the flat marker pen that came before it, unused and
  documented. `tools/check_css.py` fails if the marker block disappears, and
  also if a page starts using its class — the brush and the tint must never land
  on the same heading.
* **A clickable project name says so twice:** the 3 px link line in the area's
  accent (section 3) and the little logo dot in front of it (section 9). An
  option with no dot under it is not a link.
* **The portrait is round and belongs to the heading.** It sits in the page
  intro beside the "About" title (`.page-intro-split`), top-aligned with it, and
  the roundness is not taken on trust: `tools/analyze.py` proves it by checking
  that the corners of the picture's box are page white.
* **Accessibility:** skip link, `:focus-visible` outlines, a visually hidden
  copy of the typing line, `aria-hidden` on decorative SVG, alt text on the portrait.

 
