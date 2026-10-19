/* Header wordmark intro shared by index.html and about.html.
 *
 * The finished title is "_square one". On load the underscore blinks like a
 * caret, then -- as if the Delete key were held -- the underscore goes solid
 * and "square one" disappears one character at a time from the left, leaving
 * the blinking underscore alone on the line. After three blinks the whole
 * wordmark returns in one step and the header stays static.
 *
 * The pages ship the plain text, so a visitor without JavaScript (or with
 * reduced motion) sees the settled header. This script keeps an invisible copy
 * of the finished title in the flow to hold the wordmark's width, and lays a
 * live copy over it: the caret plus the characters still on screen. Because
 * the width comes from the copy underneath, neither the centred title nor the
 * caret moves while the intro runs.
 *
 * A classic script, like logo.js, so opening the pages from the filesystem
 * still works.
 */
(function () {
  var title = document.querySelector(".site-title");
  if (!title) return;

  /* The first character of the title is the caret, the rest is the wordmark. */
  var TEXT = title.textContent.trim();
  if (!TEXT) return;
  var CARET = TEXT.charAt(0);
  var LABEL = TEXT.slice(1);

  /* Timing. One blink is an off/on pair; the whole intro ends at
     (BLINKS_BEFORE_DELETE + BLINKS_BEFORE_REVEAL) * 2 * BLINK_HALF
     + LABEL.length * DELETE_STEP = 4800 ms. tools/smoke.sh waits 6 s before it
     captures the DOM and the screenshots, so what it records is the settled
     header, not a frame from the middle of the intro. */
  var BLINK_HALF = 350;
  var BLINKS_BEFORE_DELETE = 3;
  var DELETE_STEP = 60;
  var BLINKS_BEFORE_REVEAL = 3;

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  function span(className, text) {
    var node = document.createElement("span");
    node.className = className;
    node.setAttribute("aria-hidden", "true");
    node.textContent = text;
    return node;
  }

  var fitter = span("site-title-fitter", TEXT);

  var caret = span("site-title-caret", CARET);
  var body = span("site-title-body", LABEL);
  var live = span("site-title-live", "");
  live.appendChild(caret);
  live.appendChild(body);

  /* Both copies are decorative, so screen readers get the plain text. */
  var echo = document.createElement("span");
  echo.className = "visually-hidden";
  echo.textContent = TEXT;

  title.textContent = "";
  title.appendChild(fitter);
  title.appendChild(live);
  title.appendChild(echo);

  function after(delay, action) {
    window.setTimeout(action, delay);
  }

  function showCaret() {
    caret.classList.remove("is-off");
  }

  /* Blink the caret `count` times starting `delay` ms from now; the caret is
     visible when the phase begins, so the wordmark is never missing its
     underscore at load. Returns the delay at which the last blink ends. */
  function blink(count, delay) {
    for (var i = 0; i < count; i++) {
      (function (start) {
        after(start + BLINK_HALF, function () { caret.classList.add("is-off"); });
        after(start + 2 * BLINK_HALF, showCaret);
      })(delay + i * 2 * BLINK_HALF);
    }
    return delay + count * 2 * BLINK_HALF;
  }

  /* 1. The finished wordmark sits on screen while the underscore blinks. */
  var at = blink(BLINKS_BEFORE_DELETE, 0);

  /* 2. Delete: the underscore goes solid and the wordmark is eaten from the
        left, one character per step, with the rest closing up behind it. */
  after(at, showCaret);
  for (var removed = 1; removed <= LABEL.length; removed++) {
    (function (count) {
      after(at + count * DELETE_STEP, function () {
        body.textContent = LABEL.slice(count);
      });
    })(removed);
  }
  at += LABEL.length * DELETE_STEP;

  /* 3. Three blinks of the lone underscore ... */
  at = blink(BLINKS_BEFORE_REVEAL, at);

  /* 4. ... and then the whole wordmark returns at once and stays put. */
  after(at, function () {
    body.textContent = LABEL;
    showCaret();
  });
})();
