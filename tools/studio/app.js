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

/* Is the frame showing the phone? It is a LOOKING mode, and the drag
 * below consults it.
 *
 * On a phone the desk is a grid, and a position is read back out of
 * the page after the site's own script has placed the icon. Read from
 * a 390px frame that is a grid cell, not her arrangement — so a drag
 * in here would quietly rewrite her DESKTOP layout with numbers that
 * mean nothing. A tap still chooses a thing; a drag does nothing. */
let narrowView = false;

const tell = (m) => { says.textContent = m; };

/* A REQUEST THAT NEVER ANSWERS. `fetch` waits forever by default, and
 * the lamp above is the panel's only signal that anything is
 * happening. A server that REFUSES is handled below; a server that
 * HANGS left the lamp lit for the rest of the session with nothing to
 * tell her, which is worse than an error because it looks like work in
 * progress.
 *
 * Twenty seconds is far longer than anything here takes — this is
 * localhost, and the largest thing that travels is a photograph. It is
 * a bound, not a deadline. */
const PATIENCE = 20000;

async function ask(path, opts) {
  lamp.className = "lamp busy";
  const stop = new AbortController();
  const giveUp = setTimeout(() => stop.abort(), PATIENCE);
  try {
    const r = await fetch(q(path), { ...opts, signal: stop.signal });
    const out = await r.json();
    if (!r.ok) { lamp.className = "lamp bad"; tell(out.error || "refusé"); return null; }
    lamp.className = "lamp";
    if (out.site) site = out.site;
    if (out.tree) { model = out.tree; paint(); }
    return out;
  } catch (e) {
    lamp.className = "lamp bad";
    // Two different things, and she can act on exactly one of them.
    tell(e.name === "AbortError"
      ? "le serveur n'a pas répondu. Vérifie la fenêtre noire, puis réessaie."
      : "le panneau a perdu le serveur");
    return null;
  } finally {
    clearTimeout(giveUp);
  }
}
async function act(body) {
  const out = await ask("/api/do", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (out) {
    if (typeof out.n === "number") seen = out.n;      // we know about this one
    // the bandeau is the one change that needs the page checked rather
    // than merely reached — see reframe()
    if (!NOTHING_TO_SEE.has(body.verb))
      reframe(body.verb === "set_identity" ? body.studio : null);
  }
  return out;
}

/* Reload the frame — but only once things have settled, and only once the
 * page is actually there. Debounced, so dropping four photographs is one
 * reload and not four. */
/* `expect`: a string that must be IN the rebuilt page before reloading.
 *
 * The wait below is written for a content change, where zola answers 404
 * while it rebuilds — so "not 404" means "ready". A CONFIG change is not
 * like that: zola keeps serving the old page, happily, with a 200, for
 * about three seconds. Reloading on that shows the name she just typed
 * over, and the panel looks broken in exactly the way it has before. */
function reframe(expect) {
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
      try {
        const r = await fetch(url, { cache: "no-store" });
        if (r.ok && !expect) break;
        if (r.ok && (await r.text()).includes(expect)) break;
      } catch (e) { /* still coming up */ }
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
  if (o.kind === "about") return "présentation";
  // WHAT SHE MADE IT, said back to her in her words. It used to be
  // worked out from the folder: `o.video` meant film, `o.doc` meant
  // dossier, one photograph meant photo — so a thing she had not
  // filled in yet was described as something else.
  if (o.type === "photo") return o.photographs.length ? "une photo" : "une photo, vide";
  if (o.type === "video") return o.video ? "un film" : "un film, sans sa vidéo";
  if (o.type === "page") return "une page";
  if (o.kind === "desk" || o.kind === "folder") {
    if (o.gallery) return "galerie";
    // every folder opens a page now — a bureau of its own at the top,
    // the project page anywhere else
    return "dossier · page";
  }
  if (o.video) return "film";
  if (o.doc) return "dossier · page";
  if (o.opens === "page") return "projet · page";
  if (o.photographs.length === 1) return "une photo";
  if (o.photographs.length) return "projet · photos";
  return "projet · sans image";
}

const all = () => {
  if (!model) return [];
  const out = [];
  for (const d of model.desks) {
    out.push({ o: d, depth: d.path.split("/").length - 1 });
    for (const it of d.on) out.push({ o: it, depth: d.path.split("/").length });
  }
  return out;
};

/* What `chosen` holds. Every row used to be its path, and that was the
 * same thing — until about me.txt, which is a window declared in
 * [extra.items] and writes the home desk's own file. Two rows, one path,
 * so the path alone can no longer say which is selected. */
const keyOf = (o) => (o.kind === "about" ? "about" : o.path);

const find = (p) => all().map((r) => r.o).find((o) => keyOf(o) === p) || null;

/* ---- the list down the side -------------------------------------- */

/* What a folder put HERE would do, in her words, including the clause
 * that catches people out: a folder with nothing in it opens a page
 * wherever it is, so a brand new one always does until she fills it. */
/* What each kind REALLY is, said before she commits to it.
 *
 * "un document" made a project called Brochure.pdf and then asked for
 * photographs — because the engine has no idea how to show a PDF. The
 * extension only ever chose the drawn ICON. Offering it as a kind of
 * thing to make, without saying that, promised something the site cannot
 * do. */
const KINDS = {
  photos:   "Des photos. La première sert d'icône.",
  film:     "Un film : dépose la vidéo, et une image comme affiche.",
  document: "Un dossier PDF. Il s'affiche en grand dans sa propre page — "
            + "dépose le PDF, et une image si tu veux une couverture.",
  page:     "Une page de texte, avec des photos si tu en ajoutes.",
};

function wouldBe(intoPath, kind) {
  const into = model.desks.find((d) => d.path === intoPath);
  if (!into) return "";
  const here = into.titles.fr || into.name;
  if (kind !== "folder") {
    return `Dans <b>${esc(here)}</b>. ${esc(KINDS[kind] || "")}`;
  }
  const deep = (into.depth || 0) >= 1;
  return deep
    ? `Un dossier dans <b>${esc(here)}</b>. Il s'ouvrira comme une
       <b>fenêtre</b> sur ce bureau — mais tant qu'il est vide il ouvrira
       sa propre page.`
    : `Un dossier sur la <b>page d'accueil</b>. Il aura sa propre page,
       son fond d'écran, et une place dans le bandeau du haut.`;
}

/* WHERE A DROPPED FOLDER OF IMAGES WILL GO.
 *
 * It read the `dans …` select. With the row gone it goes into the desk
 * that is CHOSEN — which the panel always has, and which she can see
 * highlighted in the list and outlined in the page. Saying it out loud
 * here is the whole of what the select was for. */
function intoNow() {
  const o = find(chosen);
  if (!o) return "";
  // the desk it SITS ON if it is a thing, itself if it is a desk
  const d = model.desks.find((x) => x.path === o.path);
  return d && !d.gallery ? d.path : deskOf(o);
}

function sayWillBe() {
  const el_ = el("willbe");
  if (!el_ || !model) return;
  const into = intoNow();
  el_.innerHTML = into
    ? `« Ajouter un dossier » créera une page dans <b>${esc(
        (model.desks.find((d) => d.path === into) || {}).titles
          ? (model.desks.find((d) => d.path === into).titles.fr) : into)}</b>.`
    : "";
}

function paintInto() {
  sayWillBe();
}

function paint() {
  if (!model) return;
  paintInto();
  tree.innerHTML = "";
  for (const { o, depth } of all()) {
    const b = document.createElement("button");
    b.className = "row" + (depth === 2 ? " deep" : depth > 2 ? " deeper" : "");
    b.setAttribute("aria-current", String(keyOf(o) === chosen));
    const label = o.titles.fr || o.name;
    // the whole name on hover, since a long one is shortened in place
    b.title = label + " — " + kindOf(o);
    b.innerHTML = `<span>${esc(label)}</span><span class="kind">${kindOf(o)}</span>`;
    b.addEventListener("click", () => select(o));

    // Drag a row onto a bureau to move the thing into it — the Finder
    // trip this panel exists to remove. The folder travels whole, so
    // both language files and every photograph go with it.
    b.draggable = o.kind !== "about";
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
/* What a project is waiting for, said in the empty space rather than
 * left for her to guess from a generic "drop photos here". */
/* IS THIS A BLANK PAGE WITH HER CONTENT ON IT?
 *
 * `page.html` renders one, and a project declares no template and gets
 * it. That is the whole test — and it is a fact about the folder, not
 * a reading of its name.
 *
 * It replaces three different guesses that had grown up beside each
 * other: `kind === "project"`, `isDesk && !gallery`, and "does the
 * title end in .pdf". Those are why `grocery list.png` could take
 * photographs and a text while `logofolio`, `atelier mirabelle` and
 * `maison cosette` could take neither — the same kind of object,
 * told apart by how it was spelled. */
function isPage(o) {
  // HER TYPE, not the template and not the name. `type` is written into
  // the file when she makes it — see specs/the-four-types.md.
  //
  // The template was a better guess than the name and still a guess:
  // it answers "what renders this" rather than "what did she make".
  // They agree today, and the day they do not it is the type that is
  // right.
  //
  // "" is anything that predates the type being written down. It falls
  // back to the template so a folder nobody has labelled still works.
  if (o.type) return o.type === "page";
  return o.template === "page.html" || o.template === "";
}

/* The drawn folder pictures, ours and hand-drawn — see NOTICE. The
 * same four `verbs.DRAWN_FOLDERS` accepts; the server refuses anything
 * else, so this list being wrong is a refusal rather than a surprise. */
const DRAWN_FOLDERS = ["folder", "folder-olive", "folder-rust", "folder-slate"];

/* Where photographs go, in the words the thing deserves. */
function dropPhotos(o) {
  return `<p class="drop" data-drop="photos">${
    o.gallery ? "Dépose des photos ici. Elles s'affichent dans l'ordre de leur nom."
      : o.type === "photo" ? "Dépose la photo ici."
        : "Dépose des photos ici. La première est l'icône."}</p>`;
}

/* A photograph: one picture, and that is the whole object. */
function isPhoto(o) {
  return o.type === "photo";
}

/* A film: its video and its affiche. Its own mechanics, unchanged. */
function isFilm(o) {
  if (o.type) return o.type === "video";
  // unlabelled: what is in the folder, which is the old rule
  return Boolean(o.video);
}

function waitingFor(o) {
  // ONLY A PROJECT WAITS FOR A FILE. This used to exclude "desk", which
  // is what the home desk and a bureau looked at as themselves are
  // called — but a bureau sitting on another desk is a row of kind
  // "folder", and those fell straight through. So every folder with no
  // photographs of its own announced "Rien dedans pour l'instant."
  // directly under a line saying it holds four things.
  // WHAT IT IS WAITING FOR IS WHAT ITS TYPE NEEDS. No name is read
  // here any more: a film waits for a film because she made a film.
  if (isFilm(o)) return o.video ? "" : "Ce film attend sa vidéo.";
  if (isPhoto(o)) return o.photographs.length ? "" : "Cette photo attend son image.";
  if (!isPage(o)) return "";
  if (!o.photographs.length && !o.doc) return "Rien dedans pour l'instant.";
  return "";
}

/* The dossier, offered on EVERY PAGE, whatever it is called.
 *
 * It used to need the title to end in `.pdf`, or a PDF to be in the
 * folder already. So `12 regards.pdf` had somewhere to drop one and
 * `logofolio` did not — and the only difference between them was the
 * three letters she happened to type in a name.
 *
 * That is the thing to stop doing. A NAME IS A NAME. `un document`,
 * `une page` and `un dossier` are the same object: a blank page with
 * her content on it, and she may call it whatever she likes. What
 * decides is the TEMPLATE, which is a fact about the folder rather
 * than a guess from a string.
 *
 * A gallery is excluded because it renders only its own photographs: a
 * PDF dropped there would be built and shown nowhere. A desk is
 * excluded because it holds icons, not work. */
function dossier(o) {
  // A PAGE TAKES PDFs. Nothing else does — a photo is one photograph
  // and a film is its video — and the verb refuses both, so a box
  // there could only ever be refused.
  if (!isPage(o)) return "";
  return `
    <label>le dossier
      <div class="face wide" data-drop="doc">${o.doc
        ? `<span>${esc(o.doc)}</span>`
        : `<span>aucun PDF pour l'instant</span>`}</div>
    </label>
    <p class="drop" data-drop="doc">Dépose le PDF ici. Il s'affiche en grand
       dans sa page — rien ne le propose en téléchargement.</p>`;
}

function reel(o) {
  const named = (o.titles.fr || "").toLowerCase();
  // A film IS a different object — its icon opens a window rather than
  // going to a page — so unlike the dossier this one stays announced
  // by the name, or by a video already in the folder. What changed is
  // the first test: `kind === "desk"` hid it from a folder-page, which
  // is a page like any other.
  // BY TYPE. It used to be `o.video || the name ends in .mov` — so an
  // empty film had nowhere to put its film unless she had typed the
  // extension, and a page called `x.mov` was offered a film well it
  // would be refused on.
  if (!isFilm(o)) return "";
  // THE FILM HAS TO LOOK DIFFERENT ONCE IT IS THERE. It said only the
  // file name, in the same grey box as before — "I had been dropping it
  // ten times before noticing the video was already there." So: the
  // frame, the name, and a word saying it is in place.
  const landed = Boolean(o.video);
  return `
    <label>le film
      <div class="face wide ${landed ? "has" : ""}" data-drop="video">${landed
        ? (o.poster
            ? `<img src="${q("/media/" + o.path + "/" + o.poster)}" alt="">`
            : `<span>${esc(o.video)}</span>`)
        : `<span>aucun film pour l'instant</span>`}</div>
    </label>
    ${landed ? `<p class="landed">✓ <b>${esc(o.video)}</b> est en place${
        o.poster ? ` — l'affiche est la première image du film` : ""}.</p>`
      : `<p class="drop" data-drop="video">Dépose la vidéo ici (mp4, mov, webm).</p>`}
    <p class="drop" data-drop="poster">${o.poster
      ? "Dépose une image ici pour choisir une autre affiche."
      : "Et une image ici comme affiche."}</p>`;
}

function folderSays(o) {
  const k = model.desks.find((d) => d.path === o.path);
  if (!k) return "";
  if (k.gallery) return "Une galerie : ses photos sont dans le dossier, il n'y a rien à poser dessus.";
  if ((k.depth || 0) >= 1) {
    return k.empty
      ? "Il a sa propre page : son titre, sa description, et son travail dessous. Vide pour l'instant."
      : "Il a sa propre page : son titre, sa description, et son travail dessous.";
  }
  return k.empty
    ? "Vide pour l'instant. Il a déjà sa page et sa place dans le bandeau."
    : "Il a sa propre page, son fond d'écran, et une place dans le bandeau.";
}
let dragging = null;

const esc = (s) => String(s).replace(/[<>&"]/g, (c) =>
  ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" }[c]));

/* The url the site serves this thing at — content/da/theodora-01 is /da/theodora-01/ */
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

/* The desk a thing SITS ON — never the one it contains.
 *
 * This returned a bureau's own desk, so choosing a folder put that
 * folder's desk in the frame: a single click went inside it. The click
 * the site would have acted on was being stopped correctly all along,
 * and then this walked in through the front door instead. From the
 * outside the two are identical, which is why stopping the click looked
 * like it had changed nothing.
 *
 * Arranging means seeing a thing WHERE IT IS. Going inside is a
 * double-click, or "regarder" for a project's own page. */
function deskOf(o) {
  if (o.path === "content") return "content";
  return o.path.split("/").slice(0, -1).join("/");
}

function frameFor(o) {
  if (mode === "page") return urlOf(o);
  return urlOf({ path: deskOf(o) });
}

function select(o) {
  chosen = keyOf(o);
  sayWillBe();
  const show = frameFor(o);
  if (!view.src.endsWith(show)) view.src = show;
  paint();
  inspect(o);
}

/* ---- the panel on the right --------------------------------------- */

/* about me.txt, on its own.
 *
 * Its two things are a photograph and some words, and nothing else — no
 * name to type (the label is declared in [extra.items]), no wallpaper, no
 * photographs, nothing to throw away. It used to be a block inside the
 * home desk's pane, below that desk's OWN name and text, which read as
 * though those were the ones it meant.
 */
function inspectAbout(o) {
  const langs = o.languages.length ? o.languages : ["fr"];
  look.innerHTML = `
    <h2>about me.txt</h2>
    <p class="what">présentation · la fenêtre de la page d'accueil</p>
    <label>ta photo — c'est elle, l'icône sur le bureau
      <div class="face wide" data-drop="about">${o.about
        ? `<img src="${q("/media/" + o.path + "/" + o.about)}" alt="">`
        : `<span>aucune photo pour l'instant</span>`}</div>
    </label>
    <p class="drop" data-drop="about">Dépose ta photo ici.</p>
    ${langs.map((l) => `
      <label>ton texte (${l})
        <textarea data-body="${l}">${esc(o.bodies[l] || "")}</textarea>
      </label>`).join("")}
    <p class="hintline">La photo est l'icône de <em>about me.txt</em> sur
       le bureau. La fenêtre, elle, ne montre que ton texte.</p>`;
  wire(o);
}

/* NEVER PULL A FIELD OUT FROM UNDER HER.
 *
 * This pane is rebuilt from a string — `look.innerHTML = ...` — and the
 * last line of paint() rebuilds it on every tree update. Tree updates
 * arrive on their own: after any verb, and whenever the watcher sees
 * zola rebuild.
 *
 * Everything here saves on `change`, which fires on blur. That is the
 * right choice, and it is exactly what made this dangerous: text she
 * has typed and not yet left lives in the DOM, and the DOM is what got
 * replaced. She drops a photograph, starts writing the description
 * while the rebuild finishes, the stream fires — and the words are
 * gone, with nothing saved and nothing said.
 *
 * So a rebuild while she is in a field is deferred, not done. It
 * happens when she leaves the pane, by which time `change` has saved
 * what she wrote. */
let stale = false;

function typing() {
  const a = document.activeElement;
  return !!a && look.contains(a)
      && (a.tagName === "TEXTAREA" || a.tagName === "INPUT");
}

look.addEventListener("focusout", (e) => {
  // moving from one field to the next is not leaving the pane
  if (e.relatedTarget && look.contains(e.relatedTarget)) return;
  if (!stale) return;
  stale = false;
  // after the change handler, so the save goes first — and against
  // whatever is chosen NOW, because she may have left by clicking
  // something else in the tree
  setTimeout(() => { if (chosen) inspect(find(chosen)); }, 0);
});

function inspect(o) {
  if (typing()) { stale = true; return; }
  if (!o) { look.innerHTML = "<p class='what'>Choisis quelque chose à gauche.</p>"; return; }
  if (o.kind === "about") return inspectAbout(o);
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
  // THREE SLOTS, AND ONLY ONE HOLDS THE FACE.
  //
  // It was one box. Drop anything in it and you got an icon; what you
  // had before was not shown, and whether a dropped file beat a
  // declared one was a precedence rule in _icon.html that she could
  // not see. So "I chose a photograph" and "the desk draws a folder"
  // were both true at once.
  //
  // Now the three are side by side, the chosen one says so, and
  // choosing one clears the other two at the verb — `set_icon` and
  // `set_face` each call `_unface` first, so the precedence rule never
  // gets a chance to decide instead of her.
  //
  // A GIF IS ITS OWN SLOT because it moves on the desk and a
  // photograph does not — two different answers, not one with a
  // format. Which slot a dropped file fills is read from its BYTES.
  const chosen = o.face || "";
  // A FOLDER'S FACE IS A FOLDER. On the main desktop a folder is
  // always a folder — her words — so it is offered the four drawings
  // and a drop for one of her own, and nothing else. A photograph or a
  // GIF there would be a face that contradicts the thing.
  //
  // HER OWN DRAWING IS THE POINT of that drop. Before the slots
  // existed, any image she dropped became the icon, and a folder she
  // had drawn herself worked. Three slots turned that into "une
  // photo", which mislabelled it and left a folder with no way to say
  // "this is my folder picture".
  const slot = (how, label, inner) => `
    <li class="slot${chosen === how ? " is-chosen" : ""}" data-face="${how}">
      <span class="slot-what">${label}</span>
      ${inner}
      ${chosen === how ? `<b class="slot-yes">${{
        folder: shown ? "ton dessin, en place" : "ce dessin, en place",
        photo: "cette image, en place",
        gif: "ce GIF, en place",
      }[how]}</b>` : ""}
    </li>`;
  const shown = o.icon && !o.icon.includes("/")
    ? `<img src="${q("/media/" + o.path + "/" + o.icon)}" alt="">` : "";
  const face = `
    <fieldset class="faces">
      <legend>son icône${o.type === "folder"
        ? " — un dessin, le nôtre ou le tien"
        : " — un seul des trois"}</legend>
      <ul class="slots${o.type === "folder" ? " one" : ""}">
        ${slot("folder", "un dossier", `
          <div class="slot-box" data-drop="icon-folder">${
            chosen === "folder" && shown ? shown : `
            ${DRAWN_FOLDERS.map((f) => `<button type="button" class="drawn${
              o.icon === "img/icons/" + f + ".svg" ? " is-chosen" : ""}"
              data-drawn="${f}" title="${f}"><img
              src="${q("/site/img/icons/" + f + ".svg")}" alt=""></button>`).join("")}`}
          </div>
          <p class="drop" data-drop="icon-folder">Ou dépose ton propre dessin.</p>`)}
        ${o.type === "folder" ? "" : `
        ${slot("photo", "une photo", `
          <div class="slot-box" data-drop="icon-photo">${
            chosen === "photo" ? shown : ""}</div>
          <p class="drop" data-drop="icon-photo">Dépose une image.</p>`)}
        ${slot("gif", "un GIF", `
          <div class="slot-box" data-drop="icon-gif">${
            chosen === "gif" ? shown : ""}</div>
          <p class="drop" data-drop="icon-gif">Dépose un GIF.</p>`)}`}
      </ul>
      ${chosen ? "" : `<p class="hintline">${o.photographs.length
        ? "Rien de choisi : c'est la première photo qui sert d'icône."
        : "Rien de choisi : c'est le dessin par défaut."}</p>`}
    </fieldset>`;
  // A gallery ignores a wallpaper — look.py flags one declared there as a
  // line that does nothing — so the panel does not offer to set one.
  // `about me.txt` is the home desk's own window: its portrait and its
  // words. It used to be reachable only by knowing that the home desk's
  // "texte" was the about text, and there was no way to give it a face
  // at all.
  const me = (model && model.identity) || { owner: "", studio: "", live: false };
  const bandeau = o.path === "content" ? `
    <fieldset class="about">
      <legend>le bandeau, en haut de chaque page</legend>
      <label>avant le nom
        <input type="text" id="who" value="${esc(me.owner)}" maxlength="60">
      </label>
      <label>le nom du studio
        <input type="text" id="studio" value="${esc(me.studio)}" maxlength="60">
      </label>
      <p class="hintline">${me.live
        ? "Le site est en ligne : c'est ce nom que voient les visiteurs."
        : "Le site est encore en démonstration — ce nom-ci est celui de la"
          + " démo, et le vrai prend sa place le jour de la mise en ligne."}</p>
    </fieldset>` : "";
  // about me.txt has its own row and its own pane now — see
  // inspectAbout. Here, it put a photograph and a text box underneath the
  // home desk's OWN name and text, and the hint meant to tell them apart
  // pointed at the wrong ones.
  // A WALLPAPER WHERE THERE IS A DESK TO PUT IT ON.
  //
  // `section.html` is the only template that renders one, and
  // `index.html` extends it — so the home desk and the two bureaux
  // have a ground, and nothing else does. `gallery.html` and
  // `page.html` extend base.html directly and read no wallpaper at
  // all.
  //
  // This said `isDesk && !o.gallery`, and `isDesk` is true of a
  // FOLDER-PAGE as well: `travail sélectionné`, `maison cosette`,
  // `Atelier Mirabelle` and `Logofolio` were all offered a ground they
  // cannot show. Four of the seven offers did nothing — and worse than
  // nothing, because the file lands in her folder and then needs
  // `not_photographs` to keep it out of her work. Checked by dropping
  // one beside maison cosette's `_index.md` and building: no wallpaper
  // in its HTML.
  //
  // The gallery was excluded by hand, one case of the rule written out
  // as an exception. look.py already says a wallpaper declared on a
  // gallery is a line that does nothing.
  const hasAGround = o.template === "section.html" || o.template === "index.html";

  // IS THIS THING DRAWN AS AN ICON ANYWHERE?
  //
  // A desk draws one per thing on it, with the name underneath. A
  // FOLDER-PAGE draws none — it renders a route, and since the client
  // straightened it that route carries no links and no names, only
  // photographs. And nothing draws an icon for the home desk at all:
  // it is the root page, and no `data-vt=""` exists in the built site.
  //
  // Three controls mean something only where this is true:
  //
  //   the NAME      it is the label under the icon. On a route stop it
  //                 is written to an sr-only heading on a page nothing
  //                 links to.
  //   the FACE      the picture the icon wears.
  //   the POSITION  x/y on a desk. A route is ordered by folder name;
  //                 `papier calque.pdf` still carries `x = 34, y = 43`
  //                 from when `travail sélectionné` was a desk.
  //
  // The home desk keeps its NAME, because that one is still read — it
  // is the browser tab's title.
  const parent = model.desks.find((dk) => dk.path === deskOf(o));
  const onADesk = Boolean(parent)
    && (parent.template === "section.html" || parent.template === "index.html");
  const drawnAsAnIcon = o.path !== "content" && onADesk;
  const wall = hasAGround ? `
    <label>fond d'écran
      <div class="wall" id="wall">${o.wallpaper
        ? `<img src="${q("/media/" + o.path + "/" + o.wallpaper)}" alt="">`
        : `<span>${o.path === "content" ? "celui par défaut"
                                        : "hérité du bureau au-dessus"}</span>`}</div>
    </label>
    <p class="drop" data-drop="wallpaper">Dépose une image ici pour changer le fond.</p>` : "";
  // A DESCRIPTION PER PHOTOGRAPH. Without it every photograph on the
  // site carries alt="", which tells a screen reader there was nothing
  // there — and in a portfolio the photographs are the content. It was
  // writable by hand in the .md and nowhere in the panel.
  const alt = o.alt || {};
  const shots = o.photographs.map((n, i) => `
    <li class="shot" draggable="true" data-name="${esc(n)}">
      <img src="${q("/media/" + o.path + "/" + n)}" alt="">
      <b>${i + 1}</b><button class="bin" title="jeter">✕</button>
      <input class="alt" type="text" data-alt="${esc(n)}" maxlength="300"
             value="${esc(alt[n] || "")}"
             placeholder="ce qu'on voit sur cette photo">
    </li>`).join("");

  // CAN ANOTHER PHOTOGRAPH GO IN? A page and a gallery: always. A
  // photo: only while it is still empty.
  const canTakeAPhoto = isPhoto(o) ? o.photographs.length === 0 : true;

  // A PHOTO IS A PHOTO. It holds one, and `add_image` refuses a second
  // — so while it has its photograph there is nowhere to drop another.
  // Her ✕ on the picture takes it away and the drop zone comes back. A
  // drop zone that can only be refused is worse than none.
  //
  // (Said here rather than inside the template literal: a `*/` in
  // there closes the `${...}` early, and the file stopped parsing.)
  const full = `<p class="hintline">Une photo seule n'en tient qu'une.
    Jette celle-ci pour en mettre une autre, ou fais-en une page.</p>`;

  const canBin = o.path !== "content";
  // A PHOTOGRAPH IS A PHOTOGRAPH.
  //
  // One photograph lying on a desk, with no film and no dossier beside
  // it. It opens as itself, its miniature IS itself, and it has
  // nothing to say in words — so it is offered what a photograph has:
  // a name, the picture, what the picture shows, and the bin.
  //
  // What it is NOT offered, and why each one was there:
  //
  //   a text box      every content file has a body, so every object
  //                   got one. On a photograph that body appears on a
  //                   page nothing links to, so it was a box that did
  //                   nothing.
  //   what it opens   a switch that existed only to rescue that text.
  //                   With no text there is nothing to rescue, and the
  //                   verb behind it is gone with it.
  //   an appearance   the miniature of a photograph is the photograph.
  //                   Offering a different face is offering a lie.
  //
  // DESKS ONLY, deliberately. The gallery and `travail sélectionné`
  // hold photographs that behave differently — a grid, a road — and
  // this is about the ones dropped alone on DA and graphic design.
  // A PHOTO, because she said so when she made it — not because the
  // folder happens to hold one picture. The old test counted files, so
  // a page with one photograph in it became a photograph, and a photo
  // she had not filled yet was a page.
  const lonePhoto = o.type ? isPhoto(o)
    : (!isDesk && !o.gallery && !o.video && !o.doc
       && o.photographs.length === 1);

  // A TEXT BOX WHERE THE TEXT IS SHOWN, and nowhere else.
  //
  // Every content file has a body under the +++, so every object got a
  // box for it. Only two templates render one: `page.html` — a
  // folder-page, a project, a film, a dossier — and `index.html`, the
  // home page, which puts it inside the about window.
  //
  // `section.html` and `gallery.html` contain no `.content` at all. So
  // on DA, on graphic design and on pellicules she could type a
  // paragraph, see it saved, and it appeared on no page of the site.
  // Checked by putting a marker in each file and building: the two
  // folder-pages' markers came out in their HTML and these three
  // came out nowhere.
  //
  // THE HOME DESK IS LEFT OUT TOO, and it is the one case where the
  // text IS rendered. `about me.txt` is a second row on the same path
  // and writes the same body — the field appeared twice, meaning one
  // thing in one place and the same thing in the other. The about row
  // keeps it, because that is the name she is looking for when she
  // wants to change those words.
  //
  // A project declares no template and Zola gives it page.html, which
  // is why "" counts.
  const textIsShown = o.template === "page.html" || o.template === "";

  look.innerHTML = `
    <h2>${esc(o.titles.fr || o.name)}</h2>
    <p class="what">${kindOf(o)}${o.gallery ? ` · ${o.photographs.length} photos`
       : o.holds !== undefined ? ` · ${o.holds} chose${o.holds > 1 ? "s" : ""} dedans` : ""}${
       !drawnAsAnIcon ? "" : o.x !== null ? ` · ${o.x}% / ${o.y}%`
                                            : " · pas encore posé"}</p>
    ${drawnAsAnIcon || isDesk || o.kind === "about" ? "" : `<p class="what">Sur
      une page, pas sur un bureau : elle s'affiche dans l'ordre de son nom de
      dossier, sans titre et sans position.</p>`}
    ${isDesk ? `<p class="what">${folderSays(o)}</p>` : ""}
    ${waitingFor(o) ? `<p class="waiting">${esc(waitingFor(o))}</p>` : ""}
    ${drawnAsAnIcon || o.path === "content" ? titles : ""}${
      lonePhoto || !textIsShown ? "" : bodies}${bandeau}${
      lonePhoto || !drawnAsAnIcon ? "" : face}${wall}
    ${hasAGround || isFilm(o) ? "" : `<ul class="shots">${shots}</ul>`}
    ${dossier(o)}${reel(o)}
    ${hasAGround || isFilm(o) ? "" : canTakeAPhoto ? dropPhotos(o) : full}
    ${hasAGround || isFilm(o) || !o.photographs.length ? "" : `<p class="hintline">La
      description sert aux personnes qui ne voient pas la photo. Elle est
      écrite une fois pour toutes les langues.</p>`}
    ${canBin ? `<button class="bin-all" id="binall">Jeter ${esc(o.titles.fr || o.name)}</button>` : ""}`;
  wire(o);
}

function wire(o) {
  // The two words in the top bar, offered on the home desk. They belong
  // to no desk — they are on every page — but the bar's own wordmark
  // links here, and this is the screen she starts on. The empty pane
  // would have been a quieter place to put them and nobody would ever
  // have seen it: the panel always has something chosen.
  if (el("who")) {
    const send = async () => {
      const out = await act({ verb: "set_identity",
                              owner: el("who").value, studio: el("studio").value });
      if (out) tell("bandeau enregistré");
    };
    el("who").addEventListener("change", send);
    el("studio").addEventListener("change", send);
  }
  look.querySelectorAll("[data-drawn]").forEach((b) => {
    b.addEventListener("click", async () => {
      const out = await act({ verb: "set_face", item: o.path,
                              how: "folder", which: b.dataset.drawn });
      if (out) tell("icône : un dossier");
    });
  });
  look.querySelectorAll("[data-alt]").forEach((i) => {
    i.addEventListener("change", async () => {
      const out = await act({ verb: "set_alt", item: o.path,
                              name: i.dataset.alt, text: i.value });
      if (out) tell("description enregistrée");
    });
  });
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
      // Where to land afterwards, worked out BEFORE the thing is gone.
      // Throwing away whatever is on screen used to leave the frame
      // pointing at a page that no longer exists — a blank room with no
      // way out but the back button.
      const home = o.path.split("/").slice(0, -1).join("/");
      const out = await act({ verb: "throw_away", item: o.path });
      if (!out) return;
      tell("à la corbeille — Annuler la ramène");
      const back = find(home) || (model.desks[0] || null);
      chosen = null;
      if (back) select(back);
      else { paint(); inspect(null); }
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

/* WHAT MAY BE MADE HERE, AND WHERE "HERE" IS.
 * --------------------------------------------------------------------
 * She right-clicks the surface and gets a menu of what belongs there.
 * It replaces a row of selects — `dans …`, `quoi créer`, a name, a
 * button — where she could pick a film and `dans: pellicules`, press
 * Créer, and be told no. THE MENU MAKES THE REFUSAL UNREACHABLE
 * instead of explaining it afterwards.
 *
 * Pointing also says WHERE, which the row could not: the click has an
 * x and a y, so the thing appears under the pointer instead of in a
 * slot she then has to drag it out of.
 *
 *   the main desktop    un dossier — plus une galerie and une
 *                       sélection, each only while absent
 *   inside a bureau     une photo, un film, une page
 *   inside a gallery    nothing: a gallery holds the photographs she
 *                       drops, and new_project refuses a project there
 *
 * Which desk she clicked comes from `data-desk` on the surface itself
 * — the page says which it is rather than the panel mapping a url
 * back through a language prefix and a base. */
function whatFitsIn(deskPath, desks) {
  // THE DESKS ARE THE INPUT, so the answer can be asked of a desktop
  // that is missing something — which is the half that matters and
  // the half a running panel cannot show you. `model` is a `let` and
  // is not reachable from outside this file, so the seam is here.
  const all = desks || (model && model.desks) || [];
  const d = all.find((x) => x.path === deskPath);
  if (!d || d.gallery) return [];
  if ((d.depth || 0) > 0) {
    return [["photo", "une photo"], ["video", "un film"], ["page", "une page"]];
  }
  // eslint-disable-next-line no-unused-vars
  // THE MAIN DESKTOP. A gallery and a selection are one of a kind, and
  // the test is the SORT rather than the name — she may call a gallery
  // whatever she likes and still not get a second. Read from the
  // template, which is the only thing that says which is which; the
  // server refuses either way, so this list being generous would be a
  // refusal rather than a wrong file.
  const first = all.filter((x) => (x.depth || 0) === 1);
  const out = [["folder", "un dossier"]];
  if (!first.some((x) => x.gallery)) out.push(["gallery", "une galerie"]);
  if (!first.some((x) => x.template === "page.html"))
    out.push(["selection", "une sélection"]);
  return out;
}

/* The menu itself, drawn inside the framed page so a click's own
 * coordinates place it, with its look injected the way mark()'s
 * outline is. */
function shutMenu(doc) {
  const had = doc.getElementById("studio-menu");
  if (had) had.remove();
}

function openMenu(doc, e, desk) {
  shutMenu(doc);
  const deskPath = (desk.dataset.desk || "").replace(/\/$/, "");
  const fits = whatFitsIn(deskPath);
  if (!fits.length) {
    tell("rien à créer ici");
    return;
  }
  if (!doc.getElementById("studio-menu-css")) {
    const s = doc.createElement("style");
    s.id = "studio-menu-css";
    s.textContent = `#studio-menu{position:absolute;z-index:9999;margin:0;padding:.25rem;
      list-style:none;background:#fff;border:1px solid #9a9aa2;border-radius:4px;
      box-shadow:0 6px 18px rgb(0 0 0 / .25);font:13px/1.3 system-ui,sans-serif;
      min-width:11rem}
      #studio-menu li{margin:0}
      #studio-menu button{display:block;width:100%;text-align:left;padding:.3rem .5rem;
      border:0;background:none;font:inherit;cursor:pointer;border-radius:3px}
      #studio-menu button:hover,#studio-menu button:focus-visible{background:#e8eefc}
      #studio-menu .where{padding:.2rem .5rem .3rem;color:#6b6b74;font-size:11px}`;
    (doc.head || doc.documentElement).append(s);
  }
  const r = desk.getBoundingClientRect();
  const x = e.clientX - r.left, y = e.clientY - r.top;
  const menu = doc.createElement("ul");
  menu.id = "studio-menu";
  const here = (model.desks.find((d) => d.path === deskPath) || {});
  menu.innerHTML = `<li class="where">créer dans ${
    esc(here.titles ? (here.titles.fr || here.name) : deskPath)}</li>`
    + fits.map(([k, label]) =>
        `<li><button type="button" data-make="${k}">${label}</button></li>`).join("");
  // placed where she clicked, in the desk's own coordinates — the same
  // space arrange() and place() work in
  menu.style.left = Math.round(x) + "px";
  menu.style.top = Math.round(y) + "px";
  desk.append(menu);
  for (const b of menu.querySelectorAll("[data-make]")) {
    b.addEventListener("click", async () => {
      shutMenu(doc);
      await makeHere(deskPath, b.dataset.make, desk, x, y);
    });
  }
  menu.querySelector("button").focus();
}

/* Make it, and put it where she pointed. */
async function makeHere(into, what, desk, x, y) {
  const name = "sans nom";
  const out = what === "folder" || what === "gallery" || what === "selection"
    ? await act({ verb: "new_bureau", into, name,
                  display: what === "folder" ? "desk" : what })
    : await act({ verb: "new_project", into, name, kind: what });
  const made = out && out.did && out.did.made;
  if (!made) return;                       // act() has already said why
  // WHERE SHE POINTED. A percentage of the desk, which is what `place`
  // takes and what `arrange()` reads back — so it lands under the
  // pointer rather than in whatever slot the loose grid had left.
  const r = desk.getBoundingClientRect();
  await act({ verb: "place", item: made,
              x: Math.max(0, Math.min(100, Math.round(x / r.width * 100))),
              y: Math.max(0, Math.min(100, Math.round(y / r.height * 100))) });
  const o = find(made);
  if (o) select(o);
  tell("créé ici — donne-lui un nom");
  const box = look.querySelector('[data-title="fr"]');
  if (box && box.focus) { box.focus(); if (box.select) box.select(); }
}

/* WHICH BOX WILL TAKE THIS FILE.
 *
 * Every drop zone used to light up at once, whatever was being dragged —
 * "when I want to drop a video plenty of placeholders highlight". So the
 * pane lit up and said nothing about where the file could actually go.
 *
 * During a drag the files themselves are unreadable (that is the
 * browser's rule, and a good one), but `dataTransfer.items` carries each
 * one's TYPE. That is enough: a video can only be the film, a PDF only
 * the dossier, an image anything that shows a picture.
 *
 * Unknown or missing type — some browsers give "" for an unusual
 * extension — lights everything, because refusing to guide is better
 * than guiding wrong. The verb still has the last word either way. */
const TAKES = {
  video:     (kind) => kind.startsWith("video/"),
  doc:       (kind) => kind === "application/pdf",
  photos:    (kind) => kind.startsWith("image/"),
  icon:      (kind) => kind.startsWith("image/"),
  // THE THREE ICON SLOTS. `icon-gif` takes only a GIF, because the
  // slot's whole meaning is that the face MOVES — and the verb refuses
  // a still there, so lighting it would be a promise it cannot keep.
  // The other two take any picture: a folder she drew and a photograph
  // are the same kind of file, and which it is is what the slot says.
  "icon-folder": (kind) => kind.startsWith("image/"),
  "icon-photo":  (kind) => kind.startsWith("image/"),
  "icon-gif":    (kind) => kind === "image/gif",
  poster:    (kind) => kind.startsWith("image/"),
  wallpaper: (kind) => kind.startsWith("image/"),
  about:     (kind) => kind.startsWith("image/"),
};

function dragKinds(e) {
  const items = (e.dataTransfer && e.dataTransfer.items) || [];
  const out = [];
  for (const it of items) if (it.kind === "file") out.push(it.type || "");
  return out;
}

function guide(e) {
  const kinds = dragKinds(e);
  const blind = !kinds.length || kinds.some((k) => !k);
  const hit = e.target.closest && e.target.closest("[data-drop]");
  look.querySelectorAll("[data-drop]").forEach((zone) => {
    const takes = TAKES[zone.dataset.drop] || (() => true);
    const yes = blind || kinds.every(takes);
    zone.classList.toggle("can", yes);
    zone.classList.toggle("cannot", !yes);
    zone.classList.toggle("aim", yes && zone === hit);
  });
  return { blind, kinds };
}

function unguide() {
  look.querySelectorAll("[data-drop]").forEach((zone) =>
    zone.classList.remove("can", "cannot", "aim"));
}

["dragenter", "dragover"].forEach((k) =>
  look.addEventListener(k, (e) => {
    e.preventDefault();
    look.classList.add("over");
    guide(e);
  }));
["dragleave", "drop"].forEach((k) => look.addEventListener(k, () => {
  look.classList.remove("over");
  unguide();
}));
look.addEventListener("drop", async (e) => {
  const o = find(chosen);
  if (!o || !e.dataTransfer.files.length) return;
  e.preventDefault();
  // dropped on the wallpaper patch, or anywhere else in the panel
  const hit = e.target.closest && e.target.closest("[data-drop]");
  let as = hit ? hit.dataset.drop : "photos";
  const files = [...e.dataTransfer.files];
  // A PDF dropped anywhere on a project that IS a dossier goes to the
  // dossier. Dropping it on the photographs would be refused with a
  // sentence telling her to aim at a box three centimetres away, which
  // is a worse answer than doing the obvious thing.
  //
  // Only when the project already wants one — on a project of
  // photographs a PDF still refuses, because accepting it would quietly
  // change what clicking that icon does.
  // A PAGE TAKES PDFs, whatever it is called. This read the title's
  // extension; the type says it now.
  const wantsDoc = isPage(o);
  if (as === "photos" && wantsDoc && files.every((f) => /\.pdf$/i.test(f.name)))
    as = "doc";
  // a wallpaper and an icon are one each; photographs are a pile
  for (const f of (as === "photos" ? files : files.slice(0, 1))) {
    const out = await ask(
      `/api/upload?into=${encodeURIComponent(o.path)}&name=${encodeURIComponent(f.name)}`
      + (as === "photos" ? "" : `&as=${as}`),
      { method: "POST", body: await f.arrayBuffer() });
    const said = { wallpaper: "fond d'écran changé", icon: "apparence changée",
                   "icon-folder": "ton dessin de dossier est en place",
                   "icon-photo": "la photo est en place comme icône",
                   "icon-gif": "le GIF est en place comme icône",
                   about: "ta photo de présentation est en place",
                   doc: "le dossier est en place" }[as]
                 || `${f.name} ajoutée`;
    tell(out ? said : `${f.name} refusée`);
  }
});

/* ---- moving a real icon, in the real page ------------------------- */

/* The thing she last touched, outlined in the real page. Without it the
 * only sign a click did anything is a column on the other side of the
 * window changing, which does not read as "I selected this". */
function mark(doc, icon) {
  if (!doc.getElementById("studio-mark")) {
    const s = doc.createElement("style");
    s.id = "studio-mark";
    s.textContent = `.studio-chosen{outline:2px solid #5b86e5;outline-offset:6px;
      border-radius:3px}.icon{cursor:pointer}`;
    (doc.head || doc.documentElement).append(s);
  }
  doc.querySelectorAll(".studio-chosen").forEach((n) => n.classList.remove("studio-chosen"));
  if (icon) icon.classList.add("studio-chosen");
}

/* IN HERE, A CLICK EDITS. The page's own dynamics — a folder opening a
 * window, a project opening a preview — belong to a visitor, and firing
 * them while she is arranging a desk carries her away from the thing she
 * just touched. Caught on the way down, before the site's own handler on
 * the icon ever sees it.
 *
 * Armed once per document and guarded by a flag, because the frame is
 * reloaded often and a second copy of this would be harmless but silly. */
function arm(doc) {
  if (doc.__studioArmed) return;
  doc.__studioArmed = true;
  doc.addEventListener("click", (e) => {
    const icon = e.target.closest && e.target.closest("a.icon[data-vt]");
    if (!icon) return;
    e.preventDefault();
    e.stopImmediatePropagation();
  }, true);
  // A LEFT-CLICK ANYWHERE SHUTS THE MENU, and a right-click on the
  // surface opens one. On an ICON it does nothing: an icon is a thing
  // already, and "create here" is about the empty space.
  doc.addEventListener("click", () => shutMenu(doc));
  doc.addEventListener("keydown", (e) => {
    if (e.key === "Escape") shutMenu(doc);
  });
  doc.addEventListener("contextmenu", (e) => {
    const desk = e.target.closest && e.target.closest(".desk[data-desk]");
    if (!desk) return;                     // not a surface: let the browser be
    if (e.target.closest("a.icon")) return;
    e.preventDefault();
    openMenu(doc, e, desk);
  });
}

/* What is under the pointer, other than the thing being dragged — and
 * only if it is somewhere this thing could actually go.
 *
 * The guardrails are the verb's: a gallery shows photographs only, a
 * project is not a container, and nothing goes inside itself. Those are
 * refused by the server whatever the panel does; this stops her finding
 * out by being told no, which is the difference between a tool that
 * guides and one that scolds. */
function canTake(targetPath, movingPath) {
  if (!targetPath || targetPath === movingPath) return false;
  const k = model && model.desks.find((d) => d.path === targetPath);
  // asked of the model, not restated here — the server decides, and a
  // second copy of the rule is a second thing to keep true
  if (!k || !k.can_receive) return false;
  if (targetPath.startsWith(movingPath + "/")) return false;  // inside itself
  if (deskOf({ path: movingPath }) === targetPath) return false;  // already there
  return true;
}

function under(doc, e, self) {
  const seen = doc.elementsFromPoint
    ? doc.elementsFromPoint(e.clientX, e.clientY) : [];
  for (const node of seen) {
    const icon = node.closest && node.closest("a.icon[data-vt]");
    if (!icon || icon === self) continue;
    const path = bySlug.get(icon.dataset.vt);
    return canTake(path, bySlug.get(self.dataset.vt)) ? icon : null;
  }
  return null;
}

/* The folder she is about to drop into, lit up in the real page. */
function aimAt(doc, icon) {
  if (!doc.getElementById("studio-aim")) {
    const s = doc.createElement("style");
    s.id = "studio-aim";
    s.textContent = ".studio-aim{outline:3px dashed #3aa76d;outline-offset:6px;border-radius:3px}";
    (doc.head || doc.documentElement).append(s);
  }
  doc.querySelectorAll(".studio-aim").forEach((n) => n.classList.remove("studio-aim"));
  if (icon) icon.classList.add("studio-aim");
}

function hook() {
  let doc;
  try { doc = view.contentDocument; } catch (e) { return; }
  if (!doc) return;
  const desk = doc.querySelector(".desk");
  tip.textContent = desk
    ? "Clique pour modifier · double-clique pour entrer · attrape pour poser,"
      + " ou lâche sur un dossier pour l'y ranger"
    : "Cette page n'est pas un bureau — rien à déplacer ici.";
  if (!desk) return;

  // FIRST, and before anything that can fail. This used to sit below the
  // code that builds the slug map, which reads `model` — and `model` is
  // null until the tree arrives. The first load therefore threw here and
  // the suppression was never installed at all, so a click went straight
  // through to the site and opened the window. Nothing that follows may
  // be allowed to stop this being armed.
  arm(doc);
  if (!model) return;

  // data-vt in the page -> the row's key, and back. about me.txt is a
  // declared window, so its slug comes from the name she typed in
  // [extra.items] rather than from a path — clicking it used to find
  // nothing in here and select nothing at all, which is what "there is
  // no possibility to choose anything" was.
  bySlug = new Map();
  const slugOf = new Map();
  for (const { o } of all()) {
    const slug = o.kind === "about"
      ? "about-me-txt"
      : o.path.replace(/^content\//, "").replace(/\//g, "-");
    bySlug.set(slug, keyOf(o));
    slugOf.set(keyOf(o), slug);
  }
  // the frame is rebuilt often; put the outline back on whatever is chosen
  if (chosen && slugOf.has(chosen)) {
    mark(doc, doc.querySelector(`a.icon[data-vt="${slugOf.get(chosen)}"]`));
  }

  doc.querySelectorAll("a.icon[data-vt]").forEach((icon) => {
    const path = bySlug.get(icon.dataset.vt);
    if (!path) {
      // a window or a shortcut: declared in config.toml, nothing to edit
      icon.title = "déclaré dans config.toml — pas modifiable ici";
      return;
    }
    icon.addEventListener("dblclick", (e) => {
      e.preventDefault();
      e.stopImmediatePropagation();
      const o = find(path);
      if (!o) return;
      // WHAT THE SITE DOES, read off the icon the site rendered.
      //
      // `data-window` is the engine's own answer to "what does this
      // open?", written by _icon.html and acted on by desk.js. The
      // panel suppresses the site's click in arm() — it has to, or
      // choosing anything on a desk navigates — so it opens the dialog
      // itself, which is the site's behaviour arriving by another road.
      //
      // IT USED TO DECIDE FOR ITSELF, and got it wrong: `about me.txt`
      // was special-cased to open its window and EVERYTHING ELSE went
      // to its page. So a photograph, which opens in place on the site,
      // opened a page with a white ground, a title and a paragraph in
      // the editor. She was being shown something the site does not do.
      //
      // The about case was never special. It carries
      // `data-window="about"` like any other, and this is that one
      // branch written for all of them.
      const id = icon.dataset.window;
      const win = id ? doc.getElementById(id) : null;
      if (win && win.showModal) {
        if (!win.open) win.showModal();
        return;
      }
      // nothing to open: a bureau becomes the desk shown, anything else
      // is a page, which is what its icon is a plain link to
      if (isBureau(o)) { mode = "desk"; setPressed(); chosen = o.path; view.src = urlOf(o); paint(); }
      else setMode("page");
    }, true);
    // ON THE DESK, or in a folder's window? Inside a window the icons are
    // a LIST — the site deliberately does not make them draggable, and
    // their x/y means nothing there. Attaching position-dragging to them
    // would write a coordinate for something that has none.
    // `about me.txt` is on the desk, but its position lives in
    // [extra.items] and no verb writes there — so a drag must not try to
    // place it. Treated like an icon in a window: a click chooses it, a
    // drag does nothing.
    const onDesk = desk.contains(icon) && (find(path) || {}).kind !== "about";

    let from = null;
    icon.addEventListener("pointerdown", (e) => { from = { x: e.clientX, y: e.clientY }; }, true);
    if (onDesk) {
      icon.addEventListener("pointermove", (e) => {
        if (!from || narrowView) return;
        aimAt(doc, under(doc, e, icon));
      }, true);
    }
    icon.addEventListener("pointerup", async (e) => {
      const was = from; from = null;
      if (!was) return;
      const moved = Math.abs(e.clientX - was.x) > 3 || Math.abs(e.clientY - was.y) > 3;
      const o = find(path);
      // Looking, not arranging. See narrowView above.
      if (!moved || !onDesk || narrowView) {
        aimAt(doc, null);
        if (o) { select(o); mark(doc, icon); }
        return;
      }
      // Dropped ON something? Then she is filing it, not placing it —
      // the gesture a desktop has always had.
      const onto = under(doc, e, icon);
      aimAt(doc, null);
      if (onto) {
        const target = bySlug.get(onto.dataset.vt);
        const out = target && await act({ verb: "move", item: path, into: target });
        if (out && out.did) {
          const moved_ = find(out.did.moved);
          tell("rangé dans " + (find(target) || { name: target }).name);
          if (moved_) select(moved_);
        }
        return;
      }
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
// the frame's src is in the markup, so its first load can land BEFORE
// this script runs. Hook what is already there.
hook();

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



/* A WHOLE FOLDER, IN ONE GESTURE.
 *
 * She picks a folder in the native dialog and the browser hands over
 * every file inside it. The panel makes the project, named after the
 * folder, and puts the photographs in — in the order their names put
 * them. One gesture instead of: open the Finder, size two windows so
 * neither covers the other, drag.
 *
 * TWO THINGS ARE FILTERED OUT HERE rather than left to the server.
 *
 * Hidden files, because macOS writes a `.DS_Store` into every folder a
 * Finder window has been opened on. The server would refuse it,
 * correctly, and she would get an error about a file she never chose —
 * which is the same noise that used to stop her preview.
 *
 * And anything deeper than the folder itself. `webkitRelativePath` is
 * "Dossier/01.jpg" for a file in it and "Dossier/vieux/01.jpg" for one
 * below — a project is one folder of photographs, so the second is not
 * hers to flatten without asking.
 */
el("adddir").addEventListener("click", () => el("pickdir").click());

el("pickdir").addEventListener("change", async () => {
  const picked = [...el("pickdir").files];
  el("pickdir").value = "";                 // so the same folder can be picked twice
  if (!picked.length) return;

  const parts = (f) => (f.webkitRelativePath || f.name).split("/");
  const folder = parts(picked[0])[0];
  const mine = picked
    .filter((f) => parts(f).length === 2)
    .filter((f) => !parts(f)[1].startsWith("."))
    .sort((a, b) => parts(a)[1].localeCompare(parts(b)[1], "fr", { numeric: true }));

  if (!mine.length) {
    tell(`${folder} : rien à mettre dedans — que des fichiers cachés ou des sous-dossiers.`);
    return;
  }

  // A FOLDER OF IMAGES IS A PAGE. It read the row's `kind`, so she
  // could drop a folder of photographs and have it arrive as a film.
  const into = intoNow();
  if (!into) { tell("choisis d'abord un bureau"); return; }
  const made = await act({ verb: "new_project", into, name: folder,
                           kind: "page" });
  if (!made || !made.made) return;          // act() has already said why

  let put = 0;
  for (const f of mine) {
    const out = await ask(
      `/api/upload?into=${encodeURIComponent(made.made)}`
      + `&name=${encodeURIComponent(parts(f)[1])}`,
      { method: "POST", body: await f.arrayBuffer() });
    if (out) put += 1;
  }
  const o = find(made.made);
  if (o) select(o);
  tell(put === mine.length
    ? `${folder} : ${put} image(s) en place.`
    : `${folder} : ${put} sur ${mine.length} — le reste a été refusé.`);
});

function setPressed() {
  el("asdesk").setAttribute("aria-pressed", String(mode === "desk"));
  el("aspage").setAttribute("aria-pressed", String(mode === "page"));
}

const setMode = (m) => {
  mode = m;
  setPressed();
  const o = find(chosen);
  if (o) select(o);
};
function setWidth(phone) {
  narrowView = phone;
  el("asphone").closest(".stage").classList.toggle("is-phone", phone);
  el("aswide").setAttribute("aria-pressed", String(!phone));
  el("asphone").setAttribute("aria-pressed", String(phone));
  tell(phone
    ? "Le téléphone, tel quel. Ici on regarde : pour déplacer, repasse en écran."
    : "Attrape une icône dans la page et pose-la.");
}
el("aswide").addEventListener("click", () => setWidth(false));
el("asphone").addEventListener("click", () => setWidth(true));

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
  hook();                      // now that there IS a model to hook with
  if (model && model.desks.length) select(model.desks[0]);
  tell("prêt");
});
