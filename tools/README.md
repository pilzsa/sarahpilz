# tools/ — development and verification scripts

These are the scripts used to build, inspect and verify the site. **They are not
part of the published page** — nothing under `tools/` is linked from any page, so
the site stays a plain static folder you can open or upload as-is.

Everything here runs **from any directory**: each script finds the repo root
from its own location (`Path(__file__).resolve().parents[1]` in Python,
`cd "$(dirname "$0")/.."` in shell). Output goes to `tools/.out/`, which is
git-ignored, so running the checks never dirties the working tree.

## Requirements

| Tool | Used for | Notes |
| --- | --- | --- |
| `python3` | all `*.py` scripts | stdlib only, except Pillow |
| `Pillow` (`python3 -m pip install Pillow`) | `make_image.py`, `make_gallery.py`, `make_publications.py`, `analyze.py` | image resize, drawing, download + pixel analysis |
| `node` | `check_js.js`, `check_theme.js` | JS syntax checking via `vm.Script`, and running `theme.js` against a stub DOM |
| `google-chrome-stable` (or set `$CHROME`) | `smoke.sh`, `hold.sh`, `save_html.sh` | headless DOM dump + screenshots |

## One command

```sh
tools/run_all.sh          # preflight + smoke + hold frame + all checks
```

Exit code is `0` only when every check passes. Individual pieces:

```sh
tools/smoke.sh            # serve, dump the DOM of every page, capture the
                          # light and dark screenshots
tools/hold.sh             # capture the logo at its frozen "hold" frame
tools/check_dom.py        # assertions over the served DOM + source files
tools/check_css.py        # stylesheet sanity: braces, selectors, var() usage
tools/check_colors.py     # accents agree across CSS/hero.js/logo.js; area map
tools/check_html.py       # tag balance in the HTML
tools/check_js.js         # syntax-check the JS files and inline scripts
tools/check_theme.js      # run theme.js against a stub DOM; check its decisions
tools/analyze.py          # pixel-level check of the captured screenshots
tools/extract.py          # print selectors / inline blocks from files
tools/make_image.py       # regenerate images/sarah-pilz.jpg from the original
tools/make_gallery.py     # regenerate the gallery placeholder art
tools/make_brush.py       # regenerate the --brush-stroke highlight token
tools/make_publications.py # rebuild the publications feed from its list of links
tools/save_html.sh        # save every page + piece page as an editable snapshot
tools/hold_frame.py       # build the phase-locked harness page (used by hold.sh)
```

## What each script is for

### `smoke.sh` — does the page actually build and render?
Serves the repo with `python3 -m http.server`, then uses headless Chrome with
`--virtual-time-budget` to (a) `--dump-dom` every page after its scripts have
run, and (b) screenshot the home page, About, Publications, the gallery and a
piece page at desktop and mobile widths. The budget is 6 s, which is longer than
every animation on the page — the hero types its line in ~3 s and the wordmark
intro in `title.js` takes 4.8 s — so the captures show the settled page that the
checks assert against. Writes to `tools/.out/`:

* `v_index.html`, `v_about.html`, `v_publications.html`, `v_gallery.html`,
  `v_viz.html` — post-JS DOM, the input for `check_dom.py`
* `v_index_desktop.png`, `v_index_mobile.png`, `v_about_desktop.png`,
  `v_about_mobile.png`, `v_publications_desktop.png`,
  `v_publications_mobile.png`, `v_gallery_desktop.png`, `v_gallery_mobile.png`,
  `v_viz_desktop.png` — the input for `analyze.py`
* `v_index_dark.html`, `v_index_dark_system.html` and the `*_dark_*.png`
  screenshots — the dark theme by both of its doors: `theme.js`'s `?theme=dark`
  preview (deterministic and free of any browser preference, so the screenshots
  and their pixel checks come from here) and
  `--blink-settings=preferredColorScheme=0`, which is the page a dark-mode
  visitor with no stored choice gets and the only capture where the theme comes
  from the system rather than from the URL. Neither can capture the stylesheet's
  own `prefers-color-scheme` block, because every served page runs `theme.js` in
  `<head>` and the attribute is settled before the paint: that block is held to
  `[data-theme="dark"]` value for value by `check_css.py` instead, while
  `check_dom.py` reads the two dark dumps and `analyze.py` the dark screenshots

### `hold.sh` + `hold_frame.py` — the animated mark, frozen
The header mark is 5.2 s of animation, so a screenshot catches it in a random
phase. `hold_frame.py` writes a throwaway harness page that stubs
`requestAnimationFrame` to deliver exactly two frames (t=0, then t at the middle
of the mark's hold window — 0.87 of the duration with the current constants),
which is the "hold" moment where the dots sit on the square's
corners and all four sides are fully drawn. `hold.sh` copies the real `logo.js`
next to it and captures both the DOM (`hold_dom.html`) and a scale-factor-8
screenshot (`hold_logo.png`) of just the mark.

This is the only way to assert "the logo resolves into a square" without
eyeballing a video, and it exercises the *shipped* `logo.js` rather than a copy.

### `check_dom.py` — the main assertion suite
Runs 390 checks over the captured DOM and the source files (a check is generated
for every link, every `id` and every page, so the total moves with the markup):

* files exist, HTML tags balance, no absolute `/home/...` paths leaked into pages
* every page's source: shared stylesheet, scripts and the `color-scheme` meta,
  the shared header markup, and every copy of the nav — and of the theme toggle —
  compared against each other
* the `contact.html` icon row: six links — one per channel, each a real
  destination — with six distinct `aria-label`s, six icons painted with
  `stroke="currentColor"` and six icons hidden from screen readers
* the gallery feed: one tile per visualisation, each with an id, an image with
  alt text, an area and a year, and a link to its piece page — which must link
  back to `gallery.html#<id>`. The tiles must be newest first, must all be
  visualisations, must carry no colour of their own, and must be exactly the
  pieces listed in the home page's Visualization section
* the sections that are not visualisations — Research, Data, Coordination and
  `publications.html` — must not link into the gallery at all, and no area
  legend may come back to the gallery
* every `id` a page declares survives into its rendered DOM
* every local `href`/`src` resolves to a real file, and every `#anchor` used in
  a cross-page link exists as an `id` in the target page

The source checks cover every page. The served-DOM checks below cover the pages
`smoke.sh` captures — `index.html`, `about.html`, `publications.html` and
`gallery.html`; the others carry the same shared header scripts and no
page-specific JavaScript.

* the served DOM really contains: 4 `<circle>` + 4 sides in the mark, the
  cropped `viewBox="5 5 34 34"`, the hero beams SVG with 4 `<rect>`, the typed
  hero line, and the nav anchors
* the gallery's served DOM carries one tile per piece, each id intact, and the
  same nav as the source
* the publications feed is checked tile by tile **against
  `tools/publications.json`** — same ids in the same order, the same headline
  text, the same date in its `<time>`, the same outlet, the same teaser and the
  same picture file (which must exist on disk) — so a page that was hand-edited
  or not rebuilt after a link was added fails here, in either direction
* the wordmark intro ran to completion and left the header static: the settled
  text is `_square one`, with the caret, the invisible width-holder and the
  screen-reader copy in place and no `is-off` class left behind
* the theme on every captured page: `<html data-theme="light">` and a toggle that
  `theme.js` has revealed and labelled `aria-pressed="false"` — and, in the
  `?theme=dark` dump, `data-theme="dark"` with `aria-pressed="true"` while the
  mark's four circles, the typed hero line and the nav are all unchanged — and in
  the dark-system dump, the same dark theme arrived at from the browser's own
  preference with nothing stored and no query string
* the phase-locked hold frame has `stroke-dashoffset="0.00"` on all four sides
  and dots exactly on `(10,10) (34,10) (34,34) (10,34)`
* `logo.js`, `title.js` and `hero.js` parse under `node --check`

### `check_css.py` — the stylesheet is complete
Balanced braces, every `var(--token)` used has a declaration — in `:root` or
scoped to a component, as the contact chips do with `--accent` — and every class
used in any page (the home page, the three area pages, the gallery and one page
per visualisation) has a rule in `styles.css`. The page list is globbed, so a
new piece page is covered as soon as it exists. It also keeps the two highlights
apart: the marker pen in section 19 is a reference, so the block must stay in the
stylesheet **and** no page may use its class — a heading wearing a tint and a
brush stroke at once is exactly the sort of thing a screenshot does not catch.
It also holds the dark theme's two token blocks — `[data-theme="dark"]` and the
`prefers-color-scheme` copy a visitor with no stored choice inherits — to the same
values and to a light default each. No screenshot of a served page can tell the
two apart: `theme.js` settles the attribute before the paint, so the media query
never gets to decide one on its own — which is exactly why the comparison is
worth having.

### `check_colors.py` — one palette, three files
The four accent colours exist in `styles.css` (`:root`), `hero.js`
(`BEAMS[].color`, the D3 beam gradients) and `logo.js` (`COLORS[]`). This
script extracts all three sets and fails if they disagree. The CSS `--orange`
is `#ffa310ed` (with alpha) while the JS uses the opaque `#ffa310`, so
comparisons are made on the first six hex digits. It also checks the contact
chips' cycle in `styles.css` (`li:nth-child(4n + 1..4)` → yellow, lime, orange,
blue) and that their hover rule reads `var(--accent)`, so the row cannot lose
one of the logo colours. It also keeps the four accents out of the dark theme:
the dark token blocks may swap the neutrals and the theme mechanics, but a
redeclared accent would break the map of the site that the palette is.

It also guards the **area map**, which is what makes the palette mean something:
the eight values the pages use must match the `[data-area="…"]` groups in
section 3 of `styles.css` (`research`/`publications` → lime, `data`/`gallery` →
blue, `coordination`/`about` → orange, `visualization`/`contact` → yellow),
every area a page or section declares must have a colour, and no mapped area may
go unused.

### `check_html.py` — strict tag balancing
Walks the HTML with `html.parser` and reports unclosed or mismatched tags,
including SVG void elements. Catches the "I deleted a closing `</div>`" class of
mistake that browsers silently forgive.

### `check_js.js` — syntax only, no execution
Reads every `<script>` block, skips the `src=` ones, and compiles the rest with
`new vm.Script(...)`. Also checks the standalone `.js` files parse. Fastest way
to catch a typo in `logo.js`/`title.js`/`hero.js` before opening a browser.

### `check_theme.js` — what theme.js decides, with no browser
`theme.js` touches only `<html>`, one button, `localStorage` and `matchMedia`, so
this runs the real file with node's `vm` against a hand-rolled stub of those four
and reads the result back: the order of preference (`?theme=` preview, then the
stored choice, then the system, then light), the system being followed only while
nothing is stored, the theme being settled while the page is still **loading**
(the reason the script lives in `<head>` and cannot flash white), and a store that
throws not stopping the page. `theme.js` is `node --check`ed with the other
scripts by `check_dom.py`.

### `analyze.py` — pixel-level proof
Classifies pixels of a screenshot by nearest accent colour, with a brightness
guard so anti-aliased white background is not mistaken for a pale accent, then
prints each accent's bounding box in CSS pixels. Used to confirm the hold frame
really shows four accents occupying the four sides of the square, that every
page's header crop contains all four accents, and that the gallery below its
header shows the gallery's own blue and no lime, orange or yellow — the
pixel-level half of "visualisations only, nothing differentiated inside". The
dark captures (`*_dark_*.png`, from `smoke.sh`) are held to the same rules and to
two of their own: the same corner of the same page must report the dark page
colour instead of white, and the brush behind the first section heading must be a
**wash** in the dark — the crop may hold none of the raw accent — with the
heading's own near-white ink still on top of it, or the heading would be
unreadable. On white the same crop must be a solid band of that accent with the
near-black heading on it, so the two themes are measured side by side.

Two checks work on shape rather than colour:

* **the round portrait on About.** It takes the box of everything that is not
  page white in the top right of the intro and looks at the four corners of that
  box. A rectangular picture fills its box corner to corner; a circle does not,
  so white corners are the proof that the CSS clip is doing its job (and the
  hairline border, being `--line` grey, is deliberately not counted as ink).
  Tested against drawn shapes: a circle reports 0 inked corners, a square 4.
* **the publications preview pictures.** Below the header it counts the distinct
  colours in the region: a page of type and hairlines brings a few hundred, a
  photograph tens of thousands, so a feed whose images failed to load cannot
  pass.

### `extract.py` — read things out of the built files
Prints the selectors defined in a stylesheet, or the inline `<style>`/`<script>`
blocks of an HTML file. Handy when reviewing what a page actually ships; it is
what was used to confirm no CSS rule was lost when the inline styles moved into
`styles.css`.

### `make_image.py` — regenerate the portrait
Re-creates `images/sarah-pilz.jpg` (900 px wide, JPEG q82, progressive) from the
original photo. Run only when the original changes; the committed file is the
source of truth for the site.

### `make_gallery.py` — regenerate the placeholder art
Draws the four gallery images — a square tile and a wide version for each of the
two visualisations — with Pillow: a line chart for UK Ventilator Challenge and a
lobby network for Big Tech Lobby Writes EU AI Act. Every coordinate is a fixed
formula, never a random number, so re-running it rewrites byte-identical files
and the screenshots in `tools/.out/` stay valid. The art is deliberately neutral
(ink, greys and the gallery's blue) so that nothing in the feed suggests one of
the other three areas — which `analyze.py` then checks. Run it only when the
placeholders themselves should change; real screenshots can simply replace the
files at the same paths.

### `make_brush.py` — regenerate the highlight stroke
The paint-brush highlight behind the four section headings on the home page is a
masked SVG, so its whole shape lives in the `--brush-stroke` custom property of
`styles.css`. This script generates that shape — a tapered sweep with bristle
streaks knocked out of it by `fill-rule="evenodd"`, plus a faint second pass
under the tail — and rewrites the declaration in place, printing the size
change. The value is far too long to hand-edit, so the committed token is the
source of truth for the page and this script is how it is reproduced.

### `make_publications.py` — build the publications feed from links
`publications.html` shows one card per article — preview picture, date, outlet,
headline, teaser — and every card links to the piece where it was published.
The only hand-written thing is the list of links in `tools/publications.json`;
this script does the rest:

```sh
python3 tools/make_publications.py            # fetch what is missing, rebuild
python3 tools/make_publications.py --refresh  # read every link again
python3 tools/make_publications.py --offline  # fetch nothing, rebuild from the file
python3 tools/make_publications.py --check    # write nothing; exit 1 when the page
                                              # is not what the script would write
```

For each link it reads the page once and takes what the page says about itself —
`og:title`, `og:description`, `og:site_name`, `og:image`, `article:published_time`
and friends, with `itemprop="datePublished"`, `<time datetime>` and `<title>` as
fallbacks — then downloads the preview picture into `images/publications/` and
re-saves it as a 1200 px-wide progressive JPEG (a picture it cannot read, an SVG
logo say, is simply left off the card). A field already written by hand in the
JSON is never overwritten, so a wrong date or a too-long teaser can be fixed
there and it stays fixed; `--refresh` is the way to ask for the page's version
again. Cards are written between the `publications:start` / `publications:end`
markers, newest first, by date.

`--check` is what `tools/run_all.sh` runs: it renders in memory, touches neither
the network nor the disk, and fails when `publications.html` or
`tools/publications.json` is not what a real run would write — so a hand-edited
tile, or a link added without re-running the script, is caught by the suite. The
feed itself ships as plain markup: no JavaScript, no request at load time.

Two notes on the shipped list: it currently holds five real, published pieces as
a demonstration, and the two project pages (`foreverpollution.eu`) state no
publication date, so their cards carry the outlet only.

### `save_html.sh` — editable snapshots of every page
The served DOM is the only place the header mark, the wordmark intro, the theme
and the hero exist, because all four are drawn by JavaScript. `smoke.sh` dumps
that DOM into `tools/.out/`, but those dumps are git-ignored build output for the
checks. `save_html.sh` writes the same thing — for the five section pages and
every `viz-*.html`, discovered with a glob — into **`saved/`** at the repo root,
which is not ignored and is meant to be read, edited and kept:

```sh
tools/save_html.sh            # save every page; keep a snapshot you edited
tools/save_html.sh --force    # rebuild snapshots that have changed
tools/save_html.sh --raw      # Chrome's DOM exactly, without <base href="../">
```

Each snapshot carries `<base href="../">` right after `<head>`, so its relative
links — `styles.css`, `images/`, the four scripts and the other pages — resolve
against the repo root and opening the file looks like the page it came from;
`--raw` leaves Chrome's output untouched instead. A file that already exists and
would change is **kept**, not overwritten, so re-running the script cannot
silently throw away an edit — `--force` is how a snapshot is rebuilt from the
served page. So that "unchanged" means "the page has not changed" rather than
"the animation happened to line up", the comparison blanks out the two live
animations a dump can never reproduce — the header mark, caught mid-orbit on an
arbitrary frame, and the hero beam background on `index.html`, whose `d3.timer`
never stops — and compares everything else byte-for-byte. It is deliberately
**not** part of `tools/run_all.sh`: the checks must not be able to rewrite the
files you are editing.

## Not kept here

Two one-shot scripts from the redesign were deliberately **not** moved into the
repo, because they were migrations whose job is done and re-running them would
damage the current files:

* `extract_logo.py` — pulled the inline header-mark script out of `index.html`
  into `logo.js` and replaced it with a `<script src="logo.js">` tag.
* `clean_logo.py` — fixed up the comment and indentation of the extracted file.

Both were throwaway scripts that lived outside the repo and were never
committed, so nothing is lost: their effect is captured by the current files —
`logo.js` is now the single maintained copy of the mark and `index.html` simply
loads it.
