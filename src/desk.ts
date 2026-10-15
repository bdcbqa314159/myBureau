// Draggable desktop icons + window opening.
// ponytail: pointer events only, no drag library.

const clamp = (v: number, lo: number, hi: number): number =>
  Math.min(Math.max(v, lo), hi);

let topZ = 10;

function draggable(el: HTMLElement): void {
  el.addEventListener("pointerdown", (e: PointerEvent): void => {
    if (e.button !== 0) return;

    const surface = el.offsetParent;
    if (!(surface instanceof HTMLElement)) return;

    const start = el.getBoundingClientRect();
    const grabX = e.clientX - start.left;
    const grabY = e.clientY - start.top;
    let moved = false;

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
    };

    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerup", onUp, { once: true });
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
