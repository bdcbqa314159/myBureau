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
const node = (id = "") => {
  const n = rawNode(id);
  n.classList._owner = n;
  n._cls = n._cls || new Set();
  // `.closest(".stage")` HAS TO ANSWER. setWidth() walks from the phone
  // button up to the stage to put `is-phone` on it, and a stub that
  // answers null makes pressing that button throw — so the phone view
  // could not be entered here at all, and nothing that depends on it
  // could be checked.
  n.closest = (sel) => (sel === ".stage" ? STAGE : null);
  return n;
};

const STAGE = { _cls: new Set(), classList: {
  add(c) { STAGE._cls.add(c); }, remove(c) { STAGE._cls.delete(c); },
  contains: (c) => STAGE._cls.has(c),
  toggle(c, on) { if (on === undefined) on = !STAGE._cls.has(c);
                  if (on) STAGE._cls.add(c); else STAGE._cls.delete(c); },
} };

const rawNode = (id = "") => ({
  id,
  style: {}, dataset: {},
  // A REAL classList, backed by a set. It used to be four no-ops, so
  // anything the panel expressed by adding a class — which is how it
  // says "this box will take your file" — could not be observed, and no
  // check could tell guidance from none.
  _cls: new Set(),
  classList: {
    add(...c) { c.forEach((x) => this._owner._cls.add(x)); },
    remove(...c) { c.forEach((x) => this._owner._cls.delete(x)); },
    toggle(c, on) {
      if (on === undefined) on = !this._owner._cls.has(c);
      if (on) this._owner._cls.add(c); else this._owner._cls.delete(c);
      return on;
    },
    contains(c) { return this._owner._cls.has(c); },
  },
  textContent: "", value: "",
  children: [],
  // SETTING innerHTML EMPTIES THE ELEMENT. paint() clears the list with
  // `tree.innerHTML = ""` and appends the rows again, and this stub kept
  // every row from every repaint — three paints of six rows answered
  // `children.length === 18`. Any check that counted rows, or asked
  // whether they were all draggable, was reading three generations at
  // once and the first one's handlers.
  _html: "",
  get innerHTML() { return this._html; },
  set innerHTML(v) { this._html = v; this.children = []; drawn.clear(); },
  append(...n) { this.children.push(...n); },
  insertAdjacentHTML() {}, setPointerCapture() {},
  setAttribute() {}, getAttribute: () => null, removeAttribute() {},
  focus() {}, remove() {}, insertBefore() {},
  getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 450 }),
  hidden: false, src: "", contentDocument: null,
  querySelector: () => null,
  querySelectorAll: () => [],
  matchAll() { return []; },
  // THE BOXES THE PANEL DREW. wire() reaches its inputs with
  // querySelectorAll("[data-title]") and friends, and this returned []
  // for every one of them — so no name box, no text box and no
  // photograph row had ever been wired in a check. They were asserted to
  // be PRESENT in the markup and never asserted to DO anything, which is
  // the whole of "there is no possibility to add any text".
  //
  // Only `[data-x]` selectors, which is all wire() uses. Each box gets a
  // synthetic id so its listener is findable: `body:fr`, `title:en`.
  querySelectorAll(sel) {
    const attr = /^\[data-([a-z]+)\]$/.exec(sel);
    if (!attr || typeof this.innerHTML !== "string") return [];
    const key = attr[1];
    const out = [];
    const re = new RegExp('data-' + key + '="([^"]*)"', "g");
    let m;
    while ((m = re.exec(this.innerHTML))) {
      // THE SAME ELEMENT EACH TIME IT IS QUERIED. A fresh object per
      // query meant anything the panel set on it — a class saying "this
      // box takes your file" — was thrown away before a check could read
      // it. Cleared whenever innerHTML is written, as a re-render does.
      const id = key + ":" + m[1];
      if (!drawn.has(id)) {
        const n = node(id);
        n.dataset[key] = m[1];
        drawn.set(id, n);
      }
      out.push(drawn.get(id));
    }
    return out;
  },
  closest() { return null; },
  addEventListener(kind, fn) {
    const key = id + ":" + kind;
    listeners.set(key, (listeners.get(key) || []).concat(fn));
    if (kind === "click") this.__click = fn;   // so one row can be clicked
  },
});

// THE IDS COME FROM app.html, not from a list kept by hand. A list by
// hand goes stale the moment an element is renamed, and then this check
// fails for the wrong reason — or worse, passes while the real page is
// missing something the script reaches for.
// A stand-in for the page inside the frame. It exists so the check can
// ask the question that was never asked: when the panel hooks the frame
// BEFORE the tree has arrived — which is what happens on the very first
// load — does it still stop a click reaching the site?
// THE FRAMED SITE, with icons on it.
//
// It used to serve no icons at all, so nothing the panel does to a real
// desk icon could be checked — including what a double-click opens,
// which is how the panel came to show her a page where the site shows a
// photograph in place.
//
// `data-window` is the site's own answer to "what does this open?", so
// each icon carries what _icon.html would have written for it.
function frameIcon(vt, windowId) {
  const el = {
    dataset: windowId ? { vt, window: windowId } : { vt },
    classList: { add() {}, remove() {}, contains: () => false },
    style: { setProperty() {}, removeProperty() {} },
    on: {},
    addEventListener(kind, fn) { (this.on[kind] ||= []).push(fn); },
    closest: (sel) => (/a\.icon/.test(sel) ? el : null),
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 160, height: 180 }),
  };
  return el;
}
const frameIcons = [
  frameIcon("da"),                                   // a bureau: no window
  frameIcon("da-theodora", "preview-da-theodora"),   // a photograph: in place
  frameIcon("about-me-txt", "about"),                // the window she edits
];
const frameDialogs = {
  "preview-da-theodora": { opened: false, showModal() { this.opened = true; } },
  about: { opened: false, showModal() { this.opened = true; } },
};
const frameDesk = { contains: () => true,
                    getBoundingClientRect: () => ({ left: 0, top: 0, width: 900, height: 600 }) };
const frameDoc = {
  heard: [],
  addEventListener(kind) { this.heard.push(kind); },
  querySelector: (s) => (s === ".desk" ? frameDesk : null),
  querySelectorAll: (s) => (/a\.icon/.test(s) ? frameIcons : []),
  getElementById: (id) => frameDialogs[id] || null,
  // mark() paints an outline into the real page, which means a <style>
  // element and a head to put it in
  createElement: () => ({ id: "", textContent: "" }),
  head: { append() {} },
};

const markup = readFileSync(new URL("./app.html", import.meta.url), "utf8");
const ids = [...markup.matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]);
const byId = new Map(ids.map((id) => [id, node(id)]));
const made = new Map();          // elements the panel drew for itself
const drawn = new Map();         // and the ones it queries by attribute
const missing = [];

let fetched = [];
// The live stream the panel opens. KEPT, so a check can push a message
// down it: `stream` is a const inside app.js and not reachable from
// here, and the only other way to test what arrives is not to test it.
const streams = [];

const sandbox = {
  console,
  // a browser has these; a vm context does not inherit them
  setTimeout, clearTimeout, setInterval, clearInterval, Promise, Date,
  // ask() bounds every request with one of these. Without it in the
  // sandbox the call throws before any fetch happens, and the checks
  // below report no requests rather than a broken request.
  AbortController,
  // A REAL ONE, because the panel keeps where she was in it: boot with
  // nothing stored and it lands on the first desk, which is the old
  // behaviour and would hide a restore that never happens.
  localStorage: {
    store: new Map(),
    getItem(k) { return this.store.has(k) ? this.store.get(k) : null; },
    setItem(k, v) { this.store.set(k, String(v)); },
    removeItem(k) { this.store.delete(k); },
  },
  document: {
    getElementById: (id) => {
      if (byId.has(id)) return byId.get(id);
      // Not in app.html — but the panel writes fields into the editing
      // pane itself, and in a browser those are real elements the moment
      // the innerHTML lands. Without this the stub answered null, the
      // fields were never wired, and the check could not tell the
      // difference between "not wired" and "not there".
      if (made.has(id)) return made.get(id);
      const written = [...byId.values()].some(
        (n) => typeof n.innerHTML === "string" && n.innerHTML.includes('id="' + id + '"'));
      if (written) { made.set(id, node(id)); return made.get(id); }
      missing.push(id);                        // app.js asked for something
      return null;                             // nothing has ever drawn
    },
    createElement: () => node(),
    querySelectorAll: () => [],
    addEventListener() {},
  },
  location: { search: "?t=TESTTOKEN" },
  window: { open() {} },
  URLSearchParams,
  EventSource: class { constructor(u) { this.url = u; streams.push(this); } },
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
        // Shaped like the real tree: a bureau appears BOTH as a child of
        // its parent and as a desk of its own. Without the nesting the
        // check cannot ask where choosing a folder puts the frame.
        tree: {
          // What the bar says, and which of config.toml's two blocks is
          // in use. Left out of this fixture, the panel drew the bandeau
          // fields from a default and the checks below passed while the
          // real answer was never read.
          identity: { block: "demo", owner: "a demo of", studio: "myBureau",
                      live: false },
          desks: [{
            kind: "desk", path: "content", name: "content", gallery: false,
            depth: 0, empty: false,
            // THE TEMPLATE, which decides what the object can show at
            // all. Left out of this fixture, every row looked like a
            // page to the panel and the text box was asserted on a
            // DESK — which renders no body anywhere.
            template: "index.html",
            titles: { fr: "myBureau", en: "myBureau" },
            bodies: { fr: "", en: "" },
            x: null, y: null, opens: null, icon: null, wallpaper: null,
            about: "about.jpg",
            photographs: [], video: null, doc: null, languages: ["en", "fr"],
            on: [{
              kind: "folder", path: "content/da", name: "da", template: "section.html", type: "folder",
              titles: { fr: "DA", en: "art direction" }, bodies: { fr: "", en: "" },
              x: "66", y: "66", opens: null, icon: null, wallpaper: "wallpaper.jpg",
              photographs: [], video: null, languages: ["en", "fr"],
            }, {
              // about me.txt: a window declared in [extra.items], so it
              // has no path of its own and carries the home desk's. The
              // model appends it; leaving it out of this fixture is how
              // the panel got checked against a tree it never sees.
              kind: "about", path: "content", name: "about me.txt", template: "",
              titles: { fr: "about me.txt", en: "about me.txt" },
              bodies: { fr: "Je suis directrice artistique.",
                        en: "I am an art director." },
              about: "about.jpg", languages: ["en", "fr"],
              x: null, y: null, opens: null, icon: null, wallpaper: null,
              photographs: [], video: null, doc: null,
            }],
          }, {
            kind: "desk", path: "content/da", name: "da", gallery: false,
            depth: 1, empty: false, template: "section.html", type: "folder",
            titles: { fr: "DA", en: "art direction" },
            bodies: { fr: "Un texte.", en: "Some text." },
            x: "66", y: "66", opens: null, icon: null, wallpaper: "wallpaper.jpg",
            photographs: [], video: null, languages: ["en", "fr"],
            on: [{
              // A VIDEO, and nothing else — which is what the type
              // means. It used to be a film carrying two photographs
              // and a dossier's worth of boxes, an object the engine
              // now forbids: `add_image` on a video is refused.
              //
              // The photograph-description checks moved to `cosette`,
              // which is a page and is where photographs live.
              kind: "project", path: "content/da/theodora", name: "theodora",
              template: "", type: "video",
              titles: { fr: "theodora.jpeg", en: "theodora.jpeg" },
              bodies: { fr: "", en: "" },
              x: "32", y: "12", opens: null, icon: null, wallpaper: null,
              photographs: [], video: "film.mp4",
              poster: "poster.png", doc: null, languages: ["en", "fr"], alt: {},
            }, {
              // ONE WEARING A GIF and one declaring a DRAWN FOLDER, so
              // "exactly one slot is marked" has all three states to
              // be true about — the third is `grocery`, which has
              // neither and falls back.
              kind: "project", path: "content/da/gifly", name: "gifly",
              template: "", type: "page", face: "gif", icon: "icon.gif",
              titles: { fr: "gifly", en: "gifly" }, bodies: { fr: "", en: "" },
              x: "5", y: "5", opens: null, wallpaper: null,
              photographs: [], video: null, doc: null,
              languages: ["en", "fr"], alt: {},
            }, {
              kind: "project", path: "content/da/drawnly", name: "drawnly",
              template: "", type: "page", face: "folder",
              icon: "img/icons/folder-rust.svg",
              titles: { fr: "drawnly", en: "drawnly" }, bodies: { fr: "", en: "" },
              x: "6", y: "6", opens: null, wallpaper: null,
              photographs: [], video: null, doc: null,
              languages: ["en", "fr"], alt: {},
            }, {
              // A PHOTO SHE HAS NOT FILLED YET — type photo, no image.
              // This is the one shape where reading the TYPE and
              // counting the files disagree: counting says "not one
              // picture, so it must be a page" and offers it a text
              // box and a dossier, which is the whole bug. Without
              // this row the two rules are indistinguishable.
              kind: "project", path: "content/da/vide", name: "vide",
              template: "", type: "photo",
              titles: { fr: "à venir", en: "to come" },
              bodies: { fr: "", en: "" },
              x: "8", y: "8", opens: null, icon: null, wallpaper: null,
              photographs: [], video: null, doc: null,
              languages: ["en", "fr"], alt: {},
            }, {
              // A FOLDER THAT IS A PAGE, which the fixture had none of.
              // It is `kind: "folder"` with `depth >= 1` exactly like a
              // bureau, and the only thing telling them apart is the
              // template — so without one of these, every rule about
              // "a desk, but not a folder-page" was unexercised and
              // passed by finding nothing to be false about.
              kind: "folder", path: "content/da/cosette", type: "page", name: "cosette",
              template: "page.html", gallery: false, depth: 2, empty: true,
              titles: { fr: "maison cosette", en: "maison cosette" },
              bodies: { fr: "Un texte.", en: "Some text." },
              x: "41", y: "57", opens: null, icon: null, wallpaper: null,
              // PHOTOGRAPHS IN IT, because the description box only
              // appears when there are some — and without them the
              // "same as a project" checks pass on an empty pane.
              // (They were added twice at first, and a duplicate key
              // in an object literal is the LAST one, silently.)
              photographs: ["01.jpg", "02.jpg"],
              alt: { "01.jpg": "Deux silhouettes sur une plage." },
              video: null, doc: null, languages: ["en", "fr"],
            }, {
              // ONE photograph, no film, no dossier — the only shape
              // that gets a choice about what its icon opens, and the
              // shape the fixture had none of. `theodora` above holds
              // two and a video, so the switch must not appear on it.
              kind: "project", path: "content/da/seule", type: "photo", name: "seule", template: "",
              titles: { fr: "seule.jpg", en: "seule.jpg" },
              bodies: { fr: "Un texte.", en: "Some text." },
              x: "20", y: "70", opens: null, icon: null, wallpaper: null,
              photographs: ["01.jpg"], video: null, doc: null,
              languages: ["en", "fr"],
            }, {
              // a dossier that has not had its PDF yet — the state the
              // panel used to answer by asking for photographs
              // A DOSSIER, and `opens`. Neither was ever set to
              // anything in this fixture — `o.doc` was read six times
              // by app.js and was null in every row, `o.opens` read
              // once and null in every row. Audit 3.
              kind: "project", path: "content/da/brochure", type: "page",
              name: "brochure", template: "",
              titles: { fr: "brochure.pdf", en: "brochure.pdf" },
              bodies: { fr: "", en: "" },
              x: "44", y: "18", opens: null, icon: null, wallpaper: null,
              photographs: ["01.jpg"], video: null, doc: "dossier.pdf",
              alt: {}, face: "", languages: ["en", "fr"],
            }, {
              kind: "project", path: "content/da/droit-a-la-page", type: "page",
              name: "droit-a-la-page", template: "",
              titles: { fr: "tout droit.jpg", en: "straight through.jpg" },
              bodies: { fr: "", en: "" },
              x: "46", y: "20", opens: "page", icon: null, wallpaper: null,
              photographs: ["01.jpg"], video: null, doc: null,
              alt: {}, face: "", languages: ["en", "fr"],
            }, {
              kind: "project", path: "content/da/grocery", type: "page", name: "grocery", template: "",
              titles: { fr: "grocery.pdf", en: "grocery.pdf" },
              bodies: { fr: "", en: "" },
              x: "60", y: "40", opens: null, icon: null, wallpaper: null,
              // TWO photographs, not one. With exactly one it trips the
              // lone-photograph rule — a photograph lying on a desk is
              // a photograph, not a page, and is offered no text — and
              // the comparison below would then fail for a reason that
              // has nothing to do with folders against projects.
              photographs: ["01.jpg", "02.jpg"],
              alt: { "01.jpg": "Deux silhouettes sur une plage." },
              video: null, doc: null, languages: ["en", "fr"],
            }],
          }, {
            // A GALLERY AND A SELECTION on the main desktop, which the
            // fixture had neither of — so "offer them only while
            // absent" had nothing to be false about and the main
            // desktop offered all three.
            kind: "desk", path: "content/pellicules", name: "pellicules",
            gallery: true, depth: 1, empty: false, template: "gallery.html",
            type: "folder", titles: { fr: "pellicules", en: "pellicules" },
            bodies: { fr: "", en: "" }, x: "74", y: "24",
            opens: null, icon: null, wallpaper: null, about: null,
            photographs: ["01.jpg"], video: null, doc: null,
            languages: ["en", "fr"], on: [], face: "",
          }, {
            // A CANVAS, which this fixture did not hold. It carried
            // `template: "page.html"` and no `canvas` at all, so every
            // rule the panel keys on `o.canvas` — the list that offers
            // no order, because the page reads none — was dead code
            // here. Audit 3 found it by listing the fields app.js
            // reads against the fields this fixture ever sets.
            kind: "desk", path: "content/travail-selectionne",
            name: "travail-selectionne", gallery: false, canvas: true,
            holds_photographs: true, can_receive: false, depth: 1,
            empty: false, template: "selection.html", type: "folder",
            titles: { fr: "travail sélectionné", en: "selected work" },
            bodies: { fr: "", en: "" }, x: "50", y: "44",
            opens: null, icon: null, wallpaper: null, about: null,
            photographs: ["01.jpg", "02.jpg"], video: null, doc: null,
            languages: ["en", "fr"], on: [], face: "",
          }, {
            // THE FOLDER-PAGE AS A DESK OF ITS OWN, which is what the
            // real model does with every folder holding an `_index.md`
            // — see "ONE FOLDER, ONE SET OF FACTS" in model.py. Without
            // this row `isDesk` was false for it, so the OLD predicate
            // (`isDesk && !gallery`) withheld the wallpaper for the
            // wrong reason and the check could not fail on the bug it
            // was written for.
            kind: "desk", path: "content/da/cosette", type: "page", name: "cosette",
            gallery: false, depth: 2, empty: true, template: "page.html",
            titles: { fr: "maison cosette", en: "maison cosette" },
            bodies: { fr: "Un texte.", en: "Some text." },
            x: "41", y: "57", opens: null, icon: null, wallpaper: null,
            about: null, photographs: [], video: null, doc: null,
            languages: ["en", "fr"],
            // A STOP ON A ROUTE: a project inside a folder-page. It is
            // drawn as no icon, so it has no name under one, no face
            // and no position — and the fixture had nothing in this
            // position, so none of that could be checked.
            on: [{
              kind: "project", path: "content/da/cosette/nocturne", type: "photo",
              name: "nocturne", template: "",
              titles: { fr: "nocturne 01.jpg", en: "nocturne 01.jpg" },
              bodies: { fr: "", en: "" },
              x: "34", y: "43", opens: null, icon: null, wallpaper: null,
              photographs: ["01.jpg"], video: null, doc: null,
              languages: ["en", "fr"], alt: {},
            }],
          }],
        },
      }),
    };
  },
};
sandbox.globalThis = sandbox;

byId.get("view").contentDocument = frameDoc;

const code = readFileSync(new URL("./app.js", import.meta.url), "utf8");
const src0 = code;
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
  // This is the one that was missing. The suppression used to sit below
  // code that reads `model`, which is null on the first load — so it
  // threw before arming, and a click went straight through to the site
  // and opened the window.
  check("the frame is disarmed on the FIRST load, before any tree arrives",
    frameDoc.heard.includes("click"), JSON.stringify(frameDoc.heard));

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

  // Choosing a folder must not walk into it. Asked of the BEHAVIOUR,
  // not of the source: suppressing the site's own click was correct and
  // changed nothing, because the panel then navigated the frame itself.
  const daRow = tree.children.find((r) => /DA/.test(r.innerHTML));
  byId.get("view").src = "/site/";
  if (daRow && daRow.__click) daRow.__click();
  await new Promise((r) => setTimeout(r, 20));
  check("choosing a folder keeps the frame on the desk it sits on",
    byId.get("view").src === "/site/",
    "frame went to " + byId.get("view").src);
  check("something is chosen as soon as it opens, so the editor is not blank",
    look.innerHTML.length > 0 && !/Choisis quelque chose/.test(look.innerHTML),
    JSON.stringify(look.innerHTML.slice(0, 60)));
  check("the editor offers a name to type into", /<input[^>]*data-title/.test(look.innerHTML));
  // REVERSED, 2026-11-14. A DESK renders no body anywhere —
  // `section.html` has no `.content` in it — so the box that was
  // asserted here saved a paragraph onto no page of the site. Where
  // the text IS shown is checked a few lines down, on a project.
  check("and NOT a text to write, because a desk shows no text",
    !/<textarea[^>]*data-body/.test(look.innerHTML));
  check("one box per language, not one for both",
    (look.innerHTML.match(/data-title="/g) || []).length >= 2);

  // A PHOTOGRAPH IS A PHOTOGRAPH.
  //
  // One lying alone on a desk is offered what a photograph has: a
  // name, the picture, what the picture shows, and the bin. Not a text
  // box — its words would appear on a page nothing links to — not a
  // choice about what a click opens, and not a different face, because
  // the face of a photograph is the photograph.
  //
  // REVERSED from "a lone photograph is offered a choice of what its
  // icon opens", 2026-11-14. That switch existed only to rescue the
  // text box; with no text box there is nothing to rescue, and the
  // verb behind it is gone.
  const choose = (name) => {
    const row = tree.children.find((r) => new RegExp(name).test(r.innerHTML));
    if (row && row.__click) row.__click();
    return row !== undefined;
  };
  check("the fixture has a lone photograph to choose", choose("seule"));
  check("a lone photograph is offered no text to write",
    !/data-body/.test(look.innerHTML));
  check("  nor a choice about what clicking it does",
    !/name="opens"/.test(look.innerHTML));
  check("  nor a face other than itself",
    !/data-drop="icon"/.test(look.innerHTML));
  check("  while its name is still hers to change",
    /data-title/.test(look.innerHTML));
  check("  and what it shows is still hers to describe",
    /data-alt/.test(look.innerHTML));
  check("  and she can still throw it away", /id="binall"/.test(look.innerHTML));
  // THE CONTROL. Hiding those three from EVERYTHING would satisfy all
  // of the above and leave her unable to write a word anywhere.
  check("a project that is not a lone photograph keeps its text",
    choose("theodora") && /data-body/.test(look.innerHTML));
  // A TEXT BOX WHERE THE TEXT IS SHOWN. `page.html` renders a body and
  // so does a project, which declares no template and gets it.
  // `section.html` and `gallery.html` render none, so a desk and a
  // gallery are offered none.
  check("and the home desk is offered none either — about me.txt owns those words",
    choose("myBureau") && !/data-body/.test(look.innerHTML));
  check("  while about me.txt, which is the same body, keeps the box",
    choose("about me.txt") && /data-body/.test(look.innerHTML));
  // back to the desk the checks below are written against — this block
  // moved the selection, and the wallpaper and folder-says checks are
  // asked of a bureau
  if (daRow && daRow.__click) daRow.__click();

  // HER ICON: THREE SLOTS, AND ONLY ONE HOLDS THE FACE.
  //
  // It was one box. Drop anything in it and you got an icon; what you
  // had before was not shown, and whether a dropped file beat a
  // declared one was a precedence rule in _icon.html she could not
  // see — so "I chose a photograph" and "the desk draws a folder"
  // were both true at once.
  // A FOLDER'S FACE IS A FOLDER — one slot, the four drawings and a
  // drop for one of her own. A photograph or a GIF there would be a
  // face that contradicts the thing. The pane chosen here is `DA`.
  check("a folder is offered one slot, not three",
    (look.innerHTML.match(/data-face="/g) || []).length === 1
    && /data-face="folder"/.test(look.innerHTML),
    look.innerHTML.slice(0, 120));
  check("  the four drawings, as buttons",
    (look.innerHTML.match(/data-drawn="/g) || []).length === 4);
  check("  AND somewhere to drop a drawing of her own",
    /data-drop="icon-folder"/.test(look.innerHTML)
    && /propre dessin/.test(look.innerHTML));

  // AND A PAGE GETS ALL THREE.
  choose("maison cosette");
  check("a page is offered three slots",
    (look.innerHTML.match(/data-face="/g) || []).length === 3,
    look.innerHTML.slice(0, 120));
  check("  a dossier, a photo and a GIF, each named",
    /data-face="folder"/.test(look.innerHTML)
    && /data-face="photo"/.test(look.innerHTML)
    && /data-face="gif"/.test(look.innerHTML));
  check("  and each with its own drop, so the slot says what she meant",
    /data-drop="icon-folder"/.test(look.innerHTML)
    && /data-drop="icon-photo"/.test(look.innerHTML)
    && /data-drop="icon-gif"/.test(look.innerHTML));
  if (daRow && daRow.__click) daRow.__click();
  check("a bureau also offers its wallpaper",
    /data-drop="wallpaper"/.test(look.innerHTML));
  // A WALLPAPER WHERE THERE IS A DESK TO PUT IT ON. `section.html` is
  // the only template that renders one and `index.html` extends it; a
  // folder-page and a gallery read none. This was `isDesk && !gallery`
  // — and a folder-page IS a desk by that test, so four objects were
  // offered a ground they cannot show.
  check("a folder that is a page is offered none, having no ground",
    choose("maison cosette") && !/data-drop="wallpaper"/.test(look.innerHTML));
  check("  but keeps its text, which its page does render",
    /data-body/.test(look.innerHTML));

  // EXACTLY ONE SLOT IS MARKED, and it is the one the model reports.
  // `douze regards` carries an `icon.gif`; `atelier mirabelle`
  // declares a drawn folder; `grocery` has neither and falls back.
  for (const [row, want] of [["gifly", "gif"], ["drawnly", "folder"],
                             ["grocery", ""]]) {
    choose(row);
    const pane = look.innerHTML;
    const marked = (pane.match(/class="slot is-chosen" data-face="([a-z]+)"/) || [])[1] || "";
    check("a thing wearing a " + (want || "fallback") + " says so, and only that",
      marked === want
      // `class="slot is-chosen"`, not every `is-chosen` in the pane:
      // the chosen DRAWING inside the folder slot carries the same
      // class, so counting them all made this fail on a folder for a
      // reason that was the improvement working.
      && (pane.match(/class="slot is-chosen"/g) || []).length === (want ? 1 : 0),
      "marked: " + marked);
    check("  and it says in words which slot, not just an outline",
      want ? /slot-yes/.test(pane) : !/slot-yes/.test(pane));
    // REVERSED: there is no "aucun des trois" any more. For a folder
    // it was meaningless — the fallback for a folder IS one of the
    // drawings, so it handed back the thing it claimed to remove — and
    // for a page it meant "revert to the first photograph", a state
    // labelled by negation. What a thing with nothing chosen gets is
    // said in words instead.
    check("  and nothing offers to take a choice back by negation",
      !/id="noface"/.test(pane));
    check("  while one with nothing chosen says what it falls back to",
      want ? !/Rien de choisi/.test(pane) : /Rien de choisi/.test(pane));
  }
  if (daRow && daRow.__click) daRow.__click();

  // EACH TYPE IS OFFERED ITS OWN CONTROLS, AND NOT THE OTHERS'.
  //
  // One table, read both ways: every type must have what its row says
  // and must NOT have what another row has and it does not. Without
  // the second half a pane that showed everything would pass.
  //
  // What this replaces: every one of these was worked out from the
  // folder's contents or the title's extension, so a thing she had not
  // filled in yet was offered the wrong boxes — an empty film had
  // nowhere to put its film unless she had typed `.mov`.
  const OFFERS = {
    photo: { want: [/data-title/, /data-alt|n'en tient qu'une/],
             deny: [/data-body/, /data-drop="doc"/, /data-drop="video"/] },
    video: { want: [/data-title/, /data-drop="video"/, /data-drop="poster"/],
             deny: [/data-drop="photos"/, /data-drop="doc"/] },
    page:  { want: [/data-title/, /data-body/, /data-drop="photos"/,
                    /data-drop="doc"/],
             deny: [/data-drop="video"/, /data-drop="poster"/] },
  };
  // `seule`, not `nocturne`: both are photos, but `nocturne` is a stop
  // on a route and a route stop has no name box — nothing shows its
  // name, so there is nothing to type. That is #149 and it is right;
  // it just makes it the wrong pane for comparing TYPES.
  const PANE = { photo: "seule", video: "theodora", page: "maison cosette" };
  for (const [type, rules] of Object.entries(OFFERS)) {
    choose(PANE[type]);
    const pane = look.innerHTML;
    check("a " + type + " is offered what a " + type + " holds",
      rules.want.every((re_) => re_.test(pane)),
      rules.want.filter((re_) => !re_.test(pane)).join(" "));
    check("  and nothing another type holds",
      rules.deny.every((re_) => !re_.test(pane)),
      rules.deny.filter((re_) => re_.test(pane)).join(" "));
  }
  // AND IT SAYS WHAT IT IS, in her words, from the type rather than
  // from what is in the folder: a film with no video yet is still a
  // film.
  choose("theodora");
  check("a film says it is a film", /un film/.test(look.innerHTML));
  choose("seule");
  check("and a photo says it is a photo", /une photo/.test(look.innerHTML));
  // AN EMPTY PHOTO IS STILL A PHOTO. Counting files would call this a
  // page and offer it a text box and a dossier; the type knows better.
  choose("à venir");
  check("a photo with no image yet is still a photo",
    /une photo, vide/.test(look.innerHTML), look.innerHTML.slice(0, 120));
  check("  offered its image, and no text and no dossier",
    /data-drop="photos"/.test(look.innerHTML)
    && !/data-body/.test(look.innerHTML)
    && !/data-drop="doc"/.test(look.innerHTML));
  check("  and told what it is waiting for",
    /attend son image/.test(look.innerHTML));
  if (daRow && daRow.__click) daRow.__click();

  // A PAGE IS A PAGE, WHATEVER IT IS CALLED.
  //
  // `un document`, `une page` and `un dossier` are the same object: a
  // blank page with her content on it. `grocery list.png` could take
  // photographs, a text and a description; `logofolio`, `atelier
  // mirabelle` and `maison cosette` could take none of them — and the
  // only difference was that one has an `index.md` and the others an
  // `_index.md`, which she has never seen and cannot see.
  //
  // THE VERBS WERE ALWAYS WILLING. `add_image`, `set_alt` and
  // `add_doc` all succeed on `logofolio` today, checked directly. Only
  // the panel hid the controls — `isDesk && !gallery`, and a
  // folder-page is in model.desks.
  //
  // So the fixture's folder-page is asked for everything a project is
  // asked for, and the project is asked beside it, so neither can pass
  // alone.
  const SAME = [
    ["a name to type", /data-title/],
    ["a text to write", /data-body/],
    ["somewhere to drop photographs", /data-drop="photos"/],
    ["a description per photograph", /data-alt|hintline/],
    ["somewhere to drop a dossier", /data-drop="doc"/],
    ["and a way to throw it away", /id="binall"/],
  ];
  choose("maison cosette");
  const folderPane = look.innerHTML;
  choose("grocery");
  const projectPane = look.innerHTML;
  for (const [what, re_] of SAME) {
    check("a folder-page is offered " + what,
      re_.test(folderPane), folderPane.slice(0, 80));
    check("  and so is a project, which is the same object",
      re_.test(projectPane));
  }
  // A NAME IS A NAME. The dossier box used to need the title to end in
  // `.pdf`; `maison cosette` has no extension at all and gets one.
  check("and no extension in a name decides any of that",
    !/\.pdf|\.png/i.test("maison cosette"));
  // THE CONTROL: a real DESK is not a page and keeps none of it.
  check("while a bureau is offered no photographs, holding icons not work",
    choose("DA") && !/data-drop="photos"/.test(look.innerHTML));
  if (daRow && daRow.__click) daRow.__click();

  // NO CONTROL FOR A PLACE IT HAS NOT GOT.
  //
  // A thing inside a folder-page is a stop on a route: drawn as no
  // icon, so no name under one, no face, and no position. The route is
  // ordered by folder name.
  check("a stop on a route is offered no name, nothing showing one",
    choose("nocturne") && !/data-title/.test(look.innerHTML));
  check("  nor a face, because no icon is drawn for it",
    !/data-drop="icon"/.test(look.innerHTML));
  check("  nor a position, the route being in name order",
    !/34% \/ 43%/.test(look.innerHTML) && !/pas encore posé/.test(look.innerHTML));
  check("  and it says so, rather than just showing less",
    /dans l'ordre de son nom/.test(look.innerHTML));
  // A PHOTO HOLDS ONE, and `nocturne` has it — so there is nowhere to
  // drop a second, by design: `add_image` would refuse it. What is
  // offered is the picture itself, with its description and its ✕.
  check("  while its photograph and its description are still hers",
    /data-alt/.test(look.innerHTML) && /class="shot"/.test(look.innerHTML)),
  check("  and nowhere to drop a second, which would be refused",
    !/data-drop="photos"/.test(look.innerHTML)
    && /n'en tient qu'une/.test(look.innerHTML));
  check("  and she can still throw it away", /id="binall"/.test(look.innerHTML));

  // THE HOME DESK is drawn as no icon either — but its name IS read,
  // as the browser tab's title, so that one stays.
  check("the home desk is offered no face, being drawn nowhere",
    choose("myBureau") && !/data-drop="icon"/.test(look.innerHTML));
  check("  but keeps its name, which the browser tab shows",
    /data-title/.test(look.innerHTML));

  // THE CONTROL for all of the above: a thing ON a desk keeps all three.
  check("while a thing on a desk keeps its name, its face and its place",
    choose("theodora") && /data-title/.test(look.innerHTML)
    && /data-drop="icon-/.test(look.innerHTML)
    && /32% \/ 12%/.test(look.innerHTML));
  if (daRow && daRow.__click) daRow.__click();
  // REVERSED: THE ROW IS GONE. It was `dans …`, `quoi créer`, a name
  // and a button — four controls to say two things, and she could pick
  // a film and `dans: pellicules`, press Créer and be told no.
  //
  // She right-clicks the surface now. Pointing says where, so the menu
  // offers only what belongs there and the refusal is unreachable
  // rather than explained.
  check("there is no row of selects to make something with",
    !/id="make"/.test(markup) && !/id="kind"/.test(markup)
    && !/id="into"/.test(markup) && !/id="newname"/.test(markup));
  check("and the panel says how to create instead",
    /Clic droit/.test(markup));
  check("and a way to look INSIDE a thing rather than at its desk",
    /id="aspage"/.test(markup) && (listeners.get("aspage:click") || []).length > 0);

  // ARRANGING THE GALLERY, DRIVEN THE WAY A BROWSER DRIVES IT.
  //
  // A gallery is a CSS column flow with no coordinates, so "arrange"
  // can only mean the ORDER — `reorder` writes down a rank per
  // photograph and the columns reflow.
  //
  // THE FIRST THREE VERSIONS ALL PASSED AND ALL DID NOTHING.
  //
  //   one  the call sat after `hook()`'s early return, and a gallery
  //        has no `.desk`, so it was dead code
  //   two  it used HTML5 dragstart/dragover/drop. Synthetic events
  //        behaved; a browser did not — a `.shot` is an <a> round an
  //        <img>, two things with native drags of their own, and the
  //        ghost appeared while the photographs stayed put
  //   three the gesture worked and the verb RENAMED the files to put
  //        them in order, which zola serves from a cache keyed on the
  //        source path — so the page came back identical and the
  //        photographs sprang back. Nothing on this side could see
  //        that: it took a build. See specs/the-order-is-a-property.md
  //
  // So this fires POINTER events, the mechanism the desk's icon drag
  // has used all along, and the stub answers `elementFromPoint` —
  // which is the thing the gesture actually turns on.
  {
    const rects = new Map();
    const shot = (file, top) => {
      const el2 = {
        dataset: { shot: file }, style: {}, draggable: true, on: {},
        addEventListener(k, fn) { (this.on[k] ||= []).push(fn); },
        setPointerCapture() { el2.captured = true; },
        querySelector: () => el2.img,
        img: { draggable: true },
        getBoundingClientRect: () => rects.get(file),
        closest: (sel) => (/data-shot/.test(sel) ? el2 : null),
      };
      rects.set(file, { top, height: 100, left: 0, width: 100 });
      return el2;
    };
    const order = [shot("01.jpg", 0), shot("02.jpg", 100), shot("03.jpg", 200)];
    const holder = {
      children: order,
      insertBefore(node, before) {
        const at = this.children.indexOf(node);
        if (at >= 0) this.children.splice(at, 1);
        const to = before ? this.children.indexOf(before) : this.children.length;
        this.children.splice(to < 0 ? this.children.length : to, 0, node);
      },
    };
    for (const s of order) { s.parentNode = holder; }
    order[0].nextSibling = order[1];
    order[1].nextSibling = order[2];
    order[2].nextSibling = null;
    const gridDoc = {
      __grid: {},
      querySelector: (s) => (s === ".grid" ? gridDoc.__grid
        : s === "[data-desk]" ? { dataset: { desk: "content/pellicules/" } } : null),
      querySelectorAll: (s) => (/data-shot/.test(s) ? holder.children : []),
      // WHAT THE GESTURE TURNS ON: where she let go. A browser answers
      // this; the HTML5 version never needed it, which is part of why
      // it could pass while doing nothing.
      elementFromPoint: (x, y) => order.find((s) => {
        const r = rects.get(s.dataset.shot);
        return y >= r.top && y < r.top + r.height;
      }) || null,
      addEventListener() {}, createElement: () => ({ id: "", textContent: "" }),
      head: { append() {} }, getElementById: () => null,
    };
    byId.get("view").contentDocument = gridDoc;
    if (typeof sandbox.hook === "function") sandbox.hook();

    check("the native drag of a link and an image is taken out of the way",
      order.every((s) => s.draggable === false && s.img.draggable === false),
      JSON.stringify(order.map((s) => s.draggable)));
    check("  and the tip says what the gesture does here",
      /se réarrange/.test(byId.get("tip").textContent),
      byId.get("tip").textContent);

    let sent = null;
    const keep = sandbox.fetch;
    sandbox.fetch = async (url, opts) => {
      if (String(url).includes("/api/do")) sent = JSON.parse(opts.body);
      return keep(url, opts);
    };
    const fire = (el2, kind, ev) => {
      for (const fn of el2.on[kind] || []) fn(ev);
    };
    const fireAwait = async (el2, kind, ev) => {
      for (const fn of el2.on[kind] || []) await fn(ev);
    };

    // A TAP IS NOT A DRAG — and a tap MOVES, because a finger is never
    // still. The first version of this check went straight from down to
    // up with no movement at all, so deleting the 5px threshold
    // entirely left it passing: `moved` is only set inside
    // pointermove, and no pointermove was ever fired.
    fire(order[0], "pointerdown", { button: 0, clientX: 10, clientY: 10 });
    fire(order[0], "pointermove", { clientX: 11, clientY: 12 });
    await fireAwait(order[0], "pointerup", { button: 0, clientX: 11, clientY: 12 });
    check("a tap reorders nothing", sent === null, JSON.stringify(sent));
    let stoppedClick = false;
    fire(order[0], "click", { preventDefault() { stoppedClick = true; },
                              stopImmediatePropagation() {} });
    check("  and still opens the photograph", stoppedClick === false);

    // NOW A REAL DRAG: the third onto the TOP half of the first, so it
    // lands before it. Which half is the easiest thing to get
    // backwards, so the drop is at y=10 of a box 100 tall.
    const third = order[2];
    fire(third, "pointerdown", { button: 0, clientX: 10, clientY: 210 });
    fire(third, "pointermove", { clientX: 12, clientY: 150 });
    check("moving past the threshold picks it up", third.style.opacity === ".45",
      third.style.opacity);
    check("  and the pointer was captured, so it survives leaving the photo",
      third.captured === true);
    await fireAwait(third, "pointerup", { button: 0, clientX: 12, clientY: 10 });
    check("dropping one above another sends the new order",
      sent && sent.verb === "reorder"
      && JSON.stringify(sent.names) === JSON.stringify(["03.jpg", "01.jpg", "02.jpg"]),
      JSON.stringify(sent));
    check("  and it names the gallery it belongs to, not a guess",
      sent && sent.item === "content/pellicules", sent && sent.item);
    // AND THE DRAG IS NOT ALSO A CLICK. The pointer was captured, so
    // the click lands on the photograph she just moved.
    stoppedClick = false;
    fire(third, "click", { preventDefault() { stoppedClick = true; },
                           stopImmediatePropagation() {} });
    check("  and does not also open what she just moved",
      stoppedClick === true);
    sandbox.fetch = keep;

    // LOOKING, NOT ARRANGING, IN THE PHONE VIEW — the desk's rule.
    // `narrowView` is a `let` and unreachable from here, so the button
    // is pressed and the gesture tried.
    for (const fn of listeners.get("asphone:click") || []) fn();
    sent = null;
    sandbox.fetch = async (url, opts) => {
      if (String(url).includes("/api/do")) sent = JSON.parse(opts.body);
      return keep(url, opts);
    };
    fire(order[0], "pointerdown", { button: 0, clientX: 10, clientY: 10 });
    fire(order[0], "pointermove", { clientX: 40, clientY: 210 });
    await fireAwait(order[0], "pointerup", { button: 0, clientX: 40, clientY: 210 });
    sandbox.fetch = keep;
    check("in the phone view a photograph cannot be dragged",
      sent === null, JSON.stringify(sent));
    for (const fn of listeners.get("aswide:click") || []) fn();

    byId.get("view").contentDocument = frameDoc;
  }

  // WHAT MAY BE MADE WHERE, asked of the real function. The menu is
  // drawn into the framed page, so this checks the decision rather
  // than the markup — and the decision is the whole point: a refusal
  // that cannot be reached beats one that is explained.
  // The desks the fixture serves, read back from the tree the panel was
  // given rather than written out twice.
  const DESKS_IN_FIXTURE = () => [
    { path: "content", depth: 0, gallery: false, template: "index.html" },
    { path: "content/da", depth: 1, gallery: false, template: "section.html" },
    { path: "content/pellicules", depth: 1, gallery: true, template: "gallery.html" },
    { path: "content/travail-selectionne", depth: 1, gallery: false,
      template: "page.html" },
  ];
  if (typeof sandbox.whatFitsIn === "function") {
    const names = (p) => sandbox.whatFitsIn(p).map(([k]) => k);
    check("the main desktop offers a folder, and nothing else while"
      + " the gallery and the selection are both there",
      JSON.stringify(names("content")) === JSON.stringify(["folder"]),
      JSON.stringify(names("content")));
    check("a bureau offers a photo, a film and a page",
      JSON.stringify(names("content/da"))
      === JSON.stringify(["photo", "video", "page"]),
      JSON.stringify(names("content/da")));
    check("and a thing that is not a desk offers nothing",
      names("content/da/cosette/nocturne").length === 0);
    check("a gallery offers nothing — it holds the photographs she drops",
      names("content/pellicules").length === 0);
    // AND THE SINGLETONS COME BACK WHEN THEY GO. This is the whole
    // point of the rule: she can clear the desktop and build it again,
    // and the menu offers what is missing.
    // `model` is a `let` in app.js and not reachable from here, so the
    // desks are passed in — which is the function's real input.
    const whole = sandbox.whatFitsIn ? DESKS_IN_FIXTURE() : [];
    const without = (p) => whole.filter((d) => d.path !== p);
    const names2 = (p, ds) => sandbox.whatFitsIn(p, ds).map(([k]) => k);
    check("wipe the gallery and the main desktop offers one again",
      names2("content", without("content/pellicules")).includes("gallery"),
      JSON.stringify(names2("content", without("content/pellicules"))));
    check("wipe the selection and it offers one again",
      names2("content", without("content/travail-selectionne"))
        .includes("selection"));
  } else {
    check("whatFitsIn is reachable", false, "not a function");
  }

  check("a folder's job is explained, because it depends on where it is",
    /propre page|fenêtre|bandeau/.test(look.innerHTML), look.innerHTML.slice(0, 120));

  check("a thing can be thrown away from the panel",
    /id="binall"/.test(look.innerHTML));
  const rows = tree.children;
  // about me.txt is the exception: its position is declared in
  // [extra.items] and no verb writes there, so there is nowhere to drag
  // it to and dragging it would write a coordinate for something that
  // has none.
  // every row but about me.txt, whose position is declared in
  // [extra.items] and which no verb can place
  check("the rows can be dragged, which is how a thing changes folder",
    rows.length > 1 && rows.filter((r) => r.draggable === true).length
                       === rows.length - 1,
    rows.map((r) => (r.draggable ? "+" : "-")).join("")
      + " of " + rows.length);

  // Selecting the PROJECT rather than the desk. By the row that says so:
  // rows are created elements with no id, so every handler lands under
  // ":click", and "run them all" quietly meant "whichever row happens to
  // be last" — which changes the moment the fixture grows.
  const pick = async (what) => {
    const row = tree.children.find((r) => r.innerHTML.includes(what));
    if (row && row.__click) row.__click();
    await new Promise((r) => setTimeout(r, 20));
    return Boolean(row);
  };
  check("the film has a row to choose", await pick("theodora.jpeg"));
  check("a film offers somewhere to put the film",
    /data-drop="video"/.test(look.innerHTML), look.innerHTML.slice(0, 120));
  check("and somewhere for its affiche",
    /data-drop="poster"/.test(look.innerHTML));
  check("a film is not asked for a PDF",
    !/data-drop="doc"/.test(look.innerHTML));

  // ---- you can SEE that the film landed ----------------------------
  // "I had been dropping it ten times before noticing the video was
  // already there." It said the file name, in the same grey box as
  // before it arrived.
  check("a film that is there says so, by name",
    /class="landed"/.test(look.innerHTML) && /film\.mp4/.test(look.innerHTML),
    look.innerHTML.slice(0, 200));
  check("and shows the frame rather than a word",
    /media\/content\/da\/theodora\/poster\.png/.test(look.innerHTML));
  check("so the box no longer asks for a film it already has",
    !/Dépose la vidéo ici/.test(look.innerHTML));

  // ---- only the box that will take THIS file lights up -------------
  // "when I want to drop a video plenty of placeholders highlight"
  const drag = (...types) => {
    const ev = { preventDefault() {}, target: { closest: () => null },
                 dataTransfer: { items: types.map((t) => ({ kind: "file", type: t })) } };
    for (const fn of listeners.get("look:dragover") || []) fn(ev);
    const zones = {};
    for (const z of look.querySelectorAll("[data-drop]")) {
      zones[z.dataset.drop] = z._cls.has("can") ? "can"
        : z._cls.has("cannot") ? "cannot" : "-";
    }
    return zones;
  };

  // ON A FILM, whose boxes are its video, its affiche and its icon.
  // There is no photographs box on a film any more — a video holds its
  // video and nothing else, and `add_image` refuses one — so the old
  // assertions about `z.photos` here were about an object the engine
  // now forbids.
  let z = drag("video/quicktime");
  check("dragging a video lights the film box",
    z.video === "can", JSON.stringify(z));
  check("and tells the affiche it cannot have it",
    z.poster === "cannot", JSON.stringify(z));
  z = drag("image/jpeg");
  check("dragging a photograph onto a film lights only its affiche",
    z.poster === "can" && z.video === "cannot", JSON.stringify(z));
  z = drag("");
  check("a file whose type the browser will not say lights everything,"
    + " rather than guiding wrong",
    Object.values(z).every((v) => v === "can"), JSON.stringify(z));

  // AND ON A PAGE, which is where photographs and dossiers go.
  choose("maison cosette");
  z = drag("image/jpeg");
  check("dragging a photograph onto a page lights the photographs",
    z.photos === "can", JSON.stringify(z));
  check("and tells the dossier it cannot have it",
    z.doc === "cannot", JSON.stringify(z));
  z = drag("application/pdf");
  check("dragging a PDF lights the dossier, and only that",
    z.doc === "can" && z.photos === "cannot", JSON.stringify(z));
  await pick("theodora.jpeg");

  for (const fn of listeners.get("look:dragleave") || []) fn({});
  const after = {};
  for (const zz of look.querySelectorAll("[data-drop]"))
    after[zz.dataset.drop] = zz._cls.has("can") || zz._cls.has("cannot");
  check("and when the drag leaves, nothing stays lit",
    Object.values(after).every((v) => v === false), JSON.stringify(after));

  // ---- a description per photograph --------------------------------
  // Every photograph on the site carried alt="", which tells a screen
  // reader there was nothing there. It was writable by hand in the .md
  // and nowhere in the panel.
  //
  // ON A PAGE. These ran on `theodora`, which was a film carrying two
  // photographs — an object the engine now forbids, since a video
  // holds its video and its affiche and nothing else. Photographs live
  // on a page, so that is where they are described.
  choose("maison cosette");
  check("each photograph has a box for what it shows",
    (look.innerHTML.match(/data-alt="/g) || []).length === 2,
    look.innerHTML.slice(0, 300));
  check("and the one already described shows its words",
    /value="Deux silhouettes sur une plage\."/.test(look.innerHTML));
  check("the panel says the description is for people who cannot see it",
    /ne voient pas/.test(look.innerHTML));
  let saidAlt = null;
  const keepFetch = sandbox.fetch;
  sandbox.fetch = async (url, opts) => {
    if (String(url).includes("/api/do")) saidAlt = JSON.parse(opts.body);
    return keepFetch(url, opts);
  };
  for (const fn of listeners.get("alt:02.jpg:change") || []) await fn();
  sandbox.fetch = keepFetch;
  check("typing one sends it for THAT photograph",
    saidAlt && saidAlt.verb === "set_alt"
      && saidAlt.item === "content/da/cosette"
      && saidAlt.name === "02.jpg", JSON.stringify(saidAlt));

  // ---- the dossier -------------------------------------------------
  // "I created a .pdf inside a folder and it creates a pdf and keeps
  // asking for images to drop in." It asked for photographs because the
  // engine could not show a PDF at all.
  check("the dossier has a row to choose", await pick("grocery.pdf"));
  check("a dossier is offered somewhere to put its PDF",
    /data-drop="doc"/.test(look.innerHTML), look.innerHTML.slice(0, 200));
  // REVERSED, 2026-11-14. "Ce dossier attend son PDF" was announced
  // because the TITLE ended in `.pdf` — and a name is a name. A page
  // may hold a dossier whatever it is called, so saying it is waiting
  // for one told her the three letters had committed her to something.
  // They had not. What it says instead, while the folder is empty, is
  // "Rien dedans pour l'instant", which is true of any empty page.
  check("and is not told its name has committed it to a PDF",
    !/attend son PDF/.test(look.innerHTML)
    && !/JPEG/i.test(look.innerHTML), look.innerHTML.slice(0, 300));
  check("and the panel says it will be shown, not downloaded",
    /téléchargement/.test(look.innerHTML));

  // ---- the home desk: the bandeau, and about me.txt ----------------
  // Neither had anywhere to be edited. The bandeau is on every page and
  // belongs to no desk; the portrait had no convention at all, so the
  // about window was prose and nothing else.
  const homeRow = tree.children.find((r) => /myBureau/.test(r.innerHTML));
  check("the home desk has a row of its own", Boolean(homeRow));
  if (homeRow && homeRow.__click) homeRow.__click();
  await new Promise((r) => setTimeout(r, 20));
  check("the home desk offers the two words in the bandeau",
    /id="who"/.test(look.innerHTML) && /id="studio"/.test(look.innerHTML),
    look.innerHTML.slice(0, 160));
  check("and fills them with what config.toml actually says, not a default",
    /value="a demo of"/.test(look.innerHTML) && /value="myBureau"/.test(look.innerHTML));
  check("it says which name is live, so changing the wrong one is not silent",
    /démo/.test(look.innerHTML));
  check("the home desk is no longer also the about editor",
    !/data-drop="about"/.test(look.innerHTML));

  // ---- about me.txt, on its own ------------------------------------
  // "when clicking on about me there is no possibility to choose
  // anything - neither to add any text". It was a block at the bottom of
  // the home desk's pane, under that desk's own name and text.
  check("about me.txt has a row of its own", await pick("about me.txt"));
  check("its pane is about IT, not about the home desk",
    /<h2>about me\.txt<\/h2>/.test(look.innerHTML), look.innerHTML.slice(0, 120));
  check("it offers somewhere to put her portrait",
    /data-drop="about"/.test(look.innerHTML));
  check("and shows the one that is already there",
    /media\/content\/about\.jpg/.test(look.innerHTML), look.innerHTML.slice(0, 220));
  check("it offers her text, one box per language",
    (look.innerHTML.match(/data-body="/g) || []).length === 2,
    look.innerHTML.slice(0, 400));
  check("filled with the text that is actually there",
    /Je suis directrice artistique/.test(look.innerHTML));
  check("and not a name to type, which is not hers to change here",
    !/data-title/.test(look.innerHTML));
  check("nor a wallpaper, nor photographs, nor a way to throw it away",
    !/data-drop="wallpaper"/.test(look.innerHTML)
    && !/data-drop="photos"/.test(look.innerHTML)
    && !/id="binall"/.test(look.innerHTML));

  // TYPING IN IT. Not "is there a box" — does the box reach the server,
  // with the right verb, the right language and the right file.
  let said2 = null;
  const realFetch2 = sandbox.fetch;
  sandbox.fetch = async (url, opts) => {
    if (String(url).includes("/api/do")) said2 = JSON.parse(opts.body);
    return realFetch2(url, opts);
  };
  // fired by key: each render re-makes the boxes, and the listener for
  // the French one lands under "body:fr:change"
  for (const fn of listeners.get("body:fr:change") || []) await fn();
  sandbox.fetch = realFetch2;
  check("typing in its text box writes the home page's own body",
    said2 && said2.verb === "set_body" && said2.item === "content"
      && said2.lang === "fr", JSON.stringify(said2));

  // Typing a new name must reach the server as set_identity, with BOTH
  // words — sending one would blank the other.
  fetched = [];
  let sent = null;
  const realFetch = sandbox.fetch;
  sandbox.fetch = async (url, opts) => {
    if (String(url).includes("/api/do")) sent = JSON.parse(opts.body);
    return realFetch(url, opts);
  };
  // through the same door app.js uses, because these two were drawn by
  // the panel and are not in app.html
  const grab = (id) => sandbox.document.getElementById(id);
  grab("who").value = "le studio de";
  grab("studio").value = "VALENTINA";
  for (const fn of listeners.get("who:change") || []) await fn();
  check("typing a new bandeau sends it, and sends both words together",
    sent && sent.verb === "set_identity" && sent.owner === "le studio de"
      && sent.studio === "VALENTINA", JSON.stringify(sent));
  sandbox.fetch = realFetch;
  // A config change is served stale with a 200 for about three seconds,
  // so "the page answered" is not "the page changed". Reloading on the
  // first 200 put the OLD name back in front of her.
  check("and the frame waits for the new name to be in the page, not just for a 200",
    /reframe\(body\.verb === "set_identity"/.test(src0)
    && /includes\(expect\)/.test(src0));

  // Clicking in the frame must EDIT, not fire the site's own dynamics.
  // Those belong to a visitor; while she is arranging a desk they carry
  // her away from the thing she just touched.
  const src2 = readFileSync(new URL("./app.js", import.meta.url), "utf8");
  check("a click in the page is caught before the site acts on it",
    /addEventListener\("click"[\s\S]{0,260}stopImmediatePropagation/.test(src2));
  check("and double-click is how she goes in on purpose",
    /addEventListener\("dblclick"/.test(src2));

  // WHAT A DOUBLE-CLICK OPENS, asked of the behaviour.
  //
  // The panel suppresses the site's own click — it must, or choosing
  // anything on a desk navigates — and then has to reproduce what the
  // site would have done. It did not: `about me.txt` was special-cased
  // to open its window and everything else was sent to its page. So a
  // photograph, which opens IN PLACE on the site, opened a page with a
  // white ground and a paragraph on it. The editor was showing her
  // something the site does not do.
  //
  // `data-window` is the engine's answer, written by _icon.html and
  // acted on by desk.js. The panel reads it now instead of deciding.
  if (typeof sandbox.hook === "function") sandbox.hook();
  const fire = (icon) => (icon.on.dblclick || []).forEach(
    (fn) => fn({ preventDefault() {}, stopImmediatePropagation() {} }));
  const srcWas = byId.get("view").src;

  fire(frameIcons[1]);
  check("a photograph opens in place, as it does on the site",
    frameDialogs["preview-da-theodora"].opened === true);
  // NOT "and the frame did not move". That was tried: setMode("page")
  // navigates to whatever is CHOSEN, and firing a dblclick here does
  // not go through the pointerup that chooses — so the assertion
  // passed with the bug in place. The dialog being opened is the thing
  // that distinguishes the two outcomes, so it is the thing asserted.

  fire(frameIcons[2]);
  check("about me.txt opens its window — the case that was hardcoded",
    frameDialogs.about.opened === true);

  // THE CONTROL. A panel that opened a dialog for everything would
  // satisfy both of those and break going into a bureau.
  fire(frameIcons[0]);
  check("while a bureau, which opens nothing, still goes in",
    byId.get("view").src !== srcWas,
    "frame stayed at " + byId.get("view").src);
  byId.get("view").src = srcWas;
  check("what she chose is outlined in the real page",
    /studio-chosen/.test(src2));
  check("throwing a thing away lands her on the desk it was on, not nowhere",
    /const home = o\.path\.split\("\/"\)\.slice\(0, -1\)/.test(src2)
    && /const back = find\(home\)/.test(src2));

  // Choosing a folder must not walk into it. Suppressing the site's own
  // click was correct and made no difference, because the panel then
  // navigated the frame itself — the same outcome by another route.
  // Filing by dragging onto a folder, and the guardrails that decide
  // which folders will take it. The rules live in canTake(); the server
  // refuses the same cases regardless, so this is about not making her
  // find out by being told no.
  const src4 = readFileSync(new URL("./app.js", import.meta.url), "utf8");
  check("dropping a thing onto a folder files it there",
    /verb: "move", item: path, into: target/.test(src4));
  // Not "does the source say gallery" — that went stale the moment the
  // rule moved. What matters is that the panel ASKS the model instead of
  // carrying its own copy; whether the model is right is checked against
  // the server in tools/studio/check.py.
  check("the panel asks the model what may receive, rather than deciding",
    /!k\.can_receive/.test(src4) && !/k\.gallery\) return false/.test(src4));
  check("nor is a thing's own inside",
    /targetPath\.startsWith\(movingPath \+ "\/"\)/.test(src4));
  check("nor the folder it is already in",
    /deskOf\(\{ path: movingPath \}\) === targetPath/.test(src4));
  check("the folder she is aiming at is lit up in the page",
    /studio-aim/.test(src4));
  // BY THE CLAUSE, NOT BY THE CONDITION. This said so and then pinned
  // `if (!moved || !onDesk)` anyway, which is the whole condition in a
  // shorter coat — it broke again the moment a third thing that cannot
  // be placed was added, while what it is for was still true. What
  // matters is that the guard is CONSULTED, not what it sits beside.
  // A WHOLE FOLDER IN ONE GESTURE. A browser cannot browse her disk,
  // but it can take a folder — which removes the second window she had
  // to arrange beside the panel and drag out of.
  const html4 = readFileSync(new URL("./app.html", import.meta.url), "utf8");
  check("there is a way to add a folder, not only a file",
    /id="adddir"/.test(html4) && /id="pickdir"/.test(html4));
  check("and the picker really asks for a directory",
    /webkitdirectory/.test(html4));

  // macOS writes a .DS_Store into every folder a Finder window has been
  // opened on. The server refuses it, correctly — and she would get an
  // error about a file she never chose, which is the same noise that
  // used to stop her preview.
  check("hidden files are dropped before the server ever sees them",
    /startsWith\("\."\)/.test(src4));
  check("and so is anything deeper than the folder she picked",
    /parts\(f\)\.length === 2/.test(src4));
  // `[^)]*` here could never reach the flag: it stops at the first `)`,
  // which is inside `parts(b)`. The check failed from the moment it was
  // written, and counting the passing lines hid it.
  check("the photographs go in the order their names put them",
    /localeCompare\([\s\S]{0,80}numeric: true/.test(src4));
  check("the project is made first, and the files go into what was made",
    /verb: "new_project"[\s\S]{0,400}into=\$\{encodeURIComponent\(made\.made\)/.test(src4));
  check("picking the same folder twice is possible",
    /el\("pickdir"\)\.value = ""/.test(src4));

  // WHAT SHE IS TYPING SURVIVES A REBUILD. The editor pane is built
  // from a string and paint() rebuilds it on every tree update — and
  // those arrive on their own, after any verb and whenever the watcher
  // sees zola finish. Everything saves on `change`, which fires on
  // blur, so unsaved text lives in the DOM: exactly the thing being
  // replaced.
  //
  // Four separate things, because three of them can each be right while
  // the whole is useless.
  check("a rebuild is refused while she is in a field",
    /function inspect\(o\) \{\s*if \(typing\(\)\)/.test(src4));
  check("and `typing` means a field in THIS pane, not anywhere",
    /look\.contains\(a\)/.test(src4)
    && /TEXTAREA|INPUT/.test(src4));
  check("leaving the pane rebuilds what was deferred",
    /focusout/.test(src4) && /if \(!stale\) return/.test(src4));
  check("but moving between its own fields does not",
    /relatedTarget && look\.contains\(e\.relatedTarget\)\) return/.test(src4));
  check("and the rebuild uses what is chosen NOW, not what was captured",
    /setTimeout\(\(\) => \{ if \(chosen\) inspect\(find\(chosen\)\); \}/.test(src4));

  // EVERY REQUEST IS BOUNDED. `fetch` waits forever by default, and the
  // lamp is the panel's only signal that something is happening — a
  // server that HANGS used to leave it lit for the rest of the session
  // with nothing to tell her. Three separate things, because having the
  // controller and never passing its signal would abort nothing.
  check("a request cannot wait forever",
    /new AbortController\(\)/.test(src4) && /PATIENCE/.test(src4));
  check("and the signal actually reaches the request",
    /fetch\(q\(path\), \{[^}]*signal: stop\.signal/.test(src4));
  check("giving up is told apart from losing the server",
    /AbortError/.test(src4));
  check("and the timer is cleared whichever way it ends",
    /finally \{\s*clearTimeout\(giveUp\)/.test(src4));

  check("only an icon on the desk itself is given a position",
    /const onDesk = desk\.contains\(icon\)/.test(src4)
    && /if \([^)]*!onDesk[^)]*\)/.test(src4));

  // THE PHONE VIEW IS FOR LOOKING. A position is read back out of the
  // page after the site has placed the icon; in a 390px frame that
  // reads a grid cell, so a drag there would rewrite her DESKTOP
  // layout with numbers that mean nothing. Both halves are asserted
  // because gating the drop while still aiming would light folders she
  // cannot file into.
  // BOTH CLAUSES, IN THE SAME CONDITION. The first version of this
  // asked only for an `if` mentioning narrowView — and there is
  // another one, on the aiming — so it passed with the drop gate
  // removed. Lookaheads, so the order of the clauses is free but the
  // pairing is not.
  check("a drag in the phone view cannot place anything",
    /let narrowView = false/.test(src4)
    && /if \((?=[^)]*!onDesk)(?=[^)]*narrowView)[^)]*\)/.test(src4));
  check("and it does not aim at folders either while looking",
    /if \(!from \|\| narrowView\) return;/.test(src4));
  check("the two widths are a toggle, like the two modes beside them",
    /aswide/.test(src4) && /asphone/.test(src4)
    && /setAttribute\("aria-pressed"/.test(src4));

  const css = readFileSync(new URL("./app.css", import.meta.url), "utf8");
  // FLATTENED FIRST. The rule-splitting below keys on braces, and an
  // @media block nests them — so every rule inside one was swallowed
  // into its parent and never examined. Both checks that read this file
  // silently stopped looking at the narrow-screen rules, which is
  // exactly where the layout bugs live. Comments go too: one mentioning
  // a selector was enough to make a rule look like it matched.
  const flat = css.replace(/\/\*[\s\S]*?\*\//g, "")
                  .replace(/@media[^{]*\{/g, "");
  const rules = [...flat.matchAll(/(^|\})([^{}]+)\{([^}]*)\}/g)]
    .map((m) => ({ sel: m[2].trim(), body: m[3] }));

  // ---- grid placement only on things the grid actually owns --------
  // The narrow-screen rules positioned `.tree`, which lives INSIDE
  // `.side` and is not a child of the grid — so the declaration did
  // nothing, the left column was auto-placed into row 1 alone, and with
  // a second row beneath it the list was cut off from below.
  //
  // The children are read out of app.html rather than listed here, so
  // this stays true when the markup changes.
  const VOID = new Set(["area", "base", "br", "col", "embed", "hr", "img",
                        "input", "link", "meta", "source", "track", "wbr"]);
  const frameBlock = markup.slice(markup.indexOf('<main class="frame">'));
  const kids = new Set();
  {
    let depth = 0;
    const tag = /<(\/?)([a-z]+)([^>]*)>/g;
    let m;
    while ((m = tag.exec(frameBlock))) {
      const closing = m[1] === "/", name = m[2], attrs = m[3];
      if (closing) { depth--; if (depth <= 0) break; continue; }
      // void elements never close, so counting them as open put the
      // depth permanently out and the scan missed .stage and .look
      if (/\/$/.test(attrs) || VOID.has(name)) continue;
      depth++;
      if (depth === 2) {
        const cls = /class="([^"]+)"/.exec(attrs);
        if (cls) cls[1].split(/\s+/).forEach((c) => kids.add(c));
      }
    }
  }
  check("app.html really has the three panes the layout places",
    kids.has("side") && kids.has("stage") && kids.has("look"),
    [...kids].join(" "));

  const placed = new Set();
  for (const r of rules) {
    if (!/grid-(column|row)\s*:/.test(r.body)) continue;
    for (const sel of r.sel.split(",")) {
      const cls = /^\s*\.([a-z-]+)\s*$/.exec(sel);
      if (cls) placed.add(cls[1]);
    }
  }
  const strays = [...placed].filter((c) => !kids.has(c));
  check("nothing is given a grid position that the grid cannot place",
    strays.length === 0, "placed but not a child of .frame: " + strays.join(", "));

  check("a long name in the list is shortened, not sliced by the column",
    /text-overflow:\s*ellipsis/.test(css) && /\.row\s*>\s*span:first-child/.test(css));

  // BY RULE, not by a regex over the whole file. The old version looked
  // for "display:none ... } /* ...look..." anywhere, which a COMMENT
  // mentioning .look was enough to trip — and it would have missed
  // `.frame .look { display: none }` entirely. Asked properly: does any
  // rule that selects the editor hide it.
  const hiding = rules
    .filter((r) => /\blook\b/.test(r.sel) && /display:\s*none/.test(r.body))
    .map((r) => r.sel);
  check("and no rule anywhere hides the editor",
    hiding.length === 0, "hidden by: " + hiding.join(" / "));

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

  // ---- a photo has no page to look at ------------------------------
  //
  // zola builds one for every thing in content/, but NOTHING ON THE
  // SITE LINKS TO A PHOTOGRAPH'S. Its icon carries `data-window`, so a
  // click opens the picture big, in place, over the desk. "regarder"
  // took her to the page behind it instead — a white sheet with the
  // photograph in the middle and a paragraph nobody wrote — which is
  // the same mistake the double-click handler already names: she was
  // being shown something the site does not do.
  // DRIVEN THROUGH THE BUTTON SHE PRESSES. `setMode` is a `const`
  // arrow and a `const` at the top of a script is not a property of
  // the vm context, so there is nothing to call — and the paths below
  // must be ones the FIXTURE really holds, because setPressed looks
  // the chosen thing up in the model to ask whether it is a photo.
  const press = (id) => {
    for (const fn of listeners.get(id + ":click") || []) fn({});
  };
  // THE FIXTURE'S OWN ROWS, not literals written here: `select` hands
  // the thing to `inspect`, which reads languages, titles, bodies and
  // the rest — a half-made object throws before the check runs. And
  // setPressed looks the chosen path up in the model, so it has to be
  // a path the model really holds.
  const everyRow = [];
  {
    const answer = await (await sandbox.fetch("/api/tree")).json();
    const walk = (x) => { everyRow.push(x); (x.on || []).forEach(walk); };
    (answer.tree.desks || []).forEach(walk);
  }
  const seule = everyRow.find((r) => r.path === "content/da/seule");
  const page_ = everyRow.find((r) => r.path === "content/da/grocery");
  if (typeof sandbox.select === "function" && seule && page_
      && (listeners.get("aspage:click") || []).length) {
    const view2 = byId.get("view");

    sandbox.select(page_);
    press("aspage");
    sandbox.select(page_);
    check("a page looked at is its own page",
      /\/site\/da\/grocery\/$/.test(view2.src), view2.src);

    // THE ONE THAT WAS WRONG. Same mode, a photo chosen, and the frame
    // must stay on the desk it sits on.
    sandbox.select(seule);
    check("a photo looked at is the desk it sits on, not a blank page",
      /\/site\/da\/$/.test(view2.src), view2.src);
    check("  and the button that asks for a page is turned off",
      byId.get("aspage").disabled === true);
    check("  and says why, rather than just refusing",
      /pas de page/.test(byId.get("aspage").title || ""),
      byId.get("aspage").title);

    // AND IT COMES BACK. Disabled for the photograph, not for good.
    sandbox.select(page_);
    check("choosing something with a page offers it again",
      byId.get("aspage").disabled === false);
    check("  and her choice of view was not thrown away",
      /\/site\/da\/grocery\/$/.test(view2.src), view2.src);
    press("asdesk");
  } else {
    check("the fixture holds a photo and a page to drive this with", false);
  }

  // ---- placing a picture on the canvas ----------------------------
  //
  // travail sélectionné holds photographs now, like pellicules, and
  // its page places each one: a left, a top and a width, all three in
  // percentages of the PAGE WIDTH. Drag the picture to move it; drag
  // its bottom-right corner to size it. See specs/the-canvas.md.
  //
  // THE CANVAS HAS NO `.desk` EITHER, which is the trap the gallery
  // drag fell into twice: the call has to come before hook()'s early
  // return or it is dead code that every check still passes.
  //
  // The canvas here is 1000px wide, so a pixel is a tenth of a
  // percent and the arithmetic is readable.
  {
    const made = [];
    const fig = (file, x, y, w) => {
      const box = { left: x * 10, top: y * 10, width: w * 10, height: w * 10 * 2 / 3 };
      const el2 = {
        dataset: { shot: file }, on: {},
        style: {
          vals: { "--x": String(x), "--y": String(y), "--w": String(w) },
          setProperty(k, v) { this.vals[k] = v; },
          getPropertyValue(k) { return this.vals[k] ?? ""; },
        },
        addEventListener(k, fn) { (this.on[k] ||= []).push(fn); },
        setPointerCapture() { el2.captured = true; },
        querySelector: () => el2.img,
        img: { draggable: true },
        getBoundingClientRect: () => ({
          left: box.left, top: box.top, width: box.width, height: box.height,
          right: box.left + box.width, bottom: box.top + box.height,
        }),
      };
      made.push(el2);
      return el2;
    };
    const one = fig("01.jpg", 30, 0, 55);
    const two = fig("02.jpg", 2, 48, 28);
    const canvasEl = {
      dataset: { desk: "content/travail-selectionne/" },
      getBoundingClientRect: () => ({ left: 0, top: 0, width: 1000, height: 3000 }),
      querySelectorAll: () => made,
    };
    const canvasDoc = {
      querySelector: (s) => (s === ".canvas" ? canvasEl : null),
      querySelectorAll: (s) => (/data-shot/.test(s) ? made : []),
      addEventListener() {}, createElement: () => ({ id: "", textContent: "" }),
      head: { append() {} }, getElementById: () => null,
    };
    byId.get("view").contentDocument = canvasDoc;
    if (typeof sandbox.hook === "function") sandbox.hook();

    check("the tip says what the gesture does on a canvas",
      /coin en bas/.test(byId.get("tip").textContent),
      byId.get("tip").textContent);
    check("  and the picture's own native drag is out of the way",
      made.every((m) => m.img.draggable === false));

    const fire = (el2, kind, ev) => { for (const fn of el2.on[kind] || []) fn(ev); };
    const fireAwait = async (el2, kind, ev) => {
      for (const fn of el2.on[kind] || []) await fn(ev);
    };
    let sent = null;
    const keepFetch = sandbox.fetch;
    sandbox.fetch = async (url, opts) => {
      if (opts && opts.body) sent = JSON.parse(opts.body);
      return { ok: true, json: async () => ({ n: 2, did: {} }) };
    };

    // A TAP IS NOT A PLACEMENT, and a tap moves — a finger is never
    // still. Without a pointermove the threshold is never reached, so
    // a check that goes straight from down to up would pass with the
    // threshold deleted.
    fire(one, "pointerdown", { button: 0, clientX: 400, clientY: 20 });
    fire(one, "pointermove", { clientX: 402, clientY: 21 });
    await fireAwait(one, "pointerup", { clientX: 402, clientY: 21 });
    check("a tap places nothing", sent === null, JSON.stringify(sent));

    // MOVED: 150px right and 300px down on a 1000px canvas, which is
    // +15 and +30 — and `top` is divided by the WIDTH, not the
    // height, because that is the unit it is stored in. Dividing by
    // the height here would give +10 and put the picture somewhere
    // other than under her finger.
    fire(one, "pointerdown", { button: 0, clientX: 400, clientY: 20 });
    fire(one, "pointermove", { clientX: 550, clientY: 320 });
    await fireAwait(one, "pointerup", { clientX: 550, clientY: 320 });
    check("dragging a picture writes where she put it",
      sent && sent.verb === "place_shot" && sent.item === "content/travail-selectionne"
      && sent.name === "01.jpg", JSON.stringify(sent));
    check("  moved by exactly what the pointer moved, in width-percent",
      sent && sent.left === 45 && sent.top === 30,
      JSON.stringify(sent && [sent.left, sent.top])); 
    check("  and its width is untouched by a move",
      sent && sent.width === 55, JSON.stringify(sent && sent.width));
    check("  and she sees it move while she drags, not only after",
      one.style.getPropertyValue("--x") === "45");

    // SIZED: the gesture starts inside the bottom-right corner. 02 is
    // at left 2, top 48, width 28 — so its box is 20..300 across and
    // 480..666 down, and a grab at 295,660 is within 18px of the
    // corner.
    sent = null;
    fire(two, "pointerdown", { button: 0, clientX: 295, clientY: 660 });
    fire(two, "pointermove", { clientX: 395, clientY: 660 });
    await fireAwait(two, "pointerup", { clientX: 395, clientY: 660 });
    check("dragging the corner sizes it instead of moving it",
      sent && sent.name === "02.jpg" && sent.width === 38
      && sent.left === 2 && sent.top === 48, JSON.stringify(sent));

    // AND NOTHING HANGS OFF THE RIGHT EDGE. The verb clamps too, but
    // what she sees while dragging has to agree with what is written
    // or the picture jumps on reload.
    sent = null;
    fire(two, "pointerdown", { button: 0, clientX: 295, clientY: 660 });
    fire(two, "pointermove", { clientX: 1400, clientY: 660 });
    await fireAwait(two, "pointerup", { clientX: 1400, clientY: 660 });
    check("  and a corner dragged past the edge stops at it",
      sent && sent.left + sent.width === 100, JSON.stringify(sent));

    // LOOKING, NOT ARRANGING, in the phone view — the desk's rule and
    // the gallery's.
    sent = null;
    if (typeof sandbox.setWidth === "function") sandbox.setWidth(true);
    fire(one, "pointerdown", { button: 0, clientX: 400, clientY: 20 });
    fire(one, "pointermove", { clientX: 600, clientY: 400 });
    await fireAwait(one, "pointerup", { clientX: 600, clientY: 400 });
    check("the phone view looks and does not place", sent === null,
      JSON.stringify(sent));
    if (typeof sandbox.setWidth === "function") sandbox.setWidth(false);
    sandbox.fetch = keepFetch;
  }

  // ---- the shapes this fixture never had --------------------------
  //
  // AUDIT 3 listed every field app.js reads against every field this
  // fixture ever sets to something. Four came back never: `canvas`,
  // `doc`, `opens` and `holds`. Each is a branch the panel takes and
  // nothing here had ever taken — and giving the fixture a canvas
  // immediately failed a check whose label said the selection was
  // already there, because the panel was still looking for one by its
  // OLD template name and offering a second. See specs/the-audit.md.
  if (typeof sandbox.kindOf === "function") {
    const say = sandbox.kindOf;
    check("a page holding a dossier is named as one",
      say({ kind: "project", doc: "dossier.pdf", photographs: ["01.jpg"] })
      === "dossier · page");
    check("a thing that asks for its page is named as one",
      say({ kind: "project", opens: "page", photographs: ["01.jpg"], doc: null })
      === "projet · page");
    check("  and a film still outranks both",
      say({ kind: "project", video: "film.mp4", doc: "x.pdf",
            opens: "page", photographs: [] }) === "film");
    check("while one photograph is still one photograph",
      say({ kind: "project", photographs: ["01.jpg"], doc: null, opens: null })
      === "une photo");
  } else {
    check("the panel exposes kindOf, so what a row is called can be driven", false);
  }

  // ---- where she was, across a reload of the panel -----------------
  //
  // THE COMPLAINT: "every time I click refresh it sends me to the main
  // page". Reloading the panel is the obvious way to see the site as it
  // really is, and it threw the place away — the panel booted onto the
  // first desk and the frame onto /site/.
  //
  // `back()` is what boot calls. Driven here with a real localStorage,
  // since with none at all it falls back to the first desk and a restore
  // that never happens looks exactly like one that works.
  //
  // READ THROUGH THE FRAME AND THE STORE, not through `chosen`: app.js
  // declares its state with `let`, and a `let` at the top of a script
  // is NOT a property of the context — `sandbox.chosen` is undefined
  // whatever the panel is doing, and a check against it passes or fails
  // for reasons that have nothing to do with the panel. The frame's url
  // is what she actually sees; the store is what the next reload reads.
  const where = () =>
    JSON.parse(sandbox.localStorage.getItem("mybureau.where") || "null");

  if (typeof sandbox.back === "function" && typeof sandbox.paint === "function") {
    sandbox.localStorage.setItem("mybureau.where", JSON.stringify(
      { chosen: "content/da", mode: "desk", src: "/site/da/" }));
    byId.get("view").src = "/site/";
    await sandbox.back();
    check("a reload comes back to the page she was looking at",
      byId.get("view").src === "/site/da/", byId.get("view").src);

    // AND THE LIVE SELECTION IS HERS TOO, not just the frame. Written
    // fresh from the panel's own state — the stored entry is cleared
    // first, so this cannot pass by reading back what was seeded.
    sandbox.localStorage.removeItem("mybureau.where");
    sandbox.paint();
    check("  and the thing she had chosen is chosen again",
      where() && where().chosen === "content/da", JSON.stringify(where()));
    check("  so moving about is what writes it down", where() !== null);

    // A THING SHE THREW AWAY between two visits must not strand her in
    // the site's 404 — which is what an unchecked stored url does.
    sandbox.localStorage.setItem("mybureau.where", JSON.stringify(
      { chosen: "content/da/gone-for-good", mode: "page",
        src: "/site/da/gone-for-good/" }));
    await sandbox.back();
    check("a place that no longer exists falls back to the first desk",
      byId.get("view").src !== "/site/da/gone-for-good/"
      && where() && where().chosen === "content",
      byId.get("view").src + " " + JSON.stringify(where()));

    // and a url that 404s is not reloaded into even when the thing is
    // still in the tree
    const keepF = sandbox.fetch;
    sandbox.fetch = async () => ({ ok: false, json: async () => ({}) });
    sandbox.localStorage.setItem("mybureau.where", JSON.stringify(
      { chosen: "content/da", mode: "desk", src: "/site/da/thrown-away/" }));
    await sandbox.back();
    check("  and a page that has gone is not reloaded into",
      byId.get("view").src !== "/site/da/thrown-away/", byId.get("view").src);
    sandbox.fetch = keepF;
  } else {
    check("the panel has a back() to restore where she was", false);
  }

  // ---- a panel running code that is no longer on the disk ----------
  //
  // She pulls with the panel open; python loaded verbs.py once, at
  // startup, so the server stops accepting writes and pushes the
  // sentence to show down the live stream. See stale() in server.py —
  // check.py drives that end, this one is about her seeing it.
  if (streams.length && typeof streams[0].onmessage === "function") {
    const SAYS = "Le panneau a changé pendant qu'il tournait : …";
    const health = byId.get("health"), lamp = byId.get("lamp");
    health.hidden = true;
    health.textContent = "";
    await streams[0].onmessage({ data: JSON.stringify({ n: 99, stale: SAYS }) });
    check("a panel left behind by a pull says so, where it stays visible",
      health.hidden === false && health.textContent === SAYS,
      health.hidden + " " + health.textContent);
    check("  and the lamp says something is wrong",
      /bad/.test(lamp.className), lamp.className);
    // THE SENTENCE COMES FROM THE SERVER. A copy of it here would drift
    // out of step with the one the refusal carries.
    check("  and it is the server's words, not a copy kept here",
      !readFileSync(new URL("./app.js", import.meta.url), "utf8")
        .includes("relance l'aperçu, ouvre"));

    // AND AN ORDINARY MESSAGE IS STILL ORDINARY: this must not latch on
    // and freeze a panel that is perfectly up to date.
    health.hidden = true;
    const before = fetched.length;
    await streams[0].onmessage({ data: JSON.stringify({ n: 100, stale: "" }) });
    check("an ordinary message leaves the panel alone",
      health.hidden === true && fetched.length > before,
      health.hidden + " " + (fetched.length - before));
  } else {
    check("the panel listens to the live stream at all", false);
  }

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
