/* Light/dark theme shared by every page.
 *
 * The palette itself lives in styles.css: the light tokens in :root, the dark
 * ones in [data-theme="dark"]. All this script does is decide which of the two
 * <html> wears, and remember the answer:
 *
 *   * ?theme=dark or ?theme=light in the address bar wins for that page. It is
 *     a preview, never stored, so a shared link cannot pin someone else's
 *     theme -- and it is the way the dark palette is captured for the pixel
 *     checks, independent of whatever preference the browser reports;
 *   * then the visitor's stored choice;
 *   * then the operating system, through the same media query the stylesheet
 *     falls back to when no choice has been made;
 *   * then light.
 *
 * A stored choice stops the page following the system, so switching the
 * machine to dark never overrides a decision made here. The button is markup in
 * every page's header; the script only reveals it (without JavaScript there is
 * nothing to toggle) and keeps it in step with <html data-theme>.
 *
 * Loaded from every page's <head>, after the stylesheet and before the body, so
 * the palette is settled before the first paint and the dark theme is never a
 * flash of white. A classic script, like logo.js and title.js, so opening the
 * pages from the filesystem still works.
 */
(function () {
  var KEY = "theme";
  var DARK = "dark";
  var LIGHT = "light";
  var PREFERS_DARK = "(prefers-color-scheme: dark)";
  var root = document.documentElement;

  /* The one-page preview in the address bar, or null. */
  function asked() {
    var match = /[?&]theme=(dark|light)\b/.exec(window.location.search || "");
    return match ? match[1] : null;
  }

  /* The stored choice, or null when the visitor has never made one. A blocked
     or full store (private mode, some extensions) is not an error here: the
     page simply follows the system instead. */
  function stored() {
    try {
      var value = window.localStorage.getItem(KEY);
      return value === DARK || value === LIGHT ? value : null;
    } catch (error) {
      return null;
    }
  }

  function system() {
    return window.matchMedia && window.matchMedia(PREFERS_DARK).matches ? DARK : LIGHT;
  }

  /* The button is markup in every page, so this only has to reveal it and say
     which theme it is currently offering. */
  function sync(theme) {
    var button = document.querySelector(".theme-toggle");
    if (!button) return;
    button.hidden = false;
    button.setAttribute("aria-pressed", theme === DARK ? "true" : "false");
  }

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    return theme;
  }

  function choose(theme) {
    apply(theme);
    try {
      window.localStorage.setItem(KEY, theme);
    } catch (error) {
      /* The choice still holds for this page, it just cannot be remembered. */
    }
    sync(theme);
  }

  function flip() {
    choose(root.getAttribute("data-theme") === DARK ? LIGHT : DARK);
  }

  function start() {
    sync(root.getAttribute("data-theme"));

    var button = document.querySelector(".theme-toggle");
    if (button) button.addEventListener("click", flip);

    var query = window.matchMedia ? window.matchMedia(PREFERS_DARK) : null;
    if (query && query.addEventListener) {
      query.addEventListener("change", function (event) {
        if (stored() || asked()) return;   /* a decision here beats the system */
        apply(event.matches ? DARK : LIGHT);
        sync(root.getAttribute("data-theme"));
      });
    }
  }

  /* Before the first paint: the preview, then the visitor's choice, then the
     system, then light -- the same order the stylesheet uses. */
  apply(asked() || stored() || system());

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
