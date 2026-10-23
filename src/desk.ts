// Desktop behaviour: move things freely, refuse to nest them, open windows.
// ponytail: pointer events and the Web Animations API. No drag library.

/** The active language's strings, written onto <body> by base.html.
 *  An unknown key shows as the key — visible, and never a blank. */
const STRINGS: Record<string, string> =
  JSON.parse(document.body.dataset.i18n ?? "{}") as Record<string, string>;
const say = (key: string): string => STRINGS[key] ?? key;

const clamp = (v: number, lo: number, hi: number): number =>
  Math.min(Math.max(v, lo), hi);

const calm = (): boolean =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let topZ = 10;

/** How many pointers are currently holding something. A layout pass must
 *  not rewrite the position of an icon someone is in the middle of
 *  moving — a resize mid-drag used to do exactly that. */
let holding = 0;

/** Things dragged since their last pointerdown. A drag must never also
 *  count as a click — dropping `about me.txt` somewhere moves it, it does
 *  not open it. */
const justDragged = new WeakSet<HTMLElement>();

/** Where the VISITOR put things — as a FRACTION of where it was allowed
 *  to go, not as a count of pixels.
 *
 *  Pixels do not survive the viewport changing. 1180px from the left is
 *  the right-hand side of a laptop and off the edge of a phone, so an
 *  icon placed thoughtfully in a corner arrived at a rotation having
 *  been shoved somewhere arbitrary by the clamp. The arrangement was not
 *  preserved, only prevented from breaking.
 *
 *  A fraction of the PLACEABLE AREA rather than of the desk, which is
 *  the part that makes corners work: 1 means "as far right as it goes",
 *  whatever the screen, instead of "all the way to the edge and then
 *  clamped back by its own width".
 *
 *  Only their own moves belong here. A position the clamp chose on their
 *  behalf is not an arrangement, and remembering those made every return
 *  to a bureau land somewhere new. */
const byHand = new WeakMap<HTMLElement, { fx: number; fy: number }>();

/** How far down the bandeau reaches. Measured once per pass — it is the
 *  same for every icon, and it changes between a desktop and a phone,
 *  where the three slots stack. */
function barCeiling(): number {
  const bar = document.querySelector<HTMLElement>(".bar");
  return bar === null ? 0 : bar.getBoundingClientRect().height + 8;
}

/** The rectangle an icon's top-left corner may occupy: the desk, less
 *  its own size, less the bandeau above and a margin below.
 *
 *  Writing a position and reading one both go through here, so the two
 *  ends cannot disagree about what "as far right as it goes" means.
 *  Every bug in this file so far has been two pieces of code deciding
 *  the same thing slightly differently. */
function field(frame: DOMRect, ceiling: number, w: number, h: number):
  { x0: number; x1: number; y0: number; y1: number } {
  return {
    x0: 0,
    x1: Math.max(0, frame.width - w),
    y0: ceiling,
    y1: Math.max(ceiling, frame.height - h - 10),   // never flush to the bottom
  };
}

// Declarations rather than consts so tools/desk-check.mjs can reach them
// after running this script — the test exercises what actually ships
// instead of a copy of it that can drift.
function asFraction(v: number, lo: number, hi: number): number {
  return hi - lo <= 0 ? 0 : clamp((v - lo) / (hi - lo), 0, 1);
}

function asPixels(f: number, lo: number, hi: number): number {
  return lo + f * Math.max(0, hi - lo);
}

// ---------------------------------------------------------------------
// Leaving a bureau and coming back
//
// Where you left things is remembered for the session, per bureau. On
// return the icons are put back exactly where you dropped them, then
// walked home — so the reset is something you watch happen rather than
// something that already happened before the page appeared.
// ---------------------------------------------------------------------

const DESK_KEY = `bureau:${location.pathname}`;

type Layout = Record<string, { fx: number; fy: number }>;

function readLayout(): Layout {
  try {
    const raw = sessionStorage.getItem(DESK_KEY);
    if (raw === null) return {};
    // Read defensively. An entry written by an older build holds pixels,
    // not fractions, and reading one as a fraction would animate every
    // icon by NaN. Anything that is not two finite numbers is dropped,
    // which also covers a corrupt entry for free.
    const out: Layout = {};
    const parsed = JSON.parse(raw) as Record<string, { fx?: unknown; fy?: unknown }>;
    for (const key of Object.keys(parsed)) {
      const v = parsed[key];
      if (typeof v?.fx === "number" && Number.isFinite(v.fx) &&
          typeof v?.fy === "number" && Number.isFinite(v.fy)) {
        out[key] = { fx: v.fx, fy: v.fy };
      }
    }
    return out;
  } catch {
    return {};                       // private mode, quota, corrupt entry
  }
}

function saveLayout(): void {
  const out: Layout = {};
  document.querySelectorAll<HTMLElement>(".desk .icon").forEach((el) => {
    const key = el.dataset["vt"];
    const mine = byHand.get(el);
    if (key === undefined || mine === undefined) return;
    out[key] = mine;
  });
  try {
    if (Object.keys(out).length === 0) sessionStorage.removeItem(DESK_KEY);
    else sessionStorage.setItem(DESK_KEY, JSON.stringify(out));
  } catch { /* nothing we can do, and nothing worth breaking over */ }
}

// ---------------------------------------------------------------------
// Arriving
//
// The wallpaper is one large background image and every icon is its own
// request, so left alone a bureau assembles itself in front of the
// visitor — pieces landing one at a time. The overlay is held until they
// have all decoded, then everything is revealed at once.
//
// Capped, because a portfolio must never be held hostage by one slow
// image: past the cap we reveal regardless and let the stragglers land.
// ---------------------------------------------------------------------

const PATIENCE_MS = 4000;

/** What this page must have in hand before it is worth showing.
 *
 *  A bureau is a composed scene: the wallpaper and every icon, or it
 *  assembles itself in public. A project page or a gallery is a scroll —
 *  waiting for every photograph would mean staring at dots for seconds,
 *  so only what is not deferred counts, which is roughly the first
 *  screen. Everything below fades in as it lands. */
function needed(): string[] {
  const urls: string[] = [];
  const desk = document.querySelector<HTMLElement>(".desk");
  if (desk !== null) {
    const found = /url\(["']?(.+?)["']?\)/.exec(getComputedStyle(desk).backgroundImage);
    const wallpaper = found?.[1];
    if (wallpaper !== undefined) urls.push(wallpaper);
  }
  document
    .querySelectorAll<HTMLImageElement>('img:not([loading="lazy"])')
    .forEach((i) => { if (i.src !== "") urls.push(i.src); });
  return urls;
}

/** A picture arriving below the fold should read as intentional, not as
 *  the page twitching. */
function fadeInLateArrivals(): void {
  document.querySelectorAll<HTMLImageElement>('img[loading="lazy"]').forEach((img) => {
    if (img.complete) return;          // already here — leave it alone
    // hidden only now, by script. CSS alone would strand every lazy image
    // if this file failed to load.
    img.classList.add("will-fade");
    const show = (): void => img.classList.add("is-in");
    img.addEventListener("load", show, { once: true });
    img.addEventListener("error", show, { once: true });   // a gap, not a hole
  });
}

const settled = (url: string): Promise<void> =>
  new Promise((done) => {
    const img = new Image();
    img.onload = () => done();
    img.onerror = () => done();        // a broken image must not hold the page
    img.src = url;
  });

async function whenPainted(): Promise<void> {
  const everything = Promise.all([
    ...needed().map(settled),
    document.fonts.ready.then(() => undefined),
  ]).then(() => undefined);
  const cap = new Promise<void>((go) => { window.setTimeout(go, PATIENCE_MS); });
  await Promise.race([everything, cap]);
}

/** Reveal the bureau: the overlay fades while the icons arrive underneath,
 *  so the two motions overlap instead of queueing. */
/** Arriving from inside the site is not the same as arriving cold.
 *
 *  On a cross-document view transition the browser snapshots the NEW page
 *  as soon as it can render — and our first paint is an opaque overlay
 *  covering everything. So the morph animated the old page into a blank
 *  screen: a cut, then dots, then pictures arriving one by one. The
 *  transition was working; the loader was hiding it.
 *
 *  When a transition is running the old page stays on screen until this
 *  one is ready, which is the whole point. There is nothing to cover. */
let arrivedByTransition = false;
window.addEventListener("pagereveal", (e: Event): void => {
  if ("viewTransition" in e && e.viewTransition !== null) arrivedByTransition = true;
});

function reveal(): void {
  fadeInLateArrivals();
  const loader = document.querySelector<HTMLElement>(".loader");
  if (loader === null) {
    arrange();
    tidyUp();
    document.documentElement.classList.remove("booting");
    return;
  }
  // keep it painted while .booting goes away, then take it out entirely
  loader.classList.add("is-leaving");
  arrange();        // decide where everything belongs…
  tidyUp();         // …then animate the gap from where it was left

  // Showing the page is this function's job. It used to be the last line
  // of tidyUp(), which returns early under reduced motion — so the only
  // thing uncovering the page was a branch that could be skipped.
  document.documentElement.classList.remove("booting");

  if (arrivedByTransition || calm()) {
    loader.remove();     // nothing to fade: the old page covered the gap
    return;
  }
  void loader
    .animate([{ opacity: 1 }, { opacity: 0 }], {
      duration: 420, easing: "cubic-bezier(.4,0,.6,1)", fill: "forwards",
    })
    .finished.then(() => loader.remove());
}

/** Walk everything home, visibly.
 *
 *  Purely visual: it does not write a single position. arrange() has
 *  already put every icon where it belongs, so this only animates the
 *  gap between where you left something and where it now is — a FLIP
 *  with no layout involved at all.
 *
 *  The earlier version wrote positions itself, which meant it and the
 *  layout pass were two things deciding the same thing. They disagreed,
 *  and the disagreement was visible on every second visit. */
function tidyUp(): void {
  const desk = document.querySelector<HTMLElement>(".desk");
  if (desk === null) return;
  const icons = [...desk.querySelectorAll<HTMLElement>(".icon")];
  const left = readLayout();
  try { sessionStorage.removeItem(DESK_KEY); } catch { /* private mode */ }

  const quiet = calm();
  if (quiet) return;                 // already home, and nothing should move

  const frame = desk.getBoundingClientRect();
  const ceiling = barCeiling();
  let staggered = 0;

  icons.forEach((el) => {
    const key = el.dataset["vt"];
    const was = key === undefined ? undefined : left[key];
    const now = el.getBoundingClientRect();

    if (was === undefined) {
      el.animate(
        [{ opacity: 0, transform: "scale(.96)" }, { opacity: 1, transform: "scale(1)" }],
        { duration: 420, delay: staggered * 35, easing: "cubic-bezier(.22,.61,.36,1)", fill: "backwards" },
      );
      staggered += 1;
      return;
    }

    // Where you left it, read back at the size the screen is NOW. Stored
    // as pixels this was wrong the moment the window changed between
    // leaving and coming back: the icon would fly in from somewhere it
    // had never been.
    const box = field(frame, ceiling, now.width, now.height);
    const dx = asPixels(was.fx, box.x0, box.x1) - (now.left - frame.left);
    const dy = asPixels(was.fy, box.y0, box.y1) - (now.top - frame.top);
    if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return;

    el.animate(
      [
        { transform: `translate(${dx}px, ${dy}px)`, opacity: .85 },
        { transform: "translate(0, 0)", opacity: 1 },
      ],
      { duration: 620, delay: staggered * 45, easing: "cubic-bezier(.33,.9,.3,1)", fill: "backwards" },
    );
    staggered += 1;
  });
}

interface Spot { left: string; top: string; x: string; y: string; translate: string }

const spotOf = (el: HTMLElement): Spot => ({
  left: el.style.left,
  top: el.style.top,
  x: el.style.getPropertyValue("--x"),
  y: el.style.getPropertyValue("--y"),
  translate: el.style.translate,
});

function restore(el: HTMLElement, spot: Spot): void {
  el.style.left = spot.left;
  el.style.top = spot.top;
  el.style.translate = spot.translate;
  el.style.setProperty("--x", spot.x);
  el.style.setProperty("--y", spot.y);
}

/** Refuse to nest. Moving an icon around a desktop is free. Putting one
 *  INSIDE another is a different thing, and the site has no such state to
 *  change: a project belongs to the desktop whose folder holds it on disk.
 *  So the attempt is shown, and undone — back to where the drag began. */
async function refuse(el: HTMLElement, folder: HTMLElement, back: Spot): Promise<void> {
  const from = el.getBoundingClientRect();
  const to = folder.getBoundingClientRect();
  const dx = to.left + to.width / 2 - (from.left + from.width / 2);
  const dy = to.top + to.height / 2 - (from.top + from.height / 2);

  el.classList.remove("dragging");
  folder.classList.remove("rejecting");

  if (calm()) {
    restore(el, back);
    return;
  }

  folder.animate(
    [
      { transform: "translateX(0)" },
      { transform: "translateX(-3px)" },
      { transform: "translateX(3px)" },
      { transform: "translateX(-2px)" },
      { transform: "translateX(0)" },
    ],
    { duration: 260, easing: "ease-out" },
  );

  // fill:forwards holds the icon invisible at the folder while we move it
  // back. It must then be cancelled — left running, it reasserts itself
  // once the fade-in ends and the icon disappears for good.
  const fall = el.animate(
    [
      { transform: "translate(0,0) scale(1)", opacity: 1 },
      { transform: `translate(${dx}px, ${dy}px) scale(.3)`, opacity: 0 },
    ],
    { duration: 170, easing: "cubic-bezier(.4,0,.8,.3)", fill: "forwards" },
  );
  await fall.finished;

  restore(el, back);
  fall.cancel();

  await el.animate(
    [{ opacity: 0, transform: "scale(.9)" }, { opacity: 1, transform: "scale(1)" }],
    { duration: 220, easing: "cubic-bezier(.22,.61,.36,1)" },
  ).finished;
}

interface Target { el: HTMLElement; rect: DOMRect }

const hits = (r: DOMRect, x: number, y: number): boolean =>
  x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;

/** @param nests  whether this thing is content that could be filed into a
 *                folder. Icons are. Windows are furniture — they move over
 *                anything, including folders, and are never refused. */
function draggable(el: HTMLElement, nests: boolean): void {
  // An <a> and the <img> inside it are natively draggable. Left alone, the
  // browser starts its own link-drag on pointermove, which cancels our
  // pointer capture and fires pointercancel — the icon never moves. This is
  // the whole reason icons felt dead while windows (a <dialog>) worked.
  el.draggable = false;
  el.querySelectorAll("img, a").forEach((child) => {
    (child as HTMLElement).draggable = false;
  });
  el.addEventListener("dragstart", (e: Event) => e.preventDefault());

  el.addEventListener("pointerdown", (e: PointerEvent): void => {
    if (e.button !== 0) return;

    const from = e.target;
    if (!(from instanceof Element)) return;

    // Never hijack a control NESTED INSIDE the draggable thing. A drag
    // captures the pointer, which retargets the pointerup, so the click
    // never reaches the button — that is why minimise and close did
    // nothing at all.
    //
    // The `!== el` matters more than it looks: an icon IS an <a href>,
    // because that is how it still navigates with JavaScript off. Bailing
    // on any matching ancestor stopped every icon from dragging at all.
    const control = from.closest(
      "button, a[href], input, textarea, select, video, [contenteditable]",
    );
    if (control !== null && control !== el) return;

    // A window moves by its title bar, like a window. Dragging it by the
    // body would make the text unselectable and fight the video controls.
    if (el.classList.contains("win") && from.closest(".win-bar") === null) return;

    // A fixed-position element reports offsetParent === null, so windows —
    // which are all position:fixed — used to bail out here and never move
    // at all. For those the surface is the viewport, and the coordinates
    // are already viewport coordinates.
    const parent = el.offsetParent;
    const surface = parent instanceof HTMLElement ? parent : null;

    justDragged.delete(el);                   // a fresh press, a fresh verdict
    const back = spotOf(el);                  // where this drag started
    const start = el.getBoundingClientRect();
    const grabX = e.clientX - start.left;
    const grabY = e.clientY - start.top;

    // Windows are centred with a translate. Pin them to where they visibly
    // are before the first move, or setting left/top would jump them by
    // half their own size.
    if (surface === null) {
      el.style.left = `${start.left}px`;
      el.style.top = `${start.top}px`;
      el.style.translate = "none";
    }
    let moved = false;
    let over: Target | null = null;

    // folders do not move mid-drag, so measure them once
    const targets: Target[] = nests
      ? [...document.querySelectorAll<HTMLElement>(".icon[data-folder]")]
          .filter((f) => f !== el)
          .map((f) => ({ el: f, rect: f.getBoundingClientRect() }))
      : [];

    holding += 1;
    el.style.zIndex = String(++topZ);
    el.setPointerCapture(e.pointerId);

    const onMove = (ev: PointerEvent): void => {
      // A finger is never perfectly still. Without a threshold every tap
      // registers as a drag, which suppresses the click that should have
      // opened the thing — on a touch screen, that means nothing opens.
      if (!moved) {
        const far = Math.hypot(ev.clientX - e.clientX, ev.clientY - e.clientY);
        if (far < 6) return;
      }
      moved = true;
      el.classList.add("dragging");

      const bounds = surface === null
        ? { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight }
        : surface.getBoundingClientRect();
      el.style.left =
        clamp(ev.clientX - grabX - bounds.left, 0, bounds.width - start.width) + "px";
      el.style.top =
        clamp(ev.clientY - grabY - bounds.top, 0, bounds.height - start.height) + "px";
      el.style.setProperty("--x", "auto");
      el.style.setProperty("--y", "auto");

      const next = targets.find((t) => hits(t.rect, ev.clientX, ev.clientY)) ?? null;
      if (next !== over) {
        over?.el.classList.remove("rejecting");
        next?.el.classList.add("rejecting");
        el.classList.toggle("barred", next !== null);
        over = next;
      }
    };

    const onUp = (ev: PointerEvent): void => {
      holding = Math.max(0, holding - 1);
      el.removeEventListener("pointermove", onMove);
      el.releasePointerCapture(ev.pointerId);
      el.classList.remove("dragging", "barred");

      if (moved) justDragged.add(el);

      if (moved && over !== null) {
        void refuse(el, over.el, back);
      } else if (moved) {
        const desk = el.closest<HTMLElement>(".desk");
        if (desk !== null) {
          const f = desk.getBoundingClientRect();
          const r = el.getBoundingClientRect();
          const box = field(f, barCeiling(), r.width, r.height);
          byHand.set(el, {
            fx: asFraction(r.left - f.left, box.x0, box.x1),
            fy: asFraction(r.top - f.top, box.y0, box.y1),
          });
        }
        saveLayout();
      }
      over?.el.classList.remove("rejecting");
      over = null;
    };

    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerup", onUp, { once: true });
    el.addEventListener("pointercancel", onUp, { once: true });
  });
}

window.addEventListener("pagehide", saveLayout);

// ---------------------------------------------------------------------
// Where things sit
//
// One pass, run whenever the layout could have changed, and IDEMPOTENT:
// running it twice gives the same answer as running it once. That matters
// because it runs on load, on resize and on every orientation change —
// and because the previous version was three separate things writing
// positions, one of which could never be undone. Rotating a phone left
// pixel positions pinned into a layout that no longer used them.
//
// For each icon the pipeline is always the same:
//
//   1. a BASE position   — the grid on a narrow screen, the position
//                          written in the content file on a wide one
//   2. the VISITOR'S     — if they dragged it, that wins over the base
//   3. a CLAMP           — nudged back on if it would hang off the desk
//                          or hide under the bandeau
//
// Nothing destroys the authored position, so turning a phone sideways
// and back puts everything exactly where it started.
// ---------------------------------------------------------------------

/** The position the content file asked for, captured before anything
 *  overwrites it. */
const authored = new WeakMap<HTMLElement, { x: string; y: string }>();

const narrowScreen = (): boolean =>
  window.matchMedia("(max-width: 40rem)").matches;

function rememberAuthored(el: HTMLElement): void {
  if (authored.has(el)) return;
  authored.set(el, {
    x: el.style.getPropertyValue("--x"),
    y: el.style.getPropertyValue("--y"),
  });
}

function arrange(): void {
  if (holding > 0) return;           // not while something is being moved
  const desk = document.querySelector<HTMLElement>(".desk");
  if (desk === null) return;
  const icons = [...desk.querySelectorAll<HTMLElement>(".icon")];
  icons.forEach(rememberAuthored);

  // --- 1. the base layout -------------------------------------------
  // Let CSS decide first: off a narrow screen that is the authored
  // percentages, on one it is the grid. Measuring needs .arranged off.
  desk.classList.remove("arranged");
  icons.forEach((el) => {
    const home = authored.get(el);
    if (home === undefined) return;
    el.style.left = "";
    el.style.top = "";
    el.style.width = "";        // release a width pinned by a previous pass
    el.style.setProperty("--x", home.x);
    el.style.setProperty("--y", home.y);
  });

  const frame = desk.getBoundingClientRect();
  const base = icons.map((el) => {
    const r = el.getBoundingClientRect();
    return { left: r.left - frame.left, top: r.top - frame.top, w: r.width, h: r.height };
  });

  // On a narrow screen the grid has done its job; from here the icons
  // are objects again so they can be picked up.
  //
  // The WIDTH has to be pinned along with the position. The phone rules
  // give an icon `width: 100%`, which is the grid cell while it is laid
  // out by the grid — and the whole desk the moment it becomes absolute.
  // Without this the icons are correct on first paint and then fill the
  // screen as soon as this pass runs.
  if (narrowScreen()) {
    desk.classList.add("arranged");
    icons.forEach((el, i) => {
      const b = base[i];
      if (b !== undefined) el.style.width = `${b.w}px`;
    });
  }

  // --- 2 and 3. the visitor's choice, then the clamp -----------------
  const ceiling = barCeiling();
  const taken: { left: number; top: number; w: number; h: number }[] = [];

  icons.forEach((el, i) => {
    const b = base[i];
    if (b === undefined) return;
    const mine = byHand.get(el);
    const box = field(frame, ceiling, b.w, b.h);
    // The visitor's fraction read back at THIS size, or the base layout.
    // The clamp stays, but it is now the exception rather than the
    // mechanism: a fraction is already inside the field by construction,
    // so on an ordinary resize it changes nothing.
    let left = clamp(mine === undefined ? b.left : asPixels(mine.fx, box.x0, box.x1),
                     box.x0, box.x1);
    let top = clamp(mine === undefined ? b.top : asPixels(mine.fy, box.y0, box.y1),
                    box.y0, box.y1);

    // Two icons hanging off the same edge clamp to the same place and
    // end up stacked. Walk one clear of whatever is already there.
    let guard = 0;
    while (guard < 40 && taken.some((o) =>
      left < o.left + o.w && left + b.w > o.left &&
      top < o.top + o.h && top + b.h > o.top)) {
      top -= b.h * 0.55;
      if (top < ceiling) { top = ceiling; left = Math.max(0, left - b.w * 0.6); }
      guard += 1;
    }

    el.style.left = `${left}px`;
    el.style.top = `${top}px`;
    el.style.setProperty("--x", "auto");
    el.style.setProperty("--y", "auto");
    taken.push({ left, top, w: b.w, h: b.h });
  });
}

// Resizing, and turning a phone sideways, both land here.
let settling = 0;
const relayout = (): void => {
  window.clearTimeout(settling);
  settling = window.setTimeout(arrange, 120);
};
window.addEventListener("resize", relayout);
window.addEventListener("orientationchange", relayout);

// The authored position has to be captured BEFORE a drag can happen.
// arrange() captures it, but arrange() waits for images — so a drag in
// the first moments set `--x: auto`, and arrange() then recorded `auto`
// as the position the content file asked for. That icon could never go
// home again, for the life of the page.
document.querySelectorAll<HTMLElement>(".desk .icon").forEach(rememberAuthored);

// Only the icons ON the desk. The ones inside a folder window are a list,
// not objects on a surface: they have no authored position to go back to,
// and arrange() — which is what puts a dragged icon back where it belongs
// — only ever looks inside .desk. Made draggable, they could be dropped
// somewhere no pass would ever reclaim.
document.querySelectorAll<HTMLElement>(".desk .icon").forEach((el) => draggable(el, true));
document.querySelectorAll<HTMLElement>(".win").forEach((el) => draggable(el, false));

/** One handler per icon. Two separate listeners could not work: suppressing
 *  a click with preventDefault() stops an <a> navigating but does nothing to
 *  another listener on the same element, so a dragged `about me.txt` still
 *  opened its window. Deciding both outcomes in one place removes the
 *  ordering question entirely. */
document.querySelectorAll<HTMLElement>(".icon").forEach((icon) => {
  icon.addEventListener("click", (e: Event): void => {
    // `detail` is the click count, and it is 0 when the activation came
    // from the keyboard. A drag that ends in pointercancel leaves the
    // flag set with no click to clear it; the next pointerdown clears it,
    // but Enter is not a pointerdown — so without this test the first
    // Enter after an interrupted drag did nothing at all.
    const byPointer = !(e instanceof MouseEvent) || e.detail !== 0;
    if (byPointer && justDragged.has(icon)) {
      e.preventDefault();
      e.stopImmediatePropagation();
      justDragged.delete(icon);
      return;                       // it was moved, not opened
    }
    const id = icon.dataset["window"];
    if (id === undefined) return;   // an ordinary link: let it navigate
    e.preventDefault();
    const win = document.getElementById(id);
    if (win instanceof HTMLDialogElement) open_(win);
  });
});

// ---------------------------------------------------------------------
// Folder windows
//
// A folder opens as a window ON the desk, and the desk has to go on
// working underneath it: several folders open at once, all of them
// draggable, the icons behind them still live. That is show(), not
// showModal() — a modal dialog makes everything outside it inert, which
// would leave the second folder unopenable and the first undraggable.
//
// The cost is that everything a modal gets for free has to be done here
// by hand: the stacking order, the cascade so two windows do not land on
// the same pixel, raising one to the front, and Escape.
// ---------------------------------------------------------------------

const folders = (): HTMLDialogElement[] =>
  [...document.querySelectorAll<HTMLDialogElement>(".win-folder[open]")];

/** The one in front. Not the last in the DOM — the one with the highest
 *  z-index, because that is what the visitor sees on top after raising
 *  and dragging have reordered them. */
function front(): HTMLDialogElement | null {
  let best: HTMLDialogElement | null = null;
  let bestZ = -1;
  for (const w of folders()) {
    const z = Number(w.style.zIndex) || 0;
    if (z >= bestZ) { bestZ = z; best = w; }
  }
  return best;
}

// Its OWN counter, starting above the bandeau and the dock. topZ, which
// the drag handler uses, starts at 10 — fine for icons, which live inside
// .desk, and useless for a window, which is a sibling of it: at z-index
// 11 a folder window opens UNDER the bandeau and under the dock, both of
// which sit at 900.
let winZ = 1000;

function raise(win: HTMLElement): void {
  win.style.zIndex = String(++winZ);
}

function open_(win: HTMLDialogElement): void {
  if (!win.classList.contains("win-folder")) {
    win.showModal();                 // a film, the about text, the form
    return;
  }
  if (win.open) { raise(win); return; }   // already open — bring it forward

  // Cascade. Modulo, so the tenth window opened is not off the screen;
  // it lands back on the first step instead, which is what a real desk
  // did too.
  win.style.setProperty("--cascade", String(folders().length % 6));
  win.show();
  raise(win);

  // show() does not move focus the way showModal() does, so a keyboard
  // visitor would still be standing on the icon behind the window they
  // just opened.
  win.querySelector<HTMLElement>(".win-files .icon, .win-bar a, .win-bar button")?.focus();
}

// Clicking anywhere in a window brings it forward. The drag handler
// already does this when a window is picked up by its bar, but a click
// in the BODY bails out of that handler before it gets there — and a
// window you have to grab by the title bar to see all of is a window
// that feels broken.
document.querySelectorAll<HTMLDialogElement>(".win-folder").forEach((win) => {
  win.addEventListener("pointerdown", (): void => { if (win.open) raise(win); });
});

// Escape closes the front one. A modal dialog does this itself; a
// show()n one does not, so without this the only way out is the ✕.
document.addEventListener("keydown", (e: KeyboardEvent): void => {
  if (e.key !== "Escape") return;
  const win = front();
  if (win === null) return;
  // Not while a film or the contact form is open on top of it: those are
  // modal, the browser is already closing them on this same Escape, and
  // taking a folder window with it loses something the visitor did not
  // ask to lose. Their own dialog is the event's target; a folder
  // window's is not.
  const inside = e.target instanceof Element ? e.target.closest("dialog") : null;
  if (inside !== null && inside !== win) return;
  win.close();
});

/** A link to #something that turns out to be a <dialog> opens it.
 *
 *  A dialog is display:none until opened, so the browser's own anchor
 *  jump lands on an invisible element and nothing visible happens. The
 *  bandeau's `contact` link was exactly that on every page: the window
 *  existed, the id matched, a link checker would call it fine — and
 *  clicking it did nothing at all.
 *
 *  Written generally rather than for `contact`, so the next window added
 *  to the bandeau works without anyone remembering this. */
document.querySelectorAll<HTMLAnchorElement>('a[href^="#"]').forEach((link) => {
  const id = (link.getAttribute("href") ?? "").slice(1);
  if (id === "") return;                    // href="#" — an icon, handled above
  const target = document.getElementById(id);
  if (!(target instanceof HTMLDialogElement)) return;
  link.addEventListener("click", (e: Event): void => {
    e.preventDefault();
    if (!target.open) target.showModal();
  });
});

document.querySelectorAll<HTMLButtonElement>("[data-close]").forEach((b) => {
  b.addEventListener("click", (): void => b.closest("dialog")?.close());
});

// ---------------------------------------------------------------------
// Minimising a film
//
// Expanded it is modal, which is right while you are watching. Minimised
// it must NOT be: the whole point is that the bureau stays usable —
// folders draggable, other things openable — while it keeps playing.
//
// close() then show() swaps modality without ever detaching the <video>,
// so playback carries straight through. Removing and re-inserting the
// element, or setting a new src, would restart it.
// ---------------------------------------------------------------------

function shrink(win: HTMLDialogElement): void {
  if (win.classList.contains("is-mini")) return;
  win.classList.add("is-mini");
  win.close();                       // leaves the top layer, stops being modal
  win.show();                        // same element, same video, still playing

  // close() hands focus back to whatever opened the window, which for a
  // keyboard user is the icon out on the desk — so the button they just
  // pressed is suddenly several tabs away, and the way to restore the
  // film is somewhere behind them. Take it back: the button is still
  // there, it just means the opposite thing now.
  win.querySelector<HTMLButtonElement>("[data-mini]")?.focus();
}

/** The one button says what pressing it will do. */
function label(win: HTMLDialogElement): void {
  const b = win.querySelector<HTMLButtonElement>("[data-mini]");
  if (b === null) return;
  const mini = win.classList.contains("is-mini");
  b.textContent = mini ? "\u2b1c" : "\u2013";          // restore : minimise
  b.setAttribute("aria-label", say(mini ? "window_max" : "window_min"));
}

function grow(win: HTMLDialogElement): void {
  if (!win.classList.contains("is-mini")) return;
  win.classList.remove("is-mini");
  // a drag may have pinned it; give the centring back
  win.style.left = "";
  win.style.top = "";
  win.style.translate = "";
  win.close();
  win.showModal();
}

document.querySelectorAll<HTMLDialogElement>(".win-film").forEach((win) => {
  // One button, both directions. It was a minimise button that hid itself
  // once pressed, which left the only way back a click on the title bar —
  // and that never worked: a window drags by its bar, a drag captures the
  // pointer, and the capture retargets the click to the dialog. So the
  // handler on the bar could not fire, and the film was stuck small.
  //
  // A button is also simply clearer than a title bar you have to guess at.
  const toggle = win.querySelector<HTMLButtonElement>("[data-mini]");
  toggle?.addEventListener("click", (e: Event): void => {
    e.preventDefault();
    const mini = win.classList.contains("is-mini");
    if (mini) grow(win);
    else shrink(win);
    label(win);
  });

  // Keeping the title bar as a second way back, now bound where the click
  // actually lands — on the dialog, because of that same pointer capture.
  win.addEventListener("click", (e: Event): void => {
    if (!win.classList.contains("is-mini")) return;
    if (!(e instanceof MouseEvent) || e.detail !== 0) {
      if (justDragged.has(win)) { justDragged.delete(win); return; }
    }
    const t = e.target;
    // Same list the drag guard uses: anything that is itself a control
    // does its own thing, and does not also un-minimise the window.
    if (t instanceof Element && t.closest("button, a[href], video") !== null) return;
    grow(win);
    label(win);
  });

  // Closing it entirely should also stop the sound — but minimising
  // calls close() too, on its way to show(), and the close event is
  // queued rather than fired synchronously. So by the time this runs
  // after a minimise the dialog is already open again, and `open` tells
  // the two apart. Without this check, minimising stripped .is-mini and
  // paused the film: it looked exactly like the button did nothing.
  win.addEventListener("close", (): void => {
    if (win.open) return;              // it was a swap, not a close
    win.classList.remove("is-mini");
    label(win);                        // reopening starts expanded
    win.querySelector("video")?.pause();
  });
});

void whenPainted().then(reveal);
