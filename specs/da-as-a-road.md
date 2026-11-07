# DA as a road

**Status:** proposed, not built. Governs branch 3 of four.
**Date:** 2026-11-07

## The decision

`DA` stops being a desk. It becomes a page: her pictures down a single
vertical line, varying in width, scrolled continuously. Clicking one
opens it large.

This is a redirection away from the brief, which asked for *"les
dossiers comme DA ouvre une nouvelle page, comme un nouveau bureau"* —
a second desk. It follows the client's own portfolio, where a page is a
vertical stack of image modules rather than a grid.

The home desk is still a desk. DA is the exception, declared, not a new
default.

## The data model — the part the panel reads and writes

Each **photograph** is one stop on the road — not each child. A folder
holding nine photographs puts nine stops on it, and all nine lead to
that folder.

A stop takes two numbers, declared **per file** in the front matter of
the folder that holds it. This is the shape `[extra.alt]` already uses,
so there is one convention rather than two:

```toml
+++
title = "Atelier Mirabelle"
template = "page.html"

[extra.width]
"02.jpg" = 72        # per cent of the page
"05.jpg" = 24

[extra.offset]
"02.jpg" = 8         # per cent off the centre line, + is right
"05.jpg" = -26
+++
```

| field | type | default | range |
|---|---|---|---|
| `width` | integer, per cent | from the rhythm | 20–100 |
| `offset` | integer, per cent | from the rhythm | −30 to 30 |

Rules the panel can rely on:

- **Both are optional, and both are per file.** A photograph nobody has
  touched takes its place from a repeating five-step rhythm in the
  stylesheet, so an unarranged folder still reads as pinned rather than
  stacked in a column. Nothing has to be migrated.
- **They never interfere with `x`/`y`.** A thing has a position on a
  desk and its photographs have places on a road; moving between the
  two loses neither.
- **Order is filename order**, as everywhere else. Rearranging is
  renumbering, which the panel already does for photographs.
- **Written to every language file**, like `x`/`y`. A photograph wide
  in French and narrow in English is a bug.
- **Out of range is clamped, not refused.** A number she drags to is
  never an error.
- **Below 46rem the road straightens**: every stop full width, no
  offset, no rotation. The pinning is a wide-screen idea — a picture at
  24 per cent of a phone is a stamp.

## Acceptance criteria

| # | criterion | oracle |
|---|---|---|
| 1 | DA renders as a page, not a desk | no `<main class="desk">`, no wallpaper |
| 2 | every child is a stop, in filename order | count and order asserted against the tree |
| 3 | a stop with no `width` is centred at the default | rendered style carries the default |
| 4 | `width` changes how wide a stop sits | two stops, two widths, two rendered values |
| 5 | `offset` moves a stop off the centre line | asserted both directions |
| 6 | a folder shows its cover, a film its poster | each kind reaches the road |
| 7 | clicking a stop opens it large | the existing frameless preview |
| 8 | it works with no JavaScript | every stop is a plain link to its page |
| 9 | out-of-range values are clamped | 400 renders as 100, not as 400 |

## Out of scope, deliberately

- **Scroll-snap.** The reference scrolls continuously; snapping is a
  different feel and was not asked for.
- **Arbitrary x/y on the road.** A road is one line. Free placement is
  the desk's job, and DA stops being a desk.
- **Dragging stops in the panel.** That is branch 4. This branch writes
  the numbers by hand so the model can be judged before it is wired.
- **The other first-class folders.** They become plain pages in branch
  2, not roads.

## What would change this

- **She wants more than one road.** Then `template = "road.html"`
  becomes the switch and DA stops being special — the model does not
  change, only which folders use it.
- **She wants stops side by side.** Then it is not a road, and `offset`
  is the wrong model; a span-based grid would replace both fields.
- **Width per screen size.** One number cannot say "wide on a laptop,
  full width on a phone". If that is needed, `width` becomes a maximum
  and the phone always shows full width.
