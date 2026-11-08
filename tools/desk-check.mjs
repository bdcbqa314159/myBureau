#!/usr/bin/env node
// Does a remembered position survive the screen changing?
//
//     npx tsc && node tools/desk-check.mjs
//
// This runs the REAL static/js/desk.js in a vm with a stubbed document,
// then calls its own geometry functions. Not a copy of the arithmetic —
// a copy drifts, and drift in this file is what three of the last four
// pull requests were fixing.
//
// Two things get checked. First that the script survives being loaded at
// all, which is a smoke test worth having on its own. Then the property
// that matters: a position written at one size and read back at another
// means the same thing.

import { readFileSync } from "node:fs";
import vm from "node:vm";

// --- the smallest document that lets desk.js finish loading ----------
const nothing = { forEach() {}, length: 0 };
const el = {
  classList: { add() {}, remove() {}, contains: () => false },
  style: { setProperty() {}, getPropertyValue: () => "", removeProperty() {} },
  dataset: {},
  addEventListener() {},
  querySelector: () => null,
  querySelectorAll: () => nothing,
  getBoundingClientRect: () => ({ left: 0, top: 0, width: 0, height: 0 }),
};
const sandbox = {
  document: {
    body: { dataset: { i18n: "{}" } },
    documentElement: el,
    querySelector: () => null,
    querySelectorAll: () => nothing,
    getElementById: () => null,
    addEventListener() {},
    fonts: { ready: Promise.resolve() },
  },
  window: {
    addEventListener() {},
    matchMedia: () => ({ matches: false, addEventListener() {} }),
    setTimeout: () => 0,
    clearTimeout() {},
    getComputedStyle: () => ({ backgroundImage: "none" }),
  },
  location: { pathname: "/da/" },
  sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  Promise, JSON, Math, Object, Number, Date, WeakMap, WeakSet, Map, Set,
  console, URL,
};
sandbox.globalThis = sandbox;

const ctx = vm.createContext(sandbox);
let loaded = true;
try {
  vm.runInContext(readFileSync("static/js/desk.js", "utf8"), ctx);
} catch (e) {
  loaded = false;
  console.log(`  FAIL  desk.js threw while loading: ${e.message}`);
}

const { field, asFraction, asPixels } = ctx;
if (loaded && (!field || !asFraction || !asPixels)) {
  console.log("  FAIL  the geometry functions are not reachable — did they stop being declarations?");
  process.exit(1);
}

// --- the screens an icon has to survive moving between ---------------
const SCREENS = {
  "laptop 1440x900":      { width: 1440, height: 900, ceiling: 64 },
  "desktop 2560x1440":    { width: 2560, height: 1440, ceiling: 64 },
  "phone 390x844":        { width: 390, height: 844, ceiling: 96 },
  "phone sideways 844x390": { width: 844, height: 390, ceiling: 96 },
  "narrow window 520x700":  { width: 520, height: 700, ceiling: 96 },
};
const ICON = { w: 160, h: 180 };
const PHONE_ICON = { w: 96, h: 120 };

const put = (screen, size, left, top) => {
  const f = field(screen, screen.ceiling, size.w, size.h);
  return { fx: asFraction(left, f.x0, f.x1), fy: asFraction(top, f.y0, f.y1) };
};
const get = (screen, size, spot) => {
  const f = field(screen, screen.ceiling, size.w, size.h);
  return { left: asPixels(spot.fx, f.x0, f.x1), top: asPixels(spot.fy, f.y0, f.y1), f };
};

let failed = 0;
const check = (what, held, detail = "") => {
  if (!held) failed += 1;
  console.log(`  ${held ? "ok  " : "FAIL"}  ${what}${detail ? "   " + detail : ""}`);
};

console.log("\n  desk.js loads without a DOM:");
check("no exception at load", loaded);

console.log("\n  a position is never left outside the placeable area:");
for (const [fromName, from] of Object.entries(SCREENS)) {
  for (const [toName, to] of Object.entries(SCREENS)) {
    if (from === to) continue;
    const fromSize = from.width <= 640 ? PHONE_ICON : ICON;
    const toSize = to.width <= 640 ? PHONE_ICON : ICON;
    let worst = null;
    // nine places a person might drop something, corners included
    for (const px of [0, 0.5, 1]) for (const py of [0, 0.5, 1]) {
      const f0 = field(from, from.ceiling, fromSize.w, fromSize.h);
      // worked out here rather than with asPixels: a test must not build
      // its inputs out of the thing it is testing
      const spot = put(from, fromSize,
                       f0.x0 + px * (f0.x1 - f0.x0),
                       f0.y0 + py * (f0.y1 - f0.y0));
      const { left, top, f } = get(to, toSize, spot);
      const inside = left >= f.x0 - 0.001 && left <= f.x1 + 0.001 &&
                     top >= f.y0 - 0.001 && top <= f.y1 + 0.001;
      if (!inside) worst = { px, py, left, top, f };
    }
    check(`${fromName.padEnd(22)} -> ${toName}`, worst === null,
          worst ? `(${worst.px},${worst.py}) landed at ${worst.left.toFixed(0)},${worst.top.toFixed(0)}` : "");
  }
}

console.log("\n  the corners a person actually means:");
const laptop = SCREENS["laptop 1440x900"], phone = SCREENS["phone 390x844"];
const lf = field(laptop, laptop.ceiling, ICON.w, ICON.h);
const bottomRight = put(laptop, ICON, lf.x1, lf.y1);
const topLeft = put(laptop, ICON, lf.x0, lf.y0);
const pr = get(phone, PHONE_ICON, bottomRight), pl = get(phone, PHONE_ICON, topLeft);
check("bottom-right on a laptop is bottom-right on a phone",
      Math.abs(pr.left - pr.f.x1) < 0.001 && Math.abs(pr.top - pr.f.y1) < 0.001,
      `${pr.left.toFixed(0)},${pr.top.toFixed(0)} of ${pr.f.x1.toFixed(0)},${pr.f.y1.toFixed(0)}`);
check("top-left stays top-left",
      Math.abs(pl.left - pl.f.x0) < 0.001 && Math.abs(pl.top - pl.f.y0) < 0.001);

console.log("\n  reading and re-writing does not drift:");
let spot = put(laptop, ICON, 900, 400);
for (let i = 0; i < 20; i += 1) {
  const screen = i % 2 ? phone : laptop;
  const size = i % 2 ? PHONE_ICON : ICON;
  const { left, top } = get(screen, size, spot);
  spot = put(screen, size, left, top);
}
const end = get(laptop, ICON, spot);
const first = get(laptop, ICON, put(laptop, ICON, 900, 400));
check("twenty rotations later it is where it started",
      Math.abs(end.left - first.left) < 0.5 && Math.abs(end.top - first.top) < 0.5,
      `${end.left.toFixed(1)},${end.top.toFixed(1)} vs ${first.left.toFixed(1)},${first.top.toFixed(1)}`);

console.log("\n  a desk too small to hold the icon does not produce NaN:");
const tiny = { width: 80, height: 80, ceiling: 96 };
const t = get(tiny, ICON, { fx: 1, fy: 1 });
check("stays a number", Number.isFinite(t.left) && Number.isFinite(t.top),
      `${t.left}, ${t.top}`);


// --- a translation blob that does not parse --------------------------
// The strings are read at MODULE SCOPE, so a blob that throws takes the
// whole file with it: no drag, no windows, every control dead and
// nothing on screen saying why. From outside that is indistinguishable
// from a dead button, which is the hardest kind of bug to report.
//
// The blob is assembled by string concatenation in base.html — values
// go through json_encode, keys do not — so this is reachable rather
// than theoretical. What is asserted is that the file still LOADS and
// still finishes: an empty string table is survivable, a dead script
// is not.
console.log("\n  a translation blob that does not parse:");
for (const [what, blob] of [
  ["torn off halfway", '{"window_min":"Réd'],
  ["not json at all", "<!doctype html>"],
  ["an array, not an object", "[1,2,3]"],
  ["empty", ""],
]) {
  const bad = { ...sandbox, document: { ...sandbox.document, body: { dataset: { i18n: blob } } } };
  bad.globalThis = bad;
  let survived = true;
  try {
    vm.runInContext(readFileSync("static/js/desk.js", "utf8"), vm.createContext(bad));
  } catch {
    survived = false;
  }
  // Reaching the geometry functions proves it ran to the END. Catching
  // the throw alone would pass for a file that died on its first line,
  // which is the thing being guarded against.
  const whole = typeof bad.field === "function"
             && typeof bad.asFraction === "function"
             && typeof bad.asPixels === "function";
  check(`the desk still loads, whole, when the blob is ${what}`,
        survived && whole);
}


// --- a phone desk with more work on it than screen -------------------
// The failure this guards is quiet. `.desk` is one screen tall, which
// the brief asks for — "une page de la taille d'un écran qui ne
// s'étend pas" — and on a laptop that holds. On a phone the icons go
// into a three-column grid, and past about fifteen the grid is taller
// than the screen.
//
// Then: `.arranged` turns the desk into a block whose children are all
// absolute, so it has nothing left to be tall for and collapses back
// to one screen. arrange() clamps every icon into whatever it
// measures, so the bottom rows get crushed into the top of the screen
// and the collision walk stacks them.
//
// Nine icons in a grid 1200 tall on a 844 screen is that case.
function fakeStyle() {
  const v = {};
  return {
    setProperty(k, x) { v[k] = x; },
    getPropertyValue: (k) => v[k] ?? "",
    removeProperty(k) { delete v[k]; },
    get left() { return v.left ?? ""; }, set left(x) { v.left = x; },
    get top() { return v.top ?? ""; }, set top(x) { v.top = x; },
    get width() { return v.width ?? ""; }, set width(x) { v.width = x; },
    get height() { return v.height ?? ""; }, set height(x) { v.height = x; },
  };
}
function fakeIcon(left, top, w, h) {
  return {
    style: fakeStyle(), dataset: {},
    classList: { add() {}, remove() {}, contains: () => false },
    addEventListener() {},
    getBoundingClientRect: () => ({ left, top, width: w, height: h }),
  };
}

const GRID_H = 1200, SCREEN_H = 844;
const icons = [];
for (let row = 0; row < 3; row += 1) {
  for (let col = 0; col < 3; col += 1) {
    icons.push(fakeIcon(10 + col * 126, 104 + row * 365, 110, 140));
  }
}
// THE STUB HAS TO COLLAPSE THE WAY A BROWSER DOES, or it cannot fail.
// `.arranged` makes every child absolute, so the desk has no content
// left to be tall for: a browser drops it back to the one screen the
// stylesheet gives it, unless a height was pinned. A stub that always
// reported the grid height would keep passing with the fix removed —
// which is exactly what it did on the first attempt at this check.
let arranged = false;
const deskEl = {
  style: fakeStyle(),
  classList: {
    add(c) { if (c === "arranged") arranged = true; },
    remove(c) { if (c === "arranged") arranged = false; },
    contains: (c) => c === "arranged" && arranged,
  },
  addEventListener() {},
  querySelectorAll: () => icons,
  getBoundingClientRect: () => ({
    left: 0, top: 0, width: 390,
    height: arranged
      ? (parseFloat(deskEl.style.height) || SCREEN_H)
      : GRID_H,
  }),
};
const rootStyle = fakeStyle();
const narrowCtx = {
  ...sandbox,
  document: {
    ...sandbox.document,
    // a documentElement that remembers: the stub's discards every
    // setProperty, which would make the assertion below unable to fail
    documentElement: { ...el, style: rootStyle },
    querySelector: (sel) =>
      sel === ".desk" ? deskEl
      : sel === ".bar" ? { getBoundingClientRect: () => ({ height: 80 }) }
      : null,
    querySelectorAll: () => nothing,
  },
  window: { ...sandbox.window, matchMedia: () => ({ matches: true, addEventListener() {} }) },
};
narrowCtx.globalThis = narrowCtx;
const pctx = vm.createContext(narrowCtx);
vm.runInContext(readFileSync("static/js/desk.js", "utf8"), pctx);
pctx.arrange();

console.log("\n  a phone desk holding more work than screen:");
check("the desk keeps the room the grid asked for",
      deskEl.style.height === `${GRID_H}px`, deskEl.style.height || "(none)");
const tops = icons.map((i) => parseFloat(i.style.top));
const lowest = Math.max(...tops) + 140;          // + the icon's own height
// THE INVARIANT: a desk is never shorter than what is on it. That is
// the whole of the fix, and it is the assertion that fails when the
// pin goes — the desk reports one screen while holding icons below it.
check("the desk is never shorter than the icons on it",
      parseFloat(deskEl.style.height || "0") >= lowest,
      `${deskEl.style.height || "(none)"} vs ${Math.round(lowest)}px of icons`);
// Descriptive, not a guard: arrange() takes .arranged OFF before it
// measures, so it always reads the grown grid and always clamps into
// it. This passes with the fix removed too, and is here to say that
// the clamp is doing its job rather than to catch its absence.
check("and every icon landed inside what was measured",
      tops.every((y) => y >= 0 && y <= GRID_H - 140));
// The stylesheet keeps a phone's first row clear of the bandeau, and it
// needs the bar's REAL height to do it — the bar is fixed and its nav
// wraps. This is the script handing over the number it already
// measured, so the two cannot hold different answers.
check("the bar's measured height is published for the stylesheet",
      rootStyle.getPropertyValue("--bar-h") === "88px",
      rootStyle.getPropertyValue("--bar-h") || "(none)");

console.log(failed === 0 ? "\n  everything holds\n" : `\n  ${failed} FAILED\n`);
process.exit(failed === 0 ? 0 : 1);
