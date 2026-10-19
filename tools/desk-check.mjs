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

console.log(failed === 0 ? "\n  everything holds\n" : `\n  ${failed} FAILED\n`);
process.exit(failed === 0 ? 0 : 1);
