/* The panel.
 *
 * The middle of the window is the REAL site, served from this address so
 * that this script can reach into it. Nothing here draws a desk, an icon
 * or a photograph: zola already did, and a second renderer would drift
 * from the first within a month.
 *
 * Editing is therefore an overlay. The site's own desk.js still does the
 * dragging — with its collision walk and its clamping, which are already
 * right — and this only writes down where it ended up.
 */
const TOKEN = new URLSearchParams(location.search).get("t") || "";
const q = (p) => p + (p.includes("?") ? "&" : "?") + "t=" + encodeURIComponent(TOKEN);
const el = (id) => document.getElementById(id);

const view = el("view"), tree = el("tree"), look = el("look");
const lamp = el("lamp"), says = el("says"), health = el("health"), tip = el("tip");

let site = "";
let model = null;
let chosen = null;          // content path of the thing being inspected
let bySlug = new Map();     // data-vt in the page -> content path

const tell = (m) => { says.textContent = m; };

async function ask(path, opts) {
  lamp.className = "lamp busy";
  try {
    const r = await fetch(q(path), opts);
    const out = await r.json();
    if (!r.ok) { lamp.className = "lamp bad"; tell(out.error || "refusé"); return null; }
    lamp.className = "lamp";
    if (out.site) site = out.site;
    if (out.tree) { model = out.tree; paint(); }
    return out;
  } catch (e) {
    lamp.className = "lamp bad"; tell("le panneau a perdu le serveur"); return null;
  }
}
const act = (body) => ask("/api/do", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

/* ---- what kind of thing is this? --------------------------------- */
/* The engine has more than folders and photographs, and the panel has to
   say which it is looking at — a gallery has no icons to move, a film is
   not a set of stills, a shortcut is not in content/ at all. */
function kindOf(o) {
  if (o.kind === "desk" || o.kind === "folder") return o.gallery ? "galerie" : "bureau";
  if (o.video) return "film";
  if (o.opens === "page") return "projet · page";
  if (o.photographs.length) return "projet · photos";
  return "projet · sans image";
}

const all = () => {
  const out = [];
  for (const d of model.desks) {
    out.push({ o: d, depth: d.path.split("/").length - 1 });
    for (const it of d.on) out.push({ o: it, depth: d.path.split("/").length });
  }
  return out;
};

const find = (p) => all().map((r) => r.o).find((o) => o.path === p) || null;

/* ---- the list down the side -------------------------------------- */

function paint() {
  if (!model) return;
  tree.innerHTML = "";
  for (const { o, depth } of all()) {
    if (o.kind !== "desk" && !model.desks.some((d) => d.path === o.path)) {
      // a folder appears once as a child and once as a desk of its own;
      // the child row is the one that can be moved, so keep that
    }
    const b = document.createElement("button");
    b.className = "row" + (depth === 2 ? " deep" : depth > 2 ? " deeper" : "");
    b.setAttribute("aria-current", String(o.path === chosen));
    b.innerHTML = `<span>${esc(o.titles.fr || o.name)}</span><span class="kind">${kindOf(o)}</span>`;
    b.addEventListener("click", () => select(o));
    tree.append(b);
  }
  if (chosen) inspect(find(chosen));
}

const esc = (s) => String(s).replace(/[<>&"]/g, (c) =>
  ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" }[c]));

/* The url the site serves this thing at — content/da/theodora is /da/theodora/ */
const urlOf = (o) => "/site/" + o.path.replace(/^content\/?/, "") + (o.path === "content" ? "" : "/");

function select(o) {
  chosen = o.path;
  const want = urlOf(o);
  // a desk is shown as itself; a project is shown on the desk it sits on,
  // because that is where it can be moved
  const isDesk = model.desks.some((d) => d.path === o.path);
  const show = isDesk ? want : urlOf({ path: o.path.split("/").slice(0, -1).join("/") });
  if (!view.src.endsWith(show)) view.src = show;
  paint();
  inspect(o);
}

/* ---- the panel on the right --------------------------------------- */

function inspect(o) {
  if (!o) { look.innerHTML = "<p class='what'>Choisis quelque chose à gauche.</p>"; return; }
  const langs = o.languages.length ? o.languages : ["fr"];
  const titles = langs.map((l) => `
    <label>nom (${l})
      <input type="text" data-title="${l}" value="${esc(o.titles[l] || "")}">
    </label>`).join("");
  const bodies = langs.map((l) => `
    <label>texte (${l})
      <textarea data-body="${l}">${esc(o.bodies[l] || "")}</textarea>
    </label>`).join("");
  const shots = o.photographs.map((n, i) => `
    <li class="shot" draggable="true" data-name="${esc(n)}">
      <img src="${q("/media/" + o.path + "/" + n)}" alt="">
      <b>${i + 1}</b><button class="bin" title="jeter">✕</button>
    </li>`).join("");

  look.innerHTML = `
    <h2>${esc(o.titles.fr || o.name)}</h2>
    <p class="what">${kindOf(o)}${o.x !== null ? ` · ${o.x}% / ${o.y}%` : " · sur la grille"}</p>
    ${titles}${bodies}
    ${o.gallery || o.kind !== "desk" ? `<ul class="shots">${shots}</ul>
      <p class="drop">Dépose des photos ici. La première est l'icône.</p>` : ""}`;
  wire(o);
}

function wire(o) {
  look.querySelectorAll("[data-title]").forEach((i) => {
    i.addEventListener("change", async () => {
      const out = await act({ verb: "retitle", item: o.path, lang: i.dataset.title, title: i.value });
      if (out) tell("nom enregistré");
    });
  });
  look.querySelectorAll("[data-body]").forEach((t) => {
    t.addEventListener("change", async () => {
      const out = await act({ verb: "set_body", item: o.path, lang: t.dataset.body, body: t.value });
      if (out) tell("texte enregistré");
    });
  });
  const list = look.querySelector(".shots");
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
      if (await act({ verb: "reorder", item: o.path, names })) tell("ordre enregistré");
    });
    li.querySelector(".bin").addEventListener("click", async () => {
      if (await act({ verb: "remove_image", item: o.path, name: li.dataset.name }))
        tell(li.dataset.name + " jetée — Annuler la ramène");
    });
  });
}

["dragenter", "dragover"].forEach((k) =>
  look.addEventListener(k, (e) => { e.preventDefault(); look.classList.add("over"); }));
["dragleave", "drop"].forEach((k) => look.addEventListener(k, () => look.classList.remove("over")));
look.addEventListener("drop", async (e) => {
  const o = find(chosen);
  if (!o || !e.dataTransfer.files.length) return;
  e.preventDefault();
  for (const f of [...e.dataTransfer.files]) {
    const out = await ask(
      `/api/upload?into=${encodeURIComponent(o.path)}&name=${encodeURIComponent(f.name)}`,
      { method: "POST", body: await f.arrayBuffer() });
    tell(out ? `${f.name} ajoutée` : `${f.name} refusée`);
  }
});

/* ---- moving a real icon, in the real page ------------------------- */

function hook() {
  let doc;
  try { doc = view.contentDocument; } catch (e) { return; }
  if (!doc) return;
  const desk = doc.querySelector(".desk");
  tip.textContent = desk
    ? "Attrape une icône dans la page et pose-la. Clique pour l'inspecter."
    : "Cette page n'est pas un bureau — rien à déplacer ici.";
  if (!desk) return;

  bySlug = new Map();
  for (const { o } of all()) {
    bySlug.set(o.path.replace(/^content\//, "").replace(/\//g, "-"), o.path);
  }

  doc.querySelectorAll("a.icon[data-vt]").forEach((icon) => {
    const path = bySlug.get(icon.dataset.vt);
    if (!path) return;                       // a window or a shortcut: not a folder
    let from = null;
    icon.addEventListener("pointerdown", (e) => { from = { x: e.clientX, y: e.clientY }; }, true);
    icon.addEventListener("pointerup", async (e) => {
      const was = from; from = null;
      if (!was) return;
      const moved = Math.abs(e.clientX - was.x) > 3 || Math.abs(e.clientY - was.y) > 3;
      const o = find(path);
      if (!moved) { if (o) select(o); return; }
      // the site's own desk.js has already moved it, clamped it and
      // walked it clear of its neighbours. Read where it put it.
      const r = icon.getBoundingClientRect(), d = desk.getBoundingClientRect();
      const x = Math.round((r.left - d.left) / d.width * 100);
      const y = Math.round((r.top - d.top) / d.height * 100);
      if (await act({ verb: "place", item: path, x, y })) tell(`posé à ${x}% / ${y}%`);
    }, true);
  });
}

view.addEventListener("load", hook);

/* ---- staying in step ---------------------------------------------- */

const stream = new EventSource(q("/api/events"));
stream.onmessage = async () => {
  await ask("/api/tree");
  // the frame is a real page: let it rebuild, then re-attach
  const here = view.src;
  view.src = here;
};
stream.onerror = () => { lamp.className = "lamp bad"; tell("connexion perdue — relance preview"); };

el("open").addEventListener("click", () => window.open(site || "/site/", "mybureau-site"));
el("undo").addEventListener("click", async () => {
  const out = await act({ verb: "undo" });
  if (out) tell("annulé : " + ((out.did && out.did.undid) || ""));
});
el("verify").addEventListener("click", async () => {
  const out = await ask("/api/look");
  if (out) { health.hidden = false; health.textContent = out.look; tell("vérifié"); }
});

ask("/api/tree").then(() => tell("prêt"));
