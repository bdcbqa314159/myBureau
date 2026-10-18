// Desktop behaviour: move things freely, refuse to nest them, open windows.
// ponytail: pointer events and the Web Animations API. No drag library.

const clamp = (v: number, lo: number, hi: number): number =>
  Math.min(Math.max(v, lo), hi);

const calm = (): boolean =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let topZ = 10;

/** Things dragged since their last pointerdown. A drag must never also
 *  count as a click — dropping `about me.txt` somewhere moves it, it does
 *  not open it. */
const justDragged = new WeakSet<HTMLElement>();

// ---------------------------------------------------------------------
// Leaving a bureau and coming back
//
// Where you left things is remembered for the session, per bureau. On
// return the icons are put back exactly where you dropped them, then
// walked home — so the reset is something you watch happen rather than
// something that already happened before the page appeared.
// ---------------------------------------------------------------------

const DESK_KEY = `bureau:${location.pathname}`;

type Layout = Record<string, { left: string; top: string }>;

function readLayout(): Layout {
  try {
    const raw = sessionStorage.getItem(DESK_KEY);
    return raw === null ? {} : (JSON.parse(raw) as Layout);
  } catch {
    return {};                       // private mode, quota, corrupt entry
  }
}

function saveLayout(): void {
  const out: Layout = {};
  document.querySelectorAll<HTMLElement>(".desk .icon").forEach((el) => {
    const key = el.dataset["vt"];
    if (key === undefined || el.style.left === "") return;   // never moved
    out[key] = { left: el.style.left, top: el.style.top };
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
function reveal(): void {
  fadeInLateArrivals();
  const loader = document.querySelector<HTMLElement>(".loader");
  if (loader === null) {
    tidyUp();
    keepOnScreen();
    return;
  }
  // keep it painted while .booting goes away, then take it out entirely
  loader.classList.add("is-leaving");
  tidyUp();
  keepOnScreen();        // a remembered spot may not fit this window
  if (calm()) {
    loader.remove();
    return;
  }
  void loader
    .animate([{ opacity: 1 }, { opacity: 0 }], {
      duration: 420, easing: "cubic-bezier(.4,0,.6,1)", fill: "forwards",
    })
    .finished.then(() => loader.remove());
}

/** Put everything back, visibly. FLIP: place each icon where it was left,
 *  measure, restore its real position, measure again, then animate the
 *  difference away. The icon never actually sits anywhere wrong — only the
 *  transform moves, so layout is correct from the first frame. */
function tidyUp(): void {
  const icons = [...document.querySelectorAll<HTMLElement>(".desk .icon")];
  const left = readLayout();
  try { sessionStorage.removeItem(DESK_KEY); } catch { /* private mode */ }

  const quiet = calm();
  let staggered = 0;

  icons.forEach((el) => {
    const key = el.dataset["vt"];
    const was = key === undefined ? undefined : left[key];

    if (was === undefined) {
      // never moved: a soft arrival, slightly staggered
      if (!quiet) {
        el.animate(
          [{ opacity: 0, transform: "scale(.96)" }, { opacity: 1, transform: "scale(1)" }],
          { duration: 420, delay: staggered * 35, easing: "cubic-bezier(.22,.61,.36,1)", fill: "backwards" },
        );
        staggered += 1;
      }
      return;
    }

    if (quiet) return;               // reduced motion: it is simply home

    el.style.left = was.left;        // F — where you left it
    el.style.top = was.top;
    const from = el.getBoundingClientRect();

    el.style.left = "";              // L — where it belongs
    el.style.top = "";
    const home = el.getBoundingClientRect();

    const dx = from.left - home.left;
    const dy = from.top - home.top;
    if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return;

    el.animate(                      // I + P — play the difference away
      [
        { transform: `translate(${dx}px, ${dy}px)`, opacity: .85 },
        { transform: "translate(0, 0)", opacity: 1 },
      ],
      { duration: 620, delay: staggered * 45, easing: "cubic-bezier(.33,.9,.3,1)", fill: "backwards" },
    );
    staggered += 1;
  });

  document.documentElement.classList.remove("booting");
}

/** An element's resting position. Captured at the start of every drag, so a
 *  refused drop returns it to where it was a moment ago — not to wherever
 *  the content file first put it. Moving things around has to survive a
 *  refusal, or "you can move things" is not true. */
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
      el.removeEventListener("pointermove", onMove);
      el.releasePointerCapture(ev.pointerId);
      el.classList.remove("dragging", "barred");

      if (moved) justDragged.add(el);

      if (moved && over !== null) {
        void refuse(el, over.el, back);
      } else if (moved) {
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

/** On a narrow screen the desk is laid out as a grid, because positions
 *  composed for a wide screen collide at 390px. Measure where the grid put
 *  everything, pin those positions as absolute, and the icons stop being
 *  laid out and start being objects again — pickable exactly as on a
 *  desktop, from a tidy starting arrangement rather than a scatter.
 *
 *  Nothing moves on screen: the positions written are the ones just
 *  measured. Without JavaScript the grid simply stays a grid, which is a
 *  perfectly good fallback.
 *
 *  A bureau does not scroll, so there is nothing for a drag to fight and
 *  no need to make anyone hold their finger down to pick something up. */
function pinTheGrid(): void {
  if (window.matchMedia("(min-width: 40rem)").matches) return;
  const desk = document.querySelector<HTMLElement>(".desk");
  if (desk === null || desk.classList.contains("arranged")) return;

  const icons = [...desk.querySelectorAll<HTMLElement>(".icon")];
  const frame = desk.getBoundingClientRect();
  const spots = icons.map((el) => {
    const r = el.getBoundingClientRect();
    return { left: r.left - frame.left, top: r.top - frame.top, width: r.width };
  });

  desk.classList.add("arranged");
  icons.forEach((el, i) => {
    const s = spots[i];
    if (s === undefined) return;
    el.style.left = `${s.left}px`;
    el.style.top = `${s.top}px`;
    el.style.width = `${s.width}px`;
  });
}

/** Nudge anything that is hanging off the desk back onto it.
 *
 *  Positions are percentages of the desk, but an icon is a fixed number
 *  of pixels wide. At 1440px an icon is about 11% of the width and
 *  `x = 82%` sits comfortably inside; at 820px the same icon is 18% wide
 *  and its right edge lands at 101% — half on, half off. The same applies
 *  vertically, and the bandeau is fixed on top, so an icon high on a
 *  short window disappears underneath it.
 *
 *  The drag already clamps to the desk. Initial placement never did, and
 *  neither did a window being resized afterwards.
 *
 *  Only ever moves things that are actually out of bounds, so a deliberate
 *  arrangement is left exactly where it was put. */
function keepOnScreen(): void {
  const desk = document.querySelector<HTMLElement>(".desk");
  if (desk === null) return;
  const frame = desk.getBoundingClientRect();
  const bar = document.querySelector<HTMLElement>(".bar");
  const ceiling = bar === null ? 0 : bar.getBoundingClientRect().height + 8;

  const taken: { left: number; top: number; w: number; h: number }[] = [];

  desk.querySelectorAll<HTMLElement>(".icon").forEach((el) => {
    const r = el.getBoundingClientRect();
    const was = { left: r.left - frame.left, top: r.top - frame.top };
    let left = clamp(was.left, 0, Math.max(0, frame.width - r.width));
    let top = clamp(was.top, ceiling, Math.max(ceiling, frame.height - r.height));
    const moved = Math.abs(left - was.left) > 0.5 || Math.abs(top - was.top) > 0.5;

    if (moved) {
      // Two icons hanging off the same edge both clamp to the same place
      // and end up stacked. Walk one up until it is clear of whatever is
      // already there — a tidied icon must still be a separate object.
      let guard = 0;
      while (guard < 40 && taken.some((o) =>
        left < o.left + o.w && left + r.width > o.left &&
        top < o.top + o.h && top + r.height > o.top)) {
        top -= r.height * 0.55;
        if (top < ceiling) { top = ceiling; left = Math.max(0, left - r.width * 0.6); }
        guard += 1;
      }
      el.style.left = `${left}px`;
      el.style.top = `${top}px`;
      el.style.setProperty("--x", "auto");
      el.style.setProperty("--y", "auto");
    }
    taken.push({ left, top, w: r.width, h: r.height });
  });
}

pinTheGrid();
// NOT here: at script time no icon image has loaded, so every icon
// measures almost no height and the clamp moves things that were fine.
// It runs from reveal(), once whenPainted() says the pictures are in.

// A window that was wide enough a moment ago may not be any more.
let settling = 0;
window.addEventListener("resize", (): void => {
  window.clearTimeout(settling);
  settling = window.setTimeout(keepOnScreen, 120);
});

document.querySelectorAll<HTMLElement>(".icon").forEach((el) => draggable(el, true));
document.querySelectorAll<HTMLElement>(".win").forEach((el) => draggable(el, false));

/** One handler per icon. Two separate listeners could not work: suppressing
 *  a click with preventDefault() stops an <a> navigating but does nothing to
 *  another listener on the same element, so a dragged `about me.txt` still
 *  opened its window. Deciding both outcomes in one place removes the
 *  ordering question entirely. */
document.querySelectorAll<HTMLElement>(".icon").forEach((icon) => {
  icon.addEventListener("click", (e: Event): void => {
    if (justDragged.has(icon)) {
      e.preventDefault();
      e.stopImmediatePropagation();
      justDragged.delete(icon);
      return;                       // it was moved, not opened
    }
    const id = icon.dataset["window"];
    if (id === undefined) return;   // an ordinary link: let it navigate
    e.preventDefault();
    const win = document.getElementById(id);
    if (win instanceof HTMLDialogElement) win.showModal();
  });
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
}

/** The one button says what pressing it will do. */
function label(win: HTMLDialogElement): void {
  const b = win.querySelector<HTMLButtonElement>("[data-mini]");
  if (b === null) return;
  const mini = win.classList.contains("is-mini");
  b.textContent = mini ? "\u2b1c" : "\u2013";          // restore : minimise
  b.setAttribute("aria-label", mini ? "Agrandir" : "Réduire");
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
    if (justDragged.has(win)) { justDragged.delete(win); return; }
    const t = e.target;
    if (t instanceof Element && t.closest("button, video") !== null) return;
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
