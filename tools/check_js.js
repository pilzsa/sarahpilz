#!/usr/bin/env node
/*
 * Syntax-check the site's JavaScript without executing any of it.
 *
 * Compiles every .js file in the repo root and every inline <script> block in
 * the pages with `new vm.Script()`. That catches typos and stray braces in
 * logo.js / hero.js in about a second, without needing a browser.
 *
 * Usage (from anywhere):  node tools/check_js.js
 * Exit code 0 = everything parses, 1 = at least one syntax error.
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const SCRIPT_RE = /<script\b([^>]*)>([\s\S]*?)<\/script>/g;

let failures = 0;

function compile(label, code) {
  try {
    new vm.Script(code, { filename: label });
    console.log("PASS  " + label + " (" + code.trim().length + " chars)");
    return true;
  } catch (err) {
    failures += 1;
    console.log("FAIL  " + label + " -> " + err.message);
    return false;
  }
}

function checkFile(name) {
  const full = path.join(ROOT, name);
  const code = fs.readFileSync(full, "utf8");
  return compile(name, code);
}

function checkInline(name) {
  const html = fs.readFileSync(path.join(ROOT, name), "utf8");
  let match;
  let index = 0;
  let ok = true;
  while ((match = SCRIPT_RE.exec(html)) !== null) {
    const attrs = match[1];
    const code = match[2];
    const label = name + " inline script #" + index++;
    if (/\bsrc\s*=/.test(attrs)) {
      console.log("SKIP  " + label + " (external src=" + attrs.trim() + ")");
      continue;
    }
    if (!code.trim()) {
      continue;
    }
    ok = compile(label, code) && ok;
  }
  return ok;
}

const jsFiles = fs.readdirSync(ROOT).filter((n) => n.endsWith(".js")).sort();
const htmlFiles = fs.readdirSync(ROOT).filter((n) => n.endsWith(".html")).sort();

console.log("== standalone scripts ==");
jsFiles.forEach(checkFile);

console.log("\n== inline scripts ==");
htmlFiles.forEach(checkInline);

console.log();
if (failures) {
  console.log("check_js: " + failures + " syntax error(s)");
  process.exit(1);
}
console.log("check_js: all JavaScript parses");
