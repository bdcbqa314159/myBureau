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

/* ---- the loop ------------------------------------------------------
 * Measured on this machine: the panel writes a change in about 13 ms and
 * zola takes about 1.3 SECONDS to rebuild. For three edits in four it
 * answers 404 while it is working. So the frame must never be reloaded
 * eagerly — it lands on the blank page — and never reloaded at all when
 * what it would show is already on screen.
 *
 * `seen` is the state counter the server hands back. A change this panel
 * made is accounted for at once; a bump past it means somebody else
 * touched content/, which is the only thing worth reloading for.
 */
let seen = 0;
let waiting = null;

// Verbs whose effect is ALREADY on screen when they return. A drag is
// the whole list today: the site's own desk.js moved the icon before the
// write was even sent, so reloading would throw a correct view away to
// fetch an identical one — and risk the 404 doing it.
const NOTHING_TO_SEE = new Set(["place"]);

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
async function act(body) {
  const out = await ask("/api/do", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (out) {
    if (typeof out.n === "number") seen = out.n;      // we know about this one
    if (!NOTHING_TO_SEE.has(body.verb)) reframe();
  }
  return out;
}

/* Reload the frame — but only once things have settled, and only once the
 * page is actually there. Debounced, so dropping four photographs is one
 * reload and not four. */
function reframe() {
  clearTimeout(waiting);
  waiting = setTimeout(async () => {
    const url = view.src;
    let was = 0;
    try {
      const d = view.contentDocument;
      was = d ? (d.documentElement.scrollTop || d.body.scrollTop || 0) : 0;
    } catch (e) { /* nothing to remember */ }
    // wait for zola rather than race it: while it rebuilds it answers
    // 404, and reloading into that is the blank flash
    const until = Date.now() + 15000;
    while (Date.now() < until) {
      try { if ((await fetch(url, { cache: "no-store" })).ok) break; }
      catch (e) { /* still coming up */ }
      await new Promise((r) => setTimeout(r, 80));
    }
    view.addEventListener("load", function back() {
      view.removeEventListener("load", back);
      try {
        const d = view.contentDocument;
        if (d && was) { d.documentElement.scrollTop = was; d.body.scrollTop = was; }
      } catch (e) { /* nothing to restore */ }
    });
    view.src = url;
  }, 250);
}

/* ---- what kind of thing is this? --------------------------------- */
/* The engine has more than folders and photographs, and the panel has to
   say which it is looking at — a gallery has no icons to move, a film is
   not a set of stills, a shortcut is not in content/ at all. */
function kindOf(o) {
  if (o.kind === "desk" || o.kind === "folder") {
    if (o.gallery) return "galerie";
    const k = model.desks.find((d) => d.path === o.path);
    // a folder's job is not a property of the folder: it is where it is
    if (!k) return "dossier";
    return k.opens_as === "window" ? "dossier · fenêtre" : "dossier · page";
  }
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

/* What a folder put HERE would do, in her words, including the clause
 * that catches people out: a folder with nothing in it opens a page
 * wherever it is, so a brand new one always does until she fills it. */
function wouldBe(intoPath, kind) {
  const into = model.desks.find((d) => d.path === intoPath);
  if (!into) return "";
  const here = into.titles.fr || into.name;
  if (kind !== "bureau") {
    return `Un projet dans <b>${esc(here)}</b>. Il s'ouvrira sur ce bureau.`;
  }
  const deep = (into.depth || 0) >= 1;
  return deep
    ? `Un dossier dans <b>${esc(here)}</b>. Il s'ouvrira comme une
       <b>fenêtre</b> sur ce bureau — mais tant qu'il est vide il ouvrira
       sa propre page.`
    : `Un dossier sur la <b>page d'accueil</b>. Il aura sa propre page,
       son fond d'écran, et une place dans le bandeau du haut.`;
}

function sayWillBe() {
  const el_ = el("willbe");
  if (!el_ || !model) return;
  el_.innerHTML = wouldBe(el("into").value, el("kind").value);
}

function paintInto() {
  const sel = el("into");
  if (!sel || !model) return;
  const keep = sel.value;
  sel.innerHTML = "";
  for (const d of model.desks) {
    if (d.gallery) continue;              // a galerie holds photographs, not things
    const o = document.createElement("option");
    o.value = d.path;
    o.textContent = "  ".repeat(d.depth || 0) + (d.titles.fr || d.name);
    sel.append(o);
  }
  sel.value = keep && model.desks.some((d) => d.path === keep)
    ? keep : (model.desks[0] && model.desks[0].path);
  sayWillBe();
}

function paint() {
  if (!model) return;
  paintInto();
  tree.innerHTML = "";
  for (const { o, depth } of all()) {
    const b = document.createElement("button");
    b.className = "row" + (depth === 2 ? " deep" : depth > 2 ? " deeper" : "");
    b.setAttribute("aria-current", String(o.path === chosen));
    b.innerHTML = `<span>${esc(o.titles.fr || o.name)}</span><span class="kind">${kindOf(o)}</span>`;
    b.addEventListener("click", () => select(o));

    // Drag a row onto a bureau to move the thing into it — the Finder
    // trip this panel exists to remove. The folder travels whole, so
    // both language files and every photograph go with it.
    b.draggable = true;
    b.dataset.path = o.path;
    b.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", o.path);
      dragging = o.path;                 // dragover cannot read the payload
      b.classList.add("lift");
    });
    b.addEventListener("dragend", () => { dragging = null; b.classList.remove("lift"); });
    b.addEventListener("dragover", (e) => {
      const from = dragging;
      if (!from || from === o.path || !isBureau(o)) return;
      e.preventDefault();
      b.classList.add("target");
    });
    b.addEventListener("dragleave", () => b.classList.remove("target"));
    b.addEventListener("drop", async (e) => {
      e.preventDefault();
      b.classList.remove("target");
      const from = e.dataTransfer.getData("text/plain") || dragging;
      if (!from || from === o.path) return;
      const out = await act({ verb: "move", item: from, into: o.path });
      if (out && out.did) {
        tell("déplacé dans " + (o.titles.fr || o.name) + " — son adresse a changé");
        const moved = find(out.did.moved);
        if (moved) select(moved);
      }
    });
    tree.append(b);
  }
  if (chosen) inspect(find(chosen));
}

const isBureau = (o) => model.desks.some((d) => d.path === o.path);

/* A folder, explained — because its job is where it is, not what it is,
 * and because an empty one behaves like neither until it is filled. */
/* A film's own parts. Shown when the project already holds a video, and
 * offered when it was MADE as a film — otherwise there is nowhere to put
 * the film and the thing can never become what it was created to be.
 *
 * Each target takes one kind. A video dropped on the photographs is
 * refused with where it should have gone, and the same the other way. */
function reel(o) {
  const named = (o.titles.fr || "").toLowerCase();
  const wantsFilm = o.video || /\.(mov|mp4|m4v|webm)$/.test(named);
  if (o.kind === "desk" || !wantsFilm) return "";
  return `
    <label>le film
      <div class="face wide" data-drop="video">${o.video
        ? `<span>${esc(o.video)}</span>` : `<span>aucun film pour l'instant</span>`}</div>
    </label>
    <p class="drop" data-drop="video">Dépose la vidéo ici (mp4, mov, webm).</p>
    <p class="drop" data-drop="poster">Et une image ici comme affiche.</p>`;
}

function folderSays(o) {
  const k = model.desks.find((d) => d.path === o.path);
  if (!k) return "";
  if (k.gallery) return "Une galerie : ses photos sont dans le dossier, il n'y a rien à poser dessus.";
  if (k.empty) {
    return (k.depth || 0) >= 1
      ? "Vide pour l'instant, donc il ouvre sa propre page. Mets quelque chose dedans et il s'ouvrira comme une fenêtre."
      : "Vide pour l'instant. Il a déjà sa page et sa place dans le bandeau.";
  }
  return k.opens_as === "window"
    ? "Il s'ouvre comme une fenêtre sur le bureau où il est posé."
    : "Il a sa propre page, son fond d'écran, et une place dans le bandeau.";
}
let dragging = null;

const esc = (s) => String(s).replace(/[<>&"]/g, (c) =>
  ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" }[c]));

/* The url the site serves this thing at — content/da/theodora is /da/theodora/ */
const urlOf = (o) => "/site/" + o.path.replace(/^content\/?/, "") + (o.path === "content" ? "" : "/");

/* Two ways to look at a thing, because they answer different questions.
 *
 *   "sur le bureau"  where it sits, and where it can be moved to
 *   "regarder"       the thing itself — its page, its photographs, its
 *                    film playing
 *
 * A project has no desk of its own, so arranging it means looking at the
 * bureau it belongs to; and a bureau looked AT is its own desk. One
 * toggle covers both without either mode being a special case. */
let mode = "desk";

function frameFor(o) {
  const isDesk = model.desks.some((d) => d.path === o.path);
  if (mode === "page") return urlOf(o);
  return isDesk ? urlOf(o) : urlOf({ path: o.path.split("/").slice(0, -1).join("/") });
}

function select(o) {
  chosen = o.path;
  const sel = el("into");
  if (sel) {
    const home = isBureau(o) ? o.path : o.path.split("/").slice(0, -1).join("/");
    if (model.desks.some((d) => d.path === home)) { sel.value = home; sayWillBe(); }
  }
  const show = frameFor(o);
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
  const isDesk = model.desks.some((d) => d.path === o.path);
  // What it looks like on the desk. A bureau has no photograph to take a
  // face from, so without this its appearance could not be changed at all.
  const face = `
    <label>apparence
      <div class="face" data-drop="icon">${o.icon && !o.icon.includes("/")
        ? `<img src="${q("/media/" + o.path + "/" + o.icon)}" alt="">`
        : `<span>${o.icon ? "déclarée dans le texte"
             : o.photographs.length ? "la première photo"
             : "icône par défaut"}</span>`}</div>
    </label>
    <p class="drop" data-drop="icon">Dépose une image ici pour l'icône.</p>`;
  const wall = isDesk ? `
    <label>fond d'écran
      <div class="wall" id="wall">${o.wallpaper
        ? `<img src="${q("/media/" + o.path + "/" + o.wallpaper)}" alt="">`
        : `<span>${o.path === "content" ? "celui par défaut"
                                        : "hérité du bureau au-dessus"}</span>`}</div>
    </label>
    <p class="drop" data-drop="wallpaper">Dépose une image ici pour changer le fond.</p>` : "";
  const shots = o.photographs.map((n, i) => `
    <li class="shot" draggable="true" data-name="${esc(n)}">
      <img src="${q("/media/" + o.path + "/" + n)}" alt="">
      <b>${i + 1}</b><button class="bin" title="jeter">✕</button>
    </li>`).join("");

  const canBin = o.path !== "content";
  look.innerHTML = `
    <h2>${esc(o.titles.fr || o.name)}</h2>
    <p class="what">${kindOf(o)}${o.x !== null ? ` · ${o.x}% / ${o.y}%` : " · pas encore posé"}</p>
    ${isDesk ? `<p class="what">${folderSays(o)}</p>` : ""}
    ${titles}${bodies}${face}${wall}
    ${isDesk && !o.gallery ? "" : reel(o) + `<ul class="shots">${shots}</ul>
      <p class="drop" data-drop="photos">Dépose des photos ici. La première est l'icône.</p>`}
    ${canBin ? `<button class="bin-all" id="binall">Jeter ${esc(o.titles.fr || o.name)}</button>` : ""}`;
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
  const binAll = look.querySelector("#binall");
  if (binAll) {
    binAll.addEventListener("click", async () => {
      const out = await act({ verb: "throw_away", item: o.path });
      if (out) { chosen = null; tell("à la corbeille — Annuler la ramène"); paint(); }
    });
  }
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
  // dropped on the wallpaper patch, or anywhere else in the panel
  const hit = e.target.closest && e.target.closest("[data-drop]");
  const as = hit ? hit.dataset.drop : "photos";
  const files = [...e.dataTransfer.files];
  // a wallpaper and an icon are one each; photographs are a pile
  for (const f of (as === "photos" ? files : files.slice(0, 1))) {
    const out = await ask(
      `/api/upload?into=${encodeURIComponent(o.path)}&name=${encodeURIComponent(f.name)}`
      + (as === "photos" ? "" : `&as=${as}`),
      { method: "POST", body: await f.arrayBuffer() });
    const said = { wallpaper: "fond d'écran changé", icon: "apparence changée" }[as]
                 || `${f.name} ajoutée`;
    tell(out ? said : `${f.name} refusée`);
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
stream.onmessage = async (e) => {
  let n = null;
  try { n = JSON.parse(e.data).n; } catch (err) { /* keep going */ }
  await ask("/api/tree");
  // Only when somebody OTHER than this panel changed something — she
  // edited a file in TextEdit, or placeholders were fetched. Our own
  // writes were accounted for the moment the server answered.
  if (n === null || n > seen) { if (n !== null) seen = n; reframe(); }
};
stream.onerror = () => { lamp.className = "lamp bad"; tell("connexion perdue — relance preview"); };


el("kind").addEventListener("change", sayWillBe);
el("into").addEventListener("change", sayWillBe);

el("make").addEventListener("click", async () => {
  const name = el("newname").value.trim();
  if (!name) { tell("donne-lui un nom"); return; }
  const into = el("into").value;            // said out loud, not inferred
  if (!into) return;
  const kind = el("kind").value;
  const out = kind === "bureau"
    ? await act({ verb: "new_bureau", into, name })
    : await act({ verb: "new_project", into, name, kind });
  if (out) {
    el("newname").value = "";
    const made = out.did && out.did.made;
    if (made) {
      const o = find(made);
      if (o) select(o);
      // it has no place of its own yet: the loose grid put it somewhere.
      // Dragging it in the page is how it gets one.
      tell(kind === "bureau"
        ? "dossier créé — attrape-le dans la page pour le poser"
        : "créé — attrape-le dans la page pour le poser");
    }
  }
});

const setMode = (m) => {
  mode = m;
  el("asdesk").setAttribute("aria-pressed", String(m === "desk"));
  el("aspage").setAttribute("aria-pressed", String(m === "page"));
  const o = find(chosen);
  if (o) select(o);
};
el("asdesk").addEventListener("click", () => setMode("desk"));
el("aspage").addEventListener("click", () => setMode("page"));

el("open").addEventListener("click", () => window.open(site || "/site/", "mybureau-site"));
el("undo").addEventListener("click", async () => {
  const out = await act({ verb: "undo" });
  if (out) tell("annulé : " + ((out.did && out.did.undid) || ""));
});
el("verify").addEventListener("click", async () => {
  const out = await ask("/api/look");
  if (out) { health.hidden = false; health.textContent = out.look; tell("vérifié"); }
});

// Open on something. An empty inspector saying "choose something" reads
// as a label rather than an editor, and the panel looked like a viewer.
ask("/api/tree").then((out) => {
  if (out && typeof out.n === "number") seen = out.n;
  if (model && model.desks.length) select(model.desks[0]);
  tell("prêt");
});
