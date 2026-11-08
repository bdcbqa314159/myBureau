# The phone

**Status:** phases 1–3 built. Phases 4 and 5 not started.
**Date:** 2026-11-08

The desktop version is the one that has had the attention. This records
what a narrow screen actually does today, what is wrong with it, and
the order the five pieces get fixed in — one pull request at a time,
never two at once.

## What was found

**Four breakpoints, no system.** `56rem`, `52rem`, `46rem`, `40rem`,
plus a `max-height: 30rem` guard for a phone lying down. None of them
named, none shared, each the result of an independent decision.

**A dead band at 640–832px** — every tablet and every landscape phone.
A *desk* is already in desktop mode there while every *page* is still
in two-column mode. Nobody chose that; it fell out of the four.

**`.desk` declares `height: 100dvh` and never declares `overflow`** —
at any width. Below `40rem` it becomes a three-column grid, which fits
roughly fifteen icons on a tall phone. Today's desks hold five or six.
The first icon that does not fit is simply unreachable, with nothing on
screen saying so, and it arrives by her adding work rather than by
anyone changing code.

**The metaphor is absent on a phone.** Below `40rem` her authored
positions are discarded and the desk becomes a tidy grid. The code is
honest about it — *"tidy because there is no room to be untidy"* — but
the thing the site IS does not exist on the device most visitors use.
That is a decision to take deliberately, not to inherit.

**Nothing checks any of it.** `desk-check.mjs` exercises five screens
including both phone orientations, but what it checks is GEOMETRY: that
a position written at one size means the same at another. Nothing
asserts an icon lands inside the desk, that nothing overflows, or that
a layout is usable.

**Surfaces with no narrow rule at all:** `about me.txt`'s sheet and its
four buttons, the contact dialog, and the full-width photographs on a
subfolder page.

## The five phases

| # | what | status |
|---|---|---|
| 1 | **One set of breakpoints.** Name the bands, collapse the strays, write down what each means. No visual change. | **built** |
| 2 | **A desk must never hide an icon.** `min-height` on the narrow desk so the grid can grow; `arrange()` pins that grown height before the icons become absolute. | **built** |
| 3 | **The desks.** Decided: the grid stays, and is made good. One stylesheet serves all three desks, so there was no per-desk work to do. | **built** |
| 4 | **The pages** — a subfolder's column, travail sélectionné's road, a project's pairs, pellicules' grid. | not started |
| 5 | **The windows** — the about sheet and its four buttons, contact, film, preview. A 1995 window with a bevelled toolbar at 390px is where this kind of design usually breaks. | not started |

Phase 2 before 3, because a silent failure with a growing trigger beats
tidiness. Phase 1 first anyway, because the other four are unreadable
without it.

## Phase 3, as built — and the decision behind it

**The metaphor does not survive on a phone, and that is chosen rather
than inherited.** Below 40rem her authored positions stay discarded and
the icons flow into a grid. Bernardo took that call on 2026-11-08: tidy
and predictable beats a desk nobody can arrange on a 390px screen.
Phase 3 therefore means making the grid good, not replacing it.

Two things were wrong with it:

**The bandeau's height was guessed.** `.bar` is `position: fixed`, so
the grid needs padding to clear it, and the stylesheet carried
`6.5rem` — a number from before the nav held five words and a language
switch. At 390px that nav wraps, and the script three files away was
already MEASURING the bar in `barCeiling()`. Two answers to one
question, and the guess was the one that could not know. The script now
publishes `--bar-h` and the stylesheet reads it; the fallback, for a
visitor with no script, is deliberately generous because a gap is a
blemish and being under the bar is work nobody can reach.

**The grid was always three columns.** Right at 390px, sparse at 639 —
the same band, icons stranded in cells twice the size of the picture
in them. `auto-fill` with a 6.5rem minimum keeps three on a phone and
gives five near the top of the band.

## Phase 2, as built, and what it corrected about the audit

The audit said icons below the fold were "positioned outside the desk
and unreachable". That was wrong about the half of it that has a
script: `arrange()` CLAMPS every icon into the rect it measures, so
nothing is ever placed outside. The two real failures were:

- **with no script**, the grid overflows a box pinned to one screen
  with no `overflow` — those icons genuinely cannot be reached
- **with one**, `.arranged` makes every child absolute, so the desk has
  nothing left to be tall for and drops back to one screen while
  holding icons below it

`min-height` fixes the first. `arrange()` pinning the measured grid
height before adding `.arranged` fixes the second.

## Phase 1, as built

Three width bands and one height band. Each is named, each has a reason
written beside it, and `a stylesheet with one set of breakpoints` in
content-check refuses a fifth.

| band | means |
|---|---|
| `56rem` | the top bar runs out of room for its secondary wordmark |
| `52rem` | **two columns become one** — pairs, the film's spread, the gallery, the road's pinning |
| `40rem` | **the desk stops being a surface** and becomes a list |
| `30rem` **height** | a phone lying down: the icons shrink |

The road's straightening moved from `46rem` to `52rem` — it is a
"two columns become one" decision wearing a different number, and it
was the only rule at that width.

`56rem` was NOT collapsed into `52rem`. It exists to stop a collision
in the top bar that I cannot see, and moving it would let the secondary
wordmark reappear in a band where it previously hid. Keeping a band
whose reason is known beats tidying one whose consequence is not.

## What would change this

- **The dead band gets a decision.** 640–832px is a desk in desktop
  mode beside pages in narrow mode. Phase 3 either picks a side or
  gives that band its own answer; this file only records that nobody
  has.
- **Phase 3 keeps the metaphor on a phone.** Then `40rem` stops meaning
  "becomes a list" and the whole table above is rewritten.
