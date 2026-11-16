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
  // ON THE GLOBAL TOO, because that is where a browser has it and that
  // is how desk.js calls it: `getComputedStyle(desk)`, bare, when it
  // looks for the wallpaper. It was on `window` alone, so the phone
  // context below — the one with a real `.desk` — threw inside
  // `whenPainted()`, asynchronously, and the process exited before the
  // rejection surfaced. Every check in that block passed on a script
  // that had already fallen over. Found in audit 6, by adding an
  // `await` further down and watching the old failure appear.
  getComputedStyle: () => ({ backgroundImage: "none" }),
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

// --------------------------------------------------------------------
// A CLICK THAT DOES NOTHING.
//
// An icon says `data-window="preview-x"` and the dialog was never
// rendered. The handler used to suppress the link FIRST and look for
// the window after, so the icon did not open anything and did not go
// to its page either — a click that was simply ignored, with a clean
// build and a green suite behind it.
//
// The templates that disagreed agree again, so this is the floor
// rather than the fix: whatever they do next, the worst case is that
// the icon navigates, which is what it does with no JavaScript at all.
//
// Clicked for real, against the compiled desk.js. A regex over the
// source was tried first and matched `getElementById … preventDefault`
// in an unrelated handler, so it could not fail.
// --------------------------------------------------------------------
class FakeDialog {
  constructor() { this.opened = false; }
  showModal() { this.opened = true; }
}
function clickIconNaming(windowId, dialogs) {
  let listener = null;
  const icon = {
    dataset: { window: windowId },
    classList: { add() {}, remove() {}, contains: () => false },
    style: fakeStyle(),
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 160, height: 180 }),
    addEventListener(type, fn) { if (type === "click") listener = fn; },
  };
  const ctxc = {
    ...sandbox,
    HTMLDialogElement: FakeDialog,
    // the handler tests `e instanceof MouseEvent` to tell a pointer
    // click from a keyboard one; the event below is neither, which is
    // the pointer branch and the one that matters here
    MouseEvent: class MouseEvent {},
    document: {
      ...sandbox.document,
      // ONLY the bare ".icon" pass, which is the one that attaches this
      // handler. ".desk .icon" makes an icon draggable, and a dragged
      // icon sets the flag this handler checks before anything else.
      querySelectorAll: (sel) => (sel === ".icon" ? [icon] : nothing),
      getElementById: (id) => dialogs[id] ?? null,
    },
  };
  ctxc.globalThis = ctxc;
  vm.runInContext(readFileSync("static/js/desk.js", "utf8"), vm.createContext(ctxc));
  if (listener === null) return { attached: false };
  let prevented = false;
  // detail 1, so it reads as a real pointer click rather than a
  // keyboard activation
  listener({ detail: 1, preventDefault() { prevented = true; },
             stopImmediatePropagation() {} });
  return { attached: true, prevented };
}

console.log("\n  an icon naming a window that is not there:");
const missing = clickIconNaming("preview-nobody", {});
check("the handler is attached at all", missing.attached === true);
check("the link is NOT suppressed, so the icon goes to its page",
      missing.prevented === false,
      missing.prevented ? "preventDefault was called — the click does nothing" : "");

// The control. Without it, a handler that never suppressed anything
// would satisfy the assertion above and break every preview on the
// site.
const real = new FakeDialog();
const there = clickIconNaming("preview-real", { "preview-real": real });
check("while a window that IS there opens, and the link is suppressed",
      there.prevented === true && real.opened === true,
      `prevented=${there.prevented} opened=${real.opened}`);

// --- a click that follows a DRAG -------------------------------------
//
// AUDIT 3 FOUND THIS MISSING. The two checks above drive a click on an
// icon that was never moved; the handler's FIRST branch is the other
// case — a click arriving straight after a drag, which must open
// nothing and navigate nowhere, because she was moving the thing.
//
// A mutation sweep commented out the `preventDefault()` in that branch
// and all five suites stayed green: dragging an icon would have ALSO
// opened its page, and nothing here could see it. See
// specs/the-audit.md.
//
// Driven through the real handlers — pointerdown, a move past the 6px
// threshold, pointerup, then the click — because the flag that branch
// reads is set by the drag itself and by nothing else.
function dragThenClick({ move }) {
  const seen = {};
  const opened = [];
  class FakeDialog2 {
    constructor() { this.opened = false; }
    showModal() { this.opened = true; opened.push(this); }
    close() {}
  }
  const dial = new FakeDialog2();
  const icon = {
    className: "icon",
    dataset: { window: "preview-une" },
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
    style: fakeStyle(),
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 160, height: 180 }),
    addEventListener(type, fn) { (seen[type] ||= []).push(fn); },
    removeEventListener(type, fn) {
      seen[type] = (seen[type] || []).filter((f) => f !== fn);
    },
    setPointerCapture() {}, releasePointerCapture() {},
    closest: (sel) => (sel.includes(".desk") ? deskNode : null),
    querySelector: () => null, querySelectorAll: () => nothing,
    offsetParent: null,
  };
  const deskNode = {
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 1200, height: 800 }),
  };
  // `e.target instanceof Element` is the handler's first question —
  // it refuses to drag anything whose target is not one. So the
  // sandbox needs the constructor and the icon needs to be an
  // instance of it, or the drag never starts and the check would be
  // asserting against a handler that bailed on line one.
  function Element() {}
  Object.setPrototypeOf(icon, Element.prototype);
  const ctxd = {
    ...sandbox,
    Element,
    HTMLElement: Element,
    HTMLDialogElement: FakeDialog2,
    MouseEvent: class MouseEvent {},
    document: {
      ...sandbox.document,
      // BOTH passes answer with this icon: `.desk .icon` is what makes
      // it draggable, and the bare `.icon` is what attaches the click
      // handler. The existing driver answers only the second, which is
      // exactly why the dragged branch was never reached.
      querySelectorAll: (sel) => (String(sel).includes("icon") ? [icon] : nothing),
      getElementById: (id) => (id === "preview-une" ? dial : null),
    },
  };
  ctxd.globalThis = ctxd;
  vm.runInContext(readFileSync("static/js/desk.js", "utf8"), vm.createContext(ctxd));
  const fire = (type, ev) => (seen[type] || []).slice().forEach((fn) => fn(ev));
  const at = (x, y) => ({ button: 0, pointerId: 1, clientX: x, clientY: y,
                          target: icon, preventDefault() {},
                          stopImmediatePropagation() {} });
  icon.target = icon;
  fire("pointerdown", { ...at(10, 10), target: icon });
  if (move) fire("pointermove", at(10 + move, 10 + move));
  fire("pointerup", at(10 + (move || 0), 10 + (move || 0)));
  let prevented = false;
  fire("click", { detail: 1, preventDefault() { prevented = true; },
                  stopImmediatePropagation() {} });
  return { prevented, opened: dial.opened, wired: Boolean(seen["pointerdown"]) };
}

console.log("\n  a click that arrives after a drag:");
const dragged = dragThenClick({ move: 40 });
check("the icon is draggable at all", dragged.wired === true);
check("a dragged icon does not also open its window",
      dragged.opened === false, `opened=${dragged.opened}`);
check("  and does not navigate either — the link is suppressed",
      dragged.prevented === true, `prevented=${dragged.prevented}`);
// THE CONTROL. A handler that suppressed everything would satisfy both
// lines above and break every icon on the site.
const tapped = dragThenClick({ move: 0 });
check("while a tap — a press that never moved — still opens it",
      tapped.opened === true, `opened=${tapped.opened}`);

// ---------------------------------------------------------------------
// THE PROMISES THE SITE MAKES IN THE BROWSER
//
// AUDIT 6 broke each of these on purpose and no suite anywhere
// noticed. They are not clever edge cases — they are the page showing
// at all, a window closing, a link opening one, and a film going quiet.
// Every one is a thing a visitor does in the first ten seconds.
// See specs/the-audit.md.
// ---------------------------------------------------------------------

/** Run the REAL desk.js against a document of our making, and hand back
 *  what it did. One helper, because four checks want the same thing and
 *  a fifth copy of this sandbox is how the next one drifts. */
function runDesk({ body = {}, finders = {}, root = null } = {}) {
  const classes = new Set(["booting", "js"]);
  const html = root ?? {
    classList: {
      add: (c) => classes.add(c), remove: (c) => classes.delete(c),
      contains: (c) => classes.has(c),
    },
    style: fakeStyle(),
  };
  const ctx = {
    ...sandbox,
    HTMLDialogElement: FakeDialog,
    MouseEvent: class MouseEvent {},
    Element: function Element() {},
    Image: function Image() { setTimeout(() => this.onload && this.onload(), 0); },
    // A browser has this on the global, and desk.js calls it bare when
    // it looks for the wallpaper. The base sandbox had it on `window`
    // only, so the first thing that reached it threw.
    getComputedStyle: () => ({ backgroundImage: "none" }),
    document: {
      ...sandbox.document,
      documentElement: html,
      body: { dataset: { i18n: "{}" } },
      querySelector: (s) => (finders.one ? finders.one(s) : null),
      querySelectorAll: (s) => (finders.all ? (finders.all(s) ?? nothing) : nothing),
      getElementById: (id) => (finders.byId ? finders.byId(id) : null),
      fonts: { ready: Promise.resolve() },
      addEventListener() {},
    },
    ...body,
  };
  ctx.globalThis = ctx;
  vm.runInContext(readFileSync("static/js/desk.js", "utf8"), vm.createContext(ctx));
  return { classes, ctx };
}

// 1. THE PAGE IS SHOWN AT ALL. `html.booting` hides everything until
//    the images are in; `reveal()` takes it off. Delete that one line
//    and the site is a blank screen — and every suite stayed green.
{
  const { classes } = runDesk();
  await new Promise((r) => setTimeout(r, 40));   // whenPainted() is async
  console.log("\n  the page is actually shown:");
  check("the booting class comes off, so the site is not a blank screen",
    !classes.has("booting"), [...classes].join(" "));
}

// 2. A FRAMELESS PREVIEW CLOSES ON A CLICK OFF THE PICTURE. There is no
//    ✕ to press — that was her ask — so Escape and this are the only two
//    ways out, and someone on a trackpad has only this one.
{
  let closed = 0;
  const win = {
    classList: { add() {}, remove() {}, contains: () => false },
    style: fakeStyle(), dataset: {}, on: {},
    addEventListener(k, fn) { (this.on[k] ||= []).push(fn); },
    removeEventListener() {},
    close() { closed += 1; },
    querySelector: () => null, querySelectorAll: () => nothing,
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 400, height: 300 }),
  };
  runDesk({ finders: { all: (s) => (String(s).includes("win-preview") ? [win] : nothing) } });
  const fire = (t) => (win.on["click"] || []).forEach((fn) => fn({ target: t }));
  console.log("\n  a window with no close box:");
  check("the handler is attached", Boolean(win.on["click"]));
  fire(win);
  check("a click on the dark closes it", closed === 1, String(closed));
  // AND THE PICTURE DOES NOT. Clicking the photograph itself must not
  // close the thing you opened to look at it.
  const picture = { closest: (sel) => (sel.includes("img") ? picture : null) };
  Object.setPrototypeOf(picture, (class Element {}).prototype);
  fire(picture);
  check("  while a click on the picture does not", closed === 1, String(closed));
}

// 3. A LINK TO A WINDOW OPENS IT. The bandeau's `contact` link is an
//    <a href="#contact"> pointing at a <dialog>, which is display:none
//    until opened — so the browser's own anchor jump lands on nothing.
//    desk.js says this in a comment and nothing checked it.
{
  const dial = new FakeDialog();
  dial.open = false;
  const link = {
    on: {}, getAttribute: () => "#contact",
    addEventListener(k, fn) { (this.on[k] ||= []).push(fn); },
  };
  runDesk({
    finders: {
      all: (s) => (String(s).includes('href^="#"') ? [link] : nothing),
      byId: (id) => (id === "contact" ? dial : null),
    },
  });
  console.log("\n  a link that names a window:");
  check("the link is wired", Boolean(link.on["click"]));
  let stopped = false;
  (link.on["click"] || []).forEach((fn) =>
    fn({ preventDefault() { stopped = true; } }));
  check("clicking it opens the window rather than jumping to nothing",
    dial.opened === true && stopped === true,
    `opened=${dial.opened} prevented=${stopped}`);
}

// 4. A FILM GOES QUIET WHEN ITS WINDOW IS CLOSED. Minimising calls
//    close() on its way to show(), so the handler has to tell the two
//    apart — and if it stops pausing, the sound carries on over a desk
//    with no window on it.
{
  let paused = 0;
  const video = { pause() { paused += 1; } };
  const film = {
    open: false, on: {},
    classList: { add() {}, remove() {}, contains: () => false, toggle: () => false },
    style: fakeStyle(), dataset: {},
    addEventListener(k, fn) { (this.on[k] ||= []).push(fn); },
    removeEventListener() {},
    close() {}, show() {}, showModal() {},
    querySelector: (s) => (s === "video" ? video : null),
    querySelectorAll: () => nothing,
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 400, height: 300 }),
  };
  runDesk({ finders: { all: (s) => (String(s).includes("win-film") ? [film] : nothing) } });
  console.log("\n  a film that is closed:");
  check("the close handler is attached", Boolean(film.on["close"]));
  (film.on["close"] || []).forEach((fn) => fn({}));
  check("closing the window stops the sound", paused === 1, String(paused));
  // AND MINIMISING DOES NOT. close() is called on the way to show(),
  // and the film must keep playing — that is the whole point of the
  // minimise.
  film.open = true;
  (film.on["close"] || []).forEach((fn) => fn({}));
  check("  while minimising leaves it playing", paused === 1, String(paused));
}

console.log(failed === 0 ? "\n  everything holds\n" : `\n  ${failed} FAILED\n`);
process.exit(failed === 0 ? 0 : 1);
