// Desktop behaviour: pick icons up, drop them on folders, open windows.
// ponytail: pointer events and the Web Animations API. No drag library.

const clamp = (v: number, lo: number, hi: number): number =>
  Math.min(Math.max(v, lo), hi);

const calm = (): boolean =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let topZ = 10;

/** Where an icon rests when nothing is dragging it. Captured once, before
 *  the first drag overwrites the inline style. */
interface Home { left: string; top: string; x: string; y: string }

function rememberHome(el: HTMLElement): void {
  if (el.dataset["home"] !== undefined) return;
  const home: Home = {
    left: el.style.left,
    top: el.style.top,
    x: el.style.getPropertyValue("--x"),
    y: el.style.getPropertyValue("--y"),
  };
  el.dataset["home"] = JSON.stringify(home);
}

function goHome(el: HTMLElement): void {
  const raw = el.dataset["home"];
  if (raw === undefined) return;
  const home = JSON.parse(raw) as Home;
  el.style.left = home.left;
  el.style.top = home.top;
  el.style.setProperty("--x", home.x);
  el.style.setProperty("--y", home.y);
}

/** Refuse the drop. Moving an icon around a desktop is free — that is not
 *  a state change. Putting one thing INSIDE another is, and the site does
 *  not have that state to change: a project belongs to the desktop whose
 *  folder it sits in on disk. So the attempt is shown, and undone.
 *
 *  The icon falls into the folder, the folder shakes it off, the icon
 *  returns to where it lives. */
async function refuse(el: HTMLElement, folder: HTMLElement): Promise<void> {
  const from = el.getBoundingClientRect();
  const to = folder.getBoundingClientRect();
  const dx = to.left + to.width / 2 - (from.left + from.width / 2);
  const dy = to.top + to.height / 2 - (from.top + from.height / 2);

  el.classList.remove("dragging");
  folder.classList.remove("rejecting");

  if (calm()) {
    goHome(el);
    return;
  }

  // the folder shrugs it off — a refusal, not a gulp
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

  await el.animate(
    [
      { transform: "translate(0,0) scale(1)", opacity: 1 },
      { transform: `translate(${dx}px, ${dy}px) scale(.3)`, opacity: 0 },
    ],
    { duration: 170, easing: "cubic-bezier(.4,0,.8,.3)", fill: "forwards" },
  ).finished;

  goHome(el);

  await el.animate(
    [{ opacity: 0, transform: "scale(.9)" }, { opacity: 1, transform: "scale(1)" }],
    { duration: 220, easing: "cubic-bezier(.22,.61,.36,1)" },
  ).finished;
}

interface Target { el: HTMLElement; rect: DOMRect }

const hits = (r: DOMRect, x: number, y: number): boolean =>
  x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;

function draggable(el: HTMLElement): void {
  rememberHome(el);

  el.addEventListener("pointerdown", (e: PointerEvent): void => {
    if (e.button !== 0) return;

    const surface = el.offsetParent;
    if (!(surface instanceof HTMLElement)) return;

    const start = el.getBoundingClientRect();
    const grabX = e.clientX - start.left;
    const grabY = e.clientY - start.top;
    let moved = false;
    let over: Target | null = null;

    // folders do not move mid-drag, so measure them once
    const targets: Target[] = [...document.querySelectorAll<HTMLElement>(".icon[data-folder]")]
      .filter((f) => f !== el)
      .map((f) => ({ el: f, rect: f.getBoundingClientRect() }));

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
        // the cursor says no before the drop does
        el.classList.toggle("barred", next !== null);
        over = next;
      }
    };

    const onUp = (ev: PointerEvent): void => {
      el.removeEventListener("pointermove", onMove);
      el.releasePointerCapture(ev.pointerId);
      el.classList.remove("dragging");

      // a drag must not also fire the click that follows it
      if (moved) {
        el.addEventListener("click", (c: Event) => c.preventDefault(), {
          once: true,
          capture: true,
        });
      }

      el.classList.remove("barred");
      if (moved && over !== null) {
        void refuse(el, over.el);
      }
      over?.el.classList.remove("rejecting");
      over = null;
    };

    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerup", onUp, { once: true });
    el.addEventListener("pointercancel", onUp, { once: true });
  });
}

document.querySelectorAll<HTMLElement>(".icon, .win").forEach(draggable);

// icons carrying data-window open a <dialog> instead of navigating
document.querySelectorAll<HTMLAnchorElement>(".icon[data-window]").forEach((icon) => {
  icon.addEventListener("click", (e: Event): void => {
    e.preventDefault();
    const id = icon.dataset["window"];
    if (id === undefined) return;
    const win = document.getElementById(id);
    if (win instanceof HTMLDialogElement) win.showModal();
  });
});

document.querySelectorAll<HTMLButtonElement>("[data-close]").forEach((b) => {
  b.addEventListener("click", (): void => b.closest("dialog")?.close());
});
