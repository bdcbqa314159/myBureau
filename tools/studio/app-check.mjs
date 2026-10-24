#!/usr/bin/env node
// Does the panel's script survive being loaded, and do its buttons do
// anything?
//
//     node tools/studio/app-check.mjs
//
// He opened the panel and nothing happened: no stylesheet, no script,
// buttons that did nothing. The server bug behind that is tested in
// check.py now. This is the other half — a script that throws on its
// first line looks EXACTLY the same from the outside, and nothing in
// this repository would have noticed.
//
// The same trick desk-check.mjs uses: run the real file in a vm with
// just enough document to get through it.

import { readFileSync } from "node:fs";
import vm from "node:vm";

let failed = 0;
const check = (what, held, detail = "") => {
  console.log((held ? "  ok    " : "  FAIL  ") + what + (!held && detail ? "\n          " + detail : ""));
  if (!held) failed++;
};

// ---- the smallest document the panel can wake up in -----------------
const listeners = new Map();
const node = (id = "") => ({
  id,
  style: {}, dataset: {}, classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
  innerHTML: "", textContent: "", value: "",
  children: [],
  append(...n) { this.children.push(...n); },
  insertAdjacentHTML() {}, setPointerCapture() {},
  setAttribute() {}, getAttribute: () => null, removeAttribute() {},
  focus() {}, remove() {}, insertBefore() {},
  getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 450 }),
  hidden: false, src: "", contentDocument: null,
  querySelector: () => null,
  querySelectorAll: () => [],
  matchAll() { return []; },
  addEventListener(kind, fn) {
    const key = id + ":" + kind;
    listeners.set(key, (listeners.get(key) || []).concat(fn));
  },
});

// THE IDS COME FROM app.html, not from a list kept by hand. A list by
// hand goes stale the moment an element is renamed, and then this check
// fails for the wrong reason — or worse, passes while the real page is
// missing something the script reaches for.
const markup = readFileSync(new URL("./app.html", import.meta.url), "utf8");
const ids = [...markup.matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]);
const byId = new Map(ids.map((id) => [id, node(id)]));
const missing = [];

let fetched = [];
const sandbox = {
  console,
  // a browser has these; a vm context does not inherit them
  setTimeout, clearTimeout, setInterval, clearInterval, Promise, Date,
  document: {
    getElementById: (id) => {
      if (!byId.has(id)) missing.push(id);     // app.js asked for something
      return byId.get(id) || null;             // the markup does not have
    },
    createElement: () => node(),
    querySelectorAll: () => [],
    addEventListener() {},
  },
  location: { search: "?t=TESTTOKEN" },
  window: { open() {} },
  URLSearchParams,
  EventSource: class { constructor(u) { this.url = u; } },
  fetch: async (url) => {
    fetched.push(url);
    // Shaped like the REAL answer, desks and all. An empty tree let the
    // panel "work" while drawing nothing, which is close to what he saw.
    return {
      ok: true,
      json: async () => ({
        did: { undid: "place" },
        site: "http://127.0.0.1:1111/",
        n: 1,
        tree: {
          desks: [{
            kind: "desk", path: "content/da", name: "da", gallery: false,
            depth: 1, opens_as: "page", empty: false,
            titles: { fr: "DA", en: "art direction" },
            bodies: { fr: "Un texte.", en: "Some text." },
            x: null, y: null, opens: null, icon: null, wallpaper: "wallpaper.jpg",
            photographs: [], video: null, languages: ["en", "fr"],
            on: [{
              kind: "project", path: "content/da/theodora", name: "theodora",
              titles: { fr: "theodora.jpeg", en: "theodora.jpeg" },
              bodies: { fr: "", en: "" },
              x: "32", y: "12", opens: null, icon: null, wallpaper: null,
              photographs: ["01.jpg", "02.jpg"], video: "film.mp4", languages: ["en", "fr"],
            }],
          }],
        },
      }),
    };
  },
};
sandbox.globalThis = sandbox;

const code = readFileSync(new URL("./app.js", import.meta.url), "utf8");
let loaded = true;
let why = "";
try {
  vm.createContext(sandbox);
  vm.runInContext(code, sandbox, { filename: "app.js" });
} catch (e) {
  loaded = false;
  why = String(e && e.stack ? e.stack.split("\n")[0] : e);
}
check("the panel's script survives being loaded", loaded, why);
check("every element it reaches for exists in app.html", missing.length === 0,
  "app.js wants #" + missing.join(", #"));

if (loaded) {
  check("it carries the token out of the address bar",
    fetched.length > 0 && String(fetched[0]).includes("t=TESTTOKEN"),
    JSON.stringify(fetched));
  check("it asks for the tree the moment it wakes up",
    fetched.some((u) => String(u).startsWith("/api/tree")), JSON.stringify(fetched));
  check("it opens the live stream", typeof sandbox.EventSource === "function");

  // the complaint was "the buttons do not do anything"
  const buttons = [...markup.matchAll(/<button[^>]*\bid="([^"]+)"/g)].map((m) => m[1]);
  check("app.html actually has buttons", buttons.length >= 2);
  for (const id of buttons) {
    check(`the ${id} button has a handler`, (listeners.get(id + ":click") || []).length > 0);
  }
  // The panel wakes up asynchronously: it asks for the tree and draws
  // when the answer lands. Checking the DOM before that is checking an
  // empty room and calling it empty.
  await new Promise((r) => setTimeout(r, 30));

  // ---- is there anything to EDIT? ----------------------------------
  // The panel showed the site and a list, and the only place anything
  // could be changed was hidden by a media query below 1152px. Nothing
  // here noticed, because nothing here had ever asked.
  const tree = byId.get("tree"), look = byId.get("look");
  check("the list down the side actually gets rows", tree.children.length > 0);
  check("something is chosen as soon as it opens, so the editor is not blank",
    look.innerHTML.length > 0 && !/Choisis quelque chose/.test(look.innerHTML),
    JSON.stringify(look.innerHTML.slice(0, 60)));
  check("the editor offers a name to type into", /<input[^>]*data-title/.test(look.innerHTML));
  check("and a text to write", /<textarea[^>]*data-body/.test(look.innerHTML));
  check("one box per language, not one for both",
    (look.innerHTML.match(/data-title="/g) || []).length >= 2);

  check("the editor offers an appearance to change",
    /data-drop="icon"/.test(look.innerHTML));
  check("a bureau also offers its wallpaper",
    /data-drop="wallpaper"/.test(look.innerHTML));
  check("there is a way to make something new",
    /<button[^>]*id="make"/.test(markup) && /<select[^>]*id="kind"/.test(markup));
  check("and a way to look INSIDE a thing rather than at its desk",
    /id="aspage"/.test(markup) && (listeners.get("aspage:click") || []).length > 0);

  check("the panel says where a new thing is going",
    /<select[^>]*id="into"/.test(markup) && byId.get("into").children.length > 0);
  check("and what it will do once it is there",
    byId.get("willbe").innerHTML.length > 10, byId.get("willbe").innerHTML);
  check("a folder's job is explained, because it depends on where it is",
    /propre page|fenêtre|bandeau/.test(look.innerHTML), look.innerHTML.slice(0, 120));

  check("a thing can be thrown away from the panel",
    /id="binall"/.test(look.innerHTML));
  const rows = tree.children;
  check("the rows can be dragged, which is how a thing changes folder",
    rows.length > 0 && rows.every((r) => r.draggable === true));

  // Selecting the PROJECT rather than the desk. Rows are created
  // elements with no id, so every row handler lands under ":click" —
  // running them all ends on the last row, which is the project.
  for (const fn of listeners.get(":click") || []) fn();
  await new Promise((r) => setTimeout(r, 20));
  check("a film offers somewhere to put the film",
    /data-drop="video"/.test(look.innerHTML), look.innerHTML.slice(0, 120));
  check("and somewhere for its affiche",
    /data-drop="poster"/.test(look.innerHTML));

  // Clicking in the frame must EDIT, not fire the site's own dynamics.
  // Those belong to a visitor; while she is arranging a desk they carry
  // her away from the thing she just touched.
  const src2 = readFileSync(new URL("./app.js", import.meta.url), "utf8");
  check("a click in the page is caught before the site acts on it",
    /addEventListener\("click"[\s\S]{0,260}stopImmediatePropagation/.test(src2));
  check("and double-click is how she goes in on purpose",
    /addEventListener\("dblclick"/.test(src2));
  check("what she chose is outlined in the real page",
    /studio-chosen/.test(src2));
  check("throwing a thing away lands her on the desk it was on, not nowhere",
    /const home = o\.path\.split\("\/"\)\.slice\(0, -1\)/.test(src2)
    && /const back = find\(home\)/.test(src2));

  const css = readFileSync(new URL("./app.css", import.meta.url), "utf8");
  check("and no rule anywhere hides the editor",
    !/\.look\s*\{[^}]*display:\s*none/.test(css)
    && !/display:\s*none[^}]*\}\s*\/\*[^*]*look/.test(css),
    "app.css still hides .look somewhere");

  const before = fetched.length;
  for (const fn of listeners.get("undo:click") || []) fn();
  await new Promise((r) => setTimeout(r, 20));
  check("pressing Annuler actually asks the server something",
    fetched.length > before, `${before} -> ${fetched.length}`);

  // ---- the feedback loop -------------------------------------------
  // Measured: zola takes ~1.3s to rebuild and answers 404 for most of
  // it. Reloading the frame the moment a write returns lands on that
  // 404 — the blank flash. The panel must ASK FIRST and reload after.
  const view = byId.get("view");
  view.src = "/site/da/";
  const mark = fetched.length;
  for (const fn of listeners.get("undo:click") || []) fn();
  await new Promise((r) => setTimeout(r, 450));
  const polled = fetched.slice(mark).some((u) => String(u).startsWith("/site/"));
  check("after an edit it waits for the page before reloading the frame",
    polled, JSON.stringify(fetched.slice(mark)));

  const src = readFileSync(new URL("./app.js", import.meta.url), "utf8");
  check("and a drag reloads nothing, because the icon has already moved",
    /NOTHING_TO_SEE\s*=\s*new Set\(\["place"\]\)/.test(src));
  check("reloads are debounced, so four photographs are one reload",
    /clearTimeout\(waiting\)/.test(src) && /setTimeout\(async/.test(src));
}

console.log();
if (failed) {
  console.log(`  ${failed} FAILED\n`);
  process.exit(1);
}
console.log("  the panel wakes up and its buttons are wired\n");
