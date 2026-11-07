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

Each child of DA is **one stop on the road**. A stop keeps everything it
already is: its own name, its own alt text, its own page. It gains two
numbers, in the front matter it already has, beside `x` and `y`:

```toml
+++
title = "theodora 01.jpeg"

[extra]
x = 32          # where it sits on a DESK, untouched
y = 12
width = 62      # how wide on the ROAD, per cent of the road
offset = 0      # how far off the centre line, per cent, + is right
+++
```

| field | type | default | range |
|---|---|---|---|
| `width` | integer, per cent | `62` | 20–100 |
| `offset` | integer, per cent | `0` | −30 to 30 |

Rules the panel can rely on:

- **Both are optional.** A stop with neither declared is centred at the
  default width. Nothing has to be migrated for the road to render.
- **`x`/`y` and `width`/`offset` coexist and never interfere.** A thing
  has a position on a desk and a size on a road; moving it between the
  two does not lose either.
- **Order is filename order**, as everywhere else in this engine.
  Rearranging the road is renumbering, which the panel already does for
  photographs.
- **Both are written to every language file**, like `x`/`y`. A stop that
  is wide in French and narrow in English is a bug, not a feature.
- **Out of range is clamped, not refused.** A number she drags to is
  never an error.

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
