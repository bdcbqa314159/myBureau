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
  append() {}, insertAdjacentHTML() {}, setPointerCapture() {},
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
    // shaped like the real answer: /api/do always carries `did`
    return {
      ok: true,
      json: async () => ({ did: { undid: "place" }, tree: { desks: [] }, n: 1 }),
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
  const before = fetched.length;
  for (const fn of listeners.get("undo:click") || []) fn();
  await new Promise((r) => setTimeout(r, 20));
  check("pressing Annuler actually asks the server something",
    fetched.length > before, `${before} -> ${fetched.length}`);
}

console.log();
if (failed) {
  console.log(`  ${failed} FAILED\n`);
  process.exit(1);
}
console.log("  the panel wakes up and its buttons are wired\n");
