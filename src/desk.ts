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

/** An element's resting position. Captured at the start of every drag, so a
 *  refused drop returns it to where it was a moment ago — not to wherever
 *  the content file first put it. Moving things around has to survive a
 *  refusal, or "you can move things" is not true. */
interface Spot { left: string; top: string; x: string; y: string }

const spotOf = (el: HTMLElement): Spot => ({
  left: el.style.left,
  top: el.style.top,
  x: el.style.getPropertyValue("--x"),
  y: el.style.getPropertyValue("--y"),
});

function restore(el: HTMLElement, spot: Spot): void {
  el.style.left = spot.left;
  el.style.top = spot.top;
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

    const surface = el.offsetParent;
    if (!(surface instanceof HTMLElement)) return;

    justDragged.delete(el);                   // a fresh press, a fresh verdict
    const back = spotOf(el);                  // where this drag started
    const start = el.getBoundingClientRect();
    const grabX = e.clientX - start.left;
    const grabY = e.clientY - start.top;
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
      moved = true;
      el.classList.add("dragging");

      const bounds = surface.getBoundingClientRect();
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
      }
      over?.el.classList.remove("rejecting");
      over = null;
    };

    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerup", onUp, { once: true });
    el.addEventListener("pointercancel", onUp, { once: true });
  });
}

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

document.querySelectorAll<HTMLButtonElement>("[data-close]").forEach((b) => {
  b.addEventListener("click", (): void => b.closest("dialog")?.close());
});
