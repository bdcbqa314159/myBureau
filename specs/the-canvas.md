# travail sélectionné is a canvas

**Status:** built. Signed off 2026-11-15 after the reference was
measured.
**Date:** 2026-11-15
**Reference:** her own `selected work`, measured:
`3840 × 14000`, one image, eight pictures, every one a different width,
two of them sharing a vertical band.

## What it is

**A folder that holds photographs itself, like pellicules.** The two are
the same object and differ in one thing — what their page does with the
photographs:

| | pellicules | travail sélectionné |
|---|---|---|
| holds | photographs | photographs |
| selected on the desk | add, remove, describe | **the same** |
| its page | a column flow — order, no coordinates | **a canvas — left, top, width per picture** |
| she arranges by | dragging to reorder | dragging to move, a corner to size |

Everything on the left of that table is already built and does not change.
This spec is the right-hand column.

## Why a canvas and not the three columns

The three columns were built from *"the three columns setting the limits
of expression"*. Her reference does not do that: the pictures sit at
eight different left edges, at eight different widths, and the hands
portrait runs alongside the BREAKFAST poster rather than under it. A
column grid cannot say that. **The reference wins over the earlier
sentence**, confirmed before building.

## Where the numbers live

```toml
[extra.shot]
"vue sur la mer.jpg" = { left = 28, top = 4, width = 62 }
```

One line per picture, keyed by file name — the shape `[extra.alt]` and
`[extra.place]` already use, written by the same `set_map_key`.

**All three are percentages of the PAGE WIDTH**, `top` included. The
whole composition then scales with the window and keeps its proportions,
which is what her reference does by being a single image. A `top` in
pixels would mean her composition only holds at one window size.

The canvas is as tall as the lowest picture reaches:
`H = max(top + width × its own height ÷ its own width)`, computed at
build time, and set as `aspect-ratio: 100 / H`. Each picture's `top`
converts to a percentage of that height in the template — stored against
the width so that moving ONE picture down does not renumber every other
one.

**Overlap is allowed.** She is a designer and the reference comes within
a hair of it. Document order decides what sits on top; there is no
z-index and no stacking to manage.

## The one place this leaves the reference

Her reference on a phone is her composition shrunk to 390px, because it
is one image — pictures 80px wide. **On the phone band the canvas
becomes one column**, each picture full width, in reading order (top,
then left). A portfolio whose work cannot be seen is not showing it.

## What goes

`travail sélectionné` is the only page in the tree with children, so the
road exists for it alone and nothing else can reach it:

- `templates/_place.html`, and both includes of it in `page.html`
- `.proj-route`, `.stop`, the `1,3,2,1,3` rhythm in `site.css`
- `[extra.column]`, and its validation
- the content-check case `three columns, and a picture in one`
- the five placeholders inside it — `nocturne 01/02`, `papier calque`,
  `vitrine d'hiver 01/02` — whose words are all *"Texte de présentation
  à venir"*. Their photographs become its photographs; the PDF
  placeholder goes, because this folder holds photographs

## Acceptance criteria

| # | criterion | oracle |
|---|---|---|
| 1 | it holds photographs, and the verb accepts one | `add_image` on it is not refused |
| 2 | a picture dropped on it is a photograph, never the icon | the icon stays the drawn folder after a drop |
| 3 | the panel shows its photographs when it is selected | the same pane pellicules gets |
| 4 | each picture carries a left, a top and a width | `[extra.shot]`, one line, keyed by file |
| 5 | the page puts them there | a build, with the three numbers read back off the rendered page |
| 6 | the composition keeps its proportions at any width | two builds at different widths put every picture at the same percentage |
| 7 | two pictures may share a vertical band | the reference's pair, rendered |
| 8 | the canvas is as tall as the lowest picture | nothing is cut off, no trailing void |
| 9 | she moves one by dragging it on the real page | the panel writes `place_shot` |
| 10 | she sizes one by its corner | the same verb, the width changing |
| 11 | nothing hangs off the right edge | `left + width ≤ 100`, clamped not refused |
| 12 | on a phone it is one column, full width, in reading order | the phone band |
| 13 | a photograph she has never placed still appears | it goes below the rest, full width |
| 14 | the road is gone, and nothing reaches for it | no template, no CSS, no key |

1–14 hold. The oracle for most of them is `content-check`'s
`travail sélectionné is a canvas`, which **builds** and reads the three
numbers back off the rendered page: what is in the front matter means
nothing until something puts a picture there.

## What would change this

- **She wants a picture behind another.** Then document order is not
  enough and `[extra.shot]` gains a fourth number. It is one key; the
  reason it is not there now is that nothing in the reference needs it.
- **She wants to crop.** This places and sizes whole photographs. A crop
  is a different tool and belongs in the one she already owns.
- **A second canvas.** Nothing here is about *this* folder except which
  template it carries, so the lever is a template, not a new object.

## What the building taught

**Tera cannot sort, so the phone order is counted.** The canvas is
absolutely positioned and the DOM is in zola's alphabetical order, which
is not the order a person reads the page. On the phone the pictures
become one column and that column has to run top to bottom — she drops
`09.jpg`, puts it at the top, and alphabetically it is last. Each
picture therefore carries a rank counted at build time against every
other picture's `top`, and the phone rule is `order: var(--o)`.

**The height has to be computed or there is no page.** The canvas's
children are all absolutely positioned, so the content flow gives the
box a height of nothing and every picture piles at the top. It carries
`aspect-ratio: 100 / H` where `H` is the lowest picture's reach,
measured in a first pass over the assets.

**`top` is divided by the width in the panel too.** A vertical drag of
`dy` pixels is `dy / canvas-width * 100`, not `dy / canvas-height * 100`
— the number stored is in width-percent. Using the height puts the
picture somewhere other than under her finger on any page that is not
square, and a check does exactly that drag.

**One sentence for two folders.** `une galerie ne montre que ses photos`
became `cette page ne montre que ses photos`: pellicules and travail
sélectionné refuse to be filed into for the same reason, and two
sentences would have drifted.

**The model had to learn it as well.** `can_receive` was `not gallery`,
so the panel went on offering travail sélectionné as a destination that
the server refuses — caught by the check that compares what the panel
offers with what the verb accepts.

**It is paper.** The first build gave it `bodyclass: selection`, which
no stylesheet has a rule for — so the body fell through to the default,
and the default is the desktop's dark ground. A white composition
arrived on black with her paragraph in white, under a bar it collided
with. It wears `project` now, like every other page: cream, ink, an ink
bar, and the scrim that keeps a line of text off the bandeau. Her words
sit inside `.proj`, which is where the padding that clears the bar
lives. Her own selected-work page is white, which settled it.

## The phone keeps the composition, not the coordinates

Her composition cannot survive 390px as it is — a picture at 28% of
that is 109px — and flattening every picture to the full width showed
the work and lost the composition: eight identical blocks, eight
identical gaps. His ask, 2026-11-15: *the aesthetics, this is the
essence — something less rigid, always displaying the essence, so one
can see, not select, and keep scrolling.*

So three things cross over and the coordinates do not:

| | |
|---|---|
| `--pw` | her width mapped into 70–100% of the column, scaled between the narrowest and widest she actually used — so her narrowest is still the narrowest and nothing is a sliver |
| `--pml` | which edge it hangs from, taken from where its **centre** sat. A wide picture starting at 20 is a middle picture, not a left one |
| `--pgap` | the pause above it, from the gap she left between it and the picture before. 0–30 of hers becomes 1.5–7rem |

**This reopened the 2026-11-14 decision**, where the client saw varying
widths on a phone and called them raggedness. What she was shown then
was widths alone, jittering, with nothing else moving — the page had no
composition for them to belong to. Reopened knowingly; if it reads as
raggedness again the lever is the phone block in `selection.html` and
the rule in `site.css`.

## zola is not deterministic about a bad image path

The neighbour scan was written without the language strip, so the
English page asked `get_image_metadata` for
`/en/travail-selectionne/01.jpg` — a path no file has. The suite
reported **eight to thirteen unrelated cases failing, differently on
every run**, none of them naming the cause. The same tree built six
times failed twice.

So no expectation that waits for a build can be trusted to catch this
class of bug. The rule is asserted at the source instead: **every loop
over a section's assets strips the language first**, counted across
every template. The two rank-counting loops read only leaf names and
could have been excused; they are not, because a rule with exceptions
is one nobody applies — and it was precisely the loop added next to
them that forgot.
