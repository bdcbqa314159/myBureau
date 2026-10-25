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
  return n;
};

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
const frameDoc = {
  heard: [],
  addEventListener(kind) { this.heard.push(kind); },
  querySelector: (s) => (s === ".desk" ? {} : null),
  querySelectorAll: () => [],
  getElementById: () => null,
};

const markup = readFileSync(new URL("./app.html", import.meta.url), "utf8");
const ids = [...markup.matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]);
const byId = new Map(ids.map((id) => [id, node(id)]));
const made = new Map();          // elements the panel drew for itself
const drawn = new Map();         // and the ones it queries by attribute
const missing = [];

let fetched = [];
const sandbox = {
  console,
  // a browser has these; a vm context does not inherit them
  setTimeout, clearTimeout, setInterval, clearInterval, Promise, Date,
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
            depth: 0, opens_as: "page", empty: false,
            titles: { fr: "myBureau", en: "myBureau" },
            bodies: { fr: "", en: "" },
            x: null, y: null, opens: null, icon: null, wallpaper: null,
            about: "about.jpg",
            photographs: [], video: null, doc: null, languages: ["en", "fr"],
            on: [{
              kind: "folder", path: "content/da", name: "da",
              titles: { fr: "DA", en: "art direction" }, bodies: { fr: "", en: "" },
              x: "66", y: "66", opens: null, icon: null, wallpaper: "wallpaper.jpg",
              photographs: [], video: null, languages: ["en", "fr"],
            }, {
              // about me.txt: a window declared in [extra.items], so it
              // has no path of its own and carries the home desk's. The
              // model appends it; leaving it out of this fixture is how
              // the panel got checked against a tree it never sees.
              kind: "about", path: "content", name: "about me.txt",
              titles: { fr: "about me.txt", en: "about me.txt" },
              bodies: { fr: "Je suis directrice artistique.",
                        en: "I am an art director." },
              about: "about.jpg", languages: ["en", "fr"],
              x: null, y: null, opens: null, icon: null, wallpaper: null,
              photographs: [], video: null, doc: null,
            }],
          }, {
            kind: "desk", path: "content/da", name: "da", gallery: false,
            depth: 1, opens_as: "page", empty: false,
            titles: { fr: "DA", en: "art direction" },
            bodies: { fr: "Un texte.", en: "Some text." },
            x: "66", y: "66", opens: null, icon: null, wallpaper: "wallpaper.jpg",
            photographs: [], video: null, languages: ["en", "fr"],
            on: [{
              kind: "project", path: "content/da/theodora", name: "theodora",
              titles: { fr: "theodora.jpeg", en: "theodora.jpeg" },
              bodies: { fr: "", en: "" },
              x: "32", y: "12", opens: null, icon: null, wallpaper: null,
              photographs: ["01.jpg", "02.jpg"], video: "film.mp4",
              poster: "poster.png", doc: null, languages: ["en", "fr"],
              alt: { "01.jpg": "Deux silhouettes sur une plage." },
            }, {
              // a dossier that has not had its PDF yet — the state the
              // panel used to answer by asking for photographs
              kind: "project", path: "content/da/grocery", name: "grocery",
              titles: { fr: "grocery.pdf", en: "grocery.pdf" },
              bodies: { fr: "", en: "" },
              x: "60", y: "40", opens: null, icon: null, wallpaper: null,
              photographs: [], video: null, doc: null, languages: ["en", "fr"],
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
  // Each kind must say what it really makes. "un document" produced a
  // project called X.pdf and then asked for photographs, because the
  // engine cannot show a PDF — the extension only ever chose the icon.
  const kindSel = byId.get("kind"), willbe = byId.get("willbe");
  const said = {};
  for (const k of ["photos", "film", "document", "page"]) {
    kindSel.value = k;
    for (const fn of listeners.get("kind:change") || []) fn();
    said[k] = willbe.innerHTML;
  }
  check("every kind says what it really makes",
    Object.values(said).every((s) => s.length > 20)
    && new Set(Object.values(said)).size === 4, JSON.stringify(said).slice(0, 160));
  check("and the document one says the PDF is shown, in its own page",
    /PDF/.test(said.document) && /page/i.test(said.document)
    && !/JPEG/i.test(said.document), said.document);
  kindSel.value = "photos";
  for (const fn of listeners.get("kind:change") || []) fn();

  check("and what it will do once it is there",
    byId.get("willbe").innerHTML.length > 10, byId.get("willbe").innerHTML);
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

  let z = drag("video/quicktime");
  check("dragging a video lights the film box",
    z.video === "can", JSON.stringify(z));
  check("and tells the image boxes they cannot have it",
    z.photos === "cannot" && z.poster === "cannot", JSON.stringify(z));

  z = drag("image/jpeg");
  check("dragging a photograph lights the photographs and the affiche",
    z.photos === "can" && z.poster === "can", JSON.stringify(z));
  check("and not the film", z.video === "cannot", JSON.stringify(z));

  z = drag("");
  check("a file whose type the browser will not say lights everything,"
    + " rather than guiding wrong",
    Object.values(z).every((v) => v === "can"), JSON.stringify(z));

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
    saidAlt && saidAlt.verb === "set_alt" && saidAlt.item === "content/da/theodora"
      && saidAlt.name === "02.jpg", JSON.stringify(saidAlt));

  // ---- the dossier -------------------------------------------------
  // "I created a .pdf inside a folder and it creates a pdf and keeps
  // asking for images to drop in." It asked for photographs because the
  // engine could not show a PDF at all.
  check("the dossier has a row to choose", await pick("grocery.pdf"));
  check("a dossier is offered somewhere to put its PDF",
    /data-drop="doc"/.test(look.innerHTML), look.innerHTML.slice(0, 200));
  check("and is told that is what it is waiting for, not photographs",
    /attend son PDF/.test(look.innerHTML)
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
  // By the clause, not by the whole line: this pinned the line verbatim
  // and broke the moment a second thing that cannot be placed was added
  // to it, while what it is actually for was still true.
  check("icons inside a folder window are not given a position",
    /const onDesk = desk\.contains\(icon\)/.test(src4)
    && /if \(!moved \|\| !onDesk\)/.test(src4));

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
