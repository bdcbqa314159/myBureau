/* The panel.
 *
 * Holds no state worth the name: the server re-reads content/ on every
 * answer and pushes a nudge whenever anything changes on disk, including
 * changes this panel had nothing to do with. So the loop is always
 * "ask, draw" — never "remember what I did".
 *
 * No framework and no build step, for the same reason the site has none.
 */
const TOKEN = new URLSearchParams(location.search).get("t") || "";
const q = (p) => p + (p.includes("?") ? "&" : "?") + "t=" + encodeURIComponent(TOKEN);

const el = (id) => document.getElementById(id);
const map = el("map"), well = el("well"), which = el("which");
const lamp = el("lamp"), says = el("says"), health = el("health");

let site = "";        // where the site is being served, per the server
let tree = null;      // what the server last told us
let deskPath = null;  // which desk is on screen
let pick = null;      // which project is in the well

const tell = (m) => { says.textContent = m; };
const busy = (on) => lamp.classList.toggle("busy", on);

async function ask(path, opts) {
  busy(true);
  try {
    const r = await fetch(q(path), opts);
    const out = await r.json();
    if (!r.ok) { lamp.classList.add("bad"); tell(out.error || "refusé"); return null; }
    lamp.classList.remove("bad");
    if (out.site) site = out.site;
    if (out.tree) { tree = out.tree; draw(); }
    return out;
  } catch (e) { lamp.classList.add("bad"); tell("le panneau a perdu le serveur"); return null; }
  finally { busy(false); }
}

const act = (body) => ask("/api/do", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

async function refresh() {
  const out = await ask("/api/tree");
  if (out) { tree = out.tree; draw(); }
}

/* ---- drawing ---------------------------------------------------- */

function deskNow() {
  if (!tree) return null;
  return tree.desks.find((d) => d.path === deskPath) || tree.desks[0];
}

function draw() {
  if (!tree) return;
  const d = deskNow();
  if (!d) return;
  deskPath = d.path;

  which.innerHTML = "";
  for (const k of tree.desks) {
    const o = document.createElement("option");
    o.value = k.path;
    o.textContent = (k.titles.fr || k.name) + (k.gallery ? "  (galerie)" : "");
    o.selected = k.path === deskPath;
    which.append(o);
  }

  map.style.backgroundImage = d.wallpaper
    ? `url("${q("/media/" + d.path + "/" + d.wallpaper)}")` : "";
  map.innerHTML = "";

  if (d.gallery) {
    map.insertAdjacentHTML("beforeend",
      `<p style="color:#fff;padding:1rem">Une galerie n'a pas d'icônes à poser —
       ses photos sont simplement dans le dossier.</p>`);
    return;
  }

  d.on.forEach((it, i) => {
    const pin = document.createElement("div");
    pin.className = "pin" + (pick === it.path ? " chosen" : "");
    // no position of its own: the site lays those out on a loose grid,
    // and this shows the same arithmetic rather than inventing one
    const x = it.x !== null ? +it.x : 12 + (i % 4) * 25;
    const y = it.y !== null ? +it.y : 20 + Math.floor(i / 4) * 26;
    pin.style.left = x + "%";
    pin.style.top = y + "%";
    pin.dataset.item = it.path;
    const face = faceOf(it);
    pin.innerHTML = `<img src="${face}" alt=""><span>${esc(it.titles.fr || it.name)}</span>`;
    map.append(pin);
    drag(pin, it);
  });
}

function faceOf(it) {
  if (it.icon && !it.icon.includes("/")) return q("/media/" + it.path + "/" + it.icon);
  if (it.icon) return q("/media/" + it.icon);
  if (it.kind === "folder") return "/img/icons/folder.svg";
  if (it.photographs.length) return q("/media/" + it.path + "/" + it.photographs[0]);
  return "/img/icons/doc.svg";
}

const esc = (s) => s.replace(/[<>&"]/g, (c) =>
  ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" }[c]));

/* ---- moving an icon ---------------------------------------------- */

function drag(pin, it) {
  let from = null;
  pin.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    pin.setPointerCapture(e.pointerId);
    const box = map.getBoundingClientRect();
    from = { x: e.clientX, y: e.clientY, left: parseFloat(pin.style.left),
             top: parseFloat(pin.style.top), box, moved: false };
    pin.classList.add("dragging");
  });
  pin.addEventListener("pointermove", (e) => {
    if (!from) return;
    const dx = (e.clientX - from.x) / from.box.width * 100;
    const dy = (e.clientY - from.y) / from.box.height * 100;
    if (Math.abs(dx) > 0.4 || Math.abs(dy) > 0.4) from.moved = true;
    // clamped, because the site clamps too: an icon dropped off the edge
    // would be walked back on and the number would disagree with the desk
    pin.style.left = Math.max(0, Math.min(100, from.left + dx)) + "%";
    pin.style.top = Math.max(0, Math.min(100, from.top + dy)) + "%";
  });
  const done = async (e) => {
    if (!from) return;
    const wasMoved = from.moved;
    const x = Math.round(parseFloat(pin.style.left));
    const y = Math.round(parseFloat(pin.style.top));
    from = null;
    pin.classList.remove("dragging");
    if (!wasMoved) { choose(it); return; }
    const out = await act({ verb: "place", item: it.path, x, y });
    if (out) tell(`${it.titles.fr || it.name} → ${x}% / ${y}%`);
  };
  pin.addEventListener("pointerup", done);
  pin.addEventListener("pointercancel", done);
}

/* ---- the photographs --------------------------------------------- */

function choose(it) {
  pick = it.path;
  draw();
  showWell();
}

function found() {
  const d = deskNow();
  return d ? d.on.find((i) => i.path === pick) : null;
}

function showWell() {
  const it = found();
  if (!it) { well.innerHTML = `<p class="well-none">Clique un projet sur le bureau.</p>`; return; }
  const shots = it.photographs.map((n, i) => `
    <li class="shot" draggable="true" data-name="${esc(n)}">
      <img src="${q("/media/" + it.path + "/" + n)}" alt="">
      <b>${i + 1}</b><button class="bin" title="à la corbeille">✕</button>
    </li>`).join("");
  well.innerHTML = `
    <h3>${esc(it.titles.fr || it.name)}</h3>
    <ul class="shots">${shots || ""}</ul>
    <p class="drop">Dépose des photos ici.<br><small>La première est l'icône.</small></p>`;
  wire(it);
}

function wire(it) {
  const list = well.querySelector(".shots");
  if (!list) return;
  let lifted = null;
  list.querySelectorAll(".shot").forEach((li) => {
    li.addEventListener("dragstart", () => { lifted = li; li.classList.add("lift"); });
    li.addEventListener("dragend", () => { li.classList.remove("lift"); lifted = null; });
    li.addEventListener("dragover", (e) => {
      e.preventDefault();
      if (!lifted || lifted === li) return;
      const r = li.getBoundingClientRect();
      list.insertBefore(lifted, (e.clientY - r.top) / r.height > .5 ? li.nextSibling : li);
    });
    li.addEventListener("drop", async (e) => {
      e.preventDefault();
      const names = [...list.querySelectorAll(".shot")].map((n) => n.dataset.name);
      const out = await act({ verb: "reorder", item: it.path, names });
      if (out) tell("ordre enregistré — la première est l'icône");
    });
    li.querySelector(".bin").addEventListener("click", async () => {
      const out = await act({ verb: "remove_image", item: it.path, name: li.dataset.name });
      if (out) tell(li.dataset.name + " est à la corbeille — Annuler la ramène");
    });
  });
}

/* ---- dropping files in ------------------------------------------- */

["dragenter", "dragover"].forEach((k) =>
  well.addEventListener(k, (e) => { e.preventDefault(); well.classList.add("over"); }));
["dragleave", "drop"].forEach((k) =>
  well.addEventListener(k, () => well.classList.remove("over")));

well.addEventListener("drop", async (e) => {
  const it = found();
  if (!it || !e.dataTransfer.files.length) return;
  e.preventDefault();
  // one file per request, in order, so the numbering is the order she
  // dropped them and a failure names the file that failed
  for (const f of [...e.dataTransfer.files]) {
    const out = await ask(
      `/api/upload?into=${encodeURIComponent(it.path)}&name=${encodeURIComponent(f.name)}`,
      { method: "POST", body: await f.arrayBuffer() });
    tell(out ? `${f.name} → ${(out.did && out.did.named) || "ajoutée"}`
             : `${f.name} refusée`);
  }
});

/* ---- the bar ------------------------------------------------------ */

which.addEventListener("change", () => { deskPath = which.value; pick = null; draw(); showWell(); });
el("site").addEventListener("click", () =>
  window.open(site || "http://127.0.0.1:1111/", "mybureau-site"));
el("undo").addEventListener("click", async () => {
  const out = await act({ verb: "undo" });
  // never reach blindly into the answer: an exception inside a click
  // handler looks, from the outside, exactly like a button that does
  // nothing at all
  if (out) { tell("annulé : " + ((out.did && out.did.undid) || "")); showWell(); }
});
el("verify").addEventListener("click", async () => {
  const out = await ask("/api/look");
  if (out) { health.textContent = out.look; tell("vérifié"); }
});

/* ---- the perpetual bit -------------------------------------------- */

const stream = new EventSource(q("/api/events"));
stream.onmessage = () => { refresh().then(showWell); };
stream.onerror = () => { lamp.classList.add("bad"); tell("connexion perdue — relance preview"); };

refresh().then(showWell);
