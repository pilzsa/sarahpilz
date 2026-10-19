#!/usr/bin/env node
/* Behavioural check of theme.js -- the light/dark toggle's decisions, with no
 * browser in sight.
 *
 * theme.js is a classic IIFE that touches only <html>, one button, localStorage
 * and matchMedia, so a small hand-rolled stub of those four is enough to run the
 * real file and read the result back. Covered here:
 *
 *   * the order of preference: ?theme= preview, then the stored choice, then the
 *     system, then light;
 *   * the system is followed only while nothing has been stored, so switching
 *     the machine to dark never overrides a decision made on the page;
 *   * the theme is settled before the body exists, so the page cannot flash
 *     white and then turn dark (the head script's whole reason for being);
 *   * a store that throws (private mode, some extensions) does not stop the
 *     page, and the button still works for that visit.
 *
 * Usage:  node tools/check_theme.js
 * Exit code 0 = every behaviour holds, 1 = something broke.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.dirname(__dirname);
const SOURCE = fs.readFileSync(path.join(ROOT, "theme.js"), "utf8");
const KEY = "theme";

let passes = 0;
const fails = [];

function check(name, ok, detail) {
  if (ok) {
    passes += 1;
    console.log("PASS  " + name);
    return;
  }
  fails.push(name);
  console.log("FAIL  " + name + (detail === undefined ? "" : " :: " + JSON.stringify(detail)));
}

/* One page: the parts of the DOM theme.js uses, and nothing else. `loading` is
   the script running from <head>, before the body -- and therefore before the
   button -- exists. */
function page(settings) {
  const options = settings || {};
  const attributes = {};
  const values = Object.assign({}, options.stored);
  const clicks = [];
  const changes = [];
  const boot = [];
  const media = {
    matches: Boolean(options.systemDark),
    addEventListener(type, fn) { if (type === "change") changes.push(fn); },
  };
  let ready = !options.loading;

  const root = {
    getAttribute(name) { return name in attributes ? attributes[name] : null; },
    setAttribute(name, value) { attributes[name] = String(value); },
  };

  const button = {
    hidden: true,
    attributes: {},
    setAttribute(name, value) { this.attributes[name] = String(value); },
    addEventListener(type, fn) { if (type === "click") clicks.push(fn); },
  };

  const document = {
    get readyState() { return ready ? "complete" : "loading"; },
    documentElement: root,
    querySelector(selector) {
      return !options.noButton && ready && selector === ".theme-toggle" ? button : null;
    },
    addEventListener(type, fn) { if (type === "DOMContentLoaded") boot.push(fn); },
  };

  const sandbox = {
    window: {
      location: { search: options.search || "" },
      localStorage: {
        getItem(key) {
          if (options.broken) throw new Error("blocked");
          return key in values ? values[key] : null;
        },
        setItem(key, value) {
          if (options.broken) throw new Error("blocked");
          values[key] = String(value);
        },
      },
      matchMedia: options.noMedia ? undefined : function () { return media; },
    },
    document: document,
  };

  vm.createContext(sandbox);
  vm.runInContext(SOURCE, sandbox, { filename: "theme.js" });

  return {
    theme() { return root.getAttribute("data-theme"); },
    pressed() { return button.attributes["aria-pressed"] || null; },
    revealed() { return button.hidden === false; },
    stored() { return KEY in values ? values[KEY] : null; },
    click() { clicks.forEach(function (fn) { fn({ type: "click" }); }); },
    system(matches) { media.matches = matches; changes.forEach(function (fn) { fn({ matches: matches }); }); },
    open() { ready = true; boot.splice(0).forEach(function (fn) { fn(); }); },
  };
}

console.log("== before the body exists (the head script) ==");
const head = page({ loading: true });
check("the theme is settled while the page is still loading", head.theme() === "light", head.theme());
check("the button stays hidden until the DOM is ready", head.revealed() === false);
head.open();
check("the DOMContentLoaded pass reveals and labels the button",
      head.revealed() && head.pressed() === "false", head.pressed());

console.log();
console.log("== the starting theme ==");
check("a first visit on a light system starts light", page({}).theme() === "light");
check("a first visit on a dark system starts dark", page({ systemDark: true }).theme() === "dark");
check("a stored light choice beats a dark system",
      page({ stored: { theme: "light" }, systemDark: true }).theme() === "light");
check("a stored dark choice beats a light system",
      page({ stored: { theme: "dark" } }).theme() === "dark");
check("a nonsense value in the store is ignored", page({ stored: { theme: "blue" } }).theme() === "light");

console.log();
console.log("== ?theme= previews one page ==");
const preview = page({ search: "?theme=dark" });
check("?theme=dark turns the page dark", preview.theme() === "dark", preview.theme());
check("?theme=dark is never stored", preview.stored() === null, preview.stored());
preview.system(false);
check("a preview does not follow the system either", preview.theme() === "dark");
check("?theme=light beats a stored dark choice",
      page({ search: "?theme=light", stored: { theme: "dark" } }).theme() === "light");
check("another query string is ignored", page({ search: "?page=2" }).theme() === "light");

console.log();
console.log("== the button ==");
const toggled = page({});
toggled.click();
check("pressing it turns the page dark", toggled.theme() === "dark", toggled.theme());
check("pressing it stores the theme to wear next time", toggled.stored() === "dark", toggled.stored());
check("aria-pressed reports the dark theme", toggled.pressed() === "true", toggled.pressed());
toggled.click();
check("pressing it again returns to light", toggled.theme() === "light");
check("the stored choice follows it back", toggled.stored() === "light", toggled.stored());
check("aria-pressed reports the light theme", toggled.pressed() === "false", toggled.pressed());
check("a page without the button still gets a theme", page({ noButton: true }).theme() === "light");

console.log();
console.log("== the system changes ==");
const following = page({});
following.system(true);
check("with nothing stored the page follows the system into dark", following.theme() === "dark");
following.system(false);
check("and out of it again", following.theme() === "light");
const decided = page({ stored: { theme: "light" } });
decided.system(true);
check("a stored choice ignores the system", decided.theme() === "light");

console.log();
console.log("== a store that throws ==");
const blocked = page({ broken: true });
check("the theme still applies when localStorage is blocked", blocked.theme() === "light");
blocked.click();
check("and the button still works for this page", blocked.theme() === "dark" && blocked.revealed());

console.log();
console.log("PASSED %d / %d", passes, passes + fails.length);
if (fails.length) {
  console.log("FAILURES:");
  fails.forEach(function (name) { console.log(" - " + name); });
  process.exit(1);
}
